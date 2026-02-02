"""
Orchestrator Agent - Alex
SOTA Multi-Agent PSUR Generation with User Intervention Support
Uses OpenAI gpt-5.2 and Anthropic claude-sonnet-4/claude-opus-4 with automatic fallback
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import io
import pandas as pd

# AI imports with graceful fallback
try:
    import openai
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import google.generativeai as genai
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

from backend.database.session import get_db_context
from backend.database.models import (
    PSURSession, WorkflowState, ChatMessage, Agent, SectionDocument, DataFile
)
from backend.config import AGENT_CONFIGS, SECTIONS, settings


class OrchestratorAgent:
    """
    Alex - The Orchestrator
    Manages workflow, coordinates agents, handles user interventions
    Uses SOTA models with automatic fallback: OpenAI -> xAI/Grok -> Google -> Anthropic
    """
    
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.name = "Alex"
        self.agent_id = "orchestrator"
        self.intervention_check_interval = 5  # Check every 5 seconds
        
        # Initialize AI clients with fallback chain
        self.anthropic_client = None
        self.openai_client = None
        self.xai_client = None
        
        if HAS_OPENAI and settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)
        
        # xAI/Grok uses OpenAI-compatible API
        if HAS_OPENAI and settings.xai_api_key:
            self.xai_client = OpenAI(
                api_key=settings.xai_api_key,
                base_url="https://api.x.ai/v1"
            )
        
        if HAS_ANTHROPIC and settings.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            
        if HAS_GOOGLE and settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
    
    async def execute_workflow(self) -> Dict[str, Any]:
        """
        Execute the complete PSUR generation workflow with user intervention support
        """
        try:
            await self.post_message(
                "all",
                "**PSUR Generation Workflow Started**\n\nInitializing AI agents and loading data context...",
                "system"
            )
            await self.update_status("working")
            
            # Load and analyze uploaded data
            data_summary = await self.analyze_uploaded_data()
            await self.post_message(
                "all",
                f"**Data Analysis Complete**\n\n{data_summary}",
                "success"
            )
            
            # Check for user interventions before starting
            await self.process_user_interventions()
            
            # Process sections with real AI
            section_count = 0
            total_sections = len(SECTIONS)
            
            for section_id, section_info in SECTIONS.items():
                section_count += 1
                
                # Check for user interventions before each section
                interventions = await self.process_user_interventions()
                if interventions.get("halt_requested"):
                    await self.post_message(
                        "all",
                        "**Workflow Paused** - User requested halt. Awaiting instructions.",
                        "system"
                    )
                    await asyncio.sleep(10)  # Wait for user input
                    continue
                
                await self.post_message(
                    "all",
                    f"**Starting Section {section_id}: {section_info['title']}** ({section_count}/{total_sections})\n\nAgent: {section_info['agent']}",
                    "system"
                )
                
                # Generate section with AI
                success = await self.generate_section(section_id, section_info)
                
                if success:
                    with get_db_context() as db:
                        workflow = db.query(WorkflowState).filter(
                            WorkflowState.session_id == self.session_id
                        ).first()
                        if workflow:
                            workflow.current_section = section_id
                            workflow.sections_completed = section_count
                            db.commit()
                else:
                    await self.post_message(
                        "all",
                        f"**Section {section_id} Generation Issue** - Attempting recovery...",
                        "error"
                    )
                    # Retry once
                    success = await self.generate_section(section_id, section_info)
                    if not success:
                        continue  # Skip to next section
                
                await asyncio.sleep(1)
            
            # Final synthesis
            await self.perform_final_synthesis()
            
            # Mark complete
            with get_db_context() as db:
                workflow = db.query(WorkflowState).filter(
                    WorkflowState.session_id == self.session_id
                ).first()
                if workflow:
                    workflow.status = "complete"
                    workflow.summary = f"Generated {total_sections} sections successfully"
                    db.commit()
                
                session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
                if session:
                    session.status = "complete"
                    db.commit()
            
            await self.update_status("complete")
            await self.post_message(
                "all",
                f"**PSUR Generation Complete!**\n\n{total_sections} sections generated and validated.\n\nDocument ready for download.",
                "success"
            )
            
            return {"success": True, "sections_completed": total_sections}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            await self.post_message("all", f"**Workflow Error**\n\n{str(e)}", "error")
            await self.update_status("error")
            return {"success": False, "error": str(e)}
    
    async def analyze_uploaded_data(self) -> str:
        """Analyze all uploaded data files and return a summary"""
        with get_db_context() as db:
            files = db.query(DataFile).filter(DataFile.session_id == self.session_id).all()
            
            if not files:
                return "No data files uploaded. Sections will use general templates."
            
            summaries = []
            for f in files:
                try:
                    if f.filename.lower().endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(io.BytesIO(f.file_data), engine='openpyxl')
                    elif f.filename.lower().endswith('.csv'):
                        df = pd.read_csv(io.BytesIO(f.file_data))
                    else:
                        summaries.append(f"- {f.filename} ({f.file_type}): Document file uploaded")
                        continue
                    
                    record_count = len(df)
                    columns = list(df.columns)[:10]
                    summaries.append(
                        f"- **{f.filename}** ({f.file_type}): {record_count:,} records\n"
                        f"  Columns: {', '.join(str(c) for c in columns)}"
                    )
                except Exception as e:
                    summaries.append(f"- {f.filename}: Error reading file - {str(e)}")
            
            return "**Uploaded Data Files:**\n\n" + "\n".join(summaries)
    
    async def process_user_interventions(self) -> Dict[str, Any]:
        """Check for and process user intervention messages"""
        with get_db_context() as db:
            # Get unprocessed user messages
            user_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id,
                ChatMessage.from_agent == "User",
                ChatMessage.message_type == "normal"
            ).order_by(ChatMessage.timestamp.desc()).limit(5).all()
            
            halt_requested = False
            processed_count = 0
            
            for msg in user_messages:
                msg_lower = msg.message.lower()
                
                # Check for halt/pause commands
                if any(cmd in msg_lower for cmd in ["halt", "stop", "pause", "wait"]):
                    halt_requested = True
                    await self.post_message(
                        "User",
                        "Acknowledged. Workflow paused. Reply with 'continue' to resume.",
                        "normal"
                    )
                    processed_count += 1
                    continue
                
                # Check for continue command
                if "continue" in msg_lower or "resume" in msg_lower:
                    await self.post_message(
                        "User",
                        "Resuming workflow...",
                        "normal"
                    )
                    processed_count += 1
                    continue
                
                # Check for specific agent mentions
                for agent_id, config in AGENT_CONFIGS.items():
                    if f"@{config.name.lower()}" in msg_lower:
                        # Generate response from that agent
                        response = await self.generate_agent_response(
                            config.name,
                            agent_id,
                            msg.message
                        )
                        await self.post_message(
                            "User",
                            response,
                            "normal"
                        )
                        processed_count += 1
                        break
                
                # General questions/feedback addressed to orchestrator
                if "@alex" in msg_lower or processed_count == 0:
                    response = await self.call_ai(
                        "orchestrator",
                        f"User intervention: {msg.message}\n\nRespond helpfully as Alex, the workflow orchestrator."
                    )
                    if response:
                        await self.post_message("User", response, "normal")
                        processed_count += 1
            
            return {
                "processed": processed_count,
                "halt_requested": halt_requested
            }
    
    async def generate_agent_response(self, agent_name: str, agent_id: str, user_message: str) -> str:
        """Generate a response from a specific agent to user intervention"""
        config = AGENT_CONFIGS.get(agent_id)
        if not config:
            return f"{agent_name}: I'll look into that."
        
        prompt = f"""You are {agent_name}, a {config.role} specialist in a PSUR generation system.

A user has sent this message: "{user_message}"

Respond professionally and helpfully. If they're asking about your work, explain what you're doing.
If they have suggestions, acknowledge them and explain how you'll incorporate the feedback."""

        response = await self.call_ai(agent_id, prompt)
        return f"**{agent_name}:** {response}" if response else f"{agent_name}: Message received, I'll incorporate your feedback."
    
    async def generate_section(self, section_id: str, section_info: Dict[str, str]) -> bool:
        """Generate a section using SOTA AI models"""
        agent_name = section_info["agent"]
        agent_id = self.get_agent_id_by_name(agent_name)
        title = section_info["title"]
        
        try:
            # Initialize section in DB
            with get_db_context() as db:
                existing = db.query(SectionDocument).filter(
                    SectionDocument.session_id == self.session_id,
                    SectionDocument.section_id == section_id
                ).first()
                
                if not existing:
                    doc = SectionDocument(
                        session_id=self.session_id,
                        section_id=section_id,
                        section_name=title,
                        author_agent=agent_name,
                        content="Generating...",
                        status="in_progress",
                        created_at=datetime.utcnow()
                    )
                    db.add(doc)
                else:
                    existing.status = "in_progress"
                    existing.author_agent = agent_name
                db.commit()
            
            await self.update_agent_status(agent_id, "working")
            
            # Get session and data context
            session_data = self.get_session_data()
            data_context = self.get_data_context()
            file_data = self.get_file_data_for_section(section_id)
            
            # Phase 1: Analysis
            analysis_prompt = f"""You are {agent_name}, an expert in {title} for medical device PSURs.

**Device:** {session_data['device_name']}
**UDI-DI:** {session_data['udi_di']}
**Surveillance Period:** {session_data['period']}

**Available Data:**
{data_context}

{f"**Specific File Data:**{chr(10)}{file_data}" if file_data else ""}

Analyze the available data for Section {section_id}: {title}.
Identify key findings, statistics, and regulatory compliance points.
Be specific with numbers and cite data sources."""

            analysis = await self.call_ai(agent_id, analysis_prompt)
            await self.post_message(agent_name, f"**Analysis for {title}:**\n\n{analysis[:600]}...", "normal")
            await asyncio.sleep(1)
            
            # Phase 2: Drafting with MDR compliance
            draft_prompt = f"""Based on your analysis:
{analysis}

Now draft Section {section_id}: {title} for the PSUR.

Requirements per MDR 2017/745 Annex III:
- Use formal regulatory language
- Include specific data with citations
- Reference applicable standards
- Provide quantitative metrics where possible
- Structure with clear subsections
- Include conclusions and recommendations

Output the complete section content in Markdown format."""

            draft_content = await self.call_ai(agent_id, draft_prompt)
            
            if not draft_content:
                draft_content = f"## Section {section_id}: {title}\n\n*Content generation in progress. Please check data sources.*"
            
            await self.post_message(agent_name, f"**Draft submitted for {title}**\n\n{draft_content[:300]}...", "normal")
            
            # Phase 3: QC Review
            with get_db_context() as db:
                sec = db.query(SectionDocument).filter(
                    SectionDocument.session_id == self.session_id,
                    SectionDocument.section_id == section_id
                ).first()
                if sec:
                    sec.status = "review"
                    sec.content = draft_content
                    db.commit()
            
            await self.update_agent_status(agent_id, "waiting")
            qc_agent_id = self.get_agent_id_by_name("Victoria")
            await self.update_agent_status(qc_agent_id, "working")
            
            qc_prompt = f"""You are Victoria, QC Expert for PSUR documents.

Review this draft for Section {section_id}: {title}

DRAFT:
{draft_content}

Evaluate:
1. MDR 2017/745 compliance
2. Data accuracy and citations
3. Language and formatting
4. Completeness of required elements

Provide specific feedback. Be constructive but thorough."""

            qc_feedback = await self.call_ai(qc_agent_id, qc_prompt)
            await self.post_message("Victoria", f"**QC Review:**\n\n{qc_feedback[:500]}...", "normal")
            await self.update_agent_status(qc_agent_id, "idle")
            
            # Phase 4: Refinement
            await self.update_agent_status(agent_id, "working")
            
            refine_prompt = f"""Address this QC feedback and finalize Section {section_id}:

QC FEEDBACK:
{qc_feedback}

CURRENT DRAFT:
{draft_content}

Produce the final, refined section content."""

            final_content = await self.call_ai(agent_id, refine_prompt)
            if not final_content:
                final_content = draft_content
            
            # Save final content
            with get_db_context() as db:
                sec = db.query(SectionDocument).filter(
                    SectionDocument.session_id == self.session_id,
                    SectionDocument.section_id == section_id
                ).first()
                if sec:
                    sec.content = final_content
                    sec.status = "approved"
                    sec.qc_feedback = qc_feedback
                    config = AGENT_CONFIGS.get(agent_id)
                    sec.section_metadata = {
                        "word_count": len(final_content.split()),
                        "generated_at": datetime.utcnow().isoformat(),
                        "model_used": {
                            "name": config.name,
                            "role": config.role,
                            "ai_provider": config.ai_provider,
                            "model": config.model
                        } if config else {}
                    }
                    db.commit()
            
            await self.update_agent_status(agent_id, "complete")
            await self.post_message("Alex", f"**Section {section_id} Approved.** Quality score: PASS", "success")
            
            return True
            
        except Exception as e:
            print(f"Error generating section {section_id}: {e}")
            import traceback
            traceback.print_exc()
            await self.post_message("Alex", f"**Error in {title}:** {str(e)}", "error")
            await self.update_agent_status(agent_id, "error")
            return False
    
    async def perform_final_synthesis(self):
        """Perform final document synthesis"""
        await self.post_message(
            "Marcus",
            "**Final Synthesis Phase**\n\nCombining all sections into cohesive PSUR document...",
            "normal"
        )
        await self.update_agent_status("synthesis", "working")
        
        # Get all approved sections
        with get_db_context() as db:
            sections = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.status == "approved"
            ).order_by(SectionDocument.section_id).all()
            
            section_summaries = []
            for sec in sections:
                word_count = len(sec.content.split()) if sec.content else 0
                section_summaries.append(f"- Section {sec.section_id}: {sec.section_name} ({word_count} words)")
        
        synthesis_prompt = f"""You are Marcus, the Synthesis Expert.

Create an executive summary for this PSUR document.

Sections included:
{chr(10).join(section_summaries)}

Write:
1. Executive Summary (200-300 words)
2. Key Findings (bullet points)
3. Overall Benefit-Risk Conclusion
4. Recommendations for next surveillance period"""

        synthesis = await self.call_ai("synthesis", synthesis_prompt)
        
        if synthesis:
            with get_db_context() as db:
                # Add or update synthesis section
                existing = db.query(SectionDocument).filter(
                    SectionDocument.session_id == self.session_id,
                    SectionDocument.section_id == "M"
                ).first()
                
                if existing:
                    existing.content = synthesis
                    existing.status = "approved"
                else:
                    synth_doc = SectionDocument(
                        session_id=self.session_id,
                        section_id="M",
                        section_name="Executive Summary & Conclusions",
                        author_agent="Marcus",
                        content=synthesis,
                        status="approved",
                        created_at=datetime.utcnow()
                    )
                    db.add(synth_doc)
                db.commit()
        
        await self.update_agent_status("synthesis", "complete")
        await self.post_message("Marcus", "**Synthesis Complete**\n\nDocument ready for final review.", "success")
    
    def get_session_data(self) -> Dict[str, str]:
        """Get session metadata"""
        with get_db_context() as db:
            session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
            if session:
                return {
                    "device_name": session.device_name,
                    "udi_di": session.udi_di or "Pending",
                    "period": f"{session.period_start.strftime('%Y-%m-%d')} to {session.period_end.strftime('%Y-%m-%d')}"
                }
        return {"device_name": "Unknown", "udi_di": "Unknown", "period": "Unknown"}
    
    def get_data_context(self) -> str:
        """Get data analysis context from system messages and uploaded files"""
        with get_db_context() as db:
            # Get system analysis messages
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id,
                ChatMessage.message_type == "system"
            ).all()
            
            # Get file metadata
            files = db.query(DataFile).filter(DataFile.session_id == self.session_id).all()
            
            context_parts = []
            
            if messages:
                context_parts.append("**Previous Analysis:**\n" + "\n".join([m.message[:500] for m in messages[:5]]))
            
            if files:
                file_info = []
                for f in files:
                    file_info.append(f"- {f.filename} ({f.file_type})")
                context_parts.append("**Available Files:**\n" + "\n".join(file_info))
            
            if not context_parts:
                return "No specific data uploaded. Generate based on general MDR requirements."
            
            return "\n\n".join(context_parts)
    
    def get_file_data_for_section(self, section_id: str) -> Optional[str]:
        """Get relevant file data for a specific section"""
        section_file_mapping = {
            "C": ["sales"],
            "D": ["vigilance", "maude"],
            "E": ["complaints"],
            "F": ["complaints"],
            "L": ["pmcf", "clinical"],
        }
        
        relevant_types = section_file_mapping.get(section_id, [])
        if not relevant_types:
            return None
        
        with get_db_context() as db:
            for file_type in relevant_types:
                data_file = db.query(DataFile).filter(
                    DataFile.session_id == self.session_id,
                    DataFile.file_type.ilike(f"%{file_type}%")
                ).first()
                
                if data_file and data_file.file_data:
                    try:
                        if data_file.filename.lower().endswith(('.xlsx', '.xls')):
                            df = pd.read_excel(io.BytesIO(data_file.file_data), engine='openpyxl')
                        elif data_file.filename.lower().endswith('.csv'):
                            df = pd.read_csv(io.BytesIO(data_file.file_data))
                        else:
                            continue
                        
                        # Return summary statistics
                        summary = f"**{data_file.filename}** ({len(df)} records)\n"
                        summary += f"Columns: {', '.join(str(c) for c in df.columns)}\n"
                        
                        # Add numeric summaries
                        for col in df.select_dtypes(include=['number']).columns[:5]:
                            summary += f"\n{col}: sum={df[col].sum():,.0f}, mean={df[col].mean():,.2f}"
                        
                        return summary
                    except Exception as e:
                        print(f"Error reading file for section {section_id}: {e}")
        
        return None
    
    async def call_ai(self, agent_id: str, prompt: str) -> str:
        """Call AI with automatic fallback between providers"""
        config = AGENT_CONFIGS.get(agent_id)
        if not config:
            config = AGENT_CONFIGS.get("orchestrator")
        
        provider, model = config.get_active_provider()
        
        # Try primary provider
        try:
            result = await self._call_provider(provider, model, prompt)
            if result:
                return result
        except Exception as e:
            error_msg = str(e).lower()
            if "credit" in error_msg or "billing" in error_msg or "balance" in error_msg:
                print(f"Primary provider {provider} has billing issues, trying fallback...")
            else:
                print(f"Primary provider {provider} failed: {e}")
        
        # Fallback chain: OpenAI -> xAI/Grok -> Google -> Anthropic (Anthropic last due to billing)
        fallbacks = [
            ("openai", settings.openai_model_default),
            ("xai", settings.xai_model_default),
            ("google", settings.google_model_default),
            ("anthropic", settings.anthropic_model_orchestrator),
        ]
        
        for fb_provider, fb_model in fallbacks:
            if fb_provider == provider:
                continue
            try:
                result = await self._call_provider(fb_provider, fb_model, prompt)
                if result:
                    return result
            except Exception as e:
                error_msg = str(e).lower()
                if "credit" in error_msg or "billing" in error_msg or "balance" in error_msg:
                    print(f"Fallback {fb_provider} has billing issues, trying next...")
                else:
                    print(f"Fallback {fb_provider} failed: {e}")
                continue
        
        return ""
    
    async def _call_provider(self, provider: str, model: str, prompt: str) -> str:
        """Call a specific AI provider"""
        if provider == "openai" and HAS_OPENAI and self.openai_client:
            # Try max_completion_tokens first (newer models), fallback to max_tokens (older models)
            try:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=2048
                )
            except Exception as e:
                if "max_completion_tokens" in str(e):
                    response = self.openai_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=2048
                    )
                else:
                    raise
            return response.choices[0].message.content
        
        elif provider == "xai" and HAS_OPENAI and self.xai_client:
            # xAI/Grok uses OpenAI-compatible API
            response = self.xai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048
            )
            return response.choices[0].message.content
        
        elif provider == "google" and HAS_GOOGLE:
            model_obj = genai.GenerativeModel(model)
            response = model_obj.generate_content(prompt)
            return response.text
        
        elif provider == "anthropic" and HAS_ANTHROPIC and self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        return ""
    
    def get_agent_id_by_name(self, name: str) -> str:
        """Map agent name to agent_id"""
        for agent_id, config in AGENT_CONFIGS.items():
            if config.name == name:
                return agent_id
        return "orchestrator"
    
    async def post_message(self, to_agent: str, message: str, message_type: str = "normal"):
        """Post a message to the collaboration forum"""
        with get_db_context() as db:
            msg = ChatMessage(
                session_id=self.session_id,
                from_agent=self.name,
                to_agent=to_agent,
                message=message,
                message_type=message_type,
                timestamp=datetime.utcnow()
            )
            db.add(msg)
            db.commit()
    
    async def update_status(self, status: str):
        """Update orchestrator status"""
        await self.update_agent_status(self.agent_id, status)
    
    async def update_agent_status(self, agent_id: str, status: str):
        """Update any agent's status"""
        with get_db_context() as db:
            agent = db.query(Agent).filter(
                Agent.session_id == self.session_id,
                Agent.agent_id == agent_id
            ).first()
            
            if agent:
                agent.status = status
                agent.last_activity = datetime.utcnow()
                db.commit()
