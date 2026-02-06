"""
Prompt Builders - Generates system prompts for all PSUR agents.

Discussion Panel Architecture: Includes personality injection,
consultation prompt builders, reputation-aware QC language,
template-aware word limits, and all existing context/constraint/
GRKB/interdependency prompts.
"""

from typing import Dict, Any, Optional

from backend.psur.context import PSURContext
from backend.psur.agents import (
    AGENT_ROLES, SECTION_DEFINITIONS, WORKFLOW_ORDER,
    SECTION_INTERDEPENDENCIES,
)
from backend.psur.templates import load_template, SectionSpec
from backend.database.session import get_db_context
from backend.database.models import SectionDocument


# ---------------------------------------------------------------------------
# Context prompt builder
# ---------------------------------------------------------------------------

def build_context_prompt(ctx: PSURContext, section_id: Optional[str] = None) -> str:
    """Generate the complete context string injected into every agent prompt.
    If section_id is provided, only include raw data samples relevant to that section."""
    period_str = (
        f"{ctx.period_start.strftime('%d %B %Y')} to {ctx.period_end.strftime('%d %B %Y')}"
        if ctx.period_start and ctx.period_end else "TBD"
    )

    sales_trend = ""
    if ctx.total_units_by_year:
        lines = [f"    {y}: {u:,} units" for y, u in sorted(ctx.total_units_by_year.items())]
        sales_trend = "\n  By year:\n" + "\n".join(lines)

    severity = ""
    if ctx.complaints_by_severity:
        lines = [f"    {s}: {c}" for s, c in ctx.complaints_by_severity.items()]
        severity = "\n  By severity:\n" + "\n".join(lines)

    ctypes = ""
    if ctx.complaints_by_type:
        lines = [f"    {t}: {c}" for t, c in ctx.complaints_by_type.items()]
        ctypes = "\n  By type:\n" + "\n".join(lines)

    complaints_by_year = ""
    if ctx.total_complaints_by_year:
        lines = [f"    {y}: {c} complaints" for y, c in sorted(ctx.total_complaints_by_year.items())]
        complaints_by_year = "\n  Complaints by year:\n" + "\n".join(lines)
    else:
        complaints_by_year = "\n  COMPLAINTS BY YEAR: Not available. Do NOT invent per-year complaint numbers. State 'Year-by-year complaint data was not available.'"

    crate_by_year = ""
    if ctx.complaint_rate_by_year:
        lines = [f"    {y}: {r:.4f}%" for y, r in sorted(ctx.complaint_rate_by_year.items())]
        crate_by_year = "\n  Complaint rate by year:\n" + "\n".join(lines)
    else:
        crate_by_year = "\n  COMPLAINT RATE BY YEAR: Not available. Do NOT invent per-year rates. State 'Year-by-year complaint rate data was not available.'"

    golden = ""
    if ctx.exposure_denominator_golden > 0 or ctx.closure_definition_text or ctx.inference_policy:
        annual = ", ".join(
            f"{y}: {u:,}" for y, u in sorted(ctx.annual_units_golden.items())
        ) if ctx.annual_units_golden else "None"
        golden = f"""
================================================================================
         SINGLE GOLDEN SOURCE -- ALL SECTIONS MUST USE THESE ONLY
================================================================================
- Exposure denominator: {ctx.exposure_denominator_golden:,} units (scope: {ctx.exposure_denominator_scope}).
- Annual distribution (canonical): {annual}.
- Complaint closures (canonical): {ctx.complaints_closed_canonical}. Definition: {ctx.closure_definition_text or 'Closed = investigation completed with root cause documented.'}
- Inference policy: {ctx.inference_policy}.
- Data availability:
  External vigilance searched: {"YES" if ctx.data_availability_external_vigilance else "NO"}
  Complaint closures complete: {"YES" if ctx.data_availability_complaint_closures_complete else "NO"}
  RMF hazard list available: {"YES" if ctx.data_availability_rmf_hazard_list else "NO"}
  Intended use provided: {"YES" if ctx.data_availability_intended_use else "NO"}
================================================================================
"""

    include_sales_raw = section_id is None or section_id == "C"
    include_complaints_raw = section_id is None or section_id in ("E", "F")
    include_vigilance_raw = section_id is None or section_id == "D"
    include_any_raw = include_sales_raw or include_complaints_raw or include_vigilance_raw
    sections_no_raw = ("G", "H", "I", "L", "A", "M", "B")
    if section_id in sections_no_raw:
        include_sales_raw = include_complaints_raw = include_vigilance_raw = False
    if section_id == "B":
        include_any_raw = False

    sales_sample = ""
    if include_sales_raw and ctx.sales_raw_sample:
        sales_sample = (
            f"### SALES DATA SAMPLE (First 15 Records per file)\n"
            f"Columns detected: {', '.join(ctx.sales_columns_detected) if ctx.sales_columns_detected else 'None'}\n\n"
            f"{ctx.sales_raw_sample}"
        )
    elif include_sales_raw:
        sales_sample = "### SALES DATA: No raw sample available"

    complaints_sample = ""
    if include_complaints_raw and ctx.complaints_raw_sample:
        complaints_sample = (
            f"### COMPLAINTS DATA SAMPLE (First 15 Records per file)\n"
            f"Columns detected: {', '.join(ctx.complaints_columns_detected) if ctx.complaints_columns_detected else 'None'}\n\n"
            f"{ctx.complaints_raw_sample}\n\n"
            "IMPORTANT: Use this raw data to understand actual complaint details."
        )
    elif include_complaints_raw:
        complaints_sample = "### COMPLAINTS DATA: No raw sample available"

    vigilance_sample = ""
    if include_vigilance_raw and ctx.vigilance_raw_sample:
        vigilance_sample = (
            f"### VIGILANCE DATA SAMPLE (First 15 Records per file)\n"
            f"Columns detected: {', '.join(ctx.vigilance_columns_detected) if ctx.vigilance_columns_detected else 'None'}\n\n"
            f"{ctx.vigilance_raw_sample}"
        )
    elif include_vigilance_raw:
        vigilance_sample = "### VIGILANCE DATA: No raw sample available"

    include_col_mappings = section_id not in sections_no_raw if section_id else True
    col_mappings = ""
    if include_col_mappings and ctx.column_mappings:
        col_parts = ["### COLUMN MAPPINGS (How source columns map to data roles)\n"]
        for fname, mappings in ctx.column_mappings.items():
            col_parts.append(f"File: {fname}")
            for role, col_name in mappings.items():
                col_parts.append(f"  {role} -> {col_name if col_name else '[not detected]'}")
        col_mappings = "\n".join(col_parts)

    include_text_docs = section_id not in sections_no_raw if section_id else True
    text_docs = ""
    if include_text_docs and ctx.text_documents:
        td_parts = ["### TEXT DOCUMENTS (Extracted content from uploaded documents)\n"]
        for td in ctx.text_documents:
            td_parts.append(
                f"--- {td.get('filename', 'unknown')} ({td.get('file_type', 'general')}, "
                f"{td.get('length', 0)} chars) ---"
            )
            td_parts.append(td.get("excerpt", ""))
            td_parts.append("")
        text_docs = "\n".join(td_parts)

    include_supp = section_id not in sections_no_raw if section_id else True
    supp_data = ""
    if include_supp and ctx.supplementary_raw_samples:
        sp_parts = ["### SUPPLEMENTARY DATA (Risk, CER, PMCF files)\n"]
        for key, sample in ctx.supplementary_raw_samples.items():
            cols = ctx.supplementary_columns.get(key, [])
            sp_parts.append(f"--- {key} (columns: {', '.join(cols[:10])}) ---")
            sp_parts.append(sample[:1500])
            sp_parts.append("")
        supp_data = "\n".join(sp_parts)

    reg_class = ""
    if ctx.regulatory_classification:
        reg_class = ", ".join(f"{k}: {v}" for k, v in ctx.regulatory_classification.items())
    else:
        reg_class = "[Not provided]"

    critical_rule = (
        "CRITICAL: If a data field shows 'Not available' or is empty, you MUST state it is not available. "
        "NEVER invent numbers to fill gaps.\n\n"
    )
    raw_block = ""
    if sales_sample or complaints_sample or vigilance_sample or col_mappings or text_docs or supp_data:
        raw_block = f"""
## RAW DATA SAMPLES
{sales_sample}

{complaints_sample}

{vigilance_sample}

{col_mappings}

{text_docs}

{supp_data}
"""

    return f"""
================================================================================
         COMPREHENSIVE PSUR REGULATORY & OPERATIONAL CONTEXT
              (MDR 2017/745 Article 86 | MDCG 2022-21 Compliance)
================================================================================
{critical_rule}
{golden}

## MANUFACTURER & DEVICE
Manufacturer: {ctx.manufacturer or '[Not provided]'}
Device: {ctx.device_name}
UDI-DI: {ctx.udi_di}
Intended Use: {ctx.intended_use or '[Not provided]'}
Classification: {reg_class}
Notified Body: {ctx.notified_body or '[Not provided]'} (No. {ctx.notified_body_number or 'N/A'})

## REPORTING PERIOD
Period: {period_str}
Cadence: {ctx.psur_cadence}

## DISTRIBUTION
Total Units (Reporting Period): {ctx.total_units_sold:,}
Cumulative Units (All Time): {ctx.cumulative_units_all_time:,}{sales_trend}
Regions: {', '.join(ctx.regions) if ctx.regions else '[Not provided]'}

## COMPLAINTS
Total: {ctx.total_complaints}
Rate: {ctx.complaint_rate_percent:.4f}%
Closed (investigation complete): {ctx.complaints_closed_count}
Root cause identified: {ctx.complaints_with_root_cause_identified}
Closure Rate: {ctx.investigation_closure_rate:.1f}%{ctypes}{severity}{complaints_by_year}{crate_by_year}

Product Defect: {ctx.complaints_product_defect} | User Error: {ctx.complaints_user_error} | Unrelated: {ctx.complaints_unrelated} | Unconfirmed: {ctx.complaints_unconfirmed}

## SERIOUS INCIDENTS
Total Vigilance Events: {ctx.total_vigilance_events}
Serious Incidents (filtered): {ctx.serious_incidents} | Deaths: {ctx.deaths} | Serious Injuries: {ctx.serious_injuries}

## DATA QUALITY
Completeness: {ctx.completeness_score:.0f}%
Sales: {'Available' if ctx.sales_data_available else 'Not available'}
Complaints: {'Available' if ctx.complaint_data_available else 'Not available'}
Vigilance: {'Available' if ctx.vigilance_data_available else 'Not available'}

{chr(10).join(ctx.data_quality_warnings) if ctx.data_quality_warnings else 'No warnings.'}
{raw_block}
"""


# ---------------------------------------------------------------------------
# Global constraints prompt
# ---------------------------------------------------------------------------

def build_global_constraints(ctx: PSURContext) -> Dict[str, Any]:
    """Build locked global constraints dict from context."""
    closure = ctx.investigation_closure_rate
    closed = ctx.complaints_closed_canonical or ctx.complaints_closed_count
    total = ctx.total_complaints

    root_status = "preliminary"
    if closure >= 80:
        root_status = "confirmed"
    elif closure >= 50:
        root_status = "partial"

    si_certainty = "inconclusive"
    if closure >= 80 and total > 0:
        si_certainty = "confirmed"
    elif closure >= 50:
        si_certainty = "provisional"

    return {
        "exposure_denominator": ctx.exposure_denominator_golden or ctx.total_units_sold,
        "exposure_denominator_scope": ctx.exposure_denominator_scope,
        "annual_units": ctx.annual_units_golden or ctx.total_units_by_year,
        "severity_levels": {
            "critical": "Death or permanent impairment directly attributable to device",
            "serious": "Hospitalization, intervention required, or temporary impairment",
            "moderate": "Medically significant but not requiring intervention",
            "minor": "No injury, user inconvenience only",
            "unknown": "Severity not determinable from available data",
        },
        "root_cause_categories": {
            "product_defect": "Manufacturing, design, or material defect confirmed",
            "user_error": "Misuse or failure to follow IFU confirmed",
            "unrelated": "Event unrelated to device confirmed",
            "indeterminate": "Insufficient evidence to determine causality",
            "pending": "Investigation not yet complete",
        },
        "investigation_closure_rate_percent": closure,
        "complaints_closed_count": closed,
        "complaints_with_root_cause_identified": ctx.complaints_with_root_cause_identified,
        "total_complaints_count": total,
        "total_complaints_by_year": ctx.total_complaints_by_year,
        "root_cause_status": root_status,
        "si_classification_certainty": si_certainty,
        "rmf_status": "complete" if ctx.data_availability_rmf_hazard_list else "incomplete_or_unavailable",
        "vigilance_methodology": "internal_and_external_databases" if ctx.data_availability_external_vigilance else "internal_only",
        "inference_policy": ctx.inference_policy,
    }


def get_global_constraints_prompt(constraints: Dict[str, Any]) -> str:
    """Render global constraints as a prompt block."""
    denom = constraints.get("exposure_denominator", 0)
    scope = constraints.get("exposure_denominator_scope", "reporting_period_only")
    annual = constraints.get("annual_units", {})
    annual_str = ", ".join(f"{y}: {u:,}" for y, u in sorted(annual.items())) if annual else "None"
    closure = constraints.get("investigation_closure_rate_percent", 0)
    root = constraints.get("root_cause_status", "preliminary")
    si = constraints.get("si_classification_certainty", "inconclusive")
    total = constraints.get("total_complaints_count", 0)
    closed = constraints.get("complaints_closed_count", 0)
    root_cause_identified = constraints.get("complaints_with_root_cause_identified", 0)
    inference = constraints.get("inference_policy", "strictly_factual")

    cby = constraints.get("total_complaints_by_year", {})
    cby_str = ", ".join(f"{y}: {c}" for y, c in sorted(cby.items())) if cby else "None"

    closure_rules = ""
    if closure < 50:
        closure_rules = (
            f"CRITICAL: Closure is {closure:.0f}% (<50%). "
            "Root causes MUST be PRELIMINARY. SI classifications INCONCLUSIVE. "
            "Trends LIMITED."
        )
    elif closure < 80:
        closure_rules = f"NOTE: Closure is {closure:.0f}% (partial). Root causes PROVISIONAL."
    else:
        closure_rules = f"Closure is {closure:.0f}% (complete). Root causes may be CONFIRMED."

    return f"""
================================================================================
              GLOBAL CONSTRAINTS -- ALL AGENTS MUST FOLLOW
================================================================================

1. DENOMINATOR: {denom:,} units ({scope}). Annual: {annual_str}.
2. COMPLAINTS: {total} total, {closed} closed, {root_cause_identified} with root cause identified. {closure_rules}
3. COMPLAINTS BY YEAR: {cby_str}.
4. ROOT STATUS: {root.upper()}. SI CERTAINTY: {si.upper()}.
5. INFERENCE: {inference.upper()}.
6. CROSS-SECTION: Same denominator, same totals, no contradictions.
7. BREVITY: Max 4 sentences/paragraph. No bullet points. No redundancy.

================================================================================
"""


# ---------------------------------------------------------------------------
# GRKB regulatory grounding
# ---------------------------------------------------------------------------

def get_grkb_context(section_id: str, ctx: PSURContext) -> str:
    """Generate GRKB regulatory grounding for a specific section."""
    if not ctx.grkb_available:
        return ""
    lines = ["## GRKB REGULATORY GROUNDING", ""]
    for sec in ctx.grkb_sections:
        sid = sec.get("section_id", "")
        if sid.endswith(section_id) or section_id in sid:
            lines.append(f"Section: {sec.get('section_number', '')} - {sec.get('title', '')}")
            if sec.get("description"):
                lines.append(f"Description: {sec['description']}")
            if sec.get("regulatory_basis"):
                lines.append(f"Regulatory Basis: {sec['regulatory_basis']}")
            break
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Inter-agent section summaries
# ---------------------------------------------------------------------------

def get_previous_sections_summary(session_id: int, current_section_id: str) -> str:
    """Get summaries of previously completed sections for cross-referencing."""
    current_idx = WORKFLOW_ORDER.index(current_section_id) if current_section_id in WORKFLOW_ORDER else 0
    prev_ids = WORKFLOW_ORDER[:current_idx]
    if not prev_ids:
        return ""

    with get_db_context() as db:
        sections = db.query(SectionDocument).filter(
            SectionDocument.session_id == session_id,
            SectionDocument.section_id.in_(prev_ids),
            SectionDocument.status.in_(["draft", "approved"]),
        ).all()
        if not sections:
            return ""

        parts = []
        for sec in sections:
            sid = getattr(sec, "section_id", "")
            name = getattr(sec, "section_name", "")
            content = getattr(sec, "content", "") or ""
            summary = content[:300].strip()
            if len(content) > 300:
                dot = summary.rfind(".")
                if dot > 150:
                    summary = summary[:dot + 1]
                summary += " [...]"
            parts.append(f"### Section {sid}: {name}\n{summary}\n")

        return (
            "## Previously Generated Sections\n"
            "Reference findings below. Do NOT repeat -- cross-reference instead.\n\n"
            + "\n".join(parts)
        )


# ---------------------------------------------------------------------------
# Workflow role context
# ---------------------------------------------------------------------------

def get_workflow_role_context(agent_name: str, section_id: str) -> str:
    """Build context about the agent's position in the workflow."""
    idx = next((i for i, s in enumerate(WORKFLOW_ORDER) if s == section_id), None)
    prev = WORKFLOW_ORDER[:idx] if idx is not None else []
    nxt = WORKFLOW_ORDER[idx + 1:] if idx is not None else []
    return (
        f"Sections completed before yours: {', '.join(prev) if prev else 'None'}. "
        f"Sections after yours: {', '.join(nxt) if nxt else 'None'}. "
        f"Your output feeds Section M (Conclusions) and A (Executive Summary)."
    )


def get_interdependency_context(section_id: str) -> str:
    """Build interdependency description for a section."""
    dep = SECTION_INTERDEPENDENCIES.get(section_id, {})
    if not dep:
        return ""
    cites = dep.get("cites", [])
    cited_by = dep.get("cited_by", [])
    return (
        f"Cite from: {', '.join(f'Section {s}' for s in cites) if cites else 'None'}. "
        f"Cited by: {', '.join(f'Section {s}' for s in cited_by) if cited_by else 'None'}. "
        f"{dep.get('data_flow', '')}"
    )


# ---------------------------------------------------------------------------
# Personality & Discussion Behavior Injection
# ---------------------------------------------------------------------------

def _get_personality_block(agent_name: str) -> str:
    """Build personality and discussion behavior prompt block for an agent."""
    role_info = AGENT_ROLES.get(agent_name, {})
    personality = role_info.get("personality", "")
    behavior = role_info.get("discussion_behavior", {})

    if not personality and not behavior:
        return ""

    parts = ["## Personality & Discussion Behavior"]
    if personality:
        parts.append(f"Personality: {personality}")
    if behavior:
        if behavior.get("initiates"):
            parts.append(f"You initiate: {behavior['initiates']}")
        if behavior.get("validates"):
            parts.append(f"You validate: {behavior['validates']}")
        if behavior.get("challenges"):
            parts.append(f"You challenge: {behavior['challenges']}")
        if behavior.get("collaborates_with"):
            parts.append(f"You collaborate with: {behavior['collaborates_with']}")

    parts.append(
        "\nAll your messages are visible to the entire team in the Discussion Panel. "
        "Be professional, direct, and data-driven."
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Agent system prompt (master builder)
# ---------------------------------------------------------------------------

def get_agent_system_prompt(agent_name: str, section_id: str,
                            ctx: PSURContext, session_id: int = 0) -> str:
    """Generate the complete system prompt for an agent generating a section."""
    agent = AGENT_ROLES.get(agent_name, {})
    section = SECTION_DEFINITIONS.get(section_id, {})

    personality_block = _get_personality_block(agent_name)

    # Load template for word limits and special instructions
    template_id = getattr(ctx, "template_id", "eu_uk_mdr")
    template = load_template(template_id)
    spec: Optional[SectionSpec] = template.section_specs.get(section_id)

    word_limit = spec.word_limit if spec else 800
    max_words = int(word_limit * 1.3)
    section_title = spec.title if spec else section.get("name", "PSUR Section")
    regulatory_ref = spec.regulatory_ref if spec else section.get("mdcg_ref", "N/A")
    special_instructions = spec.special_instructions if spec else ""
    global_instructions = template.global_instructions

    return f"""# {agent.get('name', agent_name)} -- {agent.get('title', 'PSUR Agent')}

## STRICT WORD LIMIT -- READ THIS FIRST
YOU MUST WRITE APPROXIMATELY {word_limit} WORDS. ABSOLUTE MAXIMUM: {max_words} WORDS.
If your output exceeds {max_words} words it will be automatically truncated.
The final PSUR must be approximately 30 pages total across 13 sections. Be concise.

## Identity
You are {agent.get('name', agent_name)}, a {agent.get('title', 'specialist')} specializing in regulatory compliance.
Expertise: {agent.get('expertise', 'regulatory documentation')}

{personality_block}

## Regulatory Framework
{template.name} ({template.jurisdiction})
Basis: {template.regulatory_basis}

## Assignment
Section {section_id}: {section_title}
Purpose: {section.get('purpose', '')}
Regulatory Reference: {regulatory_ref}
Required content: {', '.join(section.get('required_content', []))}

{get_workflow_role_context(agent_name, section_id)}

{get_interdependency_context(section_id)}

## Rules
1. NO fabricated data. Every number must trace to source. State "Not available" for missing data.
2. NARRATIVE ONLY. No bullet points. Max 4 sentences per paragraph.
3. DATA TABLES AND CHARTS ARE GENERATED SEPARATELY. Do NOT reproduce raw data tables.
   Reference tables instead (e.g., "As shown in Table 1...").
4. Evidence-based conclusions. Distinguish data from interpretation.
5. Do NOT repeat content from other sections; cross-reference instead.
6. Professional regulatory tone suitable for audit.
7. REMEMBER: {word_limit} words target. Do NOT exceed {max_words} words.

## Template Instructions
{global_instructions}

{('## Section-Specific Instructions' + chr(10) + special_instructions) if special_instructions else ''}

{get_global_constraints_prompt(ctx.global_constraints) if ctx.global_constraints else ''}

{get_grkb_context(section_id, ctx)}

{get_previous_sections_summary(session_id, section_id) if session_id else ''}

## SECTION REFERENCE GUIDE (Use for cross-references)
Section A = Executive Summary
Section B = Scope & Device Description
Section C = Units Distributed
Section D = Serious Incidents
Section E = Customer Feedback
Section F = Complaints Management
Section G = Trends Analysis
Section H = FSCA
Section I = CAPA
Section J = Benefit-Risk / Literature
Section K = External Databases
Section L = PMCF
Section M = Overall Conclusions

{build_context_prompt(ctx, section_id=section_id)}

Now generate Section {section_id}: {section_title}. Target {word_limit} words. MAXIMUM {max_words} words. Concise, compliant, no bullet points.
"""


# ---------------------------------------------------------------------------
# Consultation Prompt Builders
# ---------------------------------------------------------------------------

def get_consultation_prompt(requester: str, responder: str,
                            task: str, ctx: PSURContext) -> str:
    """Build system prompt for the requester agent asking a consultation question."""
    req_info = AGENT_ROLES.get(requester, {})
    resp_info = AGENT_ROLES.get(responder, {})

    return f"""# {req_info.get('name', requester)} -- Consultation Request

You are {req_info.get('name', requester)}, {req_info.get('title', 'PSUR Agent')}.
{req_info.get('personality', '')}

You are addressing {resp_info.get('name', responder)} ({resp_info.get('title', 'colleague')}) in the team Discussion Panel.
All team members can see this exchange.

Device: {ctx.device_name}
Units: {ctx.total_units_sold:,}
Complaints: {ctx.total_complaints}

Formulate a clear, direct request to {responder}. Be specific about what data or analysis you need.
Address them by name. Keep your request under 100 words.
"""


def get_consultation_response_prompt(responder: str, question: str,
                                     ctx: PSURContext) -> str:
    """Build system prompt for the responder agent answering a consultation."""
    resp_info = AGENT_ROLES.get(responder, {})

    # Build a concise data context for the responder
    data_summary = (
        f"Device: {ctx.device_name}, UDI-DI: {ctx.udi_di}\n"
        f"Total Units: {ctx.total_units_sold:,}\n"
        f"Total Complaints: {ctx.total_complaints}\n"
        f"Complaint Rate: {ctx.complaint_rate_percent:.4f}%\n"
        f"Closed Complaints: {ctx.complaints_closed_count}\n"
        f"Root Cause Identified: {ctx.complaints_with_root_cause_identified}\n"
        f"Serious Incidents: {ctx.serious_incidents}\n"
        f"Total Vigilance Events: {ctx.total_vigilance_events}\n"
    )
    if ctx.total_units_by_year:
        data_summary += "Units by Year: " + ", ".join(
            f"{y}: {u:,}" for y, u in sorted(ctx.total_units_by_year.items())) + "\n"
    if ctx.total_complaints_by_year:
        data_summary += "Complaints by Year: " + ", ".join(
            f"{y}: {c}" for y, c in sorted(ctx.total_complaints_by_year.items())) + "\n"

    return f"""# {resp_info.get('name', responder)} -- Consultation Response

You are {resp_info.get('name', responder)}, {resp_info.get('title', 'PSUR Agent')}.
{resp_info.get('personality', '')}
Expertise: {resp_info.get('expertise', '')}

You are responding to a colleague's request in the team Discussion Panel.
All team members can see your response.

## Available Data
{data_summary}

## Colleague's Request
{question}

Respond directly and concisely. Address the requester by name.
Provide factual, data-driven answers. If data is insufficient, say so.
Keep your response under 200 words. No bullet points.
"""


# ---------------------------------------------------------------------------
# QC Prompt (Victoria) with Reputation Language
# ---------------------------------------------------------------------------

def get_qc_prompt(section_id: str, content: str, ctx: PSURContext) -> str:
    """Generate QC validation prompt for Victoria with reputation feedback."""
    section = SECTION_DEFINITIONS.get(section_id, {})
    denom = ctx.global_constraints.get("exposure_denominator", ctx.total_units_sold)
    author = section.get("agent", "Unknown")

    return f"""# Victoria -- Quality Control Validator

## Your Role
You are Victoria, the QC Validator for the PSUR generation team.
Your feedback is PUBLIC and visible to all agents in the Discussion Panel.
Your assessments affect agent reputation and trust in the team.

## Guidelines for Feedback
- PUBLICLY COMMEND excellent work: "Strong compliance by [agent name]" or "Well-sourced data presentation."
- PUBLICLY IDENTIFY issues with specific corrections: "[Agent name], the denominator in paragraph 2 must be {denom:,}, not [X]."
- Be firm but constructive. Every critique must include a specific correction.
- Your reputation depends on accuracy -- do not flag false issues.

## Section Under Review
Section {section_id}: {section.get('name', '')}
Author: {author}

## Validation Checklist
1. DATA INTEGRITY: All numbers sourced, calculations correct.
2. TEMPLATE COMPLIANCE: Correct title, numbering, required subsections present.
3. GLOBAL CONSTRAINTS: Denominator is {denom:,}. Total complaints is {ctx.total_complaints}. No violations.
4. FORMAT: Narrative only, no bullet points, paragraphs <= 4 sentences.
5. COMPLETENESS: No placeholders, no [TBD], no missing sections.
6. CLOSURE CONSISTENCY: Closed complaints = {ctx.complaints_closed_count}. Root cause identified = {ctx.complaints_with_root_cause_identified}. These must not be conflated.
7. SERIOUS INCIDENT ACCURACY: Total vigilance events = {ctx.total_vigilance_events}. Serious incidents (filtered) = {ctx.serious_incidents}. These are NOT the same number.
8. CROSS-REFERENCE: Check that content does not repeat other sections. Verify references to upstream sections are accurate.

## Content:
{content}

## Task
Verdict: PASS / CONDITIONAL / FAIL.
Any denominator != {denom:,} is automatic FAIL.
Provide specific, actionable feedback addressed to {author}.
If PASS, commend the agent publicly.
If FAIL/CONDITIONAL, list each issue with the exact correction needed.
"""
