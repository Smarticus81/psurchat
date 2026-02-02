"""
Complaint Classifier Agent - Carla
Generates Section E&F: Customer Feedback & Complaints
Uses Gemini 2.5 Pro for multimodal analysis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class ComplaintClassifierAgent(BaseAgent):
    """
    Complaint Classifier Agent
    Name: Carla
    Model: Gemini 2.5 Pro
    Section: E&F - Customer Feedback & Complaints
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["complaints"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Carla's personality"""
        return """You are Carla, the Complaint Classifier specialist.

Your expertise:
- IMDRF complaint categorization
- Root cause analysis
- Complaint trending and patterns
- Customer feedback analysis

Your task for Sections E&F:
- Classify all complaints per IMDRF categories
- Document complaint rates
- Identify patterns and trends
- Assess severity distribution

Always be thorough in classification and cite IMDRF categories properly."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Section E&F: Customer Feedback & Complaints
        """
        await self.post_message(
            "📋 Carla here! Starting Sections E&F: Customer Feedback & Complaints.\n\n"
            "Retrieving complaint data...",
            message_type="normal"
        )
        
        # Step 1: Get complaint data
        complaints_data = await self.call_mcp_tool(
            server="data_access",
            tool="query_complaints",
            filters=None,
            aggregation="by_category"
        )
        
        if complaints_data.get("status") == "error":
            await self.post_message(
                f"⚠️ Failed to retrieve complaints: {complaints_data.get('error')}",
                message_type="error"
            )
            return complaints_data
        
        total_complaints = complaints_data.get("total_complaints", 0)
        by_category = complaints_data.get("aggregated_data", {})
        
        await self.post_message(
            f"✓ Complaint data retrieved:\n"
            f"- Total Complaints: {total_complaints:,}\n"
            f"- IMDRF Categories: {len(by_category)}\n"
            f"- Top Category: {max(by_category, key=by_category.get) if by_category else 'N/A'}"
        )
        
        # Step 2: Request Statler to calculate complaint rate
        await self.post_message(
            f"@Statler, please calculate the complaint rate. I have {total_complaints} complaints total.",
            to_agent="Statler"
        )
        
        # Step 3: Generate content
        prompt = f"""Generate Sections E&F (Customer Feedback & Complaints) for a PSUR.

Complaint Data:
- Total Complaints: {total_complaints:,}
- Classification by IMDRF Category: {by_category}

Requirements:
1. **Section E: Customer Feedback**
   - Overall complaint volume
   - Complaint rate calculation
   - Customer feedback summary

2. **Section F: Complaint Analysis**
   - IMDRF classification breakdown
   - Severity distribution
   - Top complaint categories
   - Identified patterns or trends

Format as professional regulatory narrative.
Use headers: 5.1 Complaint Volume, 5.2 Classification, 5.3 Severity Analysis, 5.4 Trending"""
        
        await self.post_message("🤖 Classifying complaints and generating analysis...")
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        # Step 4: Save to database
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="E&F",
                section_name="Customer Feedback & Complaints",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "total_complaints": total_complaints,
                    "categories": list(by_category.keys()),
                    "word_count": len(section_content.split())
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
            section_id_db = section.id
        
        await self.post_message(
            f"✅ **Sections E&F Complete!**\n\n"
            f"📄 {len(section_content.split())} words generated\n"
            f"📋 {total_complaints:,} complaints analyzed\n"
            f"🏷️ {len(by_category)} IMDRF categories\n\n"
            f"Alex, Sections E&F are ready for QC review.",
            message_type="normal"
        )
        
        return {
            "status": "success",
            "section_id": "E&F",
            "content_length": len(section_content),
            "database_id": section_id_db
        }


# Factory function
def create_complaint_classifier_agent(session_id: int) -> ComplaintClassifierAgent:
    """Create complaint classifier agent instance"""
    return ComplaintClassifierAgent(session_id)
