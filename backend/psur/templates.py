"""
PSUR Report Templates - Interchangeable regulatory framework definitions.

Provides data-driven template configs for EU+UK MDR (CE-marked) and
Non-CE Marked (internal QMS / FDA / TGA) report variants.  Each template
controls cover page fields, per-section word limits, required tables,
required charts, regulatory references, and agent prompt overrides.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CoverPageField:
    """Single field on the report cover page."""
    key: str
    label: str
    mandatory: bool = True
    default_value: str = ""


@dataclass
class CoverPageGroup:
    """Grouped block of cover page fields (e.g., Manufacturer Info)."""
    title: str
    fields: List[CoverPageField] = field(default_factory=list)


@dataclass
class SectionSpec:
    """Per-section configuration within a template."""
    title: str
    mandatory: bool = True
    word_limit: int = 800
    regulatory_ref: str = ""
    special_instructions: str = ""
    required_tables: List[str] = field(default_factory=list)
    required_charts: List[str] = field(default_factory=list)


@dataclass
class PSURTemplate:
    """Complete template definition for a PSUR regulatory framework."""
    id: str
    name: str
    jurisdiction: str
    regulatory_basis: str
    classification_systems: List[str] = field(default_factory=list)
    section_specs: Dict[str, SectionSpec] = field(default_factory=dict)
    global_instructions: str = ""
    cover_page_groups: List[CoverPageGroup] = field(default_factory=list)


# ---------------------------------------------------------------------------
# EU + UK MDR Template (CE-marked devices, MDCG 2022-21 full Annex II)
# ---------------------------------------------------------------------------

_EU_UK_COVER = [
    CoverPageGroup(
        title="Manufacturer Information",
        fields=[
            CoverPageField("manufacturer", "Manufacturer"),
            CoverPageField("manufacturer_address", "Address"),
            CoverPageField("manufacturer_srn", "SRN (Single Registration Number)"),
            CoverPageField("authorized_rep", "Authorised Representative"),
            CoverPageField("authorized_rep_address", "AR Address", mandatory=False),
        ],
    ),
    CoverPageGroup(
        title="Regulatory Information",
        fields=[
            CoverPageField("notified_body", "Notified Body"),
            CoverPageField("notified_body_number", "NB Number"),
            CoverPageField("certificate_number", "Certificate Number", mandatory=False),
            CoverPageField("psur_cadence", "PSUR Cadence", default_value="Every 2 Years"),
        ],
    ),
    CoverPageGroup(
        title="Document Information",
        fields=[
            CoverPageField("period_start", "Data Collection Start"),
            CoverPageField("period_end", "Data Collection End"),
            CoverPageField("generated_date", "Report Generation Date"),
            CoverPageField("psur_sequence_number", "PSUR Sequence Number"),
        ],
    ),
]

_EU_UK_SECTIONS: Dict[str, SectionSpec] = {
    "B": SectionSpec(
        title="Scope and Document References",
        word_limit=1000,
        regulatory_ref="MDCG 2022-21 Section 1",
        special_instructions=(
            "List all referenced standards, IFUs, risk management files, and "
            "CER documents. Cite EU MDR 2017/745 and UK MDR SI 2024/1368 "
            "where applicable."
        ),
    ),
    "C": SectionSpec(
        title="Post-Market Data: Units Distributed",
        word_limit=800,
        regulatory_ref="MDCG 2022-21 Section 2.1",
        special_instructions=(
            "Provide annual and cumulative distribution figures broken down by "
            "region (EU, UK, US, RoW). Data tables and charts will be generated "
            "separately. Reference them, do NOT reproduce data in narrative."
        ),
        required_tables=["sales_by_region"],
        required_charts=["table1_units_year", "table2_units_region"],
    ),
    "D": SectionSpec(
        title="Post-Market Data: Serious Incidents & Field Safety",
        word_limit=600,
        regulatory_ref="MDCG 2022-21 Section 2.2",
        special_instructions=(
            "Summarise all reportable serious incidents per MDR Article 87 and "
            "UK MDR Regulation 62. Report deaths and serious injuries separately. "
            "Data tables will be generated separately."
        ),
        required_tables=["serious_incident"],
        required_charts=["table4_si_summary", "table5_si_type"],
    ),
    "E": SectionSpec(
        title="Post-Market Data: Non-Serious Incidents / Customer Feedback",
        word_limit=500,
        regulatory_ref="MDCG 2022-21 Section 2.3",
        special_instructions=(
            "Classify customer feedback by type and severity using IMDRF codes. "
            "Data tables will be generated separately."
        ),
        required_tables=["feedback"],
    ),
    "F": SectionSpec(
        title="Post-Market Data: Complaint Analysis",
        word_limit=800,
        regulatory_ref="MDCG 2022-21 Section 2.4",
        special_instructions=(
            "Analyse complaints by type, severity, and root cause. Show complaint "
            "rate per units distributed by year. Reference data tables and charts. "
            "Do NOT reproduce raw complaint data in narrative."
        ),
        required_tables=["complaint_rate"],
        required_charts=["table3_complaints_year", "dist_severity", "dist_type", "dist_root_cause"],
    ),
    "G": SectionSpec(
        title="Trend Analysis",
        word_limit=600,
        regulatory_ref="MDR Article 88, MDCG 2022-21 Section 3",
        special_instructions=(
            "Perform full trend analysis including UCL/LCL control limits where "
            "sample size permits. Identify statistically significant trends. "
            "Reference trend charts generated separately."
        ),
        required_charts=["table6_si_time", "trend_complaint_rate"],
    ),
    "H": SectionSpec(
        title="Field Safety Corrective Actions (FSCA)",
        word_limit=500,
        regulatory_ref="MDCG 2022-21 Section 4",
        special_instructions=(
            "Document all FSCAs issued during the reporting period. If none, "
            "state explicitly. Reference FSCA table if generated."
        ),
        required_tables=["fsca"],
        required_charts=["table7_fsca"],
    ),
    "I": SectionSpec(
        title="CAPA and Effectiveness Verification",
        word_limit=600,
        regulatory_ref="MDCG 2022-21 Section 5",
        special_instructions=(
            "List all CAPAs opened, closed, and verified during the period. "
            "Reference CAPA data table generated separately."
        ),
        required_tables=["capa"],
        required_charts=["table8_capa"],
    ),
    "J": SectionSpec(
        title="Scientific / Clinical Literature Review and Benefit-Risk",
        word_limit=800,
        regulatory_ref="MDCG 2022-21 Section 6",
        special_instructions=(
            "Summarise relevant literature published during the period. "
            "Conclude with overall benefit-risk determination citing MDR "
            "Annex I General Safety and Performance Requirements."
        ),
    ),
    "K": SectionSpec(
        title="External Database Searches",
        word_limit=500,
        regulatory_ref="MDCG 2022-21 Section 7",
        special_instructions=(
            "Document searches of MAUDE, BfArM, MHRA, Eudamed where applicable. "
            "Reference external database results table generated separately."
        ),
        required_tables=["external_db"],
    ),
    "L": SectionSpec(
        title="Post-Market Clinical Follow-Up (PMCF)",
        word_limit=600,
        regulatory_ref="MDCG 2022-21 Section 8, MDR Article 61",
        special_instructions=(
            "Describe PMCF plan status, any active studies, and safety concerns. "
            "If no PMCF activity, provide justification per MDCG 2020-7."
        ),
    ),
    "M": SectionSpec(
        title="Overall Conclusions and PSUR Summary",
        word_limit=1200,
        regulatory_ref="MDCG 2022-21 Section 9",
        special_instructions=(
            "Synthesise findings from all sections. Confirm or update the "
            "benefit-risk determination. List all recommended actions. "
            "This section is written LAST and must reference all prior sections."
        ),
    ),
    "A": SectionSpec(
        title="Executive Summary and Device Identification",
        word_limit=1200,
        regulatory_ref="MDCG 2022-21 Section 0",
        special_instructions=(
            "Provide device identification (UDI-DI, classification, intended use) "
            "and a concise executive summary of the entire PSUR. This section is "
            "written LAST after all other sections are complete."
        ),
        required_tables=["classification", "device_timeline", "model_catalog"],
    ),
}

EU_UK_MDR_TEMPLATE = PSURTemplate(
    id="eu_uk_mdr",
    name="EU MDR + UK MDR (CE-marked)",
    jurisdiction="EU / UK",
    regulatory_basis="EU MDR 2017/745 Article 86, UK MDR SI 2024/1368, MDCG 2022-21",
    classification_systems=["eu_mdr", "uk_mdr"],
    section_specs=_EU_UK_SECTIONS,
    global_instructions=(
        "This PSUR must comply with EU MDR 2017/745 and UK MDR SI 2024/1368. "
        "Reference MDCG 2022-21 guidance throughout. Use FormQAR-054 structure. "
        "Include both EU and UK regulatory classifications. "
        "Cite Annex II tables by number where the template specifies them. "
        "DATA TABLES AND CHARTS ARE GENERATED SEPARATELY FROM YOUR NARRATIVE. "
        "Do NOT reproduce raw data tables in your text. Reference them instead "
        "(e.g., 'As shown in Table 1...'). Focus on analysis and interpretation."
    ),
    cover_page_groups=_EU_UK_COVER,
)


# ---------------------------------------------------------------------------
# Non-CE Marked Template (internal QMS, FDA/TGA markets)
# ---------------------------------------------------------------------------

_NON_CE_COVER = [
    CoverPageGroup(
        title="Manufacturer Information",
        fields=[
            CoverPageField("manufacturer", "Manufacturer"),
            CoverPageField("manufacturer_address", "Address"),
            CoverPageField("manufacturer_srn", "SRN", mandatory=False, default_value="N/A"),
            CoverPageField("authorized_rep", "Authorised Representative", mandatory=False, default_value="N/A"),
        ],
    ),
    CoverPageGroup(
        title="Regulatory Information",
        fields=[
            CoverPageField("notified_body", "Notified Body", mandatory=False, default_value="N/A"),
            CoverPageField("notified_body_number", "NB Number", mandatory=False, default_value="N/A"),
            CoverPageField("psur_cadence", "PSUR Cadence", default_value="Annual"),
        ],
    ),
    CoverPageGroup(
        title="Document Information",
        fields=[
            CoverPageField("period_start", "Data Collection Start"),
            CoverPageField("period_end", "Data Collection End"),
            CoverPageField("generated_date", "Report Generation Date"),
        ],
    ),
]

_NON_CE_SECTIONS: Dict[str, SectionSpec] = {
    "B": SectionSpec(
        title="Scope and Document References",
        word_limit=800,
        regulatory_ref="Internal QMS",
        special_instructions=(
            "This device is NOT CE-marked. Do NOT reference EU MDR or UK MDR "
            "requirements. List relevant FDA 21 CFR 803, TGA, or other "
            "national regulatory references as applicable."
        ),
    ),
    "C": SectionSpec(
        title="Post-Market Data: Units Distributed",
        word_limit=600,
        regulatory_ref="Internal QMS",
        special_instructions=(
            "Distribution data by market (US, Australia, etc.). "
            "Data tables generated separately."
        ),
        required_tables=["sales_by_region"],
        required_charts=["table1_units_year", "table2_units_region"],
    ),
    "D": SectionSpec(
        title="Post-Market Data: Serious Incidents",
        word_limit=500,
        regulatory_ref="FDA 21 CFR 803",
        special_instructions=(
            "Report all MDR-reportable events per FDA or relevant national "
            "authority requirements. Do NOT reference EU MDR Article 87."
        ),
        required_tables=["serious_incident"],
        required_charts=["table4_si_summary"],
    ),
    "E": SectionSpec(
        title="Post-Market Data: Customer Feedback",
        word_limit=400,
        regulatory_ref="Internal QMS",
        required_tables=["feedback"],
    ),
    "F": SectionSpec(
        title="Post-Market Data: Complaint Analysis",
        word_limit=600,
        regulatory_ref="Internal QMS",
        special_instructions="Analyse complaints per internal classification system.",
        required_tables=["complaint_rate"],
        required_charts=["table3_complaints_year", "dist_severity"],
    ),
    "G": SectionSpec(
        title="Trend Analysis",
        word_limit=400,
        regulatory_ref="Internal QMS",
        mandatory=False,
        special_instructions=(
            "Trend reporting depth may be adapted for non-CE devices. "
            "Provide a brief trend summary. Full UCL/LCL analysis is optional."
        ),
        required_charts=["trend_complaint_rate"],
    ),
    "H": SectionSpec(
        title="Field Safety Corrective Actions",
        word_limit=400,
        regulatory_ref="Internal QMS",
        required_tables=["fsca"],
    ),
    "I": SectionSpec(
        title="CAPA and Effectiveness Verification",
        word_limit=500,
        regulatory_ref="Internal QMS",
        required_tables=["capa"],
        required_charts=["table8_capa"],
    ),
    "J": SectionSpec(
        title="Literature Review and Benefit-Risk Determination",
        word_limit=600,
        regulatory_ref="Internal QMS",
    ),
    "K": SectionSpec(
        title="External Database Searches",
        word_limit=400,
        regulatory_ref="FDA MAUDE, TGA DAEN",
        special_instructions="Focus on FDA MAUDE and TGA DAEN searches.",
        required_tables=["external_db"],
    ),
    "L": SectionSpec(
        title="Post-Market Clinical Follow-Up",
        word_limit=400,
        regulatory_ref="Internal QMS",
        mandatory=False,
        special_instructions="PMCF may not be required for non-CE devices. State applicability.",
    ),
    "M": SectionSpec(
        title="Overall Conclusions",
        word_limit=1000,
        regulatory_ref="Internal QMS",
        special_instructions=(
            "Synthesise findings. Confirm benefit-risk. "
            "Do NOT reference EU MDR or Notified Body requirements."
        ),
    ),
    "A": SectionSpec(
        title="Executive Summary and Device Identification",
        word_limit=1000,
        regulatory_ref="Internal QMS",
        special_instructions=(
            "Provide device identification using applicable classification "
            "(US FDA Class, TGA). CE marking fields should show N/A."
        ),
        required_tables=["classification"],
    ),
}

NON_CE_TEMPLATE = PSURTemplate(
    id="non_ce",
    name="Non-CE Marked (Internal QMS)",
    jurisdiction="US / AU / Other",
    regulatory_basis="Internal QMS, FDA 21 CFR 803, TGA",
    classification_systems=["us_fda", "tga"],
    section_specs=_NON_CE_SECTIONS,
    global_instructions=(
        "This device is NOT CE-marked and is NOT distributed in the EU or UK. "
        "Do NOT reference EU MDR 2017/745, UK MDR, MDCG guidelines, or "
        "Notified Body requirements. Use FDA, TGA, or internal QMS references. "
        "DATA TABLES AND CHARTS ARE GENERATED SEPARATELY FROM YOUR NARRATIVE. "
        "Do NOT reproduce raw data tables in your text. Reference them instead."
    ),
    cover_page_groups=_NON_CE_COVER,
)


# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, PSURTemplate] = {
    "eu_uk_mdr": EU_UK_MDR_TEMPLATE,
    "non_ce": NON_CE_TEMPLATE,
}


def load_template(template_id: str) -> PSURTemplate:
    """Load a template by ID. Falls back to eu_uk_mdr if not found."""
    return TEMPLATES.get(template_id, EU_UK_MDR_TEMPLATE)


def get_section_spec(template_id: str, section_id: str) -> Optional[SectionSpec]:
    """Get the SectionSpec for a given template and section."""
    tmpl = load_template(template_id)
    return tmpl.section_specs.get(section_id)


def get_template_choices() -> List[Dict[str, str]]:
    """Return list of available templates for UI dropdown."""
    return [
        {"id": t.id, "name": t.name, "jurisdiction": t.jurisdiction}
        for t in TEMPLATES.values()
    ]
