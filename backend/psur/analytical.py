"""
Analytical Support Agents - Statler, Charley, Quincy.

These agents provide on-demand support to section agents:
  - Statler: Statistical calculations with explicit formulas
  - Charley: Chart and table generation (wraps chart_generator.py)
  - Quincy: Data quality auditing at workflow start
"""

import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.psur.context import PSURContext
from backend.psur.ai_client import call_ai
from backend.psur.chart_generator import generate_all_charts
from backend.database.session import get_db_context
from backend.database.models import ChatMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _post_msg(session_id: int, from_agent: str, to_agent: str,
                    message: str, msg_type: str = "normal"):
    """Insert a chat message into the DB."""
    with get_db_context() as db:
        db.add(ChatMessage(
            session_id=session_id, from_agent=from_agent,
            to_agent=to_agent, message=message,
            message_type=msg_type, timestamp=datetime.utcnow(),
        ))
        db.commit()


# ---------------------------------------------------------------------------
# Statler: Statistical Calculator
# ---------------------------------------------------------------------------

STATLER_SYSTEM = """You are Statler, the Statistical Calculator for a PSUR (Periodic Safety Update Report) generation team.

Your personality: Precise mathematician who shows all work. You ALWAYS provide:
1. The FORMULA used
2. The INPUT values (with sources)
3. The CALCULATION step-by-step
4. The RESULT with proper units
5. A VERIFICATION check

Rules:
- Use the exact data provided in the context. Never invent numbers.
- If data is insufficient, state what is missing.
- Flag any mathematical inconsistencies you find.
- Be concise but thorough. No bullet points in narrative.
- Address the requesting agent by name.
- Your math is FINAL. Other agents defer to your calculations.

Format your response as:
CALCULATION: [description]
Formula: [formula]
Inputs: [values]
Result: [answer]
Verification: [check]
"""


async def statler_calculate(ctx: PSURContext, task: str,
                            requester: str, session_id: int) -> str:
    """Statler performs a statistical calculation and posts results to chat."""
    data_context = _build_data_summary(ctx)

    user_prompt = (
        f"{requester} asks: {task}\n\n"
        f"## Available Data\n{data_context}\n\n"
        "Perform the calculation. Show formula, inputs, result, and verification."
    )

    result = await call_ai("Statler", STATLER_SYSTEM, user_prompt)
    if not result:
        result = f"Statler could not complete the calculation for: {task}. Insufficient data or AI unavailable."

    await _post_msg(session_id, "Statler", requester, result, "normal")
    return result


def _build_data_summary(ctx: PSURContext) -> str:
    """Build a concise data summary for Statler's calculations."""
    parts = []
    parts.append(f"Device: {ctx.device_name}")
    parts.append(f"Total Units Sold: {ctx.total_units_sold:,}")
    if ctx.total_units_by_year:
        parts.append("Units by Year: " + ", ".join(
            f"{y}: {u:,}" for y, u in sorted(ctx.total_units_by_year.items())))
    parts.append(f"Total Complaints: {ctx.total_complaints}")
    if ctx.total_complaints_by_year:
        parts.append("Complaints by Year: " + ", ".join(
            f"{y}: {c}" for y, c in sorted(ctx.total_complaints_by_year.items())))
    parts.append(f"Complaint Rate: {ctx.complaint_rate_percent:.4f}%")
    if ctx.complaint_rate_by_year:
        parts.append("Rate by Year: " + ", ".join(
            f"{y}: {r:.4f}%" for y, r in sorted(ctx.complaint_rate_by_year.items())))
    parts.append(f"Closed Complaints: {ctx.complaints_closed_count}")
    parts.append(f"Root Cause Identified: {ctx.complaints_with_root_cause_identified}")
    parts.append(f"Closure Rate: {ctx.investigation_closure_rate:.1f}%")
    parts.append(f"Serious Incidents: {ctx.serious_incidents}")
    parts.append(f"Total Vigilance Events: {ctx.total_vigilance_events}")
    parts.append(f"Deaths: {ctx.deaths}, Serious Injuries: {ctx.serious_injuries}")
    if ctx.complaints_by_type:
        parts.append("Complaints by Type: " + ", ".join(
            f"{k}: {v}" for k, v in ctx.complaints_by_type.items()))
    if ctx.complaints_by_severity:
        parts.append("Complaints by Severity: " + ", ".join(
            f"{k}: {v}" for k, v in ctx.complaints_by_severity.items()))
    parts.append(f"Product Defect: {ctx.complaints_product_defect}")
    parts.append(f"User Error: {ctx.complaints_user_error}")
    parts.append(f"Unrelated: {ctx.complaints_unrelated}")
    parts.append(f"Unconfirmed: {ctx.complaints_unconfirmed}")
    if ctx.total_units_by_region:
        parts.append("Units by Region: " + ", ".join(
            f"{r}: {u:,}" for r, u in ctx.total_units_by_region.items()))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Charley: Chart & Table Generator
# ---------------------------------------------------------------------------

async def charley_generate(ctx: PSURContext, task: str,
                           requester: str, session_id: int) -> str:
    """Charley generates charts/tables and stores them in the DB."""
    try:
        charts = generate_all_charts(ctx)
        if not charts:
            msg = (f"{requester}, chart generation returned no results. "
                   "Matplotlib may be unavailable or there is insufficient data for visualization.")
            await _post_msg(session_id, "Charley", requester, msg, "warning")
            return msg

        # Store charts in DB
        with get_db_context() as db:
            from backend.database.models import ChartAsset
            import base64
            for chart in charts:
                existing = db.query(ChartAsset).filter(
                    ChartAsset.session_id == session_id,
                    ChartAsset.chart_id == chart["chart_id"],
                ).first()
                png_bytes = base64.b64decode(chart["base64_png"])
                if existing:
                    setattr(existing, "png_data", png_bytes)
                    setattr(existing, "title", chart["title"])
                    setattr(existing, "category", chart["category"])
                    setattr(existing, "section_id", chart["section_id"])
                else:
                    asset = ChartAsset(
                        session_id=session_id,
                        chart_id=chart["chart_id"],
                        title=chart["title"],
                        category=chart["category"],
                        section_id=chart["section_id"],
                        png_data=png_bytes,
                    )
                    db.add(asset)
            db.commit()

        chart_names = ", ".join(c["title"] for c in charts)
        msg = (f"{requester}, I have generated {len(charts)} charts and tables: {chart_names}. "
               f"All are stored at 300 DPI and ready for embedding in the PSUR document. "
               f"You can reference them in your section narrative.")
        await _post_msg(session_id, "Charley", requester, msg, "success")
        return msg

    except Exception as e:
        traceback.print_exc()
        msg = f"{requester}, chart generation encountered an error: {e}"
        await _post_msg(session_id, "Charley", requester, msg, "error")
        return msg


# ---------------------------------------------------------------------------
# Quincy: Data Quality Auditor
# ---------------------------------------------------------------------------

QUINCY_SYSTEM = """You are Quincy, the Data Quality Auditor for a PSUR generation team.

Your personality: Meticulous auditor who finds every discrepancy. You run automated checks on uploaded data and report findings to the team.

Your audit report MUST cover:
1. DATA COMPLETENESS: Missing values, empty columns, incomplete records
2. DATE RANGE: Do records fall within the reporting period?
3. CROSS-FILE RECONCILIATION: Do sales totals match across files?
4. COLUMN DETECTION: Were all key columns detected correctly?
5. DATA QUALITY SCORE: Overall assessment (0-100)

Rules:
- Be factual. Report what you found, not what you expected.
- Flag blocking issues as ERRORS and non-blocking as WARNINGS.
- Address the team (Alex and all agents) directly.
- Format as a structured audit report.
- No bullet points in narrative sections.
"""


async def quincy_audit(ctx: PSURContext, session_id: int) -> str:
    """Quincy runs a data quality audit at workflow start."""
    audit_data = _build_audit_context(ctx)

    user_prompt = (
        "Run a comprehensive data quality audit on the uploaded PSUR data files. "
        "Report your findings to Alex and the team.\n\n"
        f"## Data Summary\n{audit_data}"
    )

    result = await call_ai("Quincy", QUINCY_SYSTEM, user_prompt)
    if not result:
        result = _fallback_audit(ctx)

    await _post_msg(session_id, "Quincy", "all", result, "normal")
    return result


def _build_audit_context(ctx: PSURContext) -> str:
    """Build audit context from PSURContext."""
    parts = []
    parts.append(f"Device: {ctx.device_name}")
    parts.append(f"Reporting Period: {ctx.period_start} to {ctx.period_end}")
    parts.append(f"Files Uploaded: {len(ctx.data_files)}")
    for f in ctx.data_files:
        parts.append(f"  - {f.get('filename', 'unknown')} (type: {f.get('type', 'unknown')})")

    parts.append(f"\nSales Data Available: {ctx.sales_data_available}")
    parts.append(f"Total Units: {ctx.total_units_sold:,}")
    parts.append(f"Complaint Data Available: {ctx.complaint_data_available}")
    parts.append(f"Total Complaints: {ctx.total_complaints}")
    parts.append(f"Vigilance Data Available: {ctx.vigilance_data_available}")
    parts.append(f"Total Vigilance Events: {ctx.total_vigilance_events}")
    parts.append(f"Serious Incidents: {ctx.serious_incidents}")

    if ctx.column_mappings:
        parts.append("\nColumn Mappings Detected:")
        for fname, mappings in ctx.column_mappings.items():
            parts.append(f"  {fname}:")
            for role, col in mappings.items():
                parts.append(f"    {role} -> {col if col else '[NOT DETECTED]'}")

    if ctx.data_quality_warnings:
        parts.append("\nExisting Warnings:")
        for w in ctx.data_quality_warnings:
            parts.append(f"  - {w}")

    parts.append(f"\nCompleteness Score: {ctx.completeness_score:.0f}%")
    return "\n".join(parts)


def _fallback_audit(ctx: PSURContext) -> str:
    """Generate a deterministic audit report if AI is unavailable."""
    issues: List[str] = []
    score = 100

    if not ctx.sales_data_available:
        issues.append("ERROR: No sales data available. Complaint rates cannot be calculated.")
        score -= 30
    elif ctx.total_units_sold == 0:
        issues.append("ERROR: Sales data present but zero units extracted. Check column detection.")
        score -= 25

    if not ctx.complaint_data_available:
        issues.append("WARNING: No complaint data uploaded. Complaint analysis will be limited.")
        score -= 20
    elif ctx.total_complaints == 0:
        issues.append("WARNING: Complaint file present but zero complaints extracted.")
        score -= 15

    if not ctx.vigilance_data_available:
        issues.append("WARNING: No vigilance data uploaded. Serious incident analysis will be limited.")
        score -= 10

    if ctx.complaints_closed_count == 0 and ctx.total_complaints > 0:
        issues.append("WARNING: No closed complaints detected. Investigation closure rate is 0%.")
        score -= 5

    if len(ctx.data_files) == 0:
        issues.append("ERROR: No data files uploaded at all.")
        score -= 40

    score = max(0, score)

    report = (
        f"DATA QUALITY AUDIT REPORT\n\n"
        f"Alex and team, here are my findings from the uploaded data.\n\n"
        f"Files analyzed: {len(ctx.data_files)}\n"
        f"Data quality score: {score}/100\n\n"
    )
    if issues:
        report += "Issues found:\n" + "\n".join(issues)
    else:
        report += "No significant issues detected. Data quality is acceptable for PSUR generation."

    return report
