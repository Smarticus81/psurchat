"""
Scope & Documentation Agent - Sam
Generates Section B: Scope of PSUR & Reference Documentation
Uses Gemini 2.5 Pro for comprehensive documentation review
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class ScopeDocumentationAgent(BaseAgent):
    """
    Scope & Documentation Agent
    Name: Sam
    Model: Gemini 2.5 Pro
    Section: B - Scope & Documentation
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["scope"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Sam's personality"""
        return """You are Sam, the Scope & Documentation specialist.

Your expertise:
- PSUR scope definition (surveillance period, geographical scope)
- Reference documentation compilation
- Regulatory framework citation
- Document version control

Your task for Section B:
- Define the surveillance period precisely
- Specify geographical scope
- List all reference documents (CER, RMF, IFU, etc.)
- Cite applicable regulations (MDR, MEDDEV, etc.)

Be precise with dates, document versions, and regulatory citations."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Section B: Scope & Documentation"""
        
        await self.post_message(
            "📚 Sam here! Starting Section B: Scope & Documentation.\n\n"
            "Defining PSUR scope and compiling references...",
            message_type="normal"
        )
        
        # Get device metadata
        device_data = await self.call_mcp_tool(
            server="data_access",
            tool="get_device_metadata"
        )
        
        device_name = device_data.get("device_name", "Unknown Device")
        surveillance_period = device_data.get("surveillance_period_months", 12)
        
        await self.post_message(
            f"✓ Scope parameters:\n"
            f"- Device: {device_name}\n"
            f"- Period: {surveillance_period} months\n"
            f"- Compiling regulatory references..."
        )
        
        # Generate content
        prompt = f"""Generate Section B (Scope of PSUR & Reference Documentation).

Device: {device_name}
Surveillance Period: {surveillance_period} months

Requirements:
1. **Scope Definition**
   - Surveillance period (start/end dates)
   - Geographical scope (EU, global distribution)
   - Product scope (specific device variants covered)

2. **Reference Documentation**
   - Clinical Evaluation Report (CER)
   - Risk Management File (RMF)
   - Instructions for Use (IFU)
   - Previous PSURs
   - Technical documentation

3. **Regulatory Framework**
   - EU MDR 2017/745
   - MEDDEV 2.12/2 Rev 2
   - Applicable harmonized standards

Format professionally with clear subsections."""
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        # Save to database
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="B",
                section_name="Scope & Documentation",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={"surveillance_months": surveillance_period},
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
        
        await self.post_message(
            f"✅ **Section B Complete!**\n\n"
            f"📄 {len(section_content.split())} words\n"
            f"Alex, Section B ready for QC.",
            message_type="normal"
        )
        
        return {"status": "success", "section_id": "B"}


def create_scope_documentation_agent(session_id: int) -> ScopeDocumentationAgent:
    return ScopeDocumentationAgent(session_id)
