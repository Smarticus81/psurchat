"""
PSURContext - Complete regulatory and operational context for all agents.
Single source of truth for device data, metrics, constraints, and raw samples.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class WorkflowStatus(Enum):
    """Workflow execution states for interactive control."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class PSURContext:
    """
    Complete regulatory and operational context for all agents.
    Every field populated from manufacturer data AND validated against regulatory requirements.
    """

    # === MANUFACTURER & DEVICE IDENTIFICATION ===
    device_name: str = ""
    device_variants: List[str] = field(default_factory=list)
    manufacturer: str = ""
    manufacturer_address: str = ""
    manufacturer_srn: str = ""
    authorized_rep: str = ""
    authorized_rep_address: str = ""
    udi_di: str = ""

    # === DEVICE CHARACTERIZATION ===
    device_type: str = ""
    intended_use: str = ""
    regulatory_classification: Dict[str, str] = field(default_factory=dict)
    notified_body: str = ""
    notified_body_number: str = ""
    sterilization_method: str = "Not applicable"

    # === REPORTING PERIOD & TIMELINE ===
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    psur_cadence: str = "Every 2 Years"
    submission_deadline: Optional[datetime] = None
    previous_psur_date: Optional[datetime] = None

    # === MARKET PRESENCE ===
    regions: List[str] = field(default_factory=list)
    total_units_sold: int = 0
    total_units_by_year: Dict[int, int] = field(default_factory=dict)
    total_units_by_region: Dict[str, int] = field(default_factory=dict)
    cumulative_units_all_time: int = 0

    # === REGULATORY PURPOSE ===
    regulatory_basis: str = "MDR 2017/745 Article 86"
    psur_purpose: str = "Demonstrate continued safety and performance"
    risk_benefit_favorable: bool = True

    # === DATA SOURCE FLAGS ===
    data_files: List[Dict] = field(default_factory=list)
    sales_data_available: bool = False
    complaint_data_available: bool = False
    vigilance_data_available: bool = False
    clinical_follow_up_data_available: bool = False

    # === COMPLAINT METRICS ===
    total_complaints: int = 0
    total_complaints_by_year: Dict[int, int] = field(default_factory=dict)
    complaint_rate_percent: float = 0.0
    complaint_rate_by_year: Dict[int, float] = field(default_factory=dict)
    complaints_by_type: Dict[str, int] = field(default_factory=dict)
    complaints_by_severity: Dict[str, int] = field(default_factory=dict)
    complaints_closed_count: int = 0
    complaints_with_root_cause_identified: int = 0
    investigation_closure_rate: float = 0.0
    complaints_product_defect: int = 0
    complaints_user_error: int = 0
    complaints_unrelated: int = 0
    complaints_unconfirmed: int = 0

    # === SERIOUS INCIDENTS & VIGILANCE ===
    serious_incidents: int = 0
    total_vigilance_events: int = 0
    serious_incidents_by_type: Dict[str, int] = field(default_factory=dict)
    deaths: int = 0
    serious_injuries: int = 0

    # === RISK MANAGEMENT ===
    known_residual_risks: List[str] = field(default_factory=list)
    new_signals_identified: List[str] = field(default_factory=list)
    changed_risk_profiles: List[str] = field(default_factory=list)

    # === CAPA ===
    capa_actions_open: int = 0
    capa_actions_closed_this_period: int = 0
    capa_actions_effectiveness_verified: int = 0
    capa_details: List[Dict] = field(default_factory=list)

    # === PMCF ===
    pmcf_plan_approved: bool = False
    pmcf_studies_active: List[str] = field(default_factory=list)
    pmcf_safety_concerns: List[str] = field(default_factory=list)

    # === TEMPORAL CONTINUITY ===
    previous_psur_safety_concerns: List[str] = field(default_factory=list)
    previous_psur_recommendations: List[str] = field(default_factory=list)
    actions_taken_on_previous_findings: List[str] = field(default_factory=list)
    psur_sequence_number: int = 1
    psur_sequence_narrative: str = ""
    previous_capa_status_summary: str = ""
    trending_across_periods_narrative: str = ""

    # === QUALITY AWARENESS ===
    missing_fields: List[str] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)
    data_confidence_by_domain: Dict[str, str] = field(default_factory=dict)
    completeness_score: float = 0.0

    # === MASTER CONTEXT (Golden Source) ===
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

    # === GLOBAL CONSTRAINTS ===
    global_constraints: Dict[str, Any] = field(default_factory=dict)

    # === TEMPLATE CONFIGURATION ===
    template_id: str = "eu_uk_mdr"
    template_config: Dict[str, Any] = field(default_factory=dict)

    # === GRKB REGULATORY GROUNDING ===
    grkb_obligations: List[Dict[str, Any]] = field(default_factory=list)
    grkb_sections: List[Dict[str, Any]] = field(default_factory=list)
    grkb_evidence_types: List[Dict[str, Any]] = field(default_factory=list)
    grkb_system_instructions: Dict[str, Any] = field(default_factory=dict)
    grkb_template: Dict[str, Any] = field(default_factory=dict)
    grkb_available: bool = False

    # === RAW DATA SAMPLES ===
    sales_raw_sample: str = ""
    complaints_raw_sample: str = ""
    vigilance_raw_sample: str = ""
    sales_columns_detected: List[str] = field(default_factory=list)
    complaints_columns_detected: List[str] = field(default_factory=list)
    vigilance_columns_detected: List[str] = field(default_factory=list)

    # === COLUMN MAPPINGS (per-file extraction diagnostics) ===
    column_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # === TEXT DOCUMENTS (extracted from DOCX/PDF/TXT uploads) ===
    text_documents: List[Dict[str, str]] = field(default_factory=list)

    # === SUPPLEMENTARY DATA SAMPLES (risk, cer, pmcf tabular files) ===
    supplementary_raw_samples: Dict[str, str] = field(default_factory=dict)
    supplementary_columns: Dict[str, List[str]] = field(default_factory=dict)

    def calculate_metrics(self):
        """Calculate derived metrics from raw data."""
        if self.total_units_sold > 0:
            self.complaint_rate_percent = (self.total_complaints / self.total_units_sold) * 100
            # Per-year complaint rates
            if self.total_complaints_by_year and self.total_units_by_year:
                self.complaint_rate_by_year = {}
                for yr, count in self.total_complaints_by_year.items():
                    units = self.total_units_by_year.get(yr, 0)
                    if units > 0:
                        self.complaint_rate_by_year[yr] = (count / units) * 100
        if self.total_complaints > 0:
            self.investigation_closure_rate = (
                self.complaints_closed_count / self.total_complaints
            ) * 100
