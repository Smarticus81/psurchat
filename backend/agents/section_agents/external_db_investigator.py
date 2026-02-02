"""
External Database Investigator Agent - Eddie
Generates Section K: External Database Review
Uses Perplexity AI for web search and literature review
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class ExternalDBInvestigatorAgent(BaseAgent):
    """
    External Database Investigator Agent
    Name: Eddie
    Model: Perplexity Sonar
    Section: K - External Database Review
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["external_db"], session_id)
    
    def get_personality_prompt(self) -> str:
        return """You are Eddie, the External Database Investigator.

Your expertise:
- FDA MAUDE database searching
- PubMed/MEDLINE literature review
- Manufacturer field safety notices
- Regulatory authority databases (BfArM, ANSM, etc.)

Your task for Section K:
- Search MAUDE for similar devices
- Review scientific literature
- Check for relevant safety notices
- Identify external safety signals

Always provide citations and assess relevance to our device."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section K: External Database Review"""
        
        await self.post_message(
            "🌐 Eddie here! Starting Section K: External Database Review.\n\n"
            "Searching external databases and literature...",
            message_type="normal"
        )
        
        # Get device info
        device_data = await self.call_mcp_tool(
            server="data_access",
            tool="get_device_metadata"
        )
        
        device_name = device_data.get("device_name", "Unknown")
        
        # Search MAUDE
        maude_results = await self.call_mcp_tool(
            server="external_search",
            tool="search_maude_database",
            device_name=device_name,
            agent_name=self.name
        )
        
        # Search literature
        literature_results = await self.call_mcp_tool(
            server="external_search",
            tool="search_literature",
            topic=f"{device_name} safety post-market surveillance",
            keywords=["medical device", "safety", "adverse events"],
            agent_name=self.name
        )
        
        await self.post_message(
            f"✓ External search complete:\n"
            f"- MAUDE: {maude_results.get('total_results', 0)} entries\n"
            f"- Literature: {len(literature_results.get('citations', []))} citations\n"
            f"Analyzing findings..."
        )
        
        prompt = f"""Generate Section K (External Database Review).

Device: {device_name}
MAUDE Results: {maude_results}
Literature: {literature_results.get('summary', '')}

Requirements:
1. **FDA MAUDE Database**
   - Search methodology
   - Relevant events for similar devices
   - Comparison to our device experience

2. **Scientific Literature**
   - PubMed/MEDLINE search results
   - Relevant safety publications
   - Clinical performance studies

3. **Regulatory Databases**
   - FSN (Field Safety Notices) review
   - Regulatory authority communications
   - International safety alerts

4. **Analysis**
   - Relevance to our device
   - External safety signals identified
   - Implications for our PSUR

Include proper citations. Format professionally."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="K",
                section_name="External Database Review",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "maude_results": maude_results.get('total_results', 0),
                    "citations": len(literature_results.get('citations', []))
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section K Complete!** External databases reviewed.\n"
            f"📄 {len(section_content.split())} words\n"
            f"🔍 {len(literature_results.get('citations', []))} citations\n"
            f"Alex, Section K ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "K"}


def create_external_db_investigator_agent(session_id: int) -> ExternalDBInvestigatorAgent:
    return ExternalDBInvestigatorAgent(session_id)
