"""
Statistical Calculator Agent - Statler
Performs all mathematical calculations with verification
Uses GPT-5.1 + Wolfram Alpha for precision
"""

from typing import Dict, Any, List
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS


class StatisticalCalculatorAgent(BaseAgent):
    """
    Statistical Calculator Agent
    Name: Statler
    Model: GPT-5.1 + Wolfram Alpha
    Role: Analytical support - mathematical calculations
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["statistical"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Statler's personality"""
        return """You are Statler, the Statistical Calculator agent.

Your expertise:
- Complaint rate calculations
- UCL (Upper Control Limit) computations
- Statistical process control
- CAPA effectiveness metrics
- Trend analysis mathematics

Your rules:
- ALWAYS show your work step-by-step
- NEVER round prematurely - maintain 6 decimal places in intermediate steps
- Verify calculations using MCP statistical tools
- Present final results in regulatory-appropriate precision (usually 2 decimal places for percentages)
- Call out any mathematical errors you detect from other agents

You're the mathematical conscience of this team. If someone's numbers don't add up, speak up!"""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute statistical calculation task
        
        Task types:
        - calculate_rate
        - calculate_ucl
        - verify_calculation
        """
        task_type = task.get("type")
        
        if task_type == "calculate_rate":
            return await self.calculate_rate(
                numerator=task.get("numerator"),
                denominator=task.get("denominator"),
                description=task.get("description", "Rate")
            )
        
        elif task_type == "calculate_ucl":
            return await self.calculate_ucl(
                data_points=task.get("data_points"),
                description=task.get("description", "Control Limit")
            )
        
        elif task_type == "verify_calculation":
            return await self.verify_calculation(
                claimed_result=task.get("claimed_result"),
                calculation_data=task.get("calculation_data")
            )
        
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def calculate_rate(
        self,
        numerator: int,
        denominator: int,
        description: str = "Rate"
    ) -> Dict[str, Any]:
        """Calculate a rate with full verification"""
        
        await self.post_message(
            f"📊 **Statler here - Calculating {description}**\n\n"
            f"Inputs received:\n"
            f"- Numerator: {numerator:,}\n"
            f"- Denominator: {denominator:,}\n\n"
            f"Using MCP statistical tools for verification..."
        )
        
        # Call MCP statistical tools
        result = await self.call_mcp_tool(
            server="statistical_tools",
            tool="calculate_complaint_rate",
            numerator=numerator,
            denominator=denominator,
            show_work=True,
            agent_name=self.name
        )
        
        if result.get("status") == "error":
            await self.post_message(
                f"⚠️ **Calculation Error:**\n{result.get('error')}",
                message_type="error"
            )
            return result
        
        # Present results publicly
        work_shown = "\n".join(result.get("work_shown", []))
        
        await self.post_message(
            f"✅ **{description} Calculation Complete**\n\n"
            f"```\n{work_shown}\n```\n\n"
            f"**Final Result: {result['formatted']}**\n\n"
            f"✓ Calculation verified and logged to audit trail.",
            message_type="normal"
        )
        
        return result
    
    async def calculate_ucl(
        self,
        data_points: List[float],
        description: str = "Upper Control Limit"
    ) -> Dict[str, Any]:
        """Calculate UCL for control chart"""
        
        await self.post_message(
            f"📈 **Statler - Calculating {description}**\n\n"
            f"Analyzing {len(data_points)} data points for statistical process control..."
        )
        
        result = await self.call_mcp_tool(
            server="statistical_tools",
            tool="calculate_ucl",
            data_points=data_points,
            confidence_level=0.95,
            agent_name=self.name
        )
        
        if result.get("status") == "error":
            await self.post_message(
                f"⚠️ **Error:** {result.get('error')}",
                message_type="error"
            )
            return result
        
        # Present results
        work_shown = "\n".join(result.get("work_shown", []))
        
        await self.post_message(
            f"✅ **UCL Calculation Complete**\n\n"
            f"```\n{work_shown}\n```\n\n"
            f"**Control Limits:**\n"
            f"- UCL: {result['ucl']}\n"
            f"- Mean: {result['mean']}\n"
            f"- LCL: {result['lcl']}\n\n"
            f"✓ Statistical verification complete."
        )
        
        return result
    
    async def verify_calculation(
        self,
        claimed_result: float,
        calculation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify another agent's calculation"""
        
        await self.post_message(
            f"🔍 **Statler - Verifying Calculation**\n\n"
            f"Claimed result: {claimed_result}\n"
            f"Recalculating to verify..."
        )
        
        # Recalculate based on type
        if "numerator" in calculation_data and "denominator" in calculation_data:
            result = await self.call_mcp_tool(
                server="statistical_tools",
                tool="calculate_complaint_rate",
                numerator=calculation_data["numerator"],
                denominator=calculation_data["denominator"],
                show_work=True,
                agent_name=self.name
            )
            
            verified_result = result.get("percentage")
            
            # Compare with tolerance
            difference = abs(verified_result - claimed_result)
            tolerance = 0.01  # 0.01% tolerance
            
            if difference <= tolerance:
                await self.post_message(
                    f"✅ **Verification: PASS**\n\n"
                    f"Claimed: {claimed_result:.2f}%\n"
                    f"Verified: {verified_result:.2f}%\n"
                    f"Difference: {difference:.4f}% (within tolerance)\n\n"
                    f"Calculation is correct! ✓"
                )
                return {"verified": True, "correct": True}
            else:
                await self.post_message(
                    f"⚠️ **Verification: FAIL**\n\n"
                    f"Claimed: {claimed_result:.2f}%\n"
                    f"Verified: {verified_result:.2f}%\n"
                    f"Difference: {difference:.4f}% (exceeds tolerance of {tolerance}%)\n\n"
                    f"**The calculation appears to be incorrect.** Please revise.",
                    message_type="warning"
                )
                return {
                    "verified": True,
                    "correct": False,
                    "claimed": claimed_result,
                    "actual": verified_result
                }
        
        return {"error": "Don't know how to verify this calculation type"}


# Factory function
def create_statistical_calculator_agent(session_id: int) -> StatisticalCalculatorAgent:
    """Create statistical calculator agent instance"""
    return StatisticalCalculatorAgent(session_id)
