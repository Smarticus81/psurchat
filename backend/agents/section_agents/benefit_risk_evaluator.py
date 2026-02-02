"""
Benefit-Risk Evaluator Agent - Brianna
Generates Section J: Benefit-Risk Assessment
Uses GPT-5.1 for comprehensive benefit-risk evaluation
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class BenefitRiskEvaluatorAgent(BaseAgent):
    """
    Benefit-Risk Evaluator Agent
    Name: Brianna
    Model: GPT-5.1
    Section: J - Benefit-Risk Assessment
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["benefit_risk"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Brianna, the Benefit-Risk Evaluator.

Your expertise:
- Benefit-risk assessment per MDR Annex I
- Clinical benefit evaluation
- Risk acceptability in context of benefits
- Benefit-risk balance determination

Your task for Section J:
- Integrate risk assessment (from Rita)
- Evaluate clinical benefits
- Assess benefit-risk balance
- Determine continued acceptability

Be evidence-based and reference Clinical Evaluation Report (CER)."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section J: Benefit-Risk Assessment"""
        
        await self.post_message(
            "⚖️ Brianna here! Starting Section J: Benefit-Risk Assessment.\n\n"
            "Integrating Rita's risk analysis with clinical benefits...",
            message_type="normal"
        )
        
        # Would receive Rita's risk content in production
        await self.post_message(
            "@Rita, please share your risk assessment. I'll integrate it with the benefit analysis."
        )
        
        prompt = f"""Generate Section J (Benefit-Risk Assessment).

Requirements:
1. **Clinical Benefits**
   - Device intended use and clinical benefits
   - Clinical evidence summary from CER
   - Post-market clinical benefit data

2. **Risk Assessment** (integrate with Rita's analysis)
   - Summary of identified risks
   - Residual risk levels
   - Risk control effectiveness

3. **Benefit-Risk Balance**
   - Comparative analysis of benefits vs risks
   - Benefit-risk ratio assessment
   - Acceptability determination per MDR Annex I

4. **Conclusions**
   - Overall benefit-risk balance
   - Changes since previous PSUR
   - Continued device acceptability

Format per MEDDEV 2.7/1 Rev 4 and MDR requirements."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="J",
                section_name="Benefit-Risk Assessment",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={"assessment_type": "benefit-risk"},
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section J Complete!** Benefit-risk balance assessed.\n"
            f"📄 {len(section_content.split())} words\n"
            f"Alex, Section J ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "J"}


def create_benefit_risk_evaluator_agent(session_id: int) -> BenefitRiskEvaluatorAgent:
    return BenefitRiskEvaluatorAgent(session_id)
