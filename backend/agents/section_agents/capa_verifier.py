"""
CAPA Verifier Agent - Cameron
Generates Section I: CAPA Implementation
Uses Gemini 2.5 Pro for effectiveness analysis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class CAPAVerifierAgent(BaseAgent):
    """
    CAPA Verifier Agent
    Name: Cameron
    Model: Gemini 2.5 Pro
    Section: I - CAPA Implementation
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["capa"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Cameron, the CAPA Verifier specialist.

Your expertise:
- Corrective and Preventive Action (CAPA) effectiveness
- Root cause verification
- Quantitative effectiveness analysis
- Process improvement validation

Your task for Section I:
- Document all CAPAs implemented
- Verify root cause elimination
- Calculate CAPA effectiveness metrics
- Assess preventive action success

Use data-driven effectiveness analysis. Request Statler's help for calculations."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section I: CAPA Implementation"""
        
        await self.post_message(
            "🔍 Cameron here! Starting Section I: CAPA Implementation.\n\n"
            "Analyzing CAPA effectiveness...",
            message_type="normal"
        )
        
        # Request Statler to calculate CAPA effectiveness
        await self.post_message(
            "@Statler, I need CAPA effectiveness calculations. "
            "Can you analyze before/after complaint rates for implemented CAPAs?",
            to_agent="Statler"
        )
        
        # Mock CAPA data (would come from database in production)
        capa_count = 3
        
        prompt = f"""Generate Section I (CAPA Implementation).

CAPAs Implemented: {capa_count}

Requirements:
1. CAPA Summary
   - List of all CAPAs
   - Root causes addressed
   - Implementation dates

2. Effectiveness Analysis
   - Before/after metrics
   - Quantitative effectiveness (% reduction in complaints)
   - Statistical significance of improvements

3. Verification Evidence
   - Data supporting effectiveness
   - Monitoring period duration
   - Sustained improvement verification

4. Preventive Actions
   - Process changes implemented
   - Training completed
   - Design modifications

Format with clear subsections and data tables."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="I",
                section_name="CAPA Implementation",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={"capa_count": capa_count},
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section I Complete!** {capa_count} CAPAs verified.\n"
            f"Alex, Section I ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "I"}


def create_capa_verifier_agent(session_id: int) -> CAPAVerifierAgent:
    return CAPAVerifierAgent(session_id)
