"""
FSCA Coordinator Agent - Frank
Generates Section H: Field Safety Corrective Actions
Uses GPT-5.1 for FSCA documentation and effectiveness
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class FSCACoordinatorAgent(BaseAgent):
    """
    FSCA Coordinator Agent
    Name: Frank
    Model: GPT-5.1
    Section: H - Field Safety Corrective Actions
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["fsca"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Frank, the FSCA Coordinator specialist.

Your expertise:
- Field Safety Corrective Actions (FSCA) per MDR
- FSCA effectiveness evaluation
- Customer notification tracking
- Regulatory authority coordination

Your task for Section H:
- Document all FSCAs in surveillance period
- Assess FSCA effectiveness
- Verify customer notification completion
- Link FSCAs to root causes

Be precise with FSCA numbers, dates, and effectiveness metrics."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section H: FSCA"""
        
        await self.post_message(
            "🔧 Frank here! Starting Section H: Field Safety Corrective Actions.\n\n"
            "Reviewing FSCA implementation...",
            message_type="normal"
        )
        
        # In production, this would query actual FSCA data
        # For now, using mock approach
        fsca_count = 0  # Would come from database
        
        await self.post_message(
            f"✓ FSCAs in period: {fsca_count}\n"
            f"Generating FSCA assessment..."
        )
        
        prompt = f"""Generate Section H (Field Safety Corrective Actions).

FSCAs Implemented: {fsca_count}

Requirements:
1. FSCA Overview
   - List of all FSCAs in surveillance period
   - FSCA reference numbers and dates
   - Type of corrective action (recall, modification, etc.)

2. FSCA Effectiveness
   - Implementation status
   - Customer notification completion rates
   - Effectiveness verification results

3. Link to Root Causes
   - Connection between FSCAs and identified issues
   - Preventive measures implemented

4. Regulatory Compliance
   - Competent authority notifications
   - Timeline compliance

Format per MDR Article 2(66) and MEDDEV 2.12/1."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="H",
                section_name="Field Safety Corrective Actions",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={"fsca_count": fsca_count},
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section H Complete!** {fsca_count} FSCAs documented.\n"
            f"Alex, Section H ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "H"}


def create_fsca_coordinator_agent(session_id: int) -> FSCACoordinatorAgent:
    return FSCACoordinatorAgent(session_id)
