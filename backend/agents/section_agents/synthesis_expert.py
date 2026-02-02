"""
Synthesis Expert Agent - Marcus
Generates Section M: Conclusions & Recommendations
Uses Claude Opus 4.5 for comprehensive synthesis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class SynthesisExpertAgent(BaseAgent):
    """
    Synthesis Expert Agent
    Name: Marcus
    Model: Claude Opus 4.5
    Section: M - Conclusions & Recommendations
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["synthesis"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Marcus, the Synthesis Expert.

Your expertise:
- PSUR synthesis and integration
- Overall safety assessment
- Strategic recommendations
- Regulatory decision-making support

Your task for Section M:
- Integrate findings from all sections (A-L)
- Provide overall safety conclusions
- Make evidence-based recommendations
- Determine if device profile changed

This is the most critical section - synthesize everything coherently."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section M: Conclusions & Recommendations"""
        
        await self.post_message(
            "📝 Marcus here! Starting Section M: Conclusions & Recommendations.\n\n"
            "This is the culmination of all our work. Reviewing all sections...",
            message_type="normal"
        )
        
        # Get all completed sections from database
        with get_db_context() as db:
            sections = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.status.in_(["approved", "draft"])
            ).all()
            
            section_summary = {}
            for sec in sections:
                section_summary[sec.section_id] = {
                    "name": sec.section_name,
                    "author": sec.author_agent,
                    "status": sec.status,
                    "key_data": sec.metadata
                }
        
        await self.post_message(
            f"✓ Reviewed {len(section_summary)} sections from the team:\n" +
            "\n".join([f"- Section {k}: {v['name']} (by {v['author']})" 
                      for k, v in section_summary.items()])
        )
        
        await self.post_message(
            "🤝 Thank you to the entire team! @Alex, @Diana, @Sam, @Raj, @Vera, "
            "@Carla, @Tara, @Frank, @Cameron, @Rita, @Brianna, @Eddie, @Clara, "
            "@Statler, @Charley, @Quincy, and @Victoria for your excellent work.\n\n"
            "Now synthesizing our collective findings..."
        )
        
        prompt = f"""Generate Section M (Conclusions & Recommendations) - the final PSUR section.

Sections Completed: {list(section_summary.keys())}
Section Data: {section_summary}

Requirements:
1. **Overall Safety Assessment**
   - Summary of surveillance period findings
   - Key safety metrics and trends
   - Significant events or changes
   - Comparison to previous periods

2. **Benefit-Risk Conclusion**
   - Overall benefit-risk balance
   - Changes to device safety profile
   - Continued acceptability determination

3. **Compliance Summary**
   - Vigilance obligations met
   - FSCA completeness
   - PMCF compliance
   - Regulatory requirements fulfilled

4. **Recommendations**
   - Risk Management File updates needed
   - CER updates required
   - IFU or labeling changes
   - Additional PMCF activities
   - Any product modifications recommended

5. **Overall Conclusion**
   - Final determination: device remains safe and performs as intended
   - Any reservations or concerns
   - Regulatory authority considerations

Format as a cohesive, professional executive summary-style section.
This section will be read by competent authorities - be precise and evidence-based."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="M",
                section_name="Conclusions & Recommendations",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "sections_synthesized": len(section_summary),
                    "synthesis_complete": True
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section M Complete!**\n\n"
            f"📄 {len(section_content.split())} words\n"
            f"📊 Synthesized {len(section_summary)} sections\n"
            f"🎯 **PSUR DRAFT COMPLETE!**\n\n"
            f"@Alex, Section M ready for final QC. "
            f"Once approved, we can proceed to document assembly!",
            message_type="success"
        )
        
        return {
            "status": "success",
            "section_id": "M",
            "sections_synthesized": len(section_summary),
            "psur_complete": True
        }


def create_synthesis_expert_agent(session_id: int) -> SynthesisExpertAgent:
    return SynthesisExpertAgent(session_id)
