"""
Risk Specialist Agent - Rita
Generates Risk Assessment portion of Section J
Uses Claude Sonnet 4.5 for comprehensive risk analysis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class RiskSpecialistAgent(BaseAgent):
    """
    Risk Specialist Agent
    Name: Rita
    Model: Claude Sonnet 4.5
    Section: J (Risk Assessment portion)
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["risk"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Rita, the Risk Specialist.

Your expertise:
- ISO 14971 risk management
- Post-market risk assessment
- Residual risk evaluation
- Risk-benefit balance analysis

Your task for Section J (Risk portion):
- Review Risk Management File (RMF)
- Assess new risks identified in surveillance period
- Evaluate residual risk acceptability
- Document risk control effectiveness

Be thorough with risk classifications and ISO 14971 compliance."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate risk assessment content"""
        
        await self.post_message(
            "⚡ Rita here! Performing risk assessment analysis...\n\n"
            "Reviewing RMF and post-market data...",
            message_type="normal"
        )
        
        prompt = f"""Generate Risk Assessment content for Section J.

Requirements:
1. **Risk Management File Review**
   - RMF version and review status
   - Compliance with ISO 14971:2019

2. **Post-Market Risk Assessment**
   - New risks identified during surveillance
   - Changes to existing risk estimates
   - Risk acceptability evaluation

3. **Risk Control Measures**
   - Effectiveness of implemented controls
   - Residual risk levels
   - Need for additional risk controls

4. **Risk Trending**
   - Changes in risk profile over time
   - Emerging risk patterns

Format per ISO 14971 and MDR Annex XIV."""
        
        risk_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        await self.post_message(
            f"✅ Risk assessment complete! Passing to Brianna for benefit-risk integration.",
            to_agent="Brianna"
        )
        
        return {
            "status": "success",
            "section_id": "J_risk",
            "content": risk_content
        }


def create_risk_specialist_agent(session_id: int) -> RiskSpecialistAgent:
    return RiskSpecialistAgent(session_id)
