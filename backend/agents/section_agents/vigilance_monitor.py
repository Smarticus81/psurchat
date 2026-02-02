"""
Vigilance Monitor Agent - Vera
Generates Section D: Vigilance - Serious Incidents
Uses GPT-5.1 for regulatory incident analysis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class VigilanceMonitorAgent(BaseAgent):
    """
    Vigilance Monitor Agent
    Name: Vera
    Model: GPT-5.1
    Section: D - Vigilance (Serious Incidents)
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["vigilance"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Vera, the Vigilance Monitor specialist.

Your expertise:
- Serious incident reporting (MDR Article 87)
- Vigilance classification per MEDDEV 2.12/1
- Root cause analysis
- Corrective action tracking

Your task for Section D:
- Document all serious incidents
- Classify by severity and type
- Assess root causes
- Verify regulatory reporting compliance

Be thorough and regulatory-compliant. Safety first."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section D: Vigilance"""
        
        await self.post_message(
            "⚠️ Vera here! Starting Section D: Vigilance - Serious Incidents.\n\n"
            "Querying serious incident data...",
            message_type="normal"
        )
        
        # Query serious incidents from complaints
        incidents = await self.call_mcp_tool(
            server="data_access",
            tool="query_complaints",
            filters={"severity": "serious"},
            aggregation="by_type"
        )
        
        total_incidents = incidents.get("total_complaints", 0)
        
        await self.post_message(
            f"✓ Serious incidents: {total_incidents}\n"
            f"Performing vigilance analysis..."
        )
        
        prompt = f"""Generate Section D (Vigilance - Serious Incidents).

Serious Incidents: {total_incidents}
Data: {incidents.get('aggregated_data', {})}

Requirements:
1. Overview of vigilance system compliance
2. Serious incident summary (count, types, outcomes)
3. Regulatory reporting status (MDR Article 87)
4. Root cause analysis summary
5. Trending of incident types

Format per MEDDEV 2.12/2 Rev 2 guidelines."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="D",
                section_name="Vigilance - Serious Incidents",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={"serious_incidents": total_incidents},
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section D Complete!** {total_incidents} incidents analyzed.\n"
            f"Alex, Section D ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "D"}


def create_vigilance_monitor_agent(session_id: int) -> VigilanceMonitorAgent:
    return VigilanceMonitorAgent(session_id)
