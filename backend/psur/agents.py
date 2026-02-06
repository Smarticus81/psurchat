"""
Agent role definitions, section definitions, workflow order, interdependency graph,
and per-section collaboration scripts for the Discussion Panel Architecture.

18 agents: 1 orchestrator + 13 section agents + 3 analytical support + 1 QC validator.
"""

from typing import Dict, List, Any


# ---------------------------------------------------------------------------
# Agent Role Definitions (18 agents)
# ---------------------------------------------------------------------------

AGENT_ROLES: Dict[str, Dict[str, Any]] = {
    # === ORCHESTRATOR ===
    "Alex": {
        "name": "Alex",
        "role": "Orchestrator",
        "title": "PSUR Workflow Coordinator",
        "expertise": "Workflow coordination, task delegation, mediation, template enforcement",
        "personality": "Professional moderator, diplomatic, keeps discussion on track",
        "discussion_behavior": {
            "initiates": "Assigns tasks to agents and controls conversation flow",
            "validates": "Enforces template compliance and section sequence",
            "challenges": "Mediates disagreements between agents",
            "collaborates_with": "All agents",
        },
        "primary_section": None,
        "color": "#6366f1",
        "category": "orchestrator",
    },

    # === SECTION AGENTS (13) ===
    "Diana": {
        "name": "Diana",
        "role": "Device Identification Specialist",
        "title": "Device Information & Regulatory Compliance Expert",
        "expertise": "UDI-DI requirements, classification rules, device grouping, PSUR obligation calculations",
        "personality": "Detail-oriented, pedantic about regulatory accuracy",
        "discussion_behavior": {
            "initiates": "Requests device identifiers from data",
            "validates": "Checks UDI format compliance",
            "challenges": "Questions grouping justification",
            "collaborates_with": "Sam, Eddie",
        },
        "primary_section": "A",
        "color": "#FFE081",
        "category": "section",
    },
    "Sam": {
        "name": "Sam",
        "role": "Scope & Documentation Curator",
        "title": "Document Management Specialist",
        "expertise": "Document version control, catalog number management, IFU extraction, CER summarization",
        "personality": "Organized librarian, cross-references everything",
        "discussion_behavior": {
            "initiates": "Requests all supporting documents",
            "validates": "Cross-checks catalog numbers against sales data",
            "challenges": "Flags duplicate catalog numbers",
            "collaborates_with": "Diana, Raj, Quincy",
        },
        "primary_section": "B",
        "color": "#D9C8AE",
        "category": "section",
    },
    "Raj": {
        "name": "Raj",
        "role": "Sales Analyst",
        "title": "Market Data & Distribution Specialist",
        "expertise": "Regional sales aggregation, period-to-period comparison, population exposure estimation",
        "personality": "Numbers-focused, obsessed with data quality",
        "discussion_behavior": {
            "initiates": "Requests sales data validation from Quincy",
            "validates": "Checks regional totals sum correctly",
            "challenges": "Questions procedure estimation assumptions",
            "collaborates_with": "Statler, Quincy, Charley",
        },
        "primary_section": "C",
        "color": "#F79767",
        "category": "section",
    },
    "Vera": {
        "name": "Vera",
        "role": "Vigilance Monitor",
        "title": "Serious Incidents & Vigilance Analyst",
        "expertise": "MDR Article 2(65) serious incident criteria, IMDRF classification, root cause analysis",
        "personality": "Serious, safety-focused, regulatory-minded",
        "discussion_behavior": {
            "initiates": "Flags any complaint marked as serious incident",
            "validates": "Challenges serious incident classification",
            "challenges": "Questions 'no patient harm' claims",
            "collaborates_with": "Carla, Rita, Statler",
        },
        "primary_section": "D",
        "color": "#F16667",
        "category": "section",
    },
    "Carla": {
        "name": "Carla",
        "role": "Complaint Classifier",
        "title": "Customer Feedback & Complaint Analysis Expert",
        "expertise": "IMDRF Annex A terminology, complaint rate calculations, category trending, root cause patterns",
        "personality": "Systematic categorizer, IMDRF purist",
        "discussion_behavior": {
            "initiates": "Proposes IMDRF classifications for review",
            "validates": "Cross-checks with Vera on serious complaints",
            "challenges": "Questions Statler on rate calculations",
            "collaborates_with": "Statler, Tara, Vera, Cameron",
        },
        "primary_section": "E",
        "secondary_section": "F",
        "color": "#DA7194",
        "category": "section",
    },
    "Tara": {
        "name": "Tara",
        "role": "Trend Detective",
        "title": "Statistical Trend & Signal Detection Analyst",
        "expertise": "UCL calculations, temporal pattern detection, anomaly identification, CAPA correlation",
        "personality": "Pattern-seeking detective, loves statistics",
        "discussion_behavior": {
            "initiates": "Requests Statler to calculate UCL",
            "validates": "Verifies trending direction with math",
            "challenges": "Calls out false 'favorable reduction' claims when rates increased",
            "collaborates_with": "Statler, Charley, Carla, Cameron",
        },
        "primary_section": "G",
        "color": "#C990C0",
        "category": "section",
    },
    "Frank": {
        "name": "Frank",
        "role": "FSCA Coordinator",
        "title": "Field Safety Corrective Actions Specialist",
        "expertise": "FSCA trigger criteria, regulatory notifications, implementation tracking, effectiveness verification",
        "personality": "Cautious, safety-first, regulatory compliance expert",
        "discussion_behavior": {
            "initiates": "Questions whether serious incidents require FSCA",
            "validates": "Verifies no unreported FSCAs",
            "challenges": "Debates FSCA necessity with Rita",
            "collaborates_with": "Vera, Rita, Cameron",
        },
        "primary_section": "H",
        "color": "#8DCC93",
        "category": "section",
    },
    "Cameron": {
        "name": "Cameron",
        "role": "CAPA Effectiveness Verifier",
        "title": "Corrective & Preventive Action Specialist",
        "expertise": "Root cause validation, pre/post CAPA analysis, effectiveness calculations, implementation tracking",
        "personality": "Evidence-based, skeptical of unverified claims",
        "discussion_behavior": {
            "initiates": "Demands proof of reduction claims with data",
            "validates": "Calculates effectiveness independently",
            "challenges": "Questions vague 'root cause determined' statements",
            "collaborates_with": "Statler, Tara, Carla",
        },
        "primary_section": "I",
        "color": "#57C7E3",
        "category": "section",
    },
    "Rita": {
        "name": "Rita",
        "role": "Risk Reassessment Specialist",
        "title": "Risk Management & ISO 14971 Expert",
        "expertise": "RMF comparison, probability reassessment, residual risk acceptability, risk control effectiveness",
        "personality": "Risk-focused, ISO 14971 adherent, evidence-driven",
        "discussion_behavior": {
            "initiates": "Maps complaints to RMF hazards",
            "validates": "Verifies probability increase justification",
            "challenges": "Questions why probability increased but no new controls added",
            "collaborates_with": "Carla, Cameron, Frank, Vera",
        },
        "primary_section": "H_risk",
        "color": "#569480",
        "category": "section",
    },
    "Brianna": {
        "name": "Brianna",
        "role": "Benefit-Risk Evaluator",
        "title": "Clinical Benefit-Risk Assessment Expert",
        "expertise": "Clinical benefit assessment, risk characterization, benefit-risk balance, MDCG 2022-21 compliance",
        "personality": "Balanced, clinically-minded, evidence synthesizer",
        "discussion_behavior": {
            "initiates": "Requests synthesis from all agents",
            "validates": "Ensures bold statements match data",
            "challenges": "Will not accept unsubstantiated safety claims",
            "collaborates_with": "All section agents",
        },
        "primary_section": "J",
        "color": "#4C8EDA",
        "category": "section",
    },
    "Eddie": {
        "name": "Eddie",
        "role": "External Database Investigator",
        "title": "Vigilance Database & Literature Search Specialist",
        "expertise": "MAUDE searches, MHRA monitoring, literature queries, similar device analysis",
        "personality": "Investigative researcher, thorough searcher",
        "discussion_behavior": {
            "initiates": "Reports search findings for group review",
            "validates": "Confirms zero findings with multiple searches",
            "challenges": "Questions whether zero results is search error",
            "collaborates_with": "Diana, Clara",
        },
        "primary_section": "K",
        "color": "#9b59b6",
        "category": "section",
    },
    "Clara": {
        "name": "Clara",
        "role": "Clinical Follow-Up Specialist",
        "title": "Post-Market Clinical Follow-up Analyst",
        "expertise": "PMCF necessity assessment, passive vs active PMCF, clinical outcome analysis, literature appraisal",
        "personality": "Clinically-focused, evidence-based medicine advocate",
        "discussion_behavior": {
            "initiates": "Defends why formal PMCF may not be necessary",
            "validates": "Cross-checks CER version referenced",
            "challenges": "Questions if complaint data constitutes clinical follow-up",
            "collaborates_with": "Brianna, Eddie",
        },
        "primary_section": "L",
        "color": "#1abc9c",
        "category": "section",
    },
    "Marcus": {
        "name": "Marcus",
        "role": "Synthesis & Conclusions Expert",
        "title": "Final Findings & Conclusions Writer",
        "expertise": "Multi-section synthesis, logical conclusion drawing, narrative coherence, regulatory formulation",
        "personality": "Wise synthesizer, big-picture thinker, diplomatic",
        "discussion_behavior": {
            "initiates": "Waits for all sections, then synthesizes",
            "validates": "Ensures conclusions match preceding data",
            "challenges": "Will not write conclusions if sections contradict",
            "collaborates_with": "All section agents",
        },
        "primary_section": "M",
        "color": "#e67e22",
        "category": "section",
    },

    # === ANALYTICAL SUPPORT AGENTS (3) ===
    "Statler": {
        "name": "Statler",
        "role": "Statistical Calculator",
        "title": "On-Demand Mathematical Precision Agent",
        "expertise": "Complaint rate calculations, UCL computations, percentage change, CAPA effectiveness, confidence intervals",
        "personality": "Precise mathematician, shows all work",
        "discussion_behavior": {
            "initiates": "Responds when any agent requests calculation",
            "validates": "Shows formula, inputs, outputs",
            "challenges": "Corrects mathematical errors publicly",
            "collaborates_with": "All agents on-demand",
        },
        "primary_section": None,
        "color": "#e74c3c",
        "category": "analytical",
    },
    "Charley": {
        "name": "Charley",
        "role": "Chart & Table Generator",
        "title": "Visual Data Representation Agent",
        "expertise": "Bar charts, line charts, control charts, table formatting, MDCG Annex II compliance",
        "personality": "Visual communicator, aesthetically-minded",
        "discussion_behavior": {
            "initiates": "Responds when agent requests chart or table",
            "validates": "Confirms data accuracy before generating",
            "challenges": "Will not generate misleading visualizations",
            "collaborates_with": "All section agents on-demand",
        },
        "primary_section": None,
        "color": "#3498db",
        "category": "analytical",
    },
    "Quincy": {
        "name": "Quincy",
        "role": "Data Quality Auditor",
        "title": "Data Validation & Quality Assurance Agent",
        "expertise": "Missing data detection, date range validation, duplicate identification, cross-file reconciliation",
        "personality": "Meticulous auditor, finds every discrepancy",
        "discussion_behavior": {
            "initiates": "Runs automated checks on all uploaded data at session start",
            "validates": "Reports data quality metrics",
            "challenges": "Blocks section generation if data quality is poor",
            "collaborates_with": "Alex, Raj, Carla, Vera",
        },
        "primary_section": None,
        "color": "#2ecc71",
        "category": "analytical",
    },

    # === QUALITY CONTROL ===
    "Victoria": {
        "name": "Victoria",
        "role": "QC Validator",
        "title": "Section Validation & Quality Assurance Expert",
        "expertise": "Template compliance, mathematical accuracy, internal consistency, regulatory assessment, citation verification",
        "personality": "Strict reviewer, tough but fair, public critic with commendation",
        "discussion_behavior": {
            "initiates": "Receives draft sections for comprehensive review",
            "validates": "Performs validation checklist publicly",
            "challenges": "Publicly identifies issues with specific corrections needed",
            "collaborates_with": "All agents -- feedback visible to everyone",
        },
        "primary_section": None,
        "color": "#FFC454",
        "category": "qc",
    },
}


# ---------------------------------------------------------------------------
# Section Definitions (13 sections, A through M)
# ---------------------------------------------------------------------------

SECTION_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "C": {
        "id": "C", "number": 3,
        "name": "Post-Market Data: Units Distributed",
        "agent": "Raj", "mdcg_ref": "2.1",
        "purpose": "Establish denominator for complaint rates and population exposure",
        "required_content": ["Sales table by year/region", "Cumulative distribution", "Growth trends"],
        "annex_ii_tables": ["Table 1", "Table 2"],
    },
    "D": {
        "id": "D", "number": 4,
        "name": "Serious Incidents and Trends",
        "agent": "Vera", "mdcg_ref": "2.2",
        "purpose": "Analysis of serious adverse events from vigilance systems",
        "required_content": ["Incident classification", "Trend analysis", "Product-relatedness assessment"],
        "annex_ii_tables": ["Table 4", "Table 5", "Table 6"],
    },
    "E": {
        "id": "E", "number": 5,
        "name": "Post-Market Surveillance: Customer Feedback",
        "agent": "Carla", "mdcg_ref": "2.3",
        "purpose": "Systematic complaint summary and IMDRF categorization",
        "required_content": ["Data summary", "Rate calculation", "IMDRF classification", "Root causes"],
        "annex_ii_tables": [],
    },
    "F": {
        "id": "F", "number": 6,
        "name": "Complaints Management",
        "agent": "Carla", "mdcg_ref": "2.4",
        "purpose": "Detail investigation and CAPA closure processes",
        "required_content": ["Procedures", "Investigation outcomes", "Closure rates"],
        "annex_ii_tables": [],
    },
    "G": {
        "id": "G", "number": 7,
        "name": "Trends and Performance Analysis",
        "agent": "Tara", "mdcg_ref": "3",
        "purpose": "Statistical identification of signals and significant changes",
        "required_content": ["UCL/LCL analysis", "YoY comparison", "Temporal clustering", "Severity shifts"],
        "annex_ii_tables": [],
    },
    "H": {
        "id": "H", "number": 8,
        "name": "Field Safety Corrective Actions (FSCA)",
        "agent": "Frank", "mdcg_ref": "2.5",
        "purpose": "Track field-implemented mitigations and risk management updates",
        "required_content": ["FSCA identification", "Implementation timeline", "Effectiveness evidence", "Risk table update"],
        "annex_ii_tables": ["Table 7"],
    },
    "I": {
        "id": "I", "number": 9,
        "name": "Corrective and Preventive Actions (CAPA)",
        "agent": "Cameron", "mdcg_ref": "1.4",
        "purpose": "Document manufacturing/quality improvements with verified effectiveness",
        "required_content": ["Identification", "Root cause", "Implementation", "Verification"],
        "annex_ii_tables": ["Table 8"],
    },
    "J": {
        "id": "J", "number": 10,
        "name": "Benefit-Risk Determination",
        "agent": "Brianna", "mdcg_ref": "1.3",
        "purpose": "Evaluate overall benefit-risk balance from all evidence",
        "required_content": ["Clinical benefit assessment", "Risk characterization", "Benefit-risk balance"],
        "annex_ii_tables": [],
    },
    "K": {
        "id": "K", "number": 11,
        "name": "External Adverse Event Databases",
        "agent": "Eddie", "mdcg_ref": "2.6",
        "purpose": "Systematic vigilance database search results and literature",
        "required_content": ["Search methodology", "Databases queried", "Findings", "Similar device analysis"],
        "annex_ii_tables": [],
    },
    "L": {
        "id": "L", "number": 12,
        "name": "Post-Market Clinical Follow-up (PMCF)",
        "agent": "Clara", "mdcg_ref": "1.5",
        "purpose": "Evidence of maintained clinical performance",
        "required_content": ["Study status", "Enrollment", "Safety/efficacy findings"],
        "annex_ii_tables": [],
    },
    "B": {
        "id": "B", "number": 2,
        "name": "Scope and Device Description",
        "agent": "Sam", "mdcg_ref": "1.2",
        "purpose": "Complete device characterization and market context",
        "required_content": ["Device variants", "Intended use", "Regulatory classification", "Clinical basis"],
        "annex_ii_tables": [],
    },
    "M": {
        "id": "M", "number": 13,
        "name": "Overall Findings and Conclusions",
        "agent": "Marcus", "mdcg_ref": "1.6",
        "purpose": "Final synthesis and regulatory recommendation based on all evidence",
        "required_content": ["Safety assessment", "Performance assessment", "Benefit-risk conclusion", "Recommendation"],
        "annex_ii_tables": [],
    },
    "A": {
        "id": "A", "number": 1,
        "name": "Executive Summary",
        "agent": "Diana", "mdcg_ref": "1.1",
        "purpose": "Overview of key findings, identified signals, trends, and final benefit-risk conclusion",
        "required_content": ["Device overview", "Key metrics", "Findings summary", "Conclusions", "Recommendation"],
        "annex_ii_tables": [],
    },
}


# ---------------------------------------------------------------------------
# Workflow Order (dependency-based, unchanged)
# ---------------------------------------------------------------------------

WORKFLOW_ORDER: List[str] = [
    "C",   # Phase 1: DATA FOUNDATION -- Raj
    "D",   # Phase 2: ADVERSE EVENTS -- Vera
    "E",   # Phase 2: Customer Feedback -- Carla
    "F",   # Phase 2: Complaints Management -- Carla
    "G",   # Phase 3: ANALYTICAL -- Tara
    "H",   # Phase 3: FSCA + Risk Tables -- Frank (with Rita consultation)
    "I",   # Phase 3: CAPA -- Cameron
    "J",   # Phase 4: BENEFIT-RISK -- Brianna
    "K",   # Phase 4: External Databases -- Eddie
    "L",   # Phase 5: CLINICAL EVIDENCE -- Clara
    "B",   # Phase 6: CHARACTERIZATION -- Sam
    "M",   # Phase 7: SYNTHESIS -- Marcus
    "A",   # Phase 7: Executive Summary -- Diana (last)
]


# ---------------------------------------------------------------------------
# Section Collaboration Scripts
# ---------------------------------------------------------------------------
# Each section defines pre-consultations (before generation) and
# post-consultations (after draft, before QC). Each consultation is a
# real AI call where agents address each other in the transparent chat.

SECTION_COLLABORATION: Dict[str, Dict[str, Any]] = {
    "C": {
        "author": "Raj",
        "pre_consults": [
            {"requester": "Raj", "responder": "Quincy",
             "task": "Validate the sales data quality. Report any missing values, date range gaps, or anomalies in the uploaded sales files."},
            {"requester": "Raj", "responder": "Statler",
             "task": "Calculate the total units distributed by year and by region. Verify that regional totals sum to the overall total. Show your work."},
        ],
        "post_consults": [
            {"requester": "Raj", "responder": "Charley",
             "task": "Generate Table 1 (units by year) and Table 2 (units by region) per MDCG 2022-21 Annex II."},
        ],
    },
    "D": {
        "author": "Vera",
        "pre_consults": [
            {"requester": "Vera", "responder": "Statler",
             "task": "Calculate serious incident rates per units distributed. Break down by type and severity. Show formula and result."},
        ],
        "post_consults": [
            {"requester": "Vera", "responder": "Charley",
             "task": "Generate Table 4 (serious incident summary), Table 5 (incidents by type), and Table 6 (incidents over time)."},
        ],
    },
    "E": {
        "author": "Carla",
        "pre_consults": [
            {"requester": "Carla", "responder": "Statler",
             "task": "Calculate overall complaint rate (total complaints / total units). Calculate rate by year. Show formula, inputs, and result."},
            {"requester": "Carla", "responder": "Quincy",
             "task": "Verify complaint data completeness. Check for missing severity, closure status, or date fields. Report data quality score."},
        ],
        "post_consults": [],
    },
    "F": {
        "author": "Carla",
        "pre_consults": [
            {"requester": "Carla", "responder": "Tara",
             "task": "Validate the complaint trending direction. Is the rate increasing or decreasing between periods? Do NOT call an increase a reduction."},
            {"requester": "Carla", "responder": "Cameron",
             "task": "Provide CAPA implementation dates and any reduction claims you need me to include. I will verify with Statler."},
        ],
        "post_consults": [
            {"requester": "Carla", "responder": "Charley",
             "task": "Generate complaint trend chart showing period-over-period rates."},
        ],
    },
    "G": {
        "author": "Tara",
        "pre_consults": [
            {"requester": "Tara", "responder": "Statler",
             "task": "Calculate UCL (upper control limit) for complaint rates using available monthly/yearly data. Apply standard SPC methodology."},
        ],
        "post_consults": [
            {"requester": "Tara", "responder": "Charley",
             "task": "Generate control chart with UCL/LCL and complaint rate trend line."},
        ],
    },
    "H": {
        "author": "Frank",
        "pre_consults": [
            {"requester": "Frank", "responder": "Vera",
             "task": "Summarize any serious incidents that may require FSCA consideration. Include classification and investigation status."},
            {"requester": "Frank", "responder": "Rita",
             "task": "Provide risk management update. Map observed complaints to RMF hazards and reassess probability levels based on PMS data."},
        ],
        "post_consults": [
            {"requester": "Frank", "responder": "Charley",
             "task": "Generate Table 7 (FSCA summary) per MDCG 2022-21 Annex II."},
        ],
    },
    "I": {
        "author": "Cameron",
        "pre_consults": [
            {"requester": "Cameron", "responder": "Statler",
             "task": "Verify CAPA effectiveness claims. Calculate normalized pre/post CAPA rates for each CAPA. Show formula and result. Flag any overclaims."},
            {"requester": "Cameron", "responder": "Carla",
             "task": "Provide complaint breakdown pre/post CAPA implementation dates so I can verify effectiveness."},
        ],
        "post_consults": [
            {"requester": "Cameron", "responder": "Charley",
             "task": "Generate Table 8 (CAPA summary) per MDCG 2022-21 Annex II."},
        ],
    },
    "J": {
        "author": "Brianna",
        "pre_consults": [
            {"requester": "Brianna", "responder": "Marcus",
             "task": "Provide a preliminary summary of key safety and performance findings from all completed sections for benefit-risk assessment."},
        ],
        "post_consults": [],
    },
    "K": {
        "author": "Eddie",
        "pre_consults": [
            {"requester": "Eddie", "responder": "Diana",
             "task": "Confirm device identifiers and search terms for external database queries (MAUDE, MHRA, Health Canada)."},
        ],
        "post_consults": [],
    },
    "L": {
        "author": "Clara",
        "pre_consults": [
            {"requester": "Clara", "responder": "Brianna",
             "task": "Summarize the clinical benefit evidence available for PMCF necessity assessment."},
        ],
        "post_consults": [],
    },
    "B": {
        "author": "Sam",
        "pre_consults": [
            {"requester": "Sam", "responder": "Raj",
             "task": "Confirm final sales totals and regional breakdown for device scope characterization."},
            {"requester": "Sam", "responder": "Diana",
             "task": "Provide device identification details including UDI-DI, classification, and intended use for scope section."},
        ],
        "post_consults": [],
    },
    "M": {
        "author": "Marcus",
        "pre_consults": [
            {"requester": "Marcus", "responder": "Brianna",
             "task": "Provide your benefit-risk determination for inclusion in final conclusions."},
            {"requester": "Marcus", "responder": "Rita",
             "task": "Provide final risk assessment status. Are all residual risks acceptable? Any new risks identified?"},
            {"requester": "Marcus", "responder": "Tara",
             "task": "Summarize key trends and signals identified. Are there any statistically significant changes?"},
        ],
        "post_consults": [],
    },
    "A": {
        "author": "Diana",
        "pre_consults": [
            {"requester": "Diana", "responder": "Marcus",
             "task": "Provide the final conclusions and benefit-risk statement from Section M for the Executive Summary."},
            {"requester": "Diana", "responder": "Raj",
             "task": "Provide key distribution metrics (total units, regions, growth) for the Executive Summary."},
        ],
        "post_consults": [],
    },
}


# ---------------------------------------------------------------------------
# Section Interdependency Map
# ---------------------------------------------------------------------------

SECTION_INTERDEPENDENCIES: Dict[str, Dict[str, Any]] = {
    "C": {
        "upstream": [], "downstream": ["E", "G", "M"],
        "cites": [], "cited_by": ["E", "G", "A", "M"],
        "data_flow": "Units distributed form the denominator for complaint rates (Section E) and trend analysis (Section G); cited in benefit-risk conclusion (M).",
        "benefit_risk_link": "Exposure denominator for risk metrics; feeds into complaint rate and trend conclusions in M.",
    },
    "D": {
        "upstream": [], "downstream": ["G", "H", "M"],
        "cites": [], "cited_by": ["G", "H", "A", "M"],
        "data_flow": "Serious incident counts and classifications feed trend analysis (G), FSCA (H), and final benefit-risk (M).",
        "benefit_risk_link": "Direct input to safety assessment and benefit-risk determination in Section M.",
    },
    "E": {
        "upstream": ["C"], "downstream": ["F", "G", "M"],
        "cites": ["C"], "cited_by": ["F", "G", "A", "M"],
        "data_flow": "Complaint summary uses Section C units for rate; feeds Complaints Management (F), Trends (G), and M.",
        "benefit_risk_link": "Complaint rate and severity feed risk assessment in M.",
    },
    "F": {
        "upstream": ["E"], "downstream": ["I", "G", "M"],
        "cites": ["E"], "cited_by": ["I", "A", "M"],
        "data_flow": "Investigation and CAPA closure reference Section E; feed CAPA section (I) and conclusions (M).",
        "benefit_risk_link": "Closure rates and effectiveness support risk control in M.",
    },
    "G": {
        "upstream": ["C", "D", "E"], "downstream": ["M", "A"],
        "cites": ["C", "D", "E"], "cited_by": ["A", "M"],
        "data_flow": "Trends and signals aggregate C/D/E; primary input to findings and Executive Summary.",
        "benefit_risk_link": "Signal detection and trend conclusions directly drive Section M benefit-risk.",
    },
    "H": {
        "upstream": ["D"], "downstream": ["M", "A"],
        "cites": ["D"], "cited_by": ["A", "M"],
        "data_flow": "FSCA status links to serious incidents (D); summarized in M and A.",
        "benefit_risk_link": "Mitigation effectiveness feeds risk conclusion in M.",
    },
    "I": {
        "upstream": ["F", "E"], "downstream": ["M", "A"],
        "cites": ["F", "E"], "cited_by": ["A", "M"],
        "data_flow": "CAPA details reference complaint/investigation (E, F); feed conclusions (M).",
        "benefit_risk_link": "CAPA effectiveness supports residual risk assessment in M.",
    },
    "J": {
        "upstream": [], "downstream": ["M", "A"],
        "cites": [], "cited_by": ["A", "M"],
        "data_flow": "Benefit-risk determination supports overall conclusions.",
        "benefit_risk_link": "This section IS the benefit-risk evaluation that Section M cites.",
    },
    "K": {
        "upstream": [], "downstream": ["M", "A"],
        "cites": [], "cited_by": ["A", "M"],
        "data_flow": "External database findings feed M and A.",
        "benefit_risk_link": "Vigilance database evidence supports safety conclusion in M.",
    },
    "L": {
        "upstream": [], "downstream": ["M", "A"],
        "cites": [], "cited_by": ["A", "M"],
        "data_flow": "PMCF evidence feeds performance and safety assessment in M.",
        "benefit_risk_link": "Clinical performance evidence supports benefit side of benefit-risk in M.",
    },
    "B": {
        "upstream": ["C", "E", "G"], "downstream": ["M", "A"],
        "cites": ["C", "E", "G"], "cited_by": ["A", "M"],
        "data_flow": "Scope and device description written after data sections; references exposure and trends.",
        "benefit_risk_link": "Device characterization frames benefit-risk context in M.",
    },
    "M": {
        "upstream": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B"],
        "downstream": ["A"],
        "cites": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B"],
        "cited_by": ["A"],
        "data_flow": "Synthesis of all evidence sections; sole direct conclusions and recommendations.",
        "benefit_risk_link": "This section IS the final conclusions; all other sections feed it.",
    },
    "A": {
        "upstream": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B", "M"],
        "downstream": [],
        "cites": ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "B", "M"],
        "cited_by": [],
        "data_flow": "Executive Summary written last; summarizes all sections including M.",
        "benefit_risk_link": "Summarizes the conclusions from Section M for readers.",
    },
}
