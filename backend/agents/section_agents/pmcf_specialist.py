"""
PMCF Specialist Agent - Clara
Generates Section L: Post-Market Clinical Follow-up (PMCF)
Uses Gemini 2.5 Pro for clinical data analysis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class PMCFSpecialistAgent(BaseAgent):
    """
    PMCF Specialist Agent
    Name: Clara
    Model: Gemini 2.5 Pro
    Section: L - Post-Market Clinical Follow-up
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["pmcf"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Clara, the PMCF Specialist.

Your expertise:
- Post-Market Clinical Follow-up (PMCF) per MDR Annex XIV Part B
- PMCF plan implementation and compliance
- Clinical data collection and analysis
- CER updates from PMCF data

Your task for Section L:
- Review PMCF plan execution
- Document PMCF activities undertaken
- Summarize clinical data collected
- Assess impact on Clinical Evaluation

Reference MEDDEV 2.12/2 and MDR requirements."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section L: PMCF Activities"""
        
        await self.post_message(
            "🏥 Clara here! Starting Section L: Post-Market Clinical Follow-up.\n\n"
            "Reviewing PMCF plan and activities...",
            message_type="normal"
        )
        
        # Mock PMCF data (would come from database)
        pmcf_studies = 1
        pmcf_active = True
        
        await self.post_message(
            f"✓ PMCF Status:\n"
            f"- Active PMCF Plan: {'Yes' if pmcf_active else 'No'}\n"
            f"- Studies in progress: {pmcf_studies}\n"
            f"Analyzing clinical data collection..."
        )
        
        prompt = f"""Generate Section L (Post-Market Clinical Follow-up).

PMCF Status: {'Active' if pmcf_active else 'Inactive'}
Studies: {pmcf_studies}

Requirements:
1. **PMCF Plan Overview**
   - PMCF plan objectives
   - Planned activities (surveys, registries, studies)
   - Timeline and milestones

2. **PMCF Activities Undertaken**
   - Activities completed in surveillance period
   - Data collection methods
   - Patient/user feedback mechanisms

3. **Clinical Data Collected**
   - Summary of PMCF findings
   - Safety data from PMCF
   - Performance data from clinical use
   - Any unexpected findings

4. **Impact on Clinical Evaluation**
   - Updates to Clinical Evaluation Report (CER)
   - Confirmation or changes to benefit-risk
   - Need for PMCF plan modifications

5. **Compliance**
   - Adherence to PMCF plan
   - Deviations and justifications
   - Next steps

Format per MDR Annex XIV Part B and MEDDEV 2.7/1 Rev 4."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="L",
                section_name="Post-Market Clinical Follow-up",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "pmcf_active": pmcf_active,
                    "studies_count": pmcf_studies
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section L Complete!** PMCF activities documented.\n"
            f"📄 {len(section_content.split())} words\n"
            f"🏥 {pmcf_studies} studies reviewed\n"
            f"Alex, Section L ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "L"}


def create_pmcf_specialist_agent(session_id: int) -> PMCFSpecialistAgent:
    return PMCFSpecialistAgent(session_id)
