"""
Sales Analysis Agent - Raj  
Generates Section C: Sales Volume
Uses Claude Haiku 4.5 for fast analysis
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class SalesAnalysisAgent(BaseAgent):
    """
    Sales Analysis Agent
    Name: Raj
    Model: Claude Haiku 4.5
    Section: C - Sales Volume
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["sales"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Raj's personality"""
        return """You are Raj, the Sales Analysis specialist.

Your expertise:
- Sales volume analysis and reporting
- Regional distribution analysis
- Market trends and patterns
- Comparative analysis (year-over-year, quarter-over-quarter)

Your task for Section C:
- Document total sales volumes
- Provide regional breakdown
- Analyze distribution patterns
- Identify significant market trends

Always present data clearly with proper units and breakdowns."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Section C: Sales Volume
        """
        await self.post_message(
            "📊 Raj here! Starting Section C: Sales Volume Analysis.\n\n"
            "Querying sales data...",
            message_type="normal"
        )
        
        # Step 1: Get sales data via MCP
        sales_data = await self.call_mcp_tool(
            server="data_access",
            tool="get_sales_data",
            region="Global"
        )
        
        if sales_data.get("status") == "error":
            await self.post_message(
                f"⚠️ Failed to retrieve sales data: {sales_data.get('error')}",
                message_type="error"
            )
            return sales_data
        
        total_units = sales_data.get("total_units_sold", 0)
        regional_breakdown = sales_data.get("regional_breakdown", {})
        
        await self.post_message(
            f"✓ Sales data retrieved:\n"
            f"- Total Units: {total_units:,}\n"
            f"- Regions: {len(regional_breakdown)}\n"
            f"- Top Region: {max(regional_breakdown, key=regional_breakdown.get)} ({max(regional_breakdown.values()):,} units)"
        )
        
        # Step 2: Request statistical analysis from Statler
        await self.post_message(
            "@Statler, can you help me calculate the regional distribution percentages?",
            to_agent="Statler"
        )
        
        # Step 3: Generate Section C content
        prompt = f"""Generate Section C (Sales Volume) for a PSUR.

Sales Data:
- Total Units Sold: {total_units:,}
- Regional Breakdown: {regional_breakdown}
- Surveillance Period: 12 months

Requirements:
1. Overall Sales Volume (units sold, global total)
2. Regional Distribution (breakdown by major regions)
3.Market Analysis (patterns, trends if notable)
4. Comparative Context (how this compares to previous periods if relevant)

Format as professional regulatory narrative with clear subsections.
Use section headers: 3.1 Total Sales, 3.2 Regional Distribution, 3.3 Market Analysis"""
        
        await self.post_message("🤖 Analyzing sales patterns and generating section content...")
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        # Step 4: Save to database
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="C",
                section_name="Sales Volume",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "total_units": total_units,
                    "regions": list(regional_breakdown.keys()),
                    "word_count": len(section_content.split())
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
            section_id_db = section.id
        
        await self.post_message(
            f"✅ **Section C Complete!**\n\n"
            f"📄 {len(section_content.split())} words generated\n"
            f"📊 {total_units:,} total units analyzed\n"
            f"🌍 {len(regional_breakdown)} regions covered\n\n"
            f"Alex, Section C is ready for QC review.",
            message_type="normal"
        )
        
        return {
            "status": "success",
            "section_id": "C",
            "content_length": len(section_content),
            "database_id": section_id_db
        }


# Factory function
def create_sales_analysis_agent(session_id: int) -> SalesAnalysisAgent:
    """Create sales analysis agent instance"""
    return SalesAnalysisAgent(session_id)
