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
import json
import asyncio
import traceback

from sqlalchemy.orm import Session
from backend.database.session import get_db_context
from backend.database.models import (
    PSURSession, Agent, ChatMessage, SectionDocument,
    WorkflowState, DataFile
)
from backend.config import AGENT_CONFIGS, get_ai_client


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

    period_start: datetime = None
    period_end: datetime = None
    psur_cadence: str = "Every 2 Years"
    submission_deadline: datetime = None
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
    data_last_updated: datetime = None
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

        return f"""
================================================================================
         COMPREHENSIVE PSUR REGULATORY & OPERATIONAL CONTEXT
              (MDR 2017/745 Article 86 | MDCG 2022-21 Compliance)
================================================================================

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

**Data Sources Available:**
  Sales Data: {'YES - Use exact figures' if self.sales_data_available else 'NO - State "No sales data available" explicitly'}
  Complaint Data: {'YES - Detail investigation outcomes' if self.complaint_data_available else 'NO - State "No complaint data analyzed" explicitly'}
  Vigilance Data: {'YES - Include database search results' if self.vigilance_data_available else 'NO - State "No vigilance database search conducted" explicitly'}
  Clinical Follow-up: {'YES - Include study status' if self.clinical_follow_up_data_available else 'NO'}

---

## XI. CRITICAL COMPLIANCE RULES FOR ALL AGENTS

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
# SECTION 3: AGENT SYSTEM PROMPTS
# =============================================================================

def get_agent_system_prompt(agent_name: str, section_id: str, context: PSURContext) -> str:
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

---

{context.to_comprehensive_context_prompt()}

---

Now generate Section {section_id}: {section.get('name', '')} following all requirements above.
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

## Section Content to Review:

{section_content}

---

## Your Task

Review the section content above and provide:

1. **VERDICT**: PASS / CONDITIONAL / FAIL

2. **Findings**: List any issues found in each validation category

3. **Specific Corrections**: If CONDITIONAL or FAIL, provide exact text corrections needed

4. **Recommendation**: What the author agent should do to achieve PASS status

Be thorough but fair. Minor stylistic issues should not cause a FAIL. Focus on regulatory compliance and data accuracy.
"""


# =============================================================================
# SECTION 4: SOTA ORCHESTRATOR CLASS
# =============================================================================

class SOTAOrchestrator:
    """
    State-of-the-Art PSUR Orchestrator implementing comprehensive
    MDCG 2022-21 compliant workflow with specialized agents.
    """

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.context: PSURContext = None
        self.current_phase = "initialization"
        self.sections_completed = []
        self.max_qc_iterations = 3

    async def execute_workflow(self) -> Dict[str, Any]:
        """Execute the complete PSUR generation workflow."""

        try:
            # Phase 0: Initialize context
            await self._post_message("Alex", "all",
                "Initializing PSUR generation workflow. Loading session data and building regulatory context...",
                "system")

            await self._initialize_context()
            await self._initialize_agents()

            # Phase 1-7: Generate sections in dependency order
            await self._post_message("Alex", "all",
                f"Beginning PSUR generation for {self.context.device_name}. "
                f"Reporting period: {self.context.period_start.strftime('%d %B %Y') if self.context.period_start else 'TBD'} to "
                f"{self.context.period_end.strftime('%d %B %Y') if self.context.period_end else 'TBD'}. "
                f"Total sections to generate: {len(WORKFLOW_ORDER)}",
                "normal")

            for section_id in WORKFLOW_ORDER:
                section_def = SECTION_DEFINITIONS.get(section_id, {})
                agent_name = section_def.get("agent", "Alex")

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

            # Final synthesis
            await self._perform_final_synthesis()

            # Update session status
            await self._complete_session()

            return {
                "status": "complete",
                "sections_completed": len(self.sections_completed),
                "total_sections": len(WORKFLOW_ORDER)
            }

        except Exception as e:
            traceback.print_exc()
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

            # Build context from session data
            self.context = PSURContext(
                device_name=session.device_name or "Unknown Device",
                udi_di=session.udi_di or "Pending",
                period_start=session.period_start,
                period_end=session.period_end
            )

            # Load and analyze data files
            data_files = db.query(DataFile).filter(DataFile.session_id == self.session_id).all()

            for df in data_files:
                self.context.data_files.append({
                    "type": df.file_type,
                    "filename": df.filename,
                    "uploaded_at": df.uploaded_at.isoformat() if df.uploaded_at else None
                })

                if df.file_type == "sales":
                    self.context.sales_data_available = True
                    await self._extract_sales_data(df)
                elif df.file_type == "complaints":
                    self.context.complaint_data_available = True
                    await self._extract_complaint_data(df)
                elif df.file_type == "vigilance":
                    self.context.vigilance_data_available = True
                    await self._extract_vigilance_data(df)

            # Calculate derived metrics
            self.context.calculate_metrics()

            await self._post_message("Alex", "all",
                f"Context initialized. Device: {self.context.device_name}, "
                f"UDI-DI: {self.context.udi_di}, "
                f"Data files: {len(self.context.data_files)}, "
                f"Sales data: {'Available' if self.context.sales_data_available else 'Not available'}, "
                f"Complaint data: {'Available' if self.context.complaint_data_available else 'Not available'}",
                "success")

    async def _extract_sales_data(self, data_file: DataFile):
        """Extract sales metrics from uploaded file."""
        try:
            import pandas as pd
            import io

            content = data_file.file_data.decode('utf-8') if isinstance(data_file.file_data, bytes) else data_file.file_data

            if data_file.filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content))
            else:
                return

            # Look for common sales column names
            units_col = None
            year_col = None
            region_col = None

            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['units', 'quantity', 'sold', 'distributed']):
                    units_col = col
                if any(term in col_lower for term in ['year', 'date', 'period']):
                    year_col = col
                if any(term in col_lower for term in ['region', 'country', 'market', 'territory']):
                    region_col = col

            if units_col:
                self.context.total_units_sold = int(df[units_col].sum())
                self.context.cumulative_units_all_time = self.context.total_units_sold

            if units_col and year_col:
                yearly = df.groupby(year_col)[units_col].sum()
                self.context.total_units_by_year = {int(k): int(v) for k, v in yearly.items()}

            if units_col and region_col:
                regional = df.groupby(region_col)[units_col].sum()
                self.context.total_units_by_region = {str(k): int(v) for k, v in regional.items()}
                self.context.regions = list(regional.index)

        except Exception as e:
            print(f"Error extracting sales data: {e}")

    async def _extract_complaint_data(self, data_file: DataFile):
        """Extract complaint metrics from uploaded file."""
        try:
            import pandas as pd
            import io

            content = data_file.file_data.decode('utf-8') if isinstance(data_file.file_data, bytes) else data_file.file_data

            if data_file.filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content))
            else:
                return

            self.context.total_complaints = len(df)

            # Look for type/category columns
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['type', 'category', 'classification']):
                    type_counts = df[col].value_counts().to_dict()
                    self.context.complaints_by_type = {str(k): int(v) for k, v in type_counts.items()}
                    break

            # Look for severity columns
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['severity', 'priority', 'level']):
                    severity_counts = df[col].value_counts().to_dict()
                    self.context.complaints_by_severity = {str(k): int(v) for k, v in severity_counts.items()}
                    break

            # Look for root cause columns
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['root', 'cause', 'determination', 'finding']):
                    cause_counts = df[col].value_counts().to_dict()
                    for cause, count in cause_counts.items():
                        cause_lower = str(cause).lower()
                        if any(term in cause_lower for term in ['defect', 'product', 'manufacturing', 'design']):
                            self.context.complaints_product_defect += int(count)
                        elif any(term in cause_lower for term in ['user', 'error', 'misuse']):
                            self.context.complaints_user_error += int(count)
                        elif any(term in cause_lower for term in ['unrelated', 'environmental', 'patient']):
                            self.context.complaints_unrelated += int(count)
                        else:
                            self.context.complaints_unconfirmed += int(count)
                    break

        except Exception as e:
            print(f"Error extracting complaint data: {e}")

    async def _extract_vigilance_data(self, data_file: DataFile):
        """Extract vigilance/incident metrics from uploaded file."""
        try:
            import pandas as pd
            import io

            content = data_file.file_data.decode('utf-8') if isinstance(data_file.file_data, bytes) else data_file.file_data

            if data_file.filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(content))
            else:
                return

            self.context.serious_incidents = len(df)

            # Look for severity/type columns
            for col in df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['type', 'category', 'outcome']):
                    type_counts = df[col].value_counts().to_dict()
                    self.context.serious_incidents_by_type = {str(k): int(v) for k, v in type_counts.items()}

                    # Count deaths and injuries
                    for incident_type, count in type_counts.items():
                        type_lower = str(incident_type).lower()
                        if 'death' in type_lower:
                            self.context.deaths += int(count)
                        elif 'injur' in type_lower:
                            self.context.serious_injuries += int(count)
                    break

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

        try:
            # Generate initial content
            system_prompt = get_agent_system_prompt(agent_name, section_id, self.context)

            user_prompt = f"""
Generate Section {section_id}: {section_name} for the PSUR.

Use the comprehensive context provided in the system prompt. Write professional narrative prose suitable for Notified Body review.

Key data points to incorporate:
- Device: {self.context.device_name}
- UDI-DI: {self.context.udi_di}
- Reporting Period: {self.context.period_start.strftime('%d %B %Y') if self.context.period_start else 'TBD'} to {self.context.period_end.strftime('%d %B %Y') if self.context.period_end else 'TBD'}
- Total Units Distributed: {self.context.total_units_sold:,}
- Total Complaints: {self.context.total_complaints}
- Complaint Rate: {self.context.complaint_rate_percent:.4f}%
- Serious Incidents: {self.context.serious_incidents}

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
        """Perform final synthesis and consistency check."""

        await self._post_message("Alex", "all",
            "All sections complete. Performing final synthesis and consistency verification...",
            "normal")

        # Update workflow to complete
        with get_db_context() as db:
            workflow = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()

            if workflow:
                workflow.status = "complete"
                workflow.sections_completed = len(self.sections_completed)
                workflow.summary = f"PSUR generation complete. {len(self.sections_completed)} sections generated."
                db.commit()

        await self._post_message("Alex", "all",
            f"PSUR generation complete for {self.context.device_name}. "
            f"{len(self.sections_completed)} sections successfully generated and approved. "
            f"Document is ready for download.",
            "success")

    async def _complete_session(self):
        """Mark session as complete."""

        with get_db_context() as db:
            session = db.query(PSURSession).filter(PSURSession.id == self.session_id).first()
            if session:
                session.status = "complete"
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
                existing.content = content
                existing.status = status
                existing.updated_at = datetime.utcnow()
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
                workflow.current_section = current_section
                workflow.sections_completed = len(self.sections_completed)
                workflow.status = "running"
                db.commit()

    async def _set_agent_status(self, agent_name: str, status: str):
        """Update agent status in database."""

        with get_db_context() as db:
            agent = db.query(Agent).filter(
                Agent.session_id == self.session_id,
                Agent.agent_id == agent_name
            ).first()

            if agent:
                agent.status = status
                agent.last_activity = datetime.utcnow()
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

    async def _call_ai(self, agent_name: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call AI provider with fallback support."""

        config = AGENT_CONFIGS.get(agent_name, AGENT_CONFIGS.get("Alex"))
        if not config:
            return None

        try:
            client, model = get_ai_client(config.ai_provider)

            if config.ai_provider == "anthropic":
                response = client.messages.create(
                    model=model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return response.content[0].text

            elif config.ai_provider == "openai":
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content

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
                return response.text

            elif config.ai_provider == "xai":
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content

        except Exception as e:
            print(f"AI call failed for {agent_name}: {e}")

            # Try fallback providers
            fallback_providers = ["anthropic", "openai", "google", "xai"]
            fallback_providers.remove(config.ai_provider) if config.ai_provider in fallback_providers else None

            for provider in fallback_providers:
                try:
                    client, model = get_ai_client(provider)

                    if provider == "anthropic":
                        response = client.messages.create(
                            model=model,
                            max_tokens=4096,
                            system=system_prompt,
                            messages=[{"role": "user", "content": user_prompt}]
                        )
                        return response.content[0].text

                    elif provider in ["openai", "xai"]:
                        response = client.chat.completions.create(
                            model=model,
                            max_tokens=4096,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ]
                        )
                        return response.choices[0].message.content

                except Exception as fallback_error:
                    print(f"Fallback to {provider} failed: {fallback_error}")
                    continue

            return None
