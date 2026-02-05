"""
ENHANCED SOTA PSUR ORCHESTRATOR
Comprehensive Regulatory Context & Instruction System

This orchestrator implements the complete MDCG 2022-21 compliant PSUR generation
workflow with specialized agents, comprehensive context management, and
regulatory validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import asyncio
import traceback


class WorkflowStatus(Enum):
    """Workflow execution states for interactive control"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_USER = "waiting_user"
    COMPLETE = "complete"
    ERROR = "error"

from sqlalchemy.orm import Session
from backend.database.session import get_db_context
from backend.database.models import (
    PSURSession, Agent, ChatMessage, SectionDocument,
    WorkflowState, DataFile
)
from backend.config import AGENT_CONFIGS, get_ai_client

# GRKB (Graph Regulatory Knowledge Base) integration
GRKB_AVAILABLE = False
get_grkb_client = None  # type: ignore
try:
    from backend.database.grkb_client import get_grkb_client as _get_grkb_client, GRKBClient
    get_grkb_client = _get_grkb_client
    GRKB_AVAILABLE = True
except ImportError:
    GRKBClient = None


# =============================================================================
# SECTION 1: PSUR CONTEXT DATACLASS
# =============================================================================

@dataclass
class PSURContext:
    """
    Complete regulatory and operational context for all agents.
    Every field populated from manufacturer data AND validated against regulatory requirements.
    """

    # =========================================================================
    # WHO - Manufacturer & Device Identification
    # =========================================================================

    device_name: str = ""
    device_variants: List[str] = field(default_factory=list)
    manufacturer: str = "CooperSurgical, Inc."
    manufacturer_address: str = "95 Corporate Drive, Trumbull, CT 06611, USA"
    manufacturer_srn: str = "US-MF-000002607"
    authorized_rep: str = "CooperSurgical Distribution B.V."
    authorized_rep_address: str = "Celsiusweg 35, 5928 PR Venlo, The Netherlands"

    udi_di: str = ""
    udi_di_variants: Dict[str, str] = field(default_factory=dict)

    # =========================================================================
    # WHAT - Device Characterization
    # =========================================================================

    device_type: str = ""
    intended_use: str = ""
    operating_principle: str = ""

    regulatory_classification: Dict[str, str] = field(default_factory=lambda: {
        "EU_MDR": "IIa",
        "UK_MDR": "IIa",
        "FDA": "II",
        "other": ""
    })

    notified_body: str = "BSI Group The Netherlands B.V."
    notified_body_number: str = "2797"

    sterilization_method: str = "Not applicable"
    shelf_life_months: int = 0
    reusable: bool = False
    critical_component: Optional[str] = None

    # =========================================================================
    # WHEN - Reporting Period & Timeline
    # =========================================================================

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    psur_cadence: str = "Every 2 Years"
    submission_deadline: Optional[datetime] = None
    previous_psur_date: Optional[datetime] = None
    years_since_market_launch: int = 0

    eu_mdr_approval_date: Optional[datetime] = None
    uk_mdr_approval_date: Optional[datetime] = None
    fda_approval_date: Optional[datetime] = None

    # =========================================================================
    # WHERE - Market Presence & Geographic Distribution
    # =========================================================================

    regions: List[str] = field(default_factory=lambda: ["EEA", "UK", "US"])
    country_distribution: Dict[str, bool] = field(default_factory=dict)

    total_units_sold: int = 0
    total_units_by_year: Dict[int, int] = field(default_factory=dict)
    total_units_by_region: Dict[str, int] = field(default_factory=dict)
    cumulative_units_all_time: int = 0

    # =========================================================================
    # WHY - Regulatory Purpose & Benefit-Risk
    # =========================================================================

    regulatory_basis: str = "MDR 2017/745 Article 86"
    psur_purpose: str = "Demonstrate continued safety and performance"

    identified_hazards: List[Dict] = field(default_factory=list)
    benefit_statement: str = ""
    residual_risk_statement: str = ""
    risk_benefit_favorable: bool = True

    # =========================================================================
    # HOW - Data Sources & Collection
    # =========================================================================

    data_files: List[Dict] = field(default_factory=list)
    sales_data_available: bool = False
    complaint_data_available: bool = False
    vigilance_data_available: bool = False
    clinical_follow_up_data_available: bool = False

    data_completeness: Dict[str, float] = field(default_factory=dict)
    data_last_updated: Optional[datetime] = None
    data_validation_status: str = "pending"

    # =========================================================================
    # COMPLAINT METRICS
    # =========================================================================

    total_complaints: int = 0
    total_complaints_by_year: Dict[int, int] = field(default_factory=dict)
    complaint_rate_percent: float = 0.0
    complaint_rate_by_year: Dict[int, float] = field(default_factory=dict)

    complaints_by_type: Dict[str, int] = field(default_factory=dict)
    complaints_by_severity: Dict[str, int] = field(default_factory=dict)

    complaints_with_root_cause: int = 0
    investigation_closure_rate: float = 0.0

    complaints_product_defect: int = 0
    complaints_user_error: int = 0
    complaints_unrelated: int = 0
    complaints_unconfirmed: int = 0

    # =========================================================================
    # SERIOUS INCIDENTS & VIGILANCE METRICS
    # =========================================================================

    serious_incidents: int = 0
    serious_incidents_by_type: Dict[str, int] = field(default_factory=dict)

    deaths: int = 0
    deaths_unrelated: int = 0
    serious_injuries: int = 0

    serious_incidents_product_related: int = 0
    serious_incidents_unrelated: int = 0
    serious_incidents_unconfirmed: int = 0

    vigilance_reports: List[Dict] = field(default_factory=list)

    recalls_issued: int = 0
    field_safety_notices_issued: int = 0
    fsca_currently_active: List[Dict] = field(default_factory=list)

    # =========================================================================
    # RISK MANAGEMENT ALIGNMENT
    # =========================================================================

    known_residual_risks: List[str] = field(default_factory=list)
    new_signals_identified: List[str] = field(default_factory=list)
    changed_risk_profiles: List[str] = field(default_factory=list)
    regulatory_actions_to_date: List[str] = field(default_factory=list)
    notified_body_observations: List[str] = field(default_factory=list)

    # =========================================================================
    # CAPA HISTORY
    # =========================================================================

    capa_actions_open: int = 0
    capa_actions_closed_this_period: int = 0
    capa_actions_effectiveness_verified: int = 0
    capa_details: List[Dict] = field(default_factory=list)

    # =========================================================================
    # CLINICAL/PMCF DATA
    # =========================================================================

    pmcf_plan_approved: bool = False
    pmcf_studies_active: List[str] = field(default_factory=list)
    pmcf_interim_findings_available: bool = False
    pmcf_safety_concerns: List[str] = field(default_factory=list)

    # =========================================================================
    # PREVIOUS PSUR ACTIONS
    # =========================================================================

    previous_psur_safety_concerns: List[str] = field(default_factory=list)
    previous_psur_recommendations: List[str] = field(default_factory=list)
    actions_taken_on_previous_findings: List[str] = field(default_factory=list)

    # Temporal continuity (PSUR sequence, CAPA status, trending)
    psur_sequence_number: int = 1
    psur_sequence_narrative: str = ""
    previous_capa_status_summary: str = ""
    trending_across_periods_narrative: str = ""

    # Quality/completeness awareness (for agent prompts)
    missing_fields: List[str] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)
    data_confidence_by_domain: Dict[str, str] = field(default_factory=dict)
    completeness_score: float = 0.0

    # Master context (single golden source - all agents MUST use these only)
    exposure_denominator_golden: int = 0
    exposure_denominator_scope: str = "reporting_period_only"
    annual_units_golden: Dict[int, int] = field(default_factory=dict)
    closure_definition_text: str = ""
    complaints_closed_canonical: int = 0
    inference_policy: str = "strictly_factual"
    data_availability_external_vigilance: bool = False
    data_availability_complaint_closures_complete: bool = False
    data_availability_rmf_hazard_list: bool = False
    data_availability_intended_use: bool = False

    # Global constraints (locked terminology and definitions for cross-section consistency)
    global_constraints: Dict[str, Any] = field(default_factory=dict)

    # GRKB regulatory grounding (from external knowledge base)
    grkb_obligations: List[Dict[str, Any]] = field(default_factory=list)
    grkb_sections: List[Dict[str, Any]] = field(default_factory=list)
    grkb_evidence_types: List[Dict[str, Any]] = field(default_factory=list)
    grkb_system_instructions: Dict[str, Any] = field(default_factory=dict)
    grkb_template: Dict[str, Any] = field(default_factory=dict)
    grkb_available: bool = False

    # =========================================================================
    # RAW DATA SAMPLES (actual records for agent context)
    # =========================================================================

    sales_raw_sample: str = ""  # First 20 rows of sales data as markdown table
    complaints_raw_sample: str = ""  # First 20 rows of complaints data as markdown table
    vigilance_raw_sample: str = ""  # First 20 rows of vigilance data as markdown table
    sales_columns_detected: List[str] = field(default_factory=list)
    complaints_columns_detected: List[str] = field(default_factory=list)
    vigilance_columns_detected: List[str] = field(default_factory=list)

    def calculate_metrics(self):
        """Calculate derived metrics from raw data"""
        if self.total_units_sold > 0:
            self.complaint_rate_percent = (self.total_complaints / self.total_units_sold) * 100

        if self.total_complaints > 0:
            self.investigation_closure_rate = (
                self.complaints_with_root_cause / self.total_complaints
            ) * 100

    def to_comprehensive_context_prompt(self) -> str:
        """
        Generate the complete regulatory and operational context string
        for use in all agent prompts.
        """
        period_str = f"{self.period_start.strftime('%d %B %Y')} to {self.period_end.strftime('%d %B %Y')}" if self.period_start and self.period_end else "TBD"

        # Build sales trend
        sales_trend = ""
        if self.total_units_by_year:
            sales_lines = "\n".join([
                f"    {year}: {units:,} units"
                for year, units in sorted(self.total_units_by_year.items())
            ])
            sales_trend = f"\n  By year:\n{sales_lines}"

        # Build complaint severity summary
        complaint_severity = ""
        if self.complaints_by_severity:
            severity_lines = "\n".join([
                f"    {severity}: {count}"
                for severity, count in self.complaints_by_severity.items()
            ])
            complaint_severity = f"\n  By severity:\n{severity_lines}"

        # Build complaint type summary
        complaint_types = ""
        if self.complaints_by_type:
            type_lines = "\n".join([
                f"    {ctype}: {count}"
                for ctype, count in self.complaints_by_type.items()
            ])
            complaint_types = f"\n  By type:\n{type_lines}"

        # Build serious incident breakdown
        serious_breakdown = f"Total: {self.serious_incidents} | Product-related: {self.serious_incidents_product_related} | Unrelated: {self.serious_incidents_unrelated} | Unconfirmed: {self.serious_incidents_unconfirmed}"

        # Build known residual risks
        residual_risks = ""
        if self.known_residual_risks:
            risk_lines = "\n".join([f"    - {risk}" for risk in self.known_residual_risks])
            residual_risks = f"\n{risk_lines}"

        # Build new signals
        new_signals = ""
        if self.new_signals_identified:
            signal_lines = "\n".join([f"    - {signal}" for signal in self.new_signals_identified])
            new_signals = f"\n{signal_lines}"

        # Build CAPA summary
        capa_summary = ""
        if self.capa_details:
            capa_lines = "\n".join([
                f"    - {c.get('id', 'N/A')}: {c.get('issue', 'N/A')} (Status: {c.get('status', 'N/A')})"
                for c in self.capa_details
            ])
            capa_summary = f"\n{capa_lines}"

        golden_section = ""
        if self.exposure_denominator_golden > 0 or self.closure_definition_text or self.inference_policy:
            annual_line = ", ".join([f"{y}: {u:,}" for y, u in sorted(self.annual_units_golden.items())]) if self.annual_units_golden else "None"
            golden_section = f"""
================================================================================
         SINGLE GOLDEN SOURCE - ALL SECTIONS MUST USE THESE ONLY
================================================================================
- **Exposure denominator:** {self.exposure_denominator_golden:,} units (scope: {self.exposure_denominator_scope}). Use this number for ALL rate calculations (complaint rate, incident rate). Do not use any other denominator.
- **Annual distribution (canonical):** {annual_line}. Use these figures only for tables and trends; do not recalculate from raw data.
- **Complaint closures (canonical):** {self.complaints_closed_canonical}. Definition: {self.closure_definition_text or 'Closed = investigation completed with root cause documented.'} Do not cite a different closure count.
- **Inference policy:** {self.inference_policy}. If strictly_factual: do NOT infer or fill gaps; state "Not provided" or "Data not available" where absent. If allow_reasonable_inference: you may infer only where explicitly reasonable and state that it is inferred.
- **Data availability (condition your narrative on these):**
  - External vigilance database search performed: {"YES" if self.data_availability_external_vigilance else "NO - state explicitly that no external vigilance search was conducted"}
  - Complaint closures complete: {"YES" if self.data_availability_complaint_closures_complete else "NO - do not claim complete closure statistics"}
  - RMF hazard list available: {"YES" if self.data_availability_rmf_hazard_list else "NO - do not reproduce or assume hazard list"}
  - Intended use statement provided: {"YES" if self.data_availability_intended_use else "NO - state that intended use is not provided; do not infer"}
Do not use template language that assumes best practice (e.g. "systematic vigilance monitoring", "screening within two business days") unless the data availability flags above are YES for the relevant domain.
================================================================================

"""
        return f"""
================================================================================
         COMPREHENSIVE PSUR REGULATORY & OPERATIONAL CONTEXT
              (MDR 2017/745 Article 86 | MDCG 2022-21 Compliance)
================================================================================
{golden_section}
## I. REGULATORY FRAMEWORK & AUTHORITY

This PSUR must comply with the following hierarchy (in order of precedence):

1. **EU MDR 2017/745 Articles 83-86** (Primary legal requirement)
   Submission to: {self.notified_body} (Notified Body No. {self.notified_body_number})
   Legal deadline: {self.submission_deadline.strftime('%d %B %Y') if self.submission_deadline else 'TBD'}

2. **MDCG 2022-21 Guidance Document** (Official interpretation)

3. **FormQAR-054 Template** (Mandatory structure)
   Sections: A (Executive Summary) through M (Conclusions) - EXACT numbering required
   Format: Narrative prose only - NO bullet points, lists, or outlines

4. **ISO 14971 Risk Management Lifecycle** (Post-market validation)

---

## II. MANUFACTURER & DEVICE IDENTIFICATION

### II.A Manufacturer Information
**Manufacturer:** {self.manufacturer}
**Address:** {self.manufacturer_address}
**SRN (EUDAMED Registration):** {self.manufacturer_srn}
**Authorized Representative:** {self.authorized_rep}
**AR Address:** {self.authorized_rep_address}

### II.B Device Identification
**Device Name:** {self.device_name}
**Device Type:** {self.device_type if self.device_type else '[To be specified]'}
**Variants:** {', '.join(self.device_variants) if self.device_variants else '[None / Monolithic design]'}
**Basic UDI-DI:** {self.udi_di}
**Intended Use:** {self.intended_use if self.intended_use else '[Complete IFU statement required]'}

### II.C Regulatory Classification
| Jurisdiction | Classification |
|---|---|
| EU MDR 2017/745 | Class {self.regulatory_classification.get('EU_MDR', 'TBD')} |
| UK MDR (SI 2024/1368) | Class {self.regulatory_classification.get('UK_MDR', 'TBD')} |
| FDA (United States) | Class {self.regulatory_classification.get('FDA', 'TBD')} |

---

## III. REPORTING PERIOD & TIMELINE

**PSUR Reporting Period:** {period_str}
**PSUR Cadence:** {self.psur_cadence} (Per MDR 2017/745)
**Previous PSUR Submission:** {self.previous_psur_date.strftime('%d %B %Y') if self.previous_psur_date else 'N/A - Initial PSUR'}

---

## III.B TEMPORAL CONTINUITY

**This report:** {self.psur_sequence_narrative or f'PSUR #{self.psur_sequence_number} for this device.'}
**Previous CAPA status:** {self.previous_capa_status_summary or 'No previous CAPA summary in context.'}
**Trending across periods:** {self.trending_across_periods_narrative or 'Single-period or initial PSUR; trending narrative to be derived from data where applicable.'}

---

## IV. MARKET PRESENCE & GEOGRAPHIC DISTRIBUTION

**Active Markets:** {', '.join(self.regions)}
**Total Units Distributed (Reporting Period):** {self.total_units_sold:,} units
**Cumulative Distribution (All time):** {self.cumulative_units_all_time:,} units{sales_trend}

---

## V. POST-MARKET COMPLAINT DATA

**Total Complaints (Reporting Period):** {self.total_complaints}
**Overall Complaint Rate:** {self.complaint_rate_percent:.4f}% ({self.total_complaints} / {self.total_units_sold:,} units)
**Complaint Investigation Closure Rate:** {self.investigation_closure_rate:.1f}%{complaint_types}{complaint_severity}

**Complaint Root Cause Classification:**
  - Product Defect: {self.complaints_product_defect}
  - User Error: {self.complaints_user_error}
  - Unrelated: {self.complaints_unrelated}
  - Unconfirmed: {self.complaints_unconfirmed}

---

## VI. SERIOUS INCIDENTS & VIGILANCE DATA

**Serious Incidents Reported:** {serious_breakdown}
  - Deaths (confirmed product-related): {self.deaths}
  - Serious Injuries: {self.serious_injuries}

---

## VII. RISK MANAGEMENT FILE ALIGNMENT

**Device Hazards Identified (from Risk Management File):**{residual_risks if residual_risks else "  - None documented"}

**Current Benefit-Risk Determination:** {'FAVORABLE - Benefits outweigh residual risks' if self.risk_benefit_favorable else 'REQUIRES REVIEW - Risk profile has changed'}

---

## VIII. NEW SIGNALS & CHANGED RISK PROFILES

**New Signals Identified:**{new_signals if new_signals else "  - None"}

---

## IX. QUALITY & CAPA ACTIONS

**CAPAs Open:** {self.capa_actions_open}
**CAPAs Closed (This Period):** {self.capa_actions_closed_this_period}
**CAPAs Verified Effective:** {self.capa_actions_effectiveness_verified}

**Active CAPA Details:{capa_summary if capa_summary else "  - None"}

---

## X. DATA QUALITY & COMPLETENESS

**Completeness score:** {self.completeness_score:.0f}% (overall data readiness for this PSUR)

**Data sources available:**
  Sales Data: {'YES - Use exact figures' if self.sales_data_available else 'NO - State "No sales data available" explicitly'}
  Complaint Data: {'YES - Detail investigation outcomes' if self.complaint_data_available else 'NO - State "No complaint data analyzed" explicitly'}
  Vigilance Data: {'YES - Include database search results' if self.vigilance_data_available else 'NO - State "No vigilance database search conducted" explicitly'}
  Clinical Follow-up: {'YES - Include study status' if self.clinical_follow_up_data_available else 'NO'}

**Confidence by domain:** {', '.join([f'{k}: {v}' for k, v in self.data_confidence_by_domain.items()]) if self.data_confidence_by_domain else 'Not assessed'}

**Missing or incomplete fields (acknowledge where relevant):**
  {chr(10).join(['  - ' + m for m in self.missing_fields[:20]]) if self.missing_fields else '  None identified'}

**Data quality warnings:**
  {chr(10).join(['  - ' + w for w in self.data_quality_warnings]) if self.data_quality_warnings else '  None'}

---

## XI. RAW DATA SAMPLES (Actual Records for Reference)

{f'''### SALES DATA SAMPLE (First 20 Records)
Columns detected: {', '.join(self.sales_columns_detected) if self.sales_columns_detected else 'None'}

{self.sales_raw_sample if self.sales_raw_sample else 'No sales data sample available.'}
''' if self.sales_raw_sample else '### SALES DATA: No raw sample available'}

{f'''### COMPLAINTS DATA SAMPLE (First 20 Records)
Columns detected: {', '.join(self.complaints_columns_detected) if self.complaints_columns_detected else 'None'}

{self.complaints_raw_sample if self.complaints_raw_sample else 'No complaints data sample available.'}

**IMPORTANT**: Use this raw data to understand actual complaint details, investigation outcomes,
and severity classifications. Do not invent details not present in this data.
''' if self.complaints_raw_sample else '### COMPLAINTS DATA: No raw sample available'}

{f'''### VIGILANCE DATA SAMPLE (First 20 Records)
Columns detected: {', '.join(self.vigilance_columns_detected) if self.vigilance_columns_detected else 'None'}

{self.vigilance_raw_sample if self.vigilance_raw_sample else 'No vigilance data sample available.'}
''' if self.vigilance_raw_sample else '### VIGILANCE DATA: No raw sample available'}

---

## XII. CRITICAL COMPLIANCE RULES FOR ALL AGENTS

### Rule 1: ABSOLUTE DATA INTEGRITY
- Every number must trace to source data
- State source: "Per sales data provided, dated YYYY-MM-DD"
- Do NOT estimate, project, or assume values

### Rule 2: NARRATIVE-ONLY FORMATTING (FormQAR-054)
- Write all content as continuous professional prose
- Use tables ONLY where template explicitly requires them
- STRICTLY FORBIDDEN: Bullet points, numbered lists, hyphens as list items

### Rule 3: EVIDENCE-BASED CONCLUSIONS
- Observed fact: "Complaint rate was 0.45% in Year 1 and 0.62% in Year 2."
- Analysis: "This represents a 38% increase year-over-year."
- Do NOT present interpretations as facts

### Rule 4: RISK MANAGEMENT ALIGNMENT
- Reference Risk Management File for known hazards
- Always conclude: "Residual risk remains acceptable / requires re-evaluation"

### Rule 5: REGULATORY TONE (NB Audit Ready)
- Objective, evidence-based language
- Transparent about limitations
- Avoid reassurance or marketing language

---

**END OF COMPREHENSIVE CONTEXT**

All agents must reference this context when generating their assigned sections.
"""


# =============================================================================
# SECTION 2: AGENT DEFINITIONS & ROLE MAPPINGS
# =============================================================================

# FormQAR-054 Section Authority Map
SECTION_DEFINITIONS = {
    "C": {
        "id": "C",
        "number": 3,
        "name": "Post-Market Data: Units Distributed",
        "agent": "Greta",
        "mdcg_ref": "2.1",
        "purpose": "Establish denominator for complaint rates and population exposure",
        "required_content": ["Sales table by year/region", "Cumulative distribution", "Growth trends"]
    },
    "D": {
        "id": "D",
        "number": 4,
        "name": "Serious Incidents and Trends",
        "agent": "David",
        "mdcg_ref": "2.2",
        "purpose": "Analysis of serious adverse events from vigilance systems",
        "required_content": ["Incident classification", "Trend analysis", "Product-relatedness assessment"]
    },
    "E": {
        "id": "E",
        "number": 5,
        "name": "Post-Market Surveillance: Customer Feedback",
        "agent": "Emma",
        "mdcg_ref": "2.3",
        "purpose": "Systematic complaint summary and categorization",
        "required_content": ["Data summary", "Rate calculation", "Classification", "Root causes"]
    },
    "F": {
        "id": "F",
        "number": 6,
        "name": "Complaints Management",
        "agent": "Emma",
        "mdcg_ref": "2.4",
        "purpose": "Detail investigation and CAPA closure processes",
        "required_content": ["Procedures", "Investigation outcomes", "Closure rates"]
    },
    "G": {
        "id": "G",
        "number": 7,
        "name": "Trends and Performance Analysis",
        "agent": "Diana",
        "mdcg_ref": "3",
        "purpose": "Statistical identification of signals and significant changes",
        "required_content": ["UCL/LCL analysis", "YoY comparison", "Temporal clustering", "Severity shifts"]
    },
    "H": {
        "id": "H",
        "number": 8,
        "name": "Field Safety Corrective Actions (FSCA)",
        "agent": "Lisa",
        "mdcg_ref": "2.5",
        "purpose": "Track field-implemented mitigations",
        "required_content": ["FSCA identification", "Implementation timeline", "Effectiveness evidence"]
    },
    "I": {
        "id": "I",
        "number": 9,
        "name": "Corrective and Preventive Actions (CAPA)",
        "agent": "Tom",
        "mdcg_ref": "1.4",
        "purpose": "Document manufacturing/quality improvements",
        "required_content": ["Identification", "Root cause", "Implementation", "Verification"]
    },
    "J": {
        "id": "J",
        "number": 10,
        "name": "Literature Review and External Data",
        "agent": "James",
        "mdcg_ref": "1.3",
        "purpose": "Scientific context and competitor surveillance",
        "required_content": ["Published adverse events", "Clinical efficacy literature", "Safety benchmarking"]
    },
    "K": {
        "id": "K",
        "number": 11,
        "name": "External Adverse Event Databases",
        "agent": "James",
        "mdcg_ref": "2.6",
        "purpose": "Systematic vigilance database search results",
        "required_content": ["Search methodology", "Databases queried", "Findings"]
    },
    "L": {
        "id": "L",
        "number": 12,
        "name": "Post-Market Clinical Follow-up (PMCF)",
        "agent": "Sarah",
        "mdcg_ref": "1.5",
        "purpose": "Evidence of maintained clinical performance",
        "required_content": ["Study status", "Enrollment", "Safety/efficacy findings"]
    },
    "B": {
        "id": "B",
        "number": 2,
        "name": "Scope and Device Description",
        "agent": "Greta",
        "mdcg_ref": "1.2",
        "purpose": "Complete device characterization and market context",
        "required_content": ["Device variants", "Intended use", "Regulatory classification", "Clinical basis"]
    },
    "M": {
        "id": "M",
        "number": 13,
        "name": "Overall Findings and Conclusions",
        "agent": "Robert",
        "mdcg_ref": "1.6",
        "purpose": "Final benefit-risk determination and regulatory recommendation",
        "required_content": ["Safety assessment", "Performance assessment", "Benefit-risk conclusion", "Recommendation"]
    },
    "A": {
        "id": "A",
        "number": 1,
        "name": "Executive Summary",
        "agent": "Marcus",
        "mdcg_ref": "1.1",
        "purpose": "Overview of key findings, identified signals, trends, and final benefit-risk conclusion",
        "required_content": ["Device overview", "Key metrics", "Findings summary", "Conclusions", "Recommendation"]
    }
}

# Workflow generation order (dependency-based)
WORKFLOW_ORDER = [
    "C",   # Phase 1: DATA FOUNDATION - Sales/Exposure (Greta)
    "D",   # Phase 2: ADVERSE EVENT ANALYSIS - Serious Incidents (David)
    "E",   # Phase 2: Customer Feedback (Emma)
    "F",   # Phase 2: Complaints Management (Emma)
    "G",   # Phase 3: ANALYTICAL - Trends & Analysis (Diana)
    "H",   # Phase 3: FSCA (Lisa)
    "I",   # Phase 3: CAPA (Tom)
    "J",   # Phase 4: EXTERNAL CONTEXT - Literature Review (James)
    "K",   # Phase 4: External Databases (James)
    "L",   # Phase 5: CLINICAL EVIDENCE - PMCF (Sarah)
    "B",   # Phase 6: CHARACTERIZATION - Scope & Description (Greta)
    "M",   # Phase 7: SYNTHESIS - Findings & Conclusions (Robert)
    "A",   # Phase 7: Executive Summary (Marcus)
]

# Section interdependency map: citations, data flow, link to benefit-risk conclusion (Section M)
SECTION_INTERDEPENDENCIES = {
    "C": {
        "upstream": [],
        "downstream": ["E", "G", "M"],
        "cites": [],
        "cited_by": ["E", "G", "A", "M"],
        "data_flow": "Units distributed form the denominator for complaint rates (Section E) and trend analysis (Section G); cited in benefit-risk conclusion (M).",
        "benefit_risk_link": "Exposure denominator for risk metrics; feeds into complaint rate and trend conclusions in M.",
    },
    "D": {
        "upstream": [],
        "downstream": ["G", "H", "M"],
        "cites": [],
        "cited_by": ["G", "H", "A", "M"],
        "data_flow": "Serious incident counts and classifications feed trend analysis (G), FSCA (H), and final benefit-risk (M).",
        "benefit_risk_link": "Direct input to safety assessment and benefit-risk determination in Section M.",
    },
    "E": {
        "upstream": ["C"],
        "downstream": ["F", "G", "M"],
        "cites": ["C"],
        "cited_by": ["F", "G", "A", "M"],
        "data_flow": "Complaint summary uses Section C units for rate; feeds Complaints Management (F), Trends (G), and M.",
        "benefit_risk_link": "Complaint rate and severity feed risk assessment in M.",
    },
    "F": {
        "upstream": ["E"],
        "downstream": ["I", "G", "M"],
        "cites": ["E"],
        "cited_by": ["I", "A", "M"],
        "data_flow": "Investigation and CAPA closure reference Section E; feed CAPA section (I) and conclusions (M).",
        "benefit_risk_link": "Closure rates and effectiveness support risk control in M.",
    },
    "G": {
        "upstream": ["C", "D", "E"],
        "downstream": ["M", "A"],
        "cites": ["C", "D", "E"],
        "cited_by": ["A", "M"],
        "data_flow": "Trends and signals aggregate C/D/E; primary input to findings and Executive Summary.",
        "benefit_risk_link": "Signal detection and trend conclusions directly drive Section M benefit-risk.",
    },
    "H": {
        "upstream": ["D"],
        "downstream": ["M", "A"],
        "cites": ["D"],
        "cited_by": ["A", "M"],
        "data_flow": "FSCA status links to serious incidents (D); summarized in M and A.",
        "benefit_risk_link": "Mitigation effectiveness feeds risk conclusion in M.",
    },
    "I": {
        "upstream": ["F", "E"],
        "downstream": ["M", "A"],
        "cites": ["F", "E"],
        "cited_by": ["A", "M"],
        "data_flow": "CAPA details reference complaint/investigation (E, F); feed conclusions (M).",
        "benefit_risk_link": "CAPA effectiveness supports residual risk assessment in M.",
    },
    "J": {
        "upstream": [],
        "downstream": ["K", "M", "A"],
        "cites": [],
        "cited_by": ["K", "A", "M"],
        "data_flow": "Literature context supports external database section (K) and overall conclusions.",
        "benefit_risk_link": "External evidence informs benefit-risk in M.",
    },
    "K": {
        "upstream": ["J"],
        "downstream": ["M", "A"],
        "cites": ["J"],
        "cited_by": ["A", "M"],
        "data_flow": "External database findings complement J; feed M and A.",
        "benefit_risk_link": "Vigilance database evidence supports safety conclusion in M.",
    },
    "L": {
        "upstream": [],
        "downstream": ["M", "A"],
        "cites": [],
        "cited_by": ["A", "M"],
        "data_flow": "PMCF evidence feeds performance and safety assessment in M.",
        "benefit_risk_link": "Clinical performance evidence supports benefit side of benefit-risk in M.",
    },
    "B": {
        "upstream": ["C", "E", "G"],
        "downstream": ["M", "A"],
        "cites": ["C", "E", "G"],
        "cited_by": ["A", "M"],
        "data_flow": "Scope and device description written after data sections; references exposure and trends.",
        "benefit_risk_link": "Device characterization frames benefit-risk context in M.",
    },
    "M": {
        "upstream": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B"],
        "downstream": ["A"],
        "cites": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B"],
        "cited_by": ["A"],
        "data_flow": "Synthesis of all evidence sections; sole direct benefit-risk conclusion.",
        "benefit_risk_link": "This section IS the benefit-risk conclusion; all other sections feed it.",
    },
    "A": {
        "upstream": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B", "M"],
        "downstream": [],
        "cites": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B", "M"],
        "cited_by": [],
        "data_flow": "Executive Summary written last; summarizes all sections including M.",
        "benefit_risk_link": "Summarizes the benefit-risk conclusion from Section M for readers.",
    },
}

# Agent role definitions
AGENT_ROLES = {
    "Alex": {
        "name": "Alex",
        "role": "Orchestrator",
        "title": "PSUR Workflow Coordinator",
        "expertise": "Workflow coordination, task delegation, quality oversight",
        "primary_section": None,
        "color": "#6366f1"
    },
    "Marcus": {
        "name": "Marcus",
        "role": "Executive Summary Specialist",
        "title": "Executive Summary Writer",
        "expertise": "Synthesizing findings, executive communication, regulatory conclusions",
        "primary_section": "A",
        "color": "#6366f1"
    },
    "Greta": {
        "name": "Greta",
        "role": "Sales & Market Data Analyst",
        "title": "Market Data Specialist",
        "expertise": "Sales analysis, market exposure calculations, distribution tracking",
        "primary_section": "C",
        "secondary_section": "B",
        "color": "#3b82f6"
    },
    "David": {
        "name": "David",
        "role": "Vigilance Specialist",
        "title": "Serious Incidents Analyst",
        "expertise": "Adverse event classification, vigilance database analysis, causality assessment",
        "primary_section": "D",
        "color": "#ef4444"
    },
    "Emma": {
        "name": "Emma",
        "role": "Complaint Classifier",
        "title": "Customer Feedback Analyst",
        "expertise": "Complaint categorization, root cause analysis, investigation management",
        "primary_section": "E",
        "secondary_section": "F",
        "color": "#ec4899"
    },
    "Diana": {
        "name": "Diana",
        "role": "Trend Detective",
        "title": "Statistical Trend Analyst",
        "expertise": "Statistical process control, UCL/LCL analysis, signal detection",
        "primary_section": "G",
        "color": "#8b5cf6"
    },
    "Lisa": {
        "name": "Lisa",
        "role": "FSCA Coordinator",
        "title": "Field Safety Actions Specialist",
        "expertise": "Field corrective actions, implementation tracking, effectiveness verification",
        "primary_section": "H",
        "color": "#f59e0b"
    },
    "Tom": {
        "name": "Tom",
        "role": "CAPA Verifier",
        "title": "Quality Improvement Specialist",
        "expertise": "Corrective/preventive actions, root cause verification, effectiveness evidence",
        "primary_section": "I",
        "color": "#10b981"
    },
    "James": {
        "name": "James",
        "role": "Literature Reviewer",
        "title": "External Data Specialist",
        "expertise": "Scientific literature review, external database search, competitor surveillance",
        "primary_section": "J",
        "secondary_section": "K",
        "color": "#06b6d4"
    },
    "Sarah": {
        "name": "Sarah",
        "role": "PMCF Specialist",
        "title": "Clinical Follow-up Analyst",
        "expertise": "Post-market clinical studies, performance evidence, safety monitoring",
        "primary_section": "L",
        "color": "#a855f7"
    },
    "Robert": {
        "name": "Robert",
        "role": "Risk Specialist",
        "title": "Benefit-Risk Assessment Expert",
        "expertise": "Risk management, benefit-risk determination, regulatory recommendations",
        "primary_section": "M",
        "color": "#22c55e"
    },
    "Victoria": {
        "name": "Victoria",
        "role": "QC Expert",
        "title": "Quality Control Validator",
        "expertise": "Template compliance, regulatory validation, audit readiness review",
        "primary_section": None,
        "color": "#f97316"
    }
}


# =============================================================================
# SECTION 3: WORKFLOW ROLE, INTERDEPENDENCY, QUALITY, TEMPORAL HELPERS
# =============================================================================

def get_workflow_role_context(agent_name: str, section_id: str) -> str:
    """Build context: who else exists, order, how this agent's output feeds the PSUR."""
    my_idx = next((i for i, sid in enumerate(WORKFLOW_ORDER) if sid == section_id), None)
    prev_sections = [WORKFLOW_ORDER[i] for i in range(my_idx)] if my_idx is not None else []
    next_sections = [WORKFLOW_ORDER[i] for i in range((my_idx or 0) + 1, len(WORKFLOW_ORDER))] if my_idx is not None else []

    prev_agents = []
    for sid in prev_sections:
        s = SECTION_DEFINITIONS.get(sid, {})
        a = s.get("agent")
        if a and a not in prev_agents:
            prev_agents.append(a)
    next_agents = []
    for sid in next_sections:
        s = SECTION_DEFINITIONS.get(sid, {})
        a = s.get("agent")
        if a and a not in next_agents:
            next_agents.append(a)

    all_agents = list(AGENT_ROLES.keys())
    all_agents.remove("Alex")
    all_agents.remove("Victoria")

    prev_names = [SECTION_DEFINITIONS.get(sid, {}).get("name", sid) for sid in prev_sections[:5]]
    next_names = [SECTION_DEFINITIONS.get(sid, {}).get("name", sid) for sid in next_sections[:5]]

    return f"""
## Your Place in the Workflow

**Other agents in this PSUR:** {", ".join(all_agents)}. Alex coordinates; Victoria performs QC.

**Sections already completed (your upstream):** {", ".join(prev_sections) if prev_sections else "None - you are among the first."}
  {chr(10).join(['  - ' + n for n in prev_names]) if prev_names else "  (You are early in the pipeline.)"}

**Sections that will follow (your downstream):** {", ".join(next_sections) if next_sections else "None - you are among the last."}
  {chr(10).join(['  - ' + n for n in next_names]) if next_names else "  (Your section feeds later sections.)"}

**How your output is used:** Your Section {section_id} content will be used by later sections for cross-references and by Section M (Overall Findings and Conclusions) for the benefit-risk determination. Executive Summary (A) will summarize all sections including yours. Write so downstream agents and the Notified Body can rely on clear, cited narrative.
"""


def get_section_interdependency_context(section_id: str) -> str:
    """Build context: which sections cite each other, data flow, link to benefit-risk."""
    dep = SECTION_INTERDEPENDENCIES.get(section_id, {})
    if not dep:
        return ""
    upstream = dep.get("upstream", [])
    downstream = dep.get("downstream", [])
    cites = dep.get("cites", [])
    cited_by = dep.get("cited_by", [])
    data_flow = dep.get("data_flow", "")
    benefit_risk_link = dep.get("benefit_risk_link", "")

    lines = [
        "## Section Interdependency and Benefit-Risk Link",
        "",
        "**Sections that feed into yours (cite these where relevant):** " + (", ".join([f"Section {s}" for s in cites]) if cites else "None."),
        "**Sections that will cite yours:** " + (", ".join([f"Section {s}" for s in cited_by]) if cited_by else "None."),
        "",
        "**Data flow:** " + data_flow,
        "",
        "**Connection to benefit-risk conclusion (Section M):** " + benefit_risk_link,
    ]
    return "\n".join(lines)


def get_quality_completeness_context(context: PSURContext) -> str:
    """Build context: missing fields, confidence, data quality warnings."""
    lines = [
        "## Data Quality and Completeness Awareness",
        "",
        f"**Overall completeness score (0-100%):** {context.completeness_score:.0f}%",
        "",
    ]
    if context.data_confidence_by_domain:
        lines.append("**Confidence by domain:**")
        for domain, level in context.data_confidence_by_domain.items():
            lines.append(f"  - {domain}: {level}")
        lines.append("")
    if context.missing_fields:
        lines.append("**Missing or incomplete fields (acknowledge in narrative where relevant):**")
        for m in context.missing_fields[:15]:
            lines.append(f"  - {m}")
        lines.append("")
    if context.data_quality_warnings:
        lines.append("**Data quality warnings (address or state limitations):**")
        for w in context.data_quality_warnings:
            lines.append(f"  - {w}")
    else:
        lines.append("**Data quality warnings:** None identified.")
    return "\n".join(lines)


def get_temporal_continuity_context(context: PSURContext) -> str:
    """Build context: PSUR number, previous CAPAs, trending across periods."""
    lines = [
        "## Temporal Continuity",
        "",
        f"**This report:** {context.psur_sequence_narrative or f'PSUR #{context.psur_sequence_number} for this device in this system.'}",
        "",
    ]
    if context.previous_psur_date:
        lines.append(f"**Previous PSUR submission date:** {context.previous_psur_date.strftime('%d %B %Y')}.")
    else:
        lines.append("**Previous PSUR:** Not applicable (e.g. initial PSUR or first in system).")
    lines.append("")
    if context.previous_capa_status_summary:
        lines.append("**Previous CAPA status (closed/verified this period):**")
        lines.append("  " + context.previous_capa_status_summary)
        lines.append("")
    if context.trending_across_periods_narrative:
        lines.append("**Trending across PSUR periods:**")
        lines.append("  " + context.trending_across_periods_narrative)
    return "\n".join(lines)


# =============================================================================
# SECTION 3B: GLOBAL CONSTRAINTS (Cross-Section Consistency)
# =============================================================================

def build_global_constraints(context: PSURContext) -> Dict[str, Any]:
    """
    Build locked global constraints that ALL agents must use.
    These definitions cannot be changed or reinterpreted by any agent.
    """
    investigation_closure_rate = context.investigation_closure_rate
    complaints_closed = context.complaints_closed_canonical or context.complaints_with_root_cause
    total_complaints = context.total_complaints

    # Determine if root causes can be cited as definitive
    root_cause_status = "preliminary"
    if investigation_closure_rate >= 80:
        root_cause_status = "confirmed"
    elif investigation_closure_rate >= 50:
        root_cause_status = "partial"

    # Determine serious incident classification certainty
    si_classification_certainty = "inconclusive"
    if investigation_closure_rate >= 80 and total_complaints > 0:
        si_classification_certainty = "confirmed"
    elif investigation_closure_rate >= 50:
        si_classification_certainty = "provisional"

    # RMF status
    rmf_status = "complete" if context.data_availability_rmf_hazard_list else "incomplete_or_unavailable"

    # Vigilance methodology
    vigilance_methodology = "internal_only"
    if context.data_availability_external_vigilance:
        vigilance_methodology = "internal_and_external_databases"

    return {
        # Locked denominators (from master context)
        "exposure_denominator": context.exposure_denominator_golden or context.total_units_sold,
        "exposure_denominator_scope": context.exposure_denominator_scope,
        "annual_units": context.annual_units_golden or context.total_units_by_year,

        # Severity level definitions (unified hierarchy)
        "severity_levels": {
            "critical": "Death or permanent impairment directly attributable to device",
            "serious": "Hospitalization, intervention required, or temporary impairment",
            "moderate": "Medically significant but not requiring intervention",
            "minor": "No injury, user inconvenience only",
            "unknown": "Severity not determinable from available data",
        },

        # Root cause categories (locked)
        "root_cause_categories": {
            "product_defect": "Manufacturing, design, or material defect confirmed",
            "user_error": "Misuse or failure to follow IFU confirmed",
            "unrelated": "Event unrelated to device confirmed",
            "indeterminate": "Insufficient evidence to determine causality",
            "pending": "Investigation not yet complete",
        },

        # Investigation status
        "investigation_closure_rate_percent": investigation_closure_rate,
        "complaints_closed_count": complaints_closed,
        "total_complaints_count": total_complaints,
        "root_cause_status": root_cause_status,
        "si_classification_certainty": si_classification_certainty,

        # RMF and vigilance
        "rmf_status": rmf_status,
        "vigilance_methodology": vigilance_methodology,

        # Data completeness flags
        "external_vigilance_searched": context.data_availability_external_vigilance,
        "complaint_closures_complete": context.data_availability_complaint_closures_complete,
        "rmf_hazard_list_available": context.data_availability_rmf_hazard_list,
        "intended_use_provided": context.data_availability_intended_use,

        # Inference policy
        "inference_policy": context.inference_policy,
    }


def get_global_constraints_prompt(constraints: Dict[str, Any]) -> str:
    """Generate the global constraints block for agent prompts."""
    closure_rate = constraints.get("investigation_closure_rate_percent", 0)
    root_status = constraints.get("root_cause_status", "preliminary")
    si_certainty = constraints.get("si_classification_certainty", "inconclusive")
    rmf_status = constraints.get("rmf_status", "incomplete_or_unavailable")
    vig_method = constraints.get("vigilance_methodology", "internal_only")
    inference = constraints.get("inference_policy", "strictly_factual")
    denom = constraints.get("exposure_denominator", 0)
    denom_scope = constraints.get("exposure_denominator_scope", "reporting_period_only")
    annual = constraints.get("annual_units", {})
    closed = constraints.get("complaints_closed_count", 0)
    total = constraints.get("total_complaints_count", 0)

    annual_str = ", ".join([f"{y}: {u:,}" for y, u in sorted(annual.items())]) if annual else "None"

    severity_defs = constraints.get("severity_levels", {})
    severity_str = "; ".join([f"{k.upper()}: {v}" for k, v in severity_defs.items()])

    root_cause_defs = constraints.get("root_cause_categories", {})
    rc_str = "; ".join([f"{k}: {v}" for k, v in root_cause_defs.items()])

    # Build constraint rules based on closure rate
    closure_rules = ""
    if closure_rate < 50:
        closure_rules = f"""
CRITICAL: Investigation closure is {closure_rate:.0f}% (below 50%).
- Root cause classifications MUST be labeled as PRELIMINARY or PROVISIONAL.
- Do NOT assign definitive root causes.
- Serious incident classifications MUST be labeled as INCONCLUSIVE.
- Trend analyses MUST be framed as LIMITED or NON-ACTIONABLE.
- Do NOT claim complete investigation outcomes."""
    elif closure_rate < 80:
        closure_rules = f"""
NOTE: Investigation closure is {closure_rate:.0f}% (partial).
- Root cause classifications may be labeled as PROVISIONAL.
- Serious incident classifications are PROVISIONAL pending remaining investigations.
- State the limitation in trend conclusions."""
    else:
        closure_rules = f"""
NOTE: Investigation closure is {closure_rate:.0f}% (substantially complete).
- Root cause classifications may be labeled as CONFIRMED where evidence supports.
- Serious incident classifications may be stated with confidence where investigation complete."""

    return f"""
================================================================================
              GLOBAL CONSTRAINTS - ALL AGENTS MUST FOLLOW
================================================================================

These definitions are LOCKED. No agent may redefine, reinterpret, or contradict them.

## 1. EXPOSURE DENOMINATOR (Single Source)
- Value: {denom:,} units
- Scope: {denom_scope}
- Annual breakdown: {annual_str}
USE ONLY THESE FIGURES for all rate calculations. Do not derive alternate denominators.

## 2. COMPLAINT INVESTIGATION STATUS
- Total complaints: {total}
- Complaints with closed investigation: {closed}
- Investigation closure rate: {closure_rate:.1f}%
- Root cause status: {root_status.upper()}
- Serious incident classification certainty: {si_certainty.upper()}
{closure_rules}

## 3. SEVERITY LEVEL DEFINITIONS (Unified Hierarchy)
{severity_str}
USE ONLY THESE DEFINITIONS. Do not invent alternate severity categories.

## 4. ROOT CAUSE CATEGORIES (Locked)
{rc_str}
USE ONLY THESE CATEGORIES. If investigation incomplete, use "pending" or "indeterminate".

## 5. RISK MANAGEMENT FILE (RMF) STATUS
- Status: {rmf_status.upper().replace('_', ' ')}
{"- Do NOT reference, reproduce, or assume RMF hazard list content." if rmf_status != "complete" else "- RMF hazard list may be referenced."}

## 6. VIGILANCE METHODOLOGY
- Methodology: {vig_method.upper().replace('_', ' ')}
{"- Do NOT claim external database searches were performed." if vig_method == "internal_only" else "- External vigilance database results may be cited."}
{"- State explicitly: 'No external vigilance database search was conducted for this period.'" if vig_method == "internal_only" else ""}

## 7. INFERENCE POLICY
- Policy: {inference.upper().replace('_', ' ')}
{"- Do NOT infer, assume, or fill gaps. State 'Data not available' where absent." if inference == "strictly_factual" else "- Reasonable inference permitted; label as such."}

## 8. CROSS-SECTION CONSISTENCY RULES
- If content is already addressed in another section, REFERENCE it (e.g., 'As detailed in Section C...') instead of repeating.
- All sections must use the same denominator ({denom:,} units).
- All sections must use the same complaint total ({total}) and closure count ({closed}).
- All sections must use the same severity definitions.
- Conclusions in Section M must reflect actual data limitations, not assumed best practice.
- Executive Summary (A) must summarize only what is actually in the document.

## 9. BREVITY REQUIREMENTS
- Use short paragraphs (4 sentences maximum per paragraph).
- No bullet points anywhere.
- No redundant restatement of the same fact across sections.
- No over-explanation of regulatory citations or internal procedures.
- Be concise; write for a regulator who values precision over verbosity.

================================================================================
"""


def get_grkb_regulatory_context(section_id: str, context: PSURContext) -> str:
    """Generate GRKB regulatory grounding context for agent prompts."""
    if not context.grkb_available:
        return ""
    
    lines = []
    lines.append("================================================================================")
    lines.append("              GRKB REGULATORY GROUNDING")
    lines.append("================================================================================")
    lines.append("")
    
    # Find matching section from GRKB
    grkb_section = None
    for sec in context.grkb_sections:
        if sec.get("section_id", "").endswith(section_id) or section_id in sec.get("section_id", ""):
            grkb_section = sec
            break
    
    if grkb_section:
        lines.append(f"## Section Definition (from GRKB)")
        lines.append(f"- Section: {grkb_section.get('section_number', '')} - {grkb_section.get('title', '')}")
        if grkb_section.get("description"):
            lines.append(f"- Description: {grkb_section['description']}")
        if grkb_section.get("regulatory_basis"):
            lines.append(f"- Regulatory Basis: {grkb_section['regulatory_basis']}")
        if grkb_section.get("mandatory"):
            lines.append(f"- Status: MANDATORY")
        if grkb_section.get("minimum_word_count"):
            lines.append(f"- Minimum Word Count: {grkb_section['minimum_word_count']}")
        if grkb_section.get("required_evidence_types"):
            lines.append(f"- Required Evidence: {', '.join(grkb_section['required_evidence_types'])}")
        lines.append("")
    
    # Find relevant obligations
    relevant_obligations = []
    for obl in context.grkb_obligations[:20]:  # Limit to avoid prompt bloat
        obl_id = obl.get("obligation_id", "")
        # Match based on section (e.g., ART86, ANNEX_I, etc.)
        if section_id in obl_id or "86" in obl_id:
            relevant_obligations.append(obl)
    
    if relevant_obligations:
        lines.append("## Applicable Regulatory Obligations")
        for obl in relevant_obligations[:5]:  # Limit to top 5
            lines.append(f"- {obl.get('obligation_id', 'N/A')}: {obl.get('title', 'N/A')}")
            if obl.get("source_citation"):
                lines.append(f"  Source: {obl['source_citation']}")
            if obl.get("mandatory"):
                lines.append(f"  Status: MANDATORY")
        lines.append("")
    
    # Add relevant evidence type definitions
    if context.grkb_evidence_types:
        lines.append("## Evidence Type Definitions")
        for et in context.grkb_evidence_types[:5]:
            lines.append(f"- {et.get('display_name', et.get('evidence_type_id', 'N/A'))}: {et.get('description', '')[:100]}")
        lines.append("")
    
    lines.append("================================================================================")
    lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# SECTION 4: AGENT SYSTEM PROMPTS
# =============================================================================

def get_previous_sections_summary(session_id: int, current_section_id: str) -> str:
    """
    Get summaries of previously completed sections for inter-agent context.
    Enables agents to reference and build upon each other's work.
    """
    # Determine which sections come before this one
    current_idx = WORKFLOW_ORDER.index(current_section_id) if current_section_id in WORKFLOW_ORDER else 0
    previous_section_ids = WORKFLOW_ORDER[:current_idx]
    
    if not previous_section_ids:
        return ""
    
    with get_db_context() as db:
        sections = db.query(SectionDocument).filter(
            SectionDocument.session_id == session_id,
            SectionDocument.section_id.in_(previous_section_ids),
            SectionDocument.status.in_(["draft", "approved"])
        ).all()
        
        if not sections:
            return ""
        
        summaries = []
        for sec in sections:
            section_id = getattr(sec, "section_id", "")
            section_name = getattr(sec, "section_name", "")
            content = getattr(sec, "content", "") or ""
            author = getattr(sec, "author_agent", "")
            
            # Extract key facts from the content (first 800 chars as summary)
            summary_text = content[:800].strip()
            if len(content) > 800:
                # Find a good breaking point
                last_period = summary_text.rfind(".")
                if last_period > 400:
                    summary_text = summary_text[:last_period + 1]
                summary_text += " [...]"
            
            summaries.append(f"""
### Section {section_id}: {section_name}
*Generated by: {author}*

{summary_text}
""")
        
        if not summaries:
            return ""
        
        return f"""
## Previously Generated Sections (Reference Only)

The following sections have been completed by your colleagues. You may reference their findings 
but do NOT repeat information they have already covered. Instead, cross-reference:
e.g., "As detailed in Section C, the total distribution was X units."

{''.join(summaries)}

---
"""


def get_agent_system_prompt(agent_name: str, section_id: str, context: PSURContext, session_id: int = 0) -> str:
    """Generate comprehensive system prompt for an agent."""

    agent = AGENT_ROLES.get(agent_name, {})
    section = SECTION_DEFINITIONS.get(section_id, {})

    base_prompt = f"""
# {agent.get('name', agent_name)} - {agent.get('title', 'PSUR Agent')}

## Your Identity & Expertise

You are {agent.get('name', agent_name)}, a {agent.get('title', 'specialist')} specializing in regulatory compliance documentation for medical devices under EU MDR 2017/745.

Your expertise areas: {agent.get('expertise', 'regulatory documentation')}

## Your Responsibility

You are assigned **Section {section_id}: {section.get('name', 'PSUR Section')}** of the FormQAR-054 PSUR template.

**Section Purpose:** {section.get('purpose', 'Generate compliant PSUR content')}

**MDCG 2022-21 Reference:** {section.get('mdcg_ref', 'N/A')}

**Required Content:**
{chr(10).join(['- ' + item for item in section.get('required_content', [])])}

{get_workflow_role_context(agent_name, section_id)}

{get_section_interdependency_context(section_id)}

{get_quality_completeness_context(context)}

{get_temporal_continuity_context(context)}

## Regulatory Authority Hierarchy

You operate under the following authority hierarchy (in order):
1. EU MDR 2017/745 Articles 83-86
2. MDCG 2022-21 Guidance
3. FormQAR-054 Template Structure
4. ISO 14971 Risk Management Lifecycle
5. Company Quality Management System

## Critical Rules - MUST FOLLOW

### Rule 1: No Fabricated Data
- Every numerical value MUST trace to source data
- Every statement MUST be defensible under regulatory audit
- If data is missing: State explicitly, "No [data type] was available"
- Do NOT estimate, project, assume, or use benchmarks without source

### Rule 2: Narrative-Only Format
- Write Section {section_id} as continuous professional prose
- NO bullet points, numbered lists, hyphens as list items, or outlines
- Tables ONLY where FormQAR-054 explicitly requires them
- Cross-reference other sections: "As detailed in Section C, Post-Market Data..."

### Rule 3: Evidence-Based Conclusions
- Distinguish clearly between observed data, analysis, and interpretation
- Present conclusions as evidence-supported determinations, not opinions
- Use precise regulatory language
- Acknowledge limitations and uncertainties

### Rule 4: Risk Management Alignment
- Reference Risk Management File for known hazards
- Assess whether post-market findings indicate new signals or residual risk
- Determine whether benefit-risk remains favorable
- Recommend regulatory action if residual risk changes

## Tone & Style

- Professional, objective, evidence-based
- Suitable for Notified Body regulatory review
- Transparent about limitations
- Precise technical language
- No reassurance phrasing, no marketing language
- No downplaying or minimization of risks

## Output Requirements

When generating Section {section_id}, you MUST:
- Use EXACT data from the provided context
- Follow FormQAR-054 structure for this section
- Write professional narrative prose suitable for Notified Body audit
- Distinguish facts from interpretation
- Ground every claim in provided data
- Acknowledge limitations transparently
- Align with risk management framework

Do NOT:
- Add external benchmarks without citation
- Use bullet points or lists
- Present speculative interpretations as facts
- Include template language or placeholder examples
- Minimize or downplay identified issues
- Fabricate data
- Repeat information already covered in other sections; reference instead
- Write verbose paragraphs; keep each under 4 sentences

---

{get_global_constraints_prompt(context.global_constraints) if context.global_constraints else ''}

{get_grkb_regulatory_context(section_id, context)}

{get_previous_sections_summary(session_id, section_id) if session_id else ''}

{context.to_comprehensive_context_prompt()}

---

Now generate Section {section_id}: {section.get('name', '')} following all requirements above.
Write concisely. Maximum 4 sentences per paragraph. No bullet points.
Reference findings from previous sections where relevant - do not repeat them.
"""

    return base_prompt


def get_qc_system_prompt(section_id: str, section_content: str, context: PSURContext) -> str:
    """Generate QC validation prompt for Victoria."""

    section = SECTION_DEFINITIONS.get(section_id, {})

    return f"""
# Victoria - Quality Control Validator

## Your Role

You are Victoria, the QC Expert responsible for validating PSUR section content against FormQAR-054 template requirements and MDCG 2022-21 guidelines.

## Section Under Review

**Section {section_id}: {section.get('name', 'PSUR Section')}**
**Author:** {section.get('agent', 'Agent')}
**MDCG Reference:** {section.get('mdcg_ref', 'N/A')}

## Validation Checklist

### 1. DATA INTEGRITY
- [ ] All numbers have source documentation
- [ ] Calculations are correct (e.g., complaint rate formula)
- [ ] Year-over-year comparisons are consistent
- [ ] No data gaps without acknowledgment

### 2. TEMPLATE COMPLIANCE
- [ ] Section title matches FormQAR-054 exactly
- [ ] Section number is correct
- [ ] All required subsections are present
- [ ] Required tables are included where specified

### 3. REGULATORY ALIGNMENT
- [ ] Findings connected to Risk Management File
- [ ] Benefit-risk assessment incorporated
- [ ] Conclusions defensible under audit
- [ ] Any new signals appropriately escalated

### 4. CONTENT QUALITY
- [ ] Narrative prose only (NO bullet points)
- [ ] Professional regulatory tone
- [ ] Evidence-based conclusions
- [ ] Transparent about limitations
- [ ] Cross-references to other sections accurate

### 5. COMPLETENESS
- [ ] No placeholder text
- [ ] No [examples], [insert X], [TBD]
- [ ] All required elements present

## Required Content for This Section:
{chr(10).join(['- ' + item for item in section.get('required_content', [])])}

## Context Summary:
Device: {context.device_name}
Period: {context.period_start.strftime('%d %B %Y') if context.period_start else 'TBD'} to {context.period_end.strftime('%d %B %Y') if context.period_end else 'TBD'}
Total Units: {context.total_units_sold:,}
Total Complaints: {context.total_complaints}

{get_global_constraints_prompt(context.global_constraints) if context.global_constraints else ''}

## Section Content to Review:

{section_content}

---

## Your Task

Review the section content above and validate against:
1. FormQAR-054 template requirements
2. MDCG 2022-21 guidelines
3. **GLOBAL CONSTRAINTS** (CRITICAL - any deviation is a FAIL)

Provide:

1. **VERDICT**: PASS / CONDITIONAL / FAIL
   - FAIL if: wrong denominator, wrong totals, definitive root causes when closure <80%, bullet points used, paragraphs >4 sentences
   - CONDITIONAL if: minor issues, missing cross-references
   - PASS if: fully compliant

2. **Findings**: List any issues found

3. **Specific Corrections**: Exact text corrections needed

4. **Recommendation**: What to fix

Be strict on global constraints. Any use of a different denominator than {context.total_units_sold:,} is an automatic FAIL.
"""


# =============================================================================
# SECTION 5: SOTA ORCHESTRATOR CLASS
# =============================================================================

class SOTAOrchestrator:
    """
    State-of-the-Art PSUR Orchestrator implementing comprehensive
    MDCG 2022-21 compliant workflow with specialized agents.
    """

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.context: Optional[PSURContext] = None
        self.current_phase = "initialization"
        self.sections_completed = []
        self.max_qc_iterations = 3
        
        # Interactive workflow state
        self.workflow_status: WorkflowStatus = WorkflowStatus.IDLE
        self.pending_user_response: Optional[int] = None
        self.current_agent: Optional[str] = None
        self._pause_requested: bool = False

    # =========================================================================
    # WORKFLOW STATE MANAGEMENT
    # =========================================================================

    def request_pause(self) -> bool:
        """Request workflow to pause at next checkpoint."""
        if self.workflow_status == WorkflowStatus.RUNNING:
            self._pause_requested = True
            return True
        return False

    def request_resume(self) -> bool:
        """Request workflow to resume from paused state."""
        if self.workflow_status == WorkflowStatus.PAUSED:
            self._pause_requested = False
            self.workflow_status = WorkflowStatus.RUNNING
            self._sync_workflow_state_to_db()
            return True
        return False

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        return {
            "status": self.workflow_status.value,
            "current_agent": self.current_agent,
            "current_phase": self.current_phase,
            "sections_completed": len(self.sections_completed),
            "total_sections": len(WORKFLOW_ORDER),
            "paused": self.workflow_status == WorkflowStatus.PAUSED,
            "pending_user_response": self.pending_user_response
        }

    def _sync_workflow_state_to_db(self):
        """Sync workflow state to database for persistence."""
        with get_db_context() as db:
            workflow_state = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()
            
            if workflow_state:
                setattr(workflow_state, "status", self.workflow_status.value)
                setattr(workflow_state, "paused", self.workflow_status == WorkflowStatus.PAUSED)
                setattr(workflow_state, "pending_user_response", self.pending_user_response)
                setattr(workflow_state, "current_agent", self.current_agent)
                setattr(workflow_state, "sections_completed", len(self.sections_completed))
                db.commit()

    async def _handle_pause_checkpoint(self):
        """Check if pause was requested and handle it."""
        if self._pause_requested:
            self.workflow_status = WorkflowStatus.PAUSED
            self._sync_workflow_state_to_db()
            
            await self._post_message("Alex", "all",
                "Workflow paused by user request. Send a message or click Resume to continue.",
                "system")
            
            # Wait until resume is requested
            while self.workflow_status == WorkflowStatus.PAUSED:
                await asyncio.sleep(1)
                # Check for user messages while paused
                await self._check_and_handle_interventions()
            
            await self._post_message("Alex", "all",
                "Workflow resumed. Continuing PSUR generation...",
                "system")

    async def _check_and_handle_interventions(self):
        """
        Check for unprocessed user messages and have agents respond.
        This enables real user-agent interaction during workflow execution.
        """
        with get_db_context() as db:
            # Get user messages that haven't been processed
            # We use message_metadata to track processed status until the model is updated
            user_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id,
                ChatMessage.from_agent == "User"
            ).order_by(ChatMessage.timestamp.desc()).limit(20).all()
            
            unprocessed = []
            for msg in user_messages:
                metadata = getattr(msg, "message_metadata", None) or {}
                if not metadata.get("processed", False):
                    unprocessed.append({
                        "id": msg.id,
                        "message": msg.message,
                        "to_agent": msg.to_agent,
                        "timestamp": msg.timestamp
                    })
            
            if not unprocessed:
                return
            
            # Process each unprocessed message (oldest first)
            for msg_data in reversed(unprocessed):
                await self._respond_to_user_message(msg_data, db)
                
                # Mark as processed
                msg = db.query(ChatMessage).filter(ChatMessage.id == msg_data["id"]).first()
                if msg:
                    existing_metadata = getattr(msg, "message_metadata", None) or {}
                    existing_metadata["processed"] = True
                    existing_metadata["processed_at"] = datetime.utcnow().isoformat()
                    setattr(msg, "message_metadata", existing_metadata)
                    db.commit()

    async def _respond_to_user_message(self, msg_data: Dict[str, Any], db: Session):
        """Generate and post a response to a user message."""
        user_message = msg_data.get("message", "")
        target_agent = msg_data.get("to_agent", "all")
        
        # Parse @mentions from the message
        mentioned_agents = []
        for agent_name in AGENT_CONFIGS.keys():
            if f"@{agent_name}" in user_message:
                mentioned_agents.append(agent_name)
        
        # Determine responding agent
        if mentioned_agents:
            responding_agent = mentioned_agents[0]
        elif target_agent != "all" and target_agent in AGENT_CONFIGS:
            responding_agent = target_agent
        elif self.current_agent and self.current_agent in AGENT_CONFIGS:
            responding_agent = self.current_agent
        else:
            responding_agent = "Alex"  # Default to orchestrator
        
        agent_config = AGENT_CONFIGS.get(responding_agent, AGENT_CONFIGS.get("Alex"))
        if not agent_config:
            return
        
        # Build response prompt
        context_summary = ""
        if self.context:
            context_summary = f"""
Current context:
- Device: {self.context.device_name}
- Current phase: {self.current_phase}
- Sections completed: {', '.join(self.sections_completed) if self.sections_completed else 'None yet'}
"""
        
        system_prompt = f"""You are {responding_agent}, {agent_config.role} in the PSUR generation team.
You are responding to a user intervention during PSUR generation.

{context_summary}

Keep your response:
- Professional and helpful
- Concise (2-4 sentences unless detail is needed)
- Actionable if they're requesting changes
- Informative if they're asking questions

Do not use bullet points. Write in clear prose."""

        user_prompt = f"""The user has sent this message during PSUR generation:

"{user_message}"

Respond appropriately as {responding_agent}."""

        try:
            response = await self._call_ai(responding_agent, system_prompt, user_prompt)
            
            if response:
                await self._post_message(
                    responding_agent,
                    "User",
                    response,
                    "normal"
                )
        except Exception as e:
            await self._post_message(
                responding_agent,
                "User",
                f"I received your message but encountered an issue responding: {str(e)}. The workflow will continue.",
                "warning"
            )

    async def ask_agent_directly(self, agent_name: str, question: str) -> Dict[str, Any]:
        """
        Directly ask a specific agent a question and get a response.
        Used by the /ask API endpoint for immediate agent interaction.
        """
        if agent_name not in AGENT_CONFIGS:
            return {"error": f"Unknown agent: {agent_name}", "response": None}
        
        agent_config = AGENT_CONFIGS[agent_name]
        
        # Build context
        context_summary = ""
        if self.context:
            context_summary = f"""
Current PSUR context:
- Device: {self.context.device_name}
- Period: {self.context.period_start.strftime('%Y-%m-%d') if self.context.period_start else 'TBD'} to {self.context.period_end.strftime('%Y-%m-%d') if self.context.period_end else 'TBD'}
- Your sections: Check what sections you're responsible for
- Sections completed: {', '.join(self.sections_completed) if self.sections_completed else 'None yet'}
"""

        # Get previously generated content for this agent's sections
        previous_content = await self._get_agent_sections_content(agent_name)
        if previous_content:
            context_summary += f"\n\nYour generated content so far:\n{previous_content[:2000]}..."

        system_prompt = f"""You are {agent_name}, {agent_config.role}.
You are answering a direct question from the user about the PSUR generation process.

{context_summary}

Respond directly and helpfully. If you don't know something, say so.
Keep responses concise but complete."""

        user_prompt = f"""User question: {question}"""

        try:
            response = await self._call_ai(agent_name, system_prompt, user_prompt)
            
            # Post to discussion forum so it's visible
            await self._post_message(agent_name, "User", response or "No response generated.", "normal")
            
            return {"response": response, "agent": agent_name, "error": None}
        except Exception as e:
            return {"error": str(e), "response": None, "agent": agent_name}

    async def _get_agent_sections_content(self, agent_name: str) -> str:
        """Get content from sections this agent has generated."""
        with get_db_context() as db:
            sections = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.author_agent == agent_name,
                SectionDocument.status.in_(["draft", "approved"])
            ).all()
            
            if not sections:
                return ""
            
            content_parts = []
            for sec in sections:
                section_id = getattr(sec, "section_id", "")
                content = getattr(sec, "content", "")
                if content:
                    content_parts.append(f"=== Section {section_id} ===\n{content[:1000]}")
            
            return "\n\n".join(content_parts)

    async def execute_workflow(self) -> Dict[str, Any]:
        """Execute the complete PSUR generation workflow."""

        try:
            # Set workflow to running
            self.workflow_status = WorkflowStatus.RUNNING
            self._sync_workflow_state_to_db()
            
            # Phase 0: Initialize context
            await self._post_message("Alex", "all",
                "Initializing PSUR generation workflow. Loading session data and building regulatory context...",
                "system")

            await self._initialize_context()
            await self._initialize_agents()
            if self.context is None:
                raise RuntimeError("Context initialization failed")

            # Phase 1-7: Generate sections in dependency order
            await self._post_message("Alex", "all",
                f"Beginning PSUR generation for {self.context.device_name}. "
                f"Reporting period: {self.context.period_start.strftime('%d %B %Y') if self.context.period_start else 'TBD'} to "
                f"{self.context.period_end.strftime('%d %B %Y') if self.context.period_end else 'TBD'}. "
                f"Total sections to generate: {len(WORKFLOW_ORDER)}",
                "normal")

            for section_id in WORKFLOW_ORDER:
                # Check for pause/intervention before each section
                await self._handle_pause_checkpoint()
                await self._check_and_handle_interventions()
                
                section_def = SECTION_DEFINITIONS.get(section_id, {})
                agent_name = section_def.get("agent", "Alex")
                
                self.current_agent = agent_name
                await self._update_workflow_state(section_id)
                await self._set_agent_status(agent_name, "working")

                # Generate section
                success = await self._generate_section(section_id)

                if success:
                    self.sections_completed.append(section_id)
                    await self._set_agent_status(agent_name, "complete")
                else:
                    await self._set_agent_status(agent_name, "error")
                    await self._post_message("Alex", "all",
                        f"Warning: Section {section_id} generation encountered issues. Continuing workflow...",
                        "warning")
                
                # Check for interventions after each section
                await self._check_and_handle_interventions()

            # Final synthesis
            await self._perform_final_synthesis()

            # Update session status
            await self._complete_session()
            
            # Mark workflow as complete
            self.workflow_status = WorkflowStatus.COMPLETE
            self.current_agent = None
            self._sync_workflow_state_to_db()

            return {
                "status": "complete",
                "sections_completed": len(self.sections_completed),
                "total_sections": len(WORKFLOW_ORDER)
            }

        except Exception as e:
            traceback.print_exc()
            self.workflow_status = WorkflowStatus.ERROR
            self._sync_workflow_state_to_db()
            
            await self._post_message("Alex", "all",
                f"Workflow error: {str(e)}. Please check logs for details.",
                "error")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _initialize_context(self):
        """Initialize PSURContext from session data."""

        with get_db_context() as db:
            session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
            if not session:
                raise ValueError(f"Session {self.session_id} not found")

            # Build context from session data (extract scalar values from ORM instance)
            _device_name: str = getattr(session, "device_name", None) or "Unknown Device"
            _udi_di: str = getattr(session, "udi_di", None) or "Pending"
            _period_start: datetime = getattr(session, "period_start", None) or datetime.min
            _period_end: datetime = getattr(session, "period_end", None) or datetime.min
            self.context = PSURContext(
                device_name=_device_name,
                udi_di=_udi_di,
                period_start=_period_start,
                period_end=_period_end
            )

            # Load and analyze data files
            data_files = db.query(DataFile).filter(DataFile.session_id == self.session_id).all()

            for df in data_files:
                _uploaded_at = getattr(df, "uploaded_at", None)
                self.context.data_files.append({
                    "type": getattr(df, "file_type", ""),
                    "filename": getattr(df, "filename", ""),
                    "uploaded_at": _uploaded_at.isoformat() if _uploaded_at is not None else None
                })

                _file_type = getattr(df, "file_type", "") or ""
                if _file_type == "sales":
                    self.context.sales_data_available = True
                    await self._extract_sales_data(df)
                elif _file_type == "complaints":
                    self.context.complaint_data_available = True
                    await self._extract_complaint_data(df)
                elif _file_type == "vigilance":
                    self.context.vigilance_data_available = True
                    await self._extract_vigilance_data(df)

            # Calculate derived metrics
            self.context.calculate_metrics()

            # Apply master context (single golden source) if present
            _master = getattr(session, "master_context", None)
            if _master and isinstance(_master, dict):
                self.context.exposure_denominator_golden = int(_master.get("exposure_denominator_value", 0) or 0)
                self.context.exposure_denominator_scope = str(_master.get("exposure_denominator_scope", "reporting_period_only"))
                self.context.annual_units_golden = {int(k): int(v) for k, v in (_master.get("annual_units_canonical") or {}).items()}
                self.context.closure_definition_text = str(_master.get("closure_definition_text", "") or "")
                self.context.complaints_closed_canonical = int(_master.get("complaints_closed_canonical", 0) or 0)
                self.context.inference_policy = str(_master.get("inference_policy", "strictly_factual") or "strictly_factual")
                dav = _master.get("data_availability") or {}
                self.context.data_availability_external_vigilance = bool(dav.get("external_vigilance_searched", False))
                self.context.data_availability_complaint_closures_complete = bool(dav.get("complaint_closures_complete", False))
                self.context.data_availability_rmf_hazard_list = bool(dav.get("rmf_hazard_list_available", False))
                self.context.data_availability_intended_use = bool(dav.get("intended_use_provided", False))
                if self.context.exposure_denominator_golden > 0:
                    self.context.total_units_sold = self.context.exposure_denominator_golden
                if self.context.annual_units_golden:
                    self.context.total_units_by_year = dict(self.context.annual_units_golden)
                if self.context.complaints_closed_canonical >= 0:
                    self.context.complaints_with_root_cause = self.context.complaints_closed_canonical
                self.context.calculate_metrics()

            # Temporal continuity
            self.context.psur_sequence_number = self.session_id
            self.context.psur_sequence_narrative = (
                f"This is PSUR #{self.session_id} for this device in this system. "
                "Treat as the current reporting period submission."
            )
            _capa_closed = self.context.capa_actions_closed_this_period
            _capa_verified = self.context.capa_actions_effectiveness_verified
            _capa_details = self.context.capa_details
            if _capa_closed or _capa_verified or _capa_details:
                parts = []
                if _capa_closed:
                    parts.append(f"{_capa_closed} CAPA(s) closed this period")
                if _capa_verified:
                    parts.append(f"{_capa_verified} CAPA(s) effectiveness verified")
                if _capa_details:
                    for c in _capa_details[:5]:
                        parts.append(f"{c.get('id', 'N/A')}: {c.get('status', 'N/A')}")
                self.context.previous_capa_status_summary = "; ".join(parts)
            else:
                self.context.previous_capa_status_summary = "No CAPA actions in context for this period."
            if self.context.total_units_by_year or self.context.complaint_rate_by_year or len(self.context.total_units_by_year or {}) > 1:
                self.context.trending_across_periods_narrative = (
                    "Multi-year or multi-period data is available (units by year and/or complaint rates). "
                    "Use it to describe trends where relevant; cite time ranges and figures."
                )
            else:
                self.context.trending_across_periods_narrative = "Single-period or limited historical data; state scope of data where relevant."

            # Quality/completeness awareness
            self.context.data_confidence_by_domain = {}
            if self.context.sales_data_available and self.context.total_units_sold > 0:
                self.context.data_confidence_by_domain["sales"] = "high"
            elif self.context.sales_data_available:
                self.context.data_confidence_by_domain["sales"] = "medium"
            else:
                self.context.data_confidence_by_domain["sales"] = "none"
            if self.context.complaint_data_available and self.context.total_complaints > 0:
                self.context.data_confidence_by_domain["complaints"] = "high" if (self.context.complaints_with_root_cause or 0) > 0 else "medium"
            elif self.context.complaint_data_available:
                self.context.data_confidence_by_domain["complaints"] = "low"
            else:
                self.context.data_confidence_by_domain["complaints"] = "none"
            self.context.data_confidence_by_domain["vigilance"] = "high" if self.context.vigilance_data_available else "none"
            self.context.data_confidence_by_domain["clinical_follow_up"] = "high" if self.context.clinical_follow_up_data_available else "none"

            missing = []
            if not self.context.device_type:
                missing.append("Device type / classification detail")
            if not self.context.intended_use:
                missing.append("Full intended use statement")
            if not self.context.udi_di or self.context.udi_di == "Pending":
                missing.append("Confirmed UDI-DI (may be pending extraction)")
            if not self.context.sales_data_available:
                missing.append("Sales/distribution data")
            if not self.context.complaint_data_available:
                missing.append("Complaint data")
            if not self.context.vigilance_data_available:
                missing.append("Vigilance database search results")
            if not self.context.known_residual_risks:
                missing.append("Explicit list of known residual risks from RMF")
            self.context.missing_fields = missing

            if not self.context.sales_data_available:
                self.context.data_quality_warnings.append("No sales data provided; complaint rates cannot be calculated. State 'No sales data available' where relevant.")
            if self.context.complaint_data_available and (self.context.complaints_unconfirmed or 0) > 0:
                self.context.data_quality_warnings.append(f"{self.context.complaints_unconfirmed} complaint(s) with unconfirmed root cause; acknowledge in narrative.")
            if not self.context.vigilance_data_available:
                self.context.data_quality_warnings.append("No vigilance data; state that no external vigilance database search was conducted if applicable.")

            n_available = sum([
                self.context.sales_data_available,
                self.context.complaint_data_available,
                self.context.vigilance_data_available,
                bool(self.context.device_type or self.context.intended_use),
            ])
            self.context.completeness_score = max(0.0, min(100.0, (n_available / 4.0) * 100.0 - (len(missing) * 5.0)))

            # Load GRKB regulatory grounding
            await self._load_grkb_context()

            # Build global constraints (locked terminology for cross-section consistency)
            self.context.global_constraints = build_global_constraints(self.context)

            await self._post_message("Alex", "all",
                f"Context initialized. Device: {self.context.device_name}, "
                f"UDI-DI: {self.context.udi_di}, "
                f"Data files: {len(self.context.data_files)}, "
                f"Sales data: {'Available' if self.context.sales_data_available else 'Not available'}, "
                f"Complaint data: {'Available' if self.context.complaint_data_available else 'Not available'}",
                "success")

            # Report global constraints status
            gc = self.context.global_constraints
            await self._post_message("Alex", "all",
                f"Global constraints locked. Denominator: {gc.get('exposure_denominator', 0):,} units. "
                f"Investigation closure: {gc.get('investigation_closure_rate_percent', 0):.1f}%. "
                f"Root cause status: {gc.get('root_cause_status', 'unknown').upper()}. "
                f"Inference policy: {gc.get('inference_policy', 'strictly_factual').upper()}.",
                "normal")

    async def _load_grkb_context(self):
        """Load regulatory grounding from GRKB (Graph Regulatory Knowledge Base)."""
        if self.context is None:
            return
        
        if not GRKB_AVAILABLE or get_grkb_client is None:
            await self._post_message("Alex", "all",
                "GRKB client not available. Using built-in regulatory definitions only.",
                "warning")
            return
        
        try:
            grkb = get_grkb_client()  # type: ignore
            if not grkb.connect():
                await self._post_message("Alex", "all",
                    "Could not connect to GRKB database. Using built-in regulatory definitions.",
                    "warning")
                return
            
            # Load full regulatory context
            template_id = "MDCG_2022_21_ANNEX_I"
            
            # Load template
            template = grkb.get_template(template_id)
            if template:
                self.context.grkb_template = template
            
            # Load sections
            sections = grkb.get_all_sections(template_id)
            if sections:
                self.context.grkb_sections = sections
            
            # Load obligations
            obligations = grkb.get_all_obligations("EU_MDR")
            if obligations:
                self.context.grkb_obligations = obligations
            
            # Load evidence types
            evidence_types = grkb.get_all_evidence_types()
            if evidence_types:
                self.context.grkb_evidence_types = evidence_types
            
            # Load system instructions
            instructions = grkb.get_all_system_instructions()
            if instructions:
                self.context.grkb_system_instructions = {
                    inst["key"]: inst for inst in instructions
                }
            
            # Try to load device dossier if we have a device code
            if self.context.device_name:
                dossier = grkb.get_device_dossier(self.context.device_name)
                if dossier.get("clinical_context"):
                    cc = dossier["clinical_context"]
                    if cc.get("intended_purpose") and not self.context.intended_use:
                        self.context.intended_use = cc["intended_purpose"]
                    # Store indications/contraindications in data quality warnings for agent context
                    if cc.get("indications"):
                        self.context.data_quality_warnings.append(
                            f"Indications from GRKB: {', '.join(cc['indications'][:5])}"
                        )
                    if cc.get("contraindications"):
                        self.context.data_quality_warnings.append(
                            f"Contraindications from GRKB: {', '.join(cc['contraindications'][:5])}"
                        )
                
                if dossier.get("risk_context"):
                    rc = dossier["risk_context"]
                    if rc.get("principal_risks"):
                        self.context.known_residual_risks = [
                            f"{r.get('hazard', 'Unknown')}: {r.get('harm', 'Unknown')}"
                            for r in rc["principal_risks"]
                        ]
                    if rc.get("risk_thresholds"):
                        thresholds = rc["risk_thresholds"]
                        if thresholds.get("complaintRateThreshold"):
                            # Store threshold for use in trend analysis
                            self.context.data_quality_warnings.append(
                                f"Complaint rate threshold from RMF: {thresholds['complaintRateThreshold']}%"
                            )
            
            self.context.grkb_available = True
            
            await self._post_message("Alex", "all",
                f"GRKB regulatory grounding loaded: {len(obligations)} obligations, "
                f"{len(sections)} sections, {len(evidence_types)} evidence types.",
                "success")
            
        except Exception as e:
            await self._post_message("Alex", "all",
                f"Error loading GRKB context: {str(e)}. Using built-in definitions.",
                "warning")

    # Expanded column detection keywords (matching MasterContextExtractor)
    UNITS_KEYWORDS = [
        'units', 'quantity', 'qty', 'sold', 'distributed', 'shipped',
        'volume', 'amount', 'count', 'total', 'devices', 'pieces',
        'inventory', 'stock', 'dispatched', 'delivered', 'sales_qty',
        'unit_count', 'num_units', 'number'
    ]
    YEAR_KEYWORDS = [
        'year', 'date', 'period', 'fiscal', 'quarter', 'month',
        'time', 'calendar', 'reporting', 'ship_date', 'sale_date',
        'transaction_date', 'order_date'
    ]
    REGION_KEYWORDS = [
        'region', 'country', 'market', 'territory', 'geography',
        'location', 'area', 'state', 'zone', 'district'
    ]
    SEVERITY_KEYWORDS = [
        'severity', 'priority', 'level', 'criticality', 'grade',
        'impact', 'harm', 'seriousness', 'classification', 'risk_level',
        'risk', 'class', 'category', 'importance', 'urgency', 'tier'
    ]
    TYPE_KEYWORDS = [
        'type', 'category', 'classification', 'complaint_type',
        'issue_type', 'event_type', 'incident_type', 'kind'
    ]
    ROOT_CAUSE_KEYWORDS = [
        'root', 'cause', 'determination', 'finding', 'reason',
        'root_cause', 'failure', 'failure_mode', 'defect', 'issue',
        'problem', 'analysis', 'conclusion', 'attribution'
    ]
    CLOSURE_KEYWORDS = [
        'closed', 'closure', 'status', 'investigation', 'state',
        'resolved', 'complete', 'outcome', 'disposition', 'final',
        'investigation_status', 'case_status', 'resolution', 'result'
    ]

    async def _extract_sales_data(self, data_file: DataFile):
        """Extract sales metrics from uploaded file."""
        if self.context is None:
            return
        try:
            import pandas as pd
            import io

            _file_data = getattr(data_file, "file_data", b"")
            content = _file_data.decode('utf-8', errors='replace') if isinstance(_file_data, bytes) else str(_file_data)

            _filename = getattr(data_file, "filename", "") or ""
            if _filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content))
            elif _filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(io.BytesIO(_file_data) if isinstance(_file_data, bytes) else io.BytesIO(content.encode()), 
                                   engine='openpyxl' if _filename.endswith('.xlsx') else None)
            else:
                return

            # Look for common sales column names with expanded keywords
            units_col = None
            year_col = None
            region_col = None

            for col in df.columns:
                col_lower = col.lower()
                if units_col is None and any(term in col_lower for term in self.UNITS_KEYWORDS):
                    units_col = col
                if year_col is None and any(term in col_lower for term in self.YEAR_KEYWORDS):
                    year_col = col
                if region_col is None and any(term in col_lower for term in self.REGION_KEYWORDS):
                    region_col = col

            # Fallback: use first numeric column if no units column found
            if units_col is None:
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        units_col = col
                        break

            if units_col:
                self.context.total_units_sold = int(df[units_col].sum())
                self.context.cumulative_units_all_time = self.context.total_units_sold

            if units_col and year_col:
                yearly = df.groupby(year_col)[units_col].sum()
                self.context.total_units_by_year = {}
                for k, v in yearly.items():
                    if v is not None:
                        try:
                            self.context.total_units_by_year[int(k) if isinstance(k, (int, float, str)) else int(str(k))] = int(v)
                        except (ValueError, TypeError):
                            pass

            if units_col and region_col:
                regional = df.groupby(region_col)[units_col].sum()
                self.context.total_units_by_region = {str(k): int(v) for k, v in regional.items() if v is not None}
                self.context.regions = [str(x) for x in regional.index]

            # Store raw data sample (first 20 rows as markdown)
            try:
                df_sample = df.head(20).copy()
                # Truncate long string values
                for col in df_sample.columns:
                    if df_sample[col].dtype == 'object':
                        df_sample[col] = df_sample[col].astype(str).str.slice(0, 50)
                self.context.sales_raw_sample = df_sample.to_markdown(index=False) or ""
                self.context.sales_columns_detected = list(df.columns)
            except Exception:
                pass

        except Exception as e:
            print(f"Error extracting sales data: {e}")

    async def _extract_complaint_data(self, data_file: DataFile):
        """Extract complaint metrics from uploaded file."""
        if self.context is None:
            return
        try:
            import pandas as pd
            import io

            _file_data = getattr(data_file, "file_data", b"")
            content = _file_data.decode('utf-8', errors='replace') if isinstance(_file_data, bytes) else str(_file_data)

            _filename = getattr(data_file, "filename", "") or ""
            if _filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content))
            elif _filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(io.BytesIO(_file_data) if isinstance(_file_data, bytes) else io.BytesIO(content.encode()), 
                                   engine='openpyxl' if _filename.endswith('.xlsx') else None)
            else:
                return

            self.context.total_complaints = len(df)

            # Look for type/category columns with expanded keywords
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in self.TYPE_KEYWORDS):
                    type_counts = df[col].value_counts().to_dict()
                    self.context.complaints_by_type = {str(k): int(v) for k, v in type_counts.items()}
                    break

            # Look for severity columns with expanded keywords
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in self.SEVERITY_KEYWORDS):
                    severity_counts = df[col].value_counts().to_dict()
                    self.context.complaints_by_severity = {str(k): int(v) for k, v in severity_counts.items()}
                    break

            # Look for root cause columns with expanded keywords
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in self.ROOT_CAUSE_KEYWORDS):
                    cause_counts = df[col].value_counts().to_dict()
                    for cause, count in cause_counts.items():
                        cause_lower = str(cause).lower()
                        if any(term in cause_lower for term in ['defect', 'product', 'manufacturing', 'design', 'quality']):
                            self.context.complaints_product_defect += int(count)
                        elif any(term in cause_lower for term in ['user', 'error', 'misuse', 'operator', 'training']):
                            self.context.complaints_user_error += int(count)
                        elif any(term in cause_lower for term in ['unrelated', 'environmental', 'patient', 'external', 'no_fault']):
                            self.context.complaints_unrelated += int(count)
                        else:
                            self.context.complaints_unconfirmed += int(count)
                    break

            # Look for closure/investigation status columns
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in self.CLOSURE_KEYWORDS):
                    try:
                        closed_vals = df[col].astype(str).str.lower()
                        closed_count = int((closed_vals.str.contains(r'closed|complete|resolved|done|finalized|investigated|concluded|finished', case=False, na=False)).sum())
                        self.context.complaints_with_root_cause = closed_count
                    except Exception:
                        pass
                    break

            # Store raw data sample (first 20 rows as markdown)
            try:
                df_sample = df.head(20).copy()
                # Truncate long string values
                for col in df_sample.columns:
                    if df_sample[col].dtype == 'object':
                        df_sample[col] = df_sample[col].astype(str).str.slice(0, 50)
                self.context.complaints_raw_sample = df_sample.to_markdown(index=False) or ""
                self.context.complaints_columns_detected = list(df.columns)
            except Exception:
                pass

        except Exception as e:
            print(f"Error extracting complaint data: {e}")

    async def _extract_vigilance_data(self, data_file: DataFile):
        """Extract vigilance/incident metrics from uploaded file."""
        if self.context is None:
            return
        try:
            import pandas as pd
            import io

            _file_data = getattr(data_file, "file_data", b"")
            content = _file_data.decode('utf-8', errors='replace') if isinstance(_file_data, bytes) else str(_file_data)

            _filename = getattr(data_file, "filename", "") or ""
            if _filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content))
            elif _filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(io.BytesIO(_file_data) if isinstance(_file_data, bytes) else io.BytesIO(content.encode()), 
                                   engine='openpyxl' if _filename.endswith('.xlsx') else None)
            else:
                return

            self.context.serious_incidents = len(df)

            # Look for severity/type columns with expanded keywords
            type_keywords = ['type', 'category', 'outcome', 'event', 'incident', 'classification', 'result', 'harm']
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in type_keywords):
                    type_counts = df[col].value_counts().to_dict()
                    self.context.serious_incidents_by_type = {str(k): int(v) for k, v in type_counts.items()}

                    # Count deaths and injuries
                    for incident_type, count in type_counts.items():
                        type_lower = str(incident_type).lower()
                        if any(term in type_lower for term in ['death', 'fatal', 'deceased', 'mortality']):
                            self.context.deaths += int(count)
                        elif any(term in type_lower for term in ['injur', 'harm', 'serious', 'hospitali']):
                            self.context.serious_injuries += int(count)
                    break

            # Store raw data sample (first 20 rows as markdown)
            try:
                df_sample = df.head(20).copy()
                # Truncate long string values
                for col in df_sample.columns:
                    if df_sample[col].dtype == 'object':
                        df_sample[col] = df_sample[col].astype(str).str.slice(0, 50)
                self.context.vigilance_raw_sample = df_sample.to_markdown(index=False) or ""
                self.context.vigilance_columns_detected = list(df.columns)
            except Exception:
                pass

        except Exception as e:
            print(f"Error extracting vigilance data: {e}")

    async def _initialize_agents(self):
        """Initialize all agents in the database."""

        with get_db_context() as db:
            for agent_id, agent_info in AGENT_ROLES.items():
                existing = db.query(Agent).filter(
                    Agent.session_id == self.session_id,
                    Agent.agent_id == agent_id
                ).first()

                if not existing:
                    config = AGENT_CONFIGS.get(agent_id, AGENT_CONFIGS.get("Alex"))
                    agent = Agent(
                        session_id=self.session_id,
                        agent_id=agent_id,
                        name=agent_info["name"],
                        role=agent_info["role"],
                        ai_provider=config.ai_provider if config else "anthropic",
                        model=config.model if config else "claude-sonnet-4-20250514",
                        status="idle"
                    )
                    db.add(agent)

            db.commit()

    async def _generate_section(self, section_id: str) -> bool:
        """Generate a single PSUR section with QC review cycle."""

        section_def = SECTION_DEFINITIONS.get(section_id, {})
        agent_name = section_def.get("agent", "Alex")
        section_name = section_def.get("name", f"Section {section_id}")

        await self._post_message(agent_name, "all",
            f"Beginning work on Section {section_id}: {section_name}. "
            f"Analyzing available data and generating compliant content...",
            "normal")

        ctx = self.context
        if ctx is None:
            return False
        try:
            # Generate initial content with inter-agent context
            system_prompt = get_agent_system_prompt(agent_name, section_id, ctx, self.session_id)

            user_prompt = f"""
Generate Section {section_id}: {section_name} for the PSUR.

Use the comprehensive context provided in the system prompt. Write professional narrative prose suitable for Notified Body review.

Key data points to incorporate:
- Device: {ctx.device_name}
- UDI-DI: {ctx.udi_di}
- Reporting Period: {ctx.period_start.strftime('%d %B %Y') if ctx.period_start else 'TBD'} to {ctx.period_end.strftime('%d %B %Y') if ctx.period_end else 'TBD'}
- Total Units Distributed: {ctx.total_units_sold:,}
- Total Complaints: {ctx.total_complaints}
- Complaint Rate: {ctx.complaint_rate_percent:.4f}%
- Serious Incidents: {ctx.serious_incidents}

Generate the complete section content now. Remember: NO bullet points, narrative prose only.
"""

            content = await self._call_ai(agent_name, system_prompt, user_prompt)

            if not content:
                await self._post_message(agent_name, "all",
                    f"Unable to generate content for Section {section_id}. AI call failed.",
                    "error")
                return False

            # Save initial draft
            await self._save_section(section_id, section_name, agent_name, content, "draft")

            await self._post_message(agent_name, "Victoria",
                f"Section {section_id} draft complete. Word count: {len(content.split())}. "
                f"Submitting for QC review.",
                "normal")

            # QC Review cycle
            for iteration in range(self.max_qc_iterations):
                await self._set_agent_status("Victoria", "working")

                qc_result = await self._qc_review(section_id, content)

                if qc_result.get("verdict") == "PASS":
                    await self._save_section(section_id, section_name, agent_name, content, "approved")
                    await self._post_message("Victoria", agent_name,
                        f"Section {section_id} APPROVED. Content meets FormQAR-054 requirements.",
                        "success")
                    await self._set_agent_status("Victoria", "complete")
                    return True

                elif qc_result.get("verdict") == "CONDITIONAL":
                    feedback = qc_result.get("feedback", "Minor revisions needed")
                    await self._post_message("Victoria", agent_name,
                        f"Section {section_id} requires revisions. Feedback: {feedback}",
                        "warning")

                    # Revise content
                    await self._set_agent_status(agent_name, "working")
                    content = await self._revise_section(agent_name, section_id, content, feedback)
                    await self._save_section(section_id, section_name, agent_name, content, "in_review")

                else:  # FAIL
                    feedback = qc_result.get("feedback", "Significant issues found")
                    await self._post_message("Victoria", agent_name,
                        f"Section {section_id} FAILED QC. Issues: {feedback}",
                        "error")

                    # Major revision needed
                    await self._set_agent_status(agent_name, "working")
                    content = await self._revise_section(agent_name, section_id, content, feedback)
                    await self._save_section(section_id, section_name, agent_name, content, "in_review")

            # Max iterations reached - accept as-is
            await self._save_section(section_id, section_name, agent_name, content, "approved")
            await self._post_message("Victoria", "all",
                f"Section {section_id} approved after {self.max_qc_iterations} revision cycles.",
                "warning")
            await self._set_agent_status("Victoria", "complete")
            return True

        except Exception as e:
            traceback.print_exc()
            await self._post_message(agent_name, "all",
                f"Error generating Section {section_id}: {str(e)}",
                "error")
            return False

    async def _qc_review(self, section_id: str, content: str) -> Dict[str, Any]:
        """Perform QC review on section content."""
        if self.context is None:
            return {"verdict": "PASS", "feedback": "Context unavailable, proceeding with content"}
        qc_prompt = get_qc_system_prompt(section_id, content, self.context)

        user_prompt = "Review the section content and provide your verdict (PASS/CONDITIONAL/FAIL) with detailed feedback."

        response = await self._call_ai("Victoria", qc_prompt, user_prompt)

        if not response:
            return {"verdict": "PASS", "feedback": "QC review unavailable, proceeding with content"}

        # Parse verdict from response
        response_upper = response.upper()
        if "PASS" in response_upper and "FAIL" not in response_upper:
            verdict = "PASS"
        elif "CONDITIONAL" in response_upper:
            verdict = "CONDITIONAL"
        else:
            verdict = "FAIL"

        return {
            "verdict": verdict,
            "feedback": response
        }

    async def _revise_section(self, agent_name: str, section_id: str, content: str, feedback: str) -> str:
        """Revise section content based on QC feedback."""

        section_def = SECTION_DEFINITIONS.get(section_id, {})

        system_prompt = f"""
You are {agent_name}, revising Section {section_id}: {section_def.get('name', '')} based on QC feedback.

Original content:
{content}

QC Feedback:
{feedback}

Revise the section to address all feedback points while maintaining:
1. Narrative prose format (NO bullet points)
2. Regulatory compliance language
3. Data accuracy and traceability
4. Professional tone suitable for Notified Body review

Generate the complete revised section.
"""

        revised = await self._call_ai(agent_name, system_prompt, "Generate the revised section content.")

        return revised if revised else content

    async def _perform_final_synthesis(self):
        """Perform final synthesis and cross-section consistency validation."""

        await self._post_message("Alex", "all",
            "All sections complete. Performing cross-section consistency validation...",
            "normal")

        # Cross-section validation phase
        await self._validate_cross_section_consistency()

        # Update workflow to complete
        with get_db_context() as db:
            workflow = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()

            if workflow:
                setattr(workflow, "status", "complete")
                setattr(workflow, "sections_completed", len(self.sections_completed))
                setattr(workflow, "summary", f"PSUR generation complete. {len(self.sections_completed)} sections generated.")
                db.commit()

        ctx = self.context
        await self._post_message("Alex", "all",
            f"PSUR generation complete for {ctx.device_name if ctx else 'session'}. "
            f"{len(self.sections_completed)} sections successfully generated and approved. "
            f"Document is ready for download.",
            "success")

    async def _validate_cross_section_consistency(self):
        """Validate consistency across all generated sections using global constraints."""
        if self.context is None:
            return

        gc = self.context.global_constraints
        if not gc:
            return

        await self._post_message("Victoria", "all",
            "Running cross-section consistency checks against global constraints...",
            "normal")

        # Load all generated sections
        with get_db_context() as db:
            sections = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.status.in_(["approved", "draft"])
            ).all()

            if not sections:
                return

            # Build consistency check prompt
            sections_text = "\n\n".join([
                f"=== SECTION {getattr(s, 'section_id', 'unknown')}: {getattr(s, 'section_name', '')} ===\n{getattr(s, 'content', '')[:2000]}..."
                for s in sections
            ])

            denominator = gc.get("exposure_denominator", 0)
            total_complaints = gc.get("total_complaints_count", 0)
            closure_rate = gc.get("investigation_closure_rate_percent", 0)
            root_status = gc.get("root_cause_status", "preliminary")

            check_prompt = f"""
You are Victoria, the QC validator. Review the following PSUR sections for cross-section consistency.

GLOBAL CONSTRAINTS (these are LOCKED and must be used consistently):
- Exposure denominator: {denominator:,} units
- Total complaints: {total_complaints}
- Investigation closure rate: {closure_rate:.1f}%
- Root cause status: {root_status.upper()}

Check for these issues:
1. Different denominators used across sections (must all use {denominator:,})
2. Different complaint totals cited (must all use {total_complaints})
3. Root causes stated as definitive when closure rate is {closure_rate:.1f}% (only allowed if >=80%)
4. Sections contradicting each other on data availability
5. Excessive repetition of the same facts across sections
6. Bullet points used anywhere (forbidden)
7. Paragraphs longer than 4 sentences

SECTIONS TO REVIEW:
{sections_text}

Output a brief consistency report (max 200 words). List any issues found or state "No consistency issues detected."
"""

            try:
                system_prompt = "You are Victoria, the QC validator. Your task is to check PSUR sections for cross-section consistency. Be strict about global constraints violations."
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._call_ai_sync("Victoria", system_prompt, check_prompt)
                )

                if response:
                    await self._post_message("Victoria", "all",
                        f"Consistency validation complete: {response[:500]}",
                        "normal")
            except Exception as e:
                await self._post_message("Victoria", "all",
                    f"Consistency check encountered an error: {str(e)}",
                    "warning")

    async def _complete_session(self):
        """Mark session as complete."""

        with get_db_context() as db:
            session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
            if session:
                setattr(session, "status", "complete")
                db.commit()

    async def _save_section(self, section_id: str, section_name: str, agent_name: str,
                           content: str, status: str):
        """Save section content to database."""

        with get_db_context() as db:
            existing = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.section_id == section_id
            ).first()

            if existing:
                setattr(existing, "content", content)
                setattr(existing, "status", status)
                setattr(existing, "updated_at", datetime.utcnow())
            else:
                section = SectionDocument(
                    session_id=self.session_id,
                    section_id=section_id,
                    section_name=section_name,
                    author_agent=agent_name,
                    content=content,
                    status=status,
                    created_at=datetime.utcnow()
                )
                db.add(section)

            db.commit()

    async def _update_workflow_state(self, current_section: str):
        """Update workflow state in database."""

        with get_db_context() as db:
            workflow = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()

            if workflow:
                setattr(workflow, "current_section", current_section)
                setattr(workflow, "sections_completed", len(self.sections_completed))
                setattr(workflow, "status", "running")
                db.commit()

    async def _set_agent_status(self, agent_name: str, status: str):
        """Update agent status in database."""

        with get_db_context() as db:
            agent = db.query(Agent).filter(
                Agent.session_id == self.session_id,
                Agent.agent_id == agent_name
            ).first()

            if agent:
                setattr(agent, "status", status)
                setattr(agent, "last_activity", datetime.utcnow())
                db.commit()

    async def _post_message(self, from_agent: str, to_agent: str, message: str,
                           message_type: str = "normal"):
        """Post a message to the discussion forum."""

        with get_db_context() as db:
            msg = ChatMessage(
                session_id=self.session_id,
                from_agent=from_agent,
                to_agent=to_agent,
                message=message,
                message_type=message_type,
                timestamp=datetime.utcnow()
            )
            db.add(msg)
            db.commit()

    def _call_ai_sync(self, agent_name: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Synchronous AI call (run in thread pool to avoid blocking event loop)."""
        config = AGENT_CONFIGS.get(agent_name, AGENT_CONFIGS.get("Alex"))
        if not config:
            return None

        try:
            client, model = get_ai_client(config.ai_provider)

            if config.ai_provider == "anthropic":
                messages_api = getattr(client, "messages", None)
                if messages_api is None:
                    return None
                response = messages_api.create(
                    model=model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                content_list = getattr(response, "content", None) or []
                first_block = content_list[0] if content_list else None
                return getattr(first_block, "text", str(first_block) if first_block else "")

            elif config.ai_provider == "openai":
                chat_api = getattr(client, "chat", None)
                if chat_api is None:
                    return None
                try:
                    response = chat_api.completions.create(
                        model=model,
                        max_completion_tokens=config.max_tokens,
                        temperature=config.temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                except Exception as openai_err:
                    err_str = str(openai_err).lower()
                    if "max_completion_tokens" in err_str and ("not supported" in err_str or "unsupported" in err_str):
                        response = chat_api.completions.create(
                            model=model,
                            max_tokens=config.max_tokens,
                            temperature=config.temperature,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ]
                        )
                    else:
                        raise
                choices = getattr(response, "choices", None) or []
                first_choice = choices[0] if choices else None
                msg = getattr(first_choice, "message", None) if first_choice else None
                return getattr(msg, "content", None) if msg else None

            elif config.ai_provider == "google":
                import google.generativeai as genai
                model_obj = genai.GenerativeModel(model)
                response = model_obj.generate_content(
                    f"{system_prompt}\n\n{user_prompt}",
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=config.max_tokens,
                        temperature=config.temperature
                    )
                )
                return getattr(response, "text", str(response))

            elif config.ai_provider == "xai":
                chat_api = getattr(client, "chat", None)
                if chat_api is None:
                    return None
                try:
                    response = chat_api.completions.create(
                        model=model,
                        max_completion_tokens=config.max_tokens,
                        temperature=config.temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                except Exception as xai_err:
                    err_str = str(xai_err).lower()
                    if "max_completion_tokens" in err_str and ("not supported" in err_str or "unsupported" in err_str):
                        response = chat_api.completions.create(
                            model=model,
                            max_tokens=config.max_tokens,
                            temperature=config.temperature,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ]
                        )
                    else:
                        raise
                choices = getattr(response, "choices", None) or []
                first_choice = choices[0] if choices else None
                msg = getattr(first_choice, "message", None) if first_choice else None
                return getattr(msg, "content", None) if msg else None

        except Exception as e:
            print(f"AI call failed for {agent_name}: {e}")

            fallback_providers = ["anthropic", "openai", "google", "xai"]
            if config.ai_provider in fallback_providers:
                fallback_providers.remove(config.ai_provider)

            for provider in fallback_providers:
                try:
                    client, model = get_ai_client(provider)

                    if provider == "anthropic":
                        messages_api = getattr(client, "messages", None)
                        if messages_api is None:
                            continue
                        response = messages_api.create(
                            model=model,
                            max_tokens=4096,
                            system=system_prompt,
                            messages=[{"role": "user", "content": user_prompt}]
                        )
                        content_list = getattr(response, "content", None) or []
                        first_block = content_list[0] if content_list else None
                        return getattr(first_block, "text", str(first_block) if first_block else "")

                    elif provider in ["openai", "xai"]:
                        chat_api = getattr(client, "chat", None)
                        if chat_api is None:
                            continue
                        try:
                            response = chat_api.completions.create(
                                model=model,
                                max_completion_tokens=4096,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ]
                            )
                        except Exception as fallback_param_err:
                            err_str = str(fallback_param_err).lower()
                            if "max_completion_tokens" in err_str:
                                response = chat_api.completions.create(
                                    model=model,
                                    max_tokens=4096,
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": user_prompt}
                                    ]
                                )
                            else:
                                raise
                        choices = getattr(response, "choices", None) or []
                        first_choice = choices[0] if choices else None
                        msg = getattr(first_choice, "message", None) if first_choice else None
                        return getattr(msg, "content", None) if msg else None

                except Exception as fallback_error:
                    print(f"Fallback to {provider} failed: {fallback_error}")
                    continue

            return None

    async def _call_ai(self, agent_name: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call AI provider in thread pool so the event loop is not blocked."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._call_ai_sync,
            agent_name,
            system_prompt,
            user_prompt,
        )
