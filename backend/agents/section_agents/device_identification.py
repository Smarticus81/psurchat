"""
Device Identification Agent - Diana
Generates Section A: Device Identification
Uses GPT-5.1 for structured data extraction and UDI documentation
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class DeviceIdentificationAgent(BaseAgent):
    """
    Device Identification Agent
    Name: Diana
    Model: GPT-5.1
    Section: A - Device Identification
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["device_id"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Diana's personality"""
        return """You are Diana, the Device Identification specialist.

Your expertise:
- UDI-DI identification and documentation
- GMDN/EMDN classification
- Risk classification per MDR Annex VIII
- Device description and intended use

Your task for Section A:
- Document complete UDI-DI information
- Classify device according to regulations
- Justify PSUR obligation per MDR Article 85
- Provide clear device description

You're meticulous about regulatory accuracy and cite all classification rules properly."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Section A: Device Identification
        """
        await self.post_message(
            "👋 Diana here! Starting Section A: Device Identification.\n\n"
            "Retrieving device metadata...",
            message_type="normal"
        )
        
        # Step 1: Get device metadata via MCP
        device_data = await self.call_mcp_tool(
            server="data_access",
            tool="get_device_metadata"
        )
        
        if device_data.get("status") == "error":
            await self.post_message(
                f"⚠️ Failed to retrieve device data: {device_data.get('error')}",
                message_type="error"
            )
            return device_data
        
        await self.post_message(
            f"✓ Device data retrieved:\n"
            f"- Device: {device_data.get('device_name')}\n"
            f"- UDI-DI: {device_data.get('udi_di')}\n"
            f"- Period: {device_data.get('surveillance_months')} months"
        )
        
        # Step 2: Generate Section A content using AI
        prompt = f"""Generate Section A (Device Identification) for a PSUR.

Device Information:
- Device Name: {device_data.get('device_name')}
- UDI-DI: {device_data.get('udi_di')}
- Surveillance Period: {device_data.get('period_start')} to {device_data.get('period_end')}

Requirements:
1. Complete UDI-DI documentation
2. GMDN classification (provide code and term)
3. Risk classification per MDR Annex VIII (provide class and rule)
4. Clear intended use statement
5. Rationale for PSUR obligation per MDR Article 85

Format as professional regulatory narrative (no bullet points).
Use section headers: 1.1 Device Identity, 1.2 Classification, 1.3 PSUR Obligation"""
        
        await self.post_message("🤖 Generating Section A content...")
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        # Step 3: Save to database
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="A",
                section_name="Device Identification",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "device_name": device_data.get('device_name'),
                    "udi_di": device_data.get('udi_di'),
                    "word_count": len(section_content.split())
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
            section_id_db = section.id
        
        await self.post_message(
            f"✅ **Section A Complete!**\n\n"
            f"📄 {len(section_content.split())} words generated\n"
            f"📋 Sections covered: UDI-DI, Classification, PSUR Obligation\n\n"
            f"Alex, Section A is ready for QC review.",
            message_type="normal"
        )
        
        return {
            "status": "success",
            "section_id": "A",
            "content_length": len(section_content),
            "database_id": section_id_db
        }


# Factory function
def create_device_identification_agent(session_id: int) -> DeviceIdentificationAgent:
    """Create device identification agent instance"""
    return DeviceIdentificationAgent(session_id)
