"""
Trend Detective Agent - Tara
Generates Section G: Trending Analysis
Uses Claude Opus 4.5 for advanced pattern detection
"""

from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument
from datetime import datetime


class TrendDetectiveAgent(BaseAgent):
    """
    Trend Detective Agent
    Name: Tara
    Model: Claude Opus 4.5
    Section: G - Trending Analysis
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["trending"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Tara's personality"""
        return """You are Tara, the Trend Detective.

Your expertise:
- Statistical trend analysis
- Pattern recognition in complaint data
- Signal vs noise detection
- Predictive analysis for emerging issues

Your task for Section G:
- Analyze complaint trends over time
- Identify emerging  patterns
- Assess statistical significance
- Provide early warning signals

Be analytical but cautious - distinguish between statistical noise and meaningful trends."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Section G: Trending Analysis
        """
        await self.post_message(
            "🔍 Tara here! Starting Section G: Trending Analysis.\n\n"
            "Gathering temporal complaint data...",
            message_type="normal"
        )
        
        # Step 1: Get time-series complaint data
        complaints_data = await self.call_mcp_tool(
            server="data_access",
            tool="query_complaints",
            filters={"group_by": "month"},
            aggregation="time_series"
        )
        
        if complaints_data.get("status") == "error":
            await self.post_message(
                f"⚠️ Failed to retrieve trending data: {complaints_data.get('error')}",
                message_type="error"
            )
            return complaints_data
        
        monthly_data = complaints_data.get("aggregated_data", {})
        
        await self.post_message(
            f"✓ Monthly data retrieved:\n"
            f"- Months analyzed: {len(monthly_data)}\n"
            f"- Identifying patterns..."
        )
        
        # Step 2: Request statistical trend analysis from Statler
        await self.post_message(
            f"@Statler, I need a trend analysis on these monthly complaint rates. "
            f"Can you calculate if there's a statistically significant trend?",
            to_agent="Statler"
        )
        
        # Call statistical trend analysis
        trend_result = await self.call_mcp_tool(
            server="statistical_tools",
            tool="analyze_trend",
            time_series_data=list(monthly_data.values()),
            agent_name=self.name
        )
        
        trend_direction = trend_result.get("trend_direction", "stable")
        significance = trend_result.get("is_significant", False)
        
        await self.post_message(
            f"📊 Statistical Analysis Complete:\n"
            f"- Trend Direction: {trend_direction}\n"
            f"- Statistically Significant: {'Yes' if significance else 'No'}\n"
            f"- Slope: {trend_result.get('slope', 0):.4f}"
        )
        
        # Step 3: Request Charley to create trend visualization
        await self.post_message(
            "@Charley, please create a trend chart for the monthly complaint data.",
            to_agent="Charley"
        )
        
        # Step 4: Generate Section G content
        prompt = f"""Generate Section G (Trending Analysis) for a PSUR.

Trending Data:
- Monthly Complaint Data: {monthly_data}
- Trend Analysis: {trend_result}
- Trend Direction: {trend_direction}
- Statistical Significance: {significance}

Requirements:
1. **Overview**: Summary of trending methodology
2. **Temporal Analysis**: Month-by-month complaint trends
3. **Statistical Assessment**: Trend direction and significance
4. **Pattern Identification**: Any emerging issues or improvements
5. **Conclusions**: Assessment of whether trends warrant action

Format as professional regulatory narrative.
Use headers: 7.1 Methodology, 7.2 Temporal Trends, 7.3 Statistical Analysis, 7.4 Findings"""
        
        await self.post_message("🤖 Analyzing patterns and generating trending report...")
        
        section_content = await self.generate(
            prompt=prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        # Step 5: Save to database
        with get_db_context() as db:
            section = SectionDocument(
                session_id=self.session_id,
                section_id="G",
                section_name="Trending Analysis",
                author_agent=self.name,
                content=section_content,
                status="draft",
                metadata={
                    "trend_direction": trend_direction,
                    "is_significant": significance,
                    "months_analyzed": len(monthly_data),
                    "word_count": len(section_content.split())
                },
                created_at=datetime.utcnow()
            )
            db.add(section)
            db.commit()
            section_id_db = section.id
        
        await self.post_message(
            f"✅ **Section G Complete!**\n\n"
            f"📄 {len(section_content.split())} words generated\n"
            f"📈 {len(monthly_data)} months analyzed\n"
            f"🔍 Trend: {trend_direction.upper()}\n"
            f"⚠️ Significant: {'YES' if significance else 'No'}\n\n"
            f"Alex, Section G is ready for QC review.",
            message_type="normal"
        )
        
        return {
            "status": "success",
            "section_id": "G",
            "content_length": len(section_content),
            "database_id": section_id_db,
            "trend_direction": trend_direction,
            "significant": significance
        }


# Factory function
def create_trend_detective_agent(session_id: int) -> TrendDetectiveAgent:
    """Create trend detective agent instance"""
    return TrendDetectiveAgent(session_id)
