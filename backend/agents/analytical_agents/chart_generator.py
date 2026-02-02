"""
Chart Generator Agent - Charley
Creates visualizations for PSUR sections
Uses GPT-5.1 + Matplotlib via MCP Visualization Server
"""

from typing import Dict, Any, List
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS


class ChartGeneratorAgent(BaseAgent):
    """
    Chart Generator Agent
    Name: Charley
    Model: GPT-5.1 + Matplotlib
    Role: Analytical support - chart generation
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["charts"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Charley's personality"""
        return """You are Charley, the Chart Generator agent.

Your expertise:
- Data visualization best practices
- Statistical charts (line, bar, control charts)
- Regulatory-compliant figure formatting
- Clear, professional chart design

Your rules:
- Always label axes clearly
- Include units and legends
- Use professional color schemes
- Ensure chart titles are descriptive
- Follow regulatory documentation standards

You work closely with Statler (calculations) and other agents to visualize their data."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        ExecuteChart generation task
        
        Task types:
        - create_trend_chart
        - create_distribution_chart
        - create_control_chart
        """
        task_type = task.get("type")
        
        if task_type == "create_trend_chart":
            return await self.create_trend_chart(
                title=task.get("title"),
                data=task.get("data"),
                save_path=task.get("save_path")
            )
        
        elif task_type == "create_control_chart":
            return await self.create_control_chart(
                title=task.get("title"),
                data_points=task.get("data_points"),
                ucl=task.get("ucl"),
                lcl=task.get("lcl"),
                mean=task.get("mean"),
                save_path=task.get("save_path")
            )
        
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def create_trend_chart(
        self,
        title: str,
        data: List[Dict[str, Any]],
        save_path: str
    ) -> Dict[str, Any]:
        """Create a trend line chart"""
        
        await self.post_message(
            f"📊 **Charley - Creating Trend Chart**\n\n"
            f"Title: {title}\n"
            f"Data points: {len(data)}\n\n"
            f"Generating visualization..."
        )
        
        # Call MCP visualization server
        result = await self.call_mcp_tool(
            server="visualization",
            tool="create_line_chart",
            title=title,
            data=data,
            save_path=save_path,
            agent_name=self.name
        )
        
        if result.get("status") == "error":
            await self.post_message(
                f"⚠️ **Chart generation failed:**\n{result.get('error')}",
                message_type="error"
            )
            return result
        
        await self.post_message(
            f"✅ **Trend Chart Created!**\n\n"
            f"📁 Saved to: {save_path}\n"
            f"📊 {len(data)} data points plotted\n\n"
            f"Chart ready for inclusion in PSUR.",
            message_type="normal"
        )
        
        return result
    
    async def create_control_chart(
        self,
        title: str,
        data_points: List[float],
        ucl: float,
        lcl: float,
        mean: float,
        save_path: str
    ) -> Dict[str, Any]:
        """Create a statistical process control chart"""
        
        await self.post_message(
            f"📈 **Charley - Creating Control Chart**\n\n"
            f"Title: {title}\n"
            f"UCL: {ucl:.4f}\n"
            f"Mean: {mean:.4f}\n"
            f"LCL: {lcl:.4f}\n\n"
            f"Generating SPC chart..."
        )
        
        # Call MCP visualization server
        result = await self.call_mcp_tool(
            server="visualization",
            tool="create_control_chart",
            title=title,
            data_points=data_points,
            ucl=ucl,
            lcl=lcl,
            mean=mean,
            save_path=save_path,
            agent_name=self.name
        )
        
        if result.get("status") == "error":
            await self.post_message(
                f"⚠️ **Chart generation failed:**\n{result.get('error')}",
                message_type="error"
            )
            return result
        
        out_of_control = result.get("out_of_control_points", [])
        
        if out_of_control:
            await self.post_message(
                f"⚠️ **Alert:** {len(out_of_control)} out-of-control points detected at samples: {out_of_control}",
                message_type="warning"
            )
        
        await self.post_message(
            f"✅ **Control Chart Created!**\n\n"
            f"📁 Saved to: {save_path}\n"
            f"📊 {len(data_points)} data points\n"
            f"🚨 Out-of-control points: {len(out_of_control)}\n\n"
            f"Chart ready for trending section.",
            message_type="normal"
        )
        
        return result


# Factory function
def create_chart_generator_agent(session_id: int) -> ChartGeneratorAgent:
    """Create chart generator agent instance"""
    return ChartGeneratorAgent(session_id)
