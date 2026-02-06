"""
PSUR Engine - Modular MDCG 2022-21 Compliant PSUR Generation System

Modules:
    context         - PSURContext dataclass and metrics
    agents          - Agent roles, section definitions, workflow order
    templates       - Interchangeable regulatory framework templates
    extraction      - Data file parsing (CSV, Excel, DOCX)
    prompts         - Prompt builders for all agents
    ai_client       - Unified AI provider abstraction with fallback
    chart_generator - MDCG Annex II tables and trend charts
    docx_tables     - python-docx table builders for report generation
    regulatory      - Unified RegulatoryKnowledgeService
    orchestrator    - Workflow engine
"""

from backend.psur.context import PSURContext, WorkflowStatus
from backend.psur.agents import (
    AGENT_ROLES, SECTION_DEFINITIONS, WORKFLOW_ORDER,
    SECTION_INTERDEPENDENCIES, SECTION_COLLABORATION,
)
from backend.psur.templates import load_template, get_template_choices, TEMPLATES
from backend.psur.orchestrator import SOTAOrchestrator
