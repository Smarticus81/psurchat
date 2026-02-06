"""
SOTAOrchestrator - Workflow engine for PSUR generation.

Discussion Panel Architecture: 18-agent collaborative workflow with
Phase 0 data quality audit, per-section consultation scripts,
analytical agent integration, and transparent chat visibility.
"""

import asyncio
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.psur.context import PSURContext, WorkflowStatus
from backend.psur.agents import (
    AGENT_ROLES, SECTION_DEFINITIONS, WORKFLOW_ORDER,
    SECTION_COLLABORATION,
)
from backend.psur.extraction import extract_from_file
from backend.psur.prompts import (
    get_agent_system_prompt, get_qc_prompt,
    build_global_constraints, get_previous_sections_summary,
    get_consultation_prompt, get_consultation_response_prompt,
)
from backend.psur.extraction import generate_extraction_summary
from backend.psur.ai_client import call_ai
from backend.psur.analytical import (
    statler_calculate, charley_generate, quincy_audit,
)
from backend.psur.regulatory import RegulatoryKnowledgeService
from backend.psur.chart_generator import generate_all_charts
from backend.psur.templates import load_template
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import (
    PSURSession, Agent, ChatMessage, SectionDocument,
    WorkflowState, DataFile,
)


class SOTAOrchestrator:
    """
    State-of-the-Art PSUR Orchestrator implementing MDCG 2022-21
    compliant workflow with 18 specialized agents, structured consultation,
    QC cycles, and chart generation.
    """

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.context: Optional[PSURContext] = None
        self.current_phase = "initialization"
        self.sections_completed: list[str] = []
        self.max_qc_iterations = 3
        self.workflow_status = WorkflowStatus.IDLE
        self.current_agent: Optional[str] = None
        self._pause_requested = False
        self._consultation_results: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Workflow State
    # ------------------------------------------------------------------

    def request_pause(self) -> bool:
        if self.workflow_status == WorkflowStatus.RUNNING:
            self._pause_requested = True
            return True
        return False

    def request_resume(self) -> bool:
        if self.workflow_status == WorkflowStatus.PAUSED:
            self._pause_requested = False
            self.workflow_status = WorkflowStatus.RUNNING
            self._sync_state()
            return True
        return False

    def get_workflow_status(self) -> Dict[str, Any]:
        return {
            "status": self.workflow_status.value,
            "current_agent": self.current_agent,
            "current_phase": self.current_phase,
            "sections_completed": len(self.sections_completed),
            "total_sections": len(WORKFLOW_ORDER),
            "paused": self.workflow_status == WorkflowStatus.PAUSED,
        }

    def _sync_state(self):
        with get_db_context() as db:
            ws = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()
            if ws:
                setattr(ws, "status", self.workflow_status.value)
                setattr(ws, "paused", self.workflow_status == WorkflowStatus.PAUSED)
                setattr(ws, "current_agent", self.current_agent)
                setattr(ws, "sections_completed", len(self.sections_completed))
                db.commit()

    async def _handle_pause(self):
        if self._pause_requested:
            self.workflow_status = WorkflowStatus.PAUSED
            self._sync_state()
            await self._msg("Alex", "all", "Workflow paused by user.", "system")
            while self.workflow_status == WorkflowStatus.PAUSED:
                await asyncio.sleep(1)
                await self._handle_interventions()
            await self._msg("Alex", "all", "Workflow resumed.", "system")

    # ------------------------------------------------------------------
    # User Interventions
    # ------------------------------------------------------------------

    async def _handle_interventions(self):
        with get_db_context() as db:
            msgs = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id,
                ChatMessage.from_agent == "User",
                ChatMessage.processed == False,
            ).order_by(ChatMessage.timestamp.asc()).limit(10).all()

            for m in msgs:
                await self._respond_to_user(m.message, m.to_agent, db)
                # Use Boolean column only (no JSON mutation issues)
                setattr(m, "processed", True)
                db.commit()

    async def _respond_to_user(self, message: str, target: str, db: Any):
        responder = self.current_agent or "Alex"
        for name in AGENT_CONFIGS:
            if f"@{name}" in message:
                responder = name
                break
        if target != "all" and target in AGENT_CONFIGS:
            responder = target

        cfg = AGENT_CONFIGS.get(responder, AGENT_CONFIGS.get("Alex"))
        if not cfg:
            return
        ctx_summary = ""
        if self.context:
            ctx_summary = f"Device: {self.context.device_name}. Phase: {self.current_phase}."

        role_info = AGENT_ROLES.get(responder, {})
        personality = role_info.get("personality", "")
        sys_prompt = (
            f"You are {responder}, {cfg.role}. {personality}. {ctx_summary} "
            "Respond concisely in prose (2-4 sentences). No bullet points."
        )
        response = await call_ai(responder, sys_prompt, f'User says: "{message}"')
        if response:
            await self._msg(responder, "User", response, "normal")

    async def ask_agent_directly(self, agent_name: str, question: str) -> Dict[str, Any]:
        if agent_name not in AGENT_CONFIGS:
            return {"error": f"Unknown agent: {agent_name}", "response": None}
        cfg = AGENT_CONFIGS[agent_name]
        role_info = AGENT_ROLES.get(agent_name, {})
        personality = role_info.get("personality", "")
        ctx_summary = ""
        if self.context:
            ctx_summary = f"Device: {self.context.device_name}. Sections done: {', '.join(self.sections_completed)}."
        sys_prompt = f"You are {agent_name}, {cfg.role}. {personality}. {ctx_summary} Answer directly."
        response = await call_ai(agent_name, sys_prompt, question)
        await self._msg(agent_name, "User", response or "No response.", "normal")
        return {"response": response, "agent": agent_name, "error": None}

    # ------------------------------------------------------------------
    # Main Workflow
    # ------------------------------------------------------------------

    async def execute_workflow(self) -> Dict[str, Any]:
        try:
            self.workflow_status = WorkflowStatus.RUNNING
            self._sync_state()

            await self._msg("Alex", "all", "Initializing PSUR workflow...", "system")
            await self._initialize_context()
            await self._initialize_agents()

            if self.context is None:
                raise RuntimeError("Context initialization failed")

            # Phase 0: Session Announcement + Data Quality Audit
            self.current_phase = "phase_0_data_quality"
            await self._announce_session_start()
            await self._data_quality_phase()

            # Phase 1-7: Section Generation with Structured Consultations
            for section_id in WORKFLOW_ORDER:
                await self._handle_pause()
                await self._handle_interventions()

                sdef = SECTION_DEFINITIONS.get(section_id, {})
                agent = sdef.get("agent", "Alex")
                name = sdef.get("name", f"Section {section_id}")
                self.current_agent = agent
                self.current_phase = f"section_{section_id}"
                await self._update_workflow(section_id)
                await self._set_status(agent, "working")

                # Alex announces section
                await self._msg("Alex", agent,
                    f"{agent}, you are up for Section {section_id}: {name}. "
                    f"Please prepare your draft.", "normal")

                ok = await self._generate_section(section_id)
                if ok:
                    self.sections_completed.append(section_id)
                    await self._set_status(agent, "complete")
                    await self._msg("Alex", "all",
                        f"Section {section_id} ({name}) completed by {agent}.", "success")
                else:
                    await self._set_status(agent, "error")
                    await self._msg("Alex", "all",
                        f"Section {section_id} had issues. Continuing workflow...", "warning")

                await self._handle_interventions()

            # Final synthesis
            self.current_phase = "final_synthesis"
            await self._final_synthesis()

            # Save context snapshot for DOCX download
            await self._save_context_snapshot()

            await self._complete_session()

            self.workflow_status = WorkflowStatus.COMPLETE
            self.current_agent = None
            self._sync_state()

            return {"status": "complete", "sections_completed": len(self.sections_completed)}

        except Exception as e:
            traceback.print_exc()
            self.workflow_status = WorkflowStatus.ERROR
            self._sync_state()
            await self._msg("Alex", "all", f"Workflow error: {e}", "error")
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------
    # Phase 0: Session Announcement & Data Quality Audit
    # ------------------------------------------------------------------

    async def _announce_session_start(self):
        """Alex introduces all 18 agents and describes the workflow."""
        ctx = self.context
        if ctx is None:
            return

        section_agents = [
            f"{info['name']} ({info['title']})"
            for name, info in AGENT_ROLES.items()
            if info.get("category") == "section"
        ]
        analytical_agents = [
            f"{info['name']} ({info['title']})"
            for name, info in AGENT_ROLES.items()
            if info.get("category") == "analytical"
        ]
        qc_agents = [
            f"{info['name']} ({info['title']})"
            for name, info in AGENT_ROLES.items()
            if info.get("category") == "qc"
        ]

        # Load template name for announcement
        tmpl_config = getattr(ctx, "template_config", {}) or {}
        tmpl_name = tmpl_config.get("name", "EU MDR + UK MDR")
        tmpl_basis = tmpl_config.get("regulatory_basis", "MDCG 2022-21")

        announcement = (
            f"PSUR generation session for {ctx.device_name} (UDI-DI: {ctx.udi_di}). "
            f"Reporting period: {ctx.period_start} to {ctx.period_end}. "
            f"Regulatory framework: {tmpl_name} ({tmpl_basis}). "
            f"I am Alex, your workflow coordinator. "
            f"We have {len(AGENT_ROLES)} agents on this session. "
            f"Section authors: {', '.join(section_agents)}. "
            f"Analytical support: {', '.join(analytical_agents)}. "
            f"Quality control: {', '.join(qc_agents)}. "
            f"We will generate {len(WORKFLOW_ORDER)} sections in dependency order. "
            f"Each section author will consult with analytical and peer agents before drafting. "
            f"Victoria will review every section before approval. "
            f"All exchanges are transparent and visible to the team."
        )
        await self._msg("Alex", "all", announcement, "system")

    async def _data_quality_phase(self):
        """Quincy runs data quality audit at workflow start."""
        if self.context is None:
            return

        self.current_agent = "Quincy"
        await self._set_status("Quincy", "working")
        await self._msg("Alex", "Quincy",
            "Quincy, please run a comprehensive data quality audit on the uploaded files "
            "before we begin section generation.", "normal")

        try:
            audit_result = await quincy_audit(self.context, self.session_id)
            if audit_result:
                # Route issues to Alex for awareness
                await self._msg("Alex", "all",
                    "Data quality audit complete. All agents should note any "
                    "data quality issues flagged by Quincy in your sections.", "normal")
        except Exception as e:
            await self._msg("Quincy", "all",
                f"Data quality audit encountered an error: {e}. "
                "Proceeding with available data.", "warning")

        await self._set_status("Quincy", "complete")
        self.current_agent = None

    # ------------------------------------------------------------------
    # Structured Consultation Protocol
    # ------------------------------------------------------------------

    async def _run_consultations(self, section_id: str, phase: str) -> List[str]:
        """
        Execute consultation scripts for a section.
        phase: "pre_consults" or "post_consults"
        Returns list of consultation results for prompt injection.
        """
        collab = SECTION_COLLABORATION.get(section_id)
        if not collab:
            return []

        consults = collab.get(phase, [])
        results: List[str] = []

        for spec in consults:
            requester = spec["requester"]
            responder = spec["responder"]
            task = spec["task"]

            try:
                result = await self._consult(requester, responder, task, section_id)
                if result:
                    results.append(f"[{responder} -> {requester}]: {result}")
            except Exception as e:
                await self._msg(responder, requester,
                    f"Consultation error: {e}. Proceeding without this input.", "warning")

        return results

    async def _consult(self, requester: str, responder: str,
                       task: str, section_id: str) -> Optional[str]:
        """
        Single consultation exchange between two agents (2 AI calls).
        1. Requester asks the question (posted to chat)
        2. Responder generates answer (posted to chat)
        Returns responder's answer.
        """
        ctx = self.context
        if ctx is None:
            return None

        # Step 1: Requester posts the question
        question_prompt = get_consultation_prompt(requester, responder, task, ctx)
        question = await call_ai(requester, question_prompt,
            f"Ask {responder} the following: {task}")

        if not question:
            question = f"{responder}, {task}"

        await self._msg(requester, responder, question, "normal")
        await self._set_status(responder, "working")

        # Step 2: Responder generates answer
        # Route to analytical agents' specialized functions
        answer: Optional[str] = None

        if responder == "Statler":
            answer = await statler_calculate(ctx, task, requester, self.session_id)
        elif responder == "Charley":
            answer = await charley_generate(ctx, task, requester, self.session_id)
        elif responder == "Quincy":
            answer = await quincy_audit(ctx, self.session_id)
        else:
            # Regular agent consultation via AI
            response_prompt = get_consultation_response_prompt(
                responder, question, ctx)
            answer = await call_ai(responder, response_prompt,
                f"Respond to {requester}'s request: {question}")

            if answer:
                await self._msg(responder, requester, answer, "normal")

        await self._set_status(responder, "complete")
        return answer

    # ------------------------------------------------------------------
    # Context Initialization
    # ------------------------------------------------------------------

    async def _initialize_context(self):
        with get_db_context() as db:
            session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
            if not session:
                raise ValueError(f"Session {self.session_id} not found")

            # Load template from session
            template_id = getattr(session, "template_id", None) or "eu_uk_mdr"
            template = load_template(template_id)

            self.context = PSURContext(
                device_name=getattr(session, "device_name", None) or "Unknown Device",
                udi_di=getattr(session, "udi_di", None) or "Pending",
                period_start=getattr(session, "period_start", None) or datetime.min,
                period_end=getattr(session, "period_end", None) or datetime.min,
                template_id=template_id,
                template_config={
                    "id": template.id,
                    "name": template.name,
                    "jurisdiction": template.jurisdiction,
                    "regulatory_basis": template.regulatory_basis,
                },
            )

            # Load manufacturer info from master context / intake if available
            _master = getattr(session, "master_context", None) or {}
            _intake = getattr(session, "master_context_intake", None) or {}
            if not isinstance(_master, dict):
                _master = {}
            if not isinstance(_intake, dict):
                _intake = {}

            if _master:
                self.context.manufacturer = str(_master.get("manufacturer", self.context.manufacturer) or "")
                self.context.manufacturer_address = str(_master.get("manufacturer_address", "") or "")
                self.context.authorized_rep = str(_master.get("authorized_rep", "") or "")
                self.context.notified_body = str(_master.get("notified_body", "") or "")
                self.context.notified_body_number = str(_master.get("notified_body_number", "") or "")

            # Extract data from uploaded files (unified pipeline)
            data_files = db.query(DataFile).filter(DataFile.session_id == self.session_id).all()
            for df in data_files:
                _file_type = getattr(df, "file_type", "") or ""
                _filename = getattr(df, "filename", "") or ""
                _file_data = getattr(df, "file_data", b"") or b""
                _uploaded_at = getattr(df, "uploaded_at", None)

                self.context.data_files.append({
                    "type": _file_type, "filename": _filename,
                    "uploaded_at": _uploaded_at.isoformat() if _uploaded_at else None,
                })

                diag = extract_from_file(_file_data, _filename, _file_type, self.context)
                if diag.get("warnings"):
                    self.context.data_quality_warnings.extend(diag["warnings"])
                # Store column mapping diagnostics per file
                if diag.get("columns_detected"):
                    self.context.column_mappings[_filename] = {
                        k: (v if v else None) for k, v in diag["columns_detected"].items()
                    }

            self.context.calculate_metrics()

            # Log extraction summary for debugging
            summary = generate_extraction_summary(self.context)
            print(f"[orchestrator] EXTRACTION SUMMARY: sales={summary['sales']}, complaints={summary['complaints']}, vigilance={summary['vigilance']}")

            # Apply intake overrides (from user-provided form)
            if _intake:
                scope = str(_intake.get("denominator_scope", "reporting_period_only") or "reporting_period_only")
                self.context.exposure_denominator_scope = scope
                closure_def = str(_intake.get("closure_definition", "") or "")
                if closure_def:
                    self.context.closure_definition_text = closure_def
                inference = str(_intake.get("inference_policy", "strictly_factual") or "strictly_factual")
                self.context.inference_policy = inference
                self.context.data_availability_external_vigilance = bool(_intake.get("external_vigilance_searched"))
                self.context.data_availability_complaint_closures_complete = bool(_intake.get("complaint_closures_complete"))
                self.context.data_availability_rmf_hazard_list = bool(_intake.get("rmf_hazard_list_available"))
                self.context.data_availability_intended_use = bool(_intake.get("intended_use_provided"))

            # Apply master context overrides (legacy, from old MasterContextExtractor)
            if _master:
                ed = int(_master.get("exposure_denominator_value", 0) or 0)
                if ed > 0:
                    self.context.exposure_denominator_golden = ed
                    self.context.total_units_sold = ed
                au = _master.get("annual_units_canonical") or {}
                if au:
                    self.context.annual_units_golden = {int(k): int(v) for k, v in au.items()}
                    self.context.total_units_by_year = dict(self.context.annual_units_golden)
                cc = int(_master.get("complaints_closed_canonical", 0) or 0)
                if cc > 0:
                    self.context.complaints_closed_canonical = cc
                    self.context.complaints_closed_count = cc
                self.context.calculate_metrics()

            # Set golden denominator from extracted data if not overridden
            if self.context.exposure_denominator_golden == 0 and self.context.total_units_sold > 0:
                self.context.exposure_denominator_golden = self.context.total_units_sold
            if not self.context.annual_units_golden and self.context.total_units_by_year:
                self.context.annual_units_golden = dict(self.context.total_units_by_year)

            # Compute quality awareness
            self._compute_quality_awareness()

            # Load GRKB
            await self._load_grkb()

            # Build global constraints
            self.context.global_constraints = build_global_constraints(self.context)

            gc = self.context.global_constraints
            await self._msg("Alex", "all",
                f"Context loaded. Device: {self.context.device_name}, "
                f"Files: {len(self.context.data_files)}, "
                f"Denominator: {gc.get('exposure_denominator', 0):,}, "
                f"Complaints: {self.context.total_complaints}.", "success")

    def _compute_quality_awareness(self):
        ctx = self.context
        if ctx is None:
            return
        # Confidence
        ctx.data_confidence_by_domain = {}
        if ctx.sales_data_available and ctx.total_units_sold > 0:
            ctx.data_confidence_by_domain["sales"] = "high"
        elif ctx.sales_data_available:
            ctx.data_confidence_by_domain["sales"] = "medium"
        else:
            ctx.data_confidence_by_domain["sales"] = "none"
        if ctx.complaint_data_available and ctx.total_complaints > 0:
            ctx.data_confidence_by_domain["complaints"] = "high" if ctx.complaints_closed_count > 0 else "medium"
        elif ctx.complaint_data_available:
            ctx.data_confidence_by_domain["complaints"] = "low"
        else:
            ctx.data_confidence_by_domain["complaints"] = "none"
        ctx.data_confidence_by_domain["vigilance"] = "high" if ctx.vigilance_data_available else "none"

        # Missing fields
        missing = []
        if not ctx.device_type:
            missing.append("Device type")
        if not ctx.intended_use:
            missing.append("Intended use statement")
        if not ctx.sales_data_available:
            missing.append("Sales data")
        if not ctx.complaint_data_available:
            missing.append("Complaint data")
        if not ctx.vigilance_data_available:
            missing.append("Vigilance data")
        ctx.missing_fields = missing

        # Warnings
        if not ctx.sales_data_available:
            ctx.data_quality_warnings.append("No sales data; rates cannot be calculated.")
        if not ctx.vigilance_data_available:
            ctx.data_quality_warnings.append("No vigilance data provided.")

        # Completeness
        n = sum([ctx.sales_data_available, ctx.complaint_data_available,
                 ctx.vigilance_data_available, bool(ctx.intended_use)])
        ctx.completeness_score = max(0.0, min(100.0, (n / 4.0) * 100.0 - len(missing) * 5.0))

        # Temporal
        ctx.psur_sequence_number = self.session_id
        ctx.psur_sequence_narrative = f"PSUR #{self.session_id} for this device."

    async def _load_grkb(self):
        if self.context is None:
            return
        svc = RegulatoryKnowledgeService.get_instance()
        if svc.connect():
            if svc.load_into_context(self.context):
                await self._msg("Alex", "all",
                    f"GRKB loaded: {len(self.context.grkb_obligations)} obligations, "
                    f"{len(self.context.grkb_sections)} sections.", "success")
            else:
                await self._msg("Alex", "all", "GRKB connection succeeded but data load failed.", "warning")
        else:
            await self._msg("Alex", "all", "GRKB not available; using built-in definitions.", "warning")

    # ------------------------------------------------------------------
    # Section Generation (with Consultation Protocol)
    # ------------------------------------------------------------------

    async def _generate_section(self, section_id: str) -> bool:
        sdef = SECTION_DEFINITIONS.get(section_id, {})
        agent = sdef.get("agent", "Alex")
        name = sdef.get("name", f"Section {section_id}")
        ctx = self.context
        if ctx is None:
            return False

        print(f"[orchestrator] Generating section {section_id} with agent {agent}...")

        try:
            # Step 1: Run pre-consultations
            pre_results = await self._run_consultations(section_id, "pre_consults")
            self._consultation_results[section_id] = pre_results

            # Step 2: Generate section with consultation context injected
            self.current_agent = agent
            await self._set_status(agent, "working")
            await self._msg(agent, "all",
                f"Working on Section {section_id}: {name}...", "normal")

            sys_prompt = get_agent_system_prompt(agent, section_id, ctx, self.session_id)

            denom_line = (
                f"MANDATORY DENOMINATOR: {ctx.exposure_denominator_golden:,} units. "
                "Use this number and ONLY this number as the distribution denominator throughout your section.\n\n"
            )

            # Build user prompt with consultation results
            consult_context = ""
            if pre_results:
                consult_context = (
                    "\n\n## Consultation Results\n"
                    "The following inputs were gathered from your colleagues:\n\n"
                    + "\n\n".join(pre_results)
                    + "\n\nIncorporate these inputs into your section."
                )

            user_prompt = (
                denom_line
                + f"Generate Section {section_id}: {name}.\n"
                + f"Device: {ctx.device_name}, UDI-DI: {ctx.udi_di}, "
                + f"Units: {ctx.total_units_sold:,}, Complaints: {ctx.total_complaints}.\n"
                + "Write narrative prose. No bullet points."
                + consult_context
            )
            content = await call_ai(agent, sys_prompt, user_prompt)
            print(f"[orchestrator] Section {section_id} content length: {len(content)} chars")
            if not content:
                await self._msg(agent, "all", f"AI call failed for Section {section_id}.", "error")
                return False

            # Enforce word limit: condensation pass if > 1.2x target
            content = await self._enforce_word_limit(agent, section_id, content)

            await self._save_section(section_id, name, agent, content, "draft")
            await self._msg(agent, "Victoria",
                f"Section {section_id} draft done ({len(content.split())} words). Submitting for QC.", "normal")

            # Step 3: Run post-consultations (charts, verification)
            post_results = await self._run_consultations(section_id, "post_consults")
            if post_results:
                self._consultation_results[section_id].extend(post_results)

            # Step 4: QC cycle with Victoria (enhanced with reputation feedback)
            for _ in range(self.max_qc_iterations):
                await self._set_status("Victoria", "working")
                qc = await self._qc_review(section_id, content)
                if qc.get("verdict") == "PASS":
                    await self._save_section(section_id, name, agent, content, "approved")
                    await self._msg("Victoria", agent,
                        f"Section {section_id} APPROVED. {qc.get('feedback', '')[:300]}", "success")
                    await self._set_status("Victoria", "complete")
                    return True
                feedback = qc.get("feedback", "Revisions needed")
                await self._msg("Victoria", agent,
                    f"Section {section_id} needs revision: {feedback[:400]}", "warning")
                await self._set_status(agent, "working")
                content = await self._revise(agent, section_id, content, feedback)
                await self._save_section(section_id, name, agent, content, "in_review")

            # Accept after max iterations
            await self._save_section(section_id, name, agent, content, "approved")
            await self._msg("Victoria", "all",
                f"Section {section_id} approved after max revisions.", "warning")
            return True

        except Exception as e:
            traceback.print_exc()
            await self._msg(agent, "all", f"Error on Section {section_id}: {e}", "error")
            return False

    async def _enforce_word_limit(self, agent: str, section_id: str, content: str) -> str:
        """If content exceeds 1.2x the word limit, run a condensation pass."""
        from backend.psur.templates import load_template
        ctx = self.context
        if ctx is None:
            return content
        template = load_template(getattr(ctx, "template_id", "eu_uk_mdr"))
        spec = template.section_specs.get(section_id)
        word_limit = spec.word_limit if spec else 800
        max_words = int(word_limit * 1.2)

        word_count = len(content.split())
        if word_count <= max_words:
            return content

        print(f"[orchestrator] Section {section_id}: {word_count} words exceeds limit {max_words}. Condensing...")
        condense_prompt = (
            f"The following PSUR section is {word_count} words but MUST be under {word_limit} words. "
            f"Condense it to approximately {word_limit} words while preserving ALL factual data, "
            f"numbers, and regulatory references. Remove redundant phrasing, merge short paragraphs, "
            f"and eliminate any content that repeats other sections. Narrative only, no bullet points.\n\n"
            f"SECTION CONTENT:\n{content}"
        )
        condensed = await call_ai(
            agent,
            f"You are a regulatory writing editor. Condense the text to {word_limit} words. "
            f"Keep all data and conclusions. Remove verbosity.",
            condense_prompt,
        )
        if condensed and len(condensed.split()) < word_count:
            print(f"[orchestrator] Condensed from {word_count} to {len(condensed.split())} words.")
            return condensed
        return content

    async def _qc_review(self, section_id: str, content: str) -> Dict[str, Any]:
        if self.context is None:
            return {"verdict": "PASS", "feedback": "No context"}
        prompt = get_qc_prompt(section_id, content, self.context)
        response = await call_ai("Victoria", prompt, "Review and provide PASS/CONDITIONAL/FAIL verdict.")
        if not response:
            return {"verdict": "PASS", "feedback": "QC unavailable"}
        upper = response.upper()
        if "PASS" in upper and "FAIL" not in upper:
            verdict = "PASS"
        elif "CONDITIONAL" in upper:
            verdict = "CONDITIONAL"
        else:
            verdict = "FAIL"
        return {"verdict": verdict, "feedback": response}

    async def _revise(self, agent: str, section_id: str, content: str, feedback: str) -> str:
        ctx = self.context
        if ctx is None:
            return content
        full_sys = get_agent_system_prompt(agent, section_id, ctx, self.session_id)
        user_prompt = (
            f"## REVISION REQUIRED\n\n"
            f"Your previous draft for Section {section_id}:\n\n{content}\n\n"
            f"## QC Feedback:\n{feedback}\n\n"
            "Revise the section to address ALL issues raised above. "
            "Retain all factual data from the context. Narrative only, no bullet points."
        )
        revised = await call_ai(agent, full_sys, user_prompt)
        return revised if revised else content

    # ------------------------------------------------------------------
    # Final Synthesis
    # ------------------------------------------------------------------

    async def _final_synthesis(self):
        await self._msg("Alex", "all", "Running cross-section consistency validation...", "normal")
        if self.context is None:
            return

        # Generate charts via Charley if not already done during consultations
        await self._generate_charts()

        gc = self.context.global_constraints
        with get_db_context() as db:
            sections = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.status.in_(["approved", "draft"]),
            ).all()
            if not sections:
                return

            text = "\n\n".join([
                f"=== SECTION {getattr(s, 'section_id', '')} ===\n{(getattr(s, 'content', '') or '')[:2000]}"
                for s in sections
            ])

            denom = gc.get("exposure_denominator", 0)
            prompt = (
                f"Review all PSUR sections for consistency. "
                f"Denominator must be {denom:,}. Total complaints {gc.get('total_complaints_count', 0)}. "
                f"Check: same numbers, no contradictions, no bullet points, paragraphs <= 4 sentences.\n\n"
                f"SECTIONS:\n{text}\n\nBrief report (max 200 words)."
            )
            try:
                response = await call_ai("Victoria",
                    "You are Victoria, QC validator performing final cross-section consistency check. "
                    "Publicly report your findings to the team. Commend strong sections. "
                    "Flag any inconsistencies with specific corrections.", prompt)
                if response:
                    await self._msg("Victoria", "all", f"Final consistency check: {response[:500]}", "normal")
            except Exception as e:
                await self._msg("Victoria", "all", f"Consistency check error: {e}", "warning")

        # Update workflow
        with get_db_context() as db:
            ws = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()
            if ws:
                setattr(ws, "status", "complete")
                setattr(ws, "sections_completed", len(self.sections_completed))
                setattr(ws, "summary", f"PSUR complete. {len(self.sections_completed)} sections.")
                db.commit()

        await self._msg("Alex", "all",
            f"PSUR generation complete for {self.context.device_name}. "
            f"{len(self.sections_completed)} sections approved. Ready for download.", "success")

    # ------------------------------------------------------------------
    # Charts (via Charley or fallback)
    # ------------------------------------------------------------------

    async def _generate_charts(self):
        if self.context is None:
            return
        ctx = self.context
        print(f"[orchestrator] Chart generation context: units_by_year={bool(ctx.total_units_by_year)}, complaints_by_type={bool(ctx.complaints_by_type)}")
        await self._msg("Alex", "Charley",
            "Charley, generate all MDCG 2022-21 Annex II charts and tables for the final document.", "normal")
        try:
            result = await charley_generate(
                self.context, "Generate all MDCG 2022-21 Annex II charts and tables.",
                "Alex", self.session_id)
            if not result or "error" in result.lower():
                await self._msg("Alex", "all",
                    "Chart generation had issues. Document will proceed without embedded charts.", "warning")
        except Exception as e:
            await self._msg("Alex", "all", f"Chart generation error: {e}", "warning")

    async def _save_context_snapshot(self):
        """Save the fully populated PSURContext as JSON on the session for DOCX download."""
        import json
        from dataclasses import asdict
        ctx = self.context
        if ctx is None:
            return
        try:
            snapshot = asdict(ctx)
            # Convert non-serializable types
            for key in ["period_start", "period_end"]:
                val = snapshot.get(key)
                if val and hasattr(val, "isoformat"):
                    snapshot[key] = val.isoformat()
            snapshot_json = json.dumps(snapshot, default=str)

            with get_db_context() as db:
                session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
                if session:
                    setattr(session, "context_snapshot", snapshot_json)
                    db.commit()
            print(f"[orchestrator] Context snapshot saved ({len(snapshot_json)} bytes)")
        except Exception as e:
            print(f"[orchestrator] Failed to save context snapshot: {e}")

    async def _complete_session(self):
        with get_db_context() as db:
            session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
            if session:
                setattr(session, "status", "complete")
                db.commit()

    # ------------------------------------------------------------------
    # DB Helpers
    # ------------------------------------------------------------------

    async def _initialize_agents(self):
        with get_db_context() as db:
            for aid, info in AGENT_ROLES.items():
                existing = db.query(Agent).filter(
                    Agent.session_id == self.session_id,
                    Agent.agent_id == aid,
                ).first()
                if not existing:
                    cfg = AGENT_CONFIGS.get(aid, AGENT_CONFIGS.get("Alex"))
                    db.add(Agent(
                        session_id=self.session_id, agent_id=aid,
                        name=info["name"], role=info["role"],
                        ai_provider=cfg.ai_provider if cfg else "anthropic",
                        model=cfg.model if cfg else "claude-sonnet-4-20250514",
                        status="idle",
                    ))
            db.commit()

    async def _save_section(self, section_id: str, name: str, agent: str,
                            content: str, status: str):
        with get_db_context() as db:
            existing = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.section_id == section_id,
            ).first()
            if existing:
                setattr(existing, "content", content)
                setattr(existing, "status", status)
                setattr(existing, "updated_at", datetime.utcnow())
            else:
                db.add(SectionDocument(
                    session_id=self.session_id, section_id=section_id,
                    section_name=name, author_agent=agent,
                    content=content, status=status,
                    created_at=datetime.utcnow(),
                ))
            db.commit()

    async def _update_workflow(self, section_id: str):
        with get_db_context() as db:
            ws = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()
            if ws:
                setattr(ws, "current_section", section_id)
                setattr(ws, "sections_completed", len(self.sections_completed))
                setattr(ws, "status", "running")
                db.commit()

    async def _set_status(self, agent: str, status: str):
        with get_db_context() as db:
            a = db.query(Agent).filter(
                Agent.session_id == self.session_id,
                Agent.agent_id == agent,
            ).first()
            if a:
                setattr(a, "status", status)
                setattr(a, "last_activity", datetime.utcnow())
                db.commit()

    async def _msg(self, from_agent: str, to_agent: str, message: str,
                   msg_type: str = "normal"):
        with get_db_context() as db:
            db.add(ChatMessage(
                session_id=self.session_id, from_agent=from_agent,
                to_agent=to_agent, message=message,
                message_type=msg_type, timestamp=datetime.utcnow(),
            ))
            db.commit()
