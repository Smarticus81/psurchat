"""
Orchestrator Agent - Alex
Manages workflow, coordinates agents, and ensures PSUR generation progresses smoothly
Uses Claude Sonnet 4.5 for balanced reasoning and coordination
"""

from typing import Dict, List, Any
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import WorkflowState, SectionDocument


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - Coordinates all other agents
    Name: Alex
    Model: Claude Sonnet 4.5
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["orchestrator"], session_id)
        self.section_order = [
            ("A", "Device Identification", "device_id"),
            ("B", "Scope & Documentation", "scope"),
            ("C", "Sales Volume", "sales"),
            ("D", "Vigilance - Serious Incidents", "vigilance"),
            ("E&F", "Customer Feedback & Complaints", "complaints"),
            ("G", "Trending Analysis", "trending"),
            ("H", "FSCA & Risk Management", "fsca"),
            ("I", "CAPA Implementation", "capa"),
            ("J", "Benefit-Risk Assessment", "benefit_risk"),
            ("K", "External Database Review", "external_db"),
            ("L", "PMCF Activities", "pmcf"),
            ("M", "Conclusions & Recommendations", "synthesis"),
        ]
    
    def get_personality_prompt(self) -> str:
        """Alex's personality"""
        return """You are Alex, the Orchestrator Agent coordinating a team of 16 specialized AI agents to generate a compliant PSUR.

Your responsibilities:
- Assign tasks to appropriate agents in the correct sequence
- Monitor progress and resolve blockers
- Mediate disputes between agents
- Ensure all sections meet quality standards
- Route completed sections to Victoria (QC Agent) for validation
- Maintain professional coordination through the public forum

Your style:
- Clear, directive communication
- Acknowledge good work
- Problem-solve when agents disagree
- Keep the team focused and moving forward

You're the conductor of this regulatory symphony."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute orchestration task
        
        Tasks:
        - initiate_psur_generation
        - assign_section
        - handle_agent_question
        - route_to_qc
        """
        task_type = task.get("type")
        
        if task_type == "initiate_psur_generation":
            return await self.initiate_psur_generation()
        
        elif task_type == "assign_section":
            section_id = task.get("section_id")
            return await self.assign_section(section_id)
        
        elif task_type == "route_to_qc":
            section_id = task.get("section_id")
            author = task.get("author")
            return await self.route_to_qc(section_id, author)
        
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def initiate_psur_generation(self) -> Dict[str, Any]:
        """Begin PSUR generation process"""
        await self.post_message(
            "🚀 **PSUR Generation Session Started**\n\n"
            "Welcome team! I'm Alex, your Orchestrator. We have 13 sections to complete.\n\n"
            "**Agent Roster (17 total):**\n"
            "- Section Agents (13): Diana, Sam, Raj, Vera, Carla, Tara, Frank, Cameron, Rita, Brianna, Eddie, Clara, Marcus\n"
            "- Analytical (3): Statler, Charley, Quincy\n"
            "- QC (1): Victoria\n\n"
            "Let's begin with data validation. Quincy, please verify all uploaded files.",
            message_type="system"
        )
        
        # Update workflow state
        with get_db_context() as db:
            workflow = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()
            
            if workflow:
                workflow.current_phase = "data_validation"
                workflow.current_agent = "Quincy"
                db.commit()
        
        return {"status": "initiated", "next_agent": "Quincy"}
    
    async def assign_section(self, section_id: str) -> Dict[str, Any]:
        """Assign a section to the appropriate agent"""
        # Find section info
        section_info = next((s for s in self.section_order if s[0] == section_id), None)
        
        if not section_info:
            return {"error": f"Unknown section: {section_id}"}
        
        section_name = section_info[1]
        agent_id = section_info[2]
        agent_config = AGENT_CONFIGS.get(agent_id)
        
        if not agent_config:
            return {"error": f"Agent not found for section {section_id}"}
        
        agent_name = agent_config.name
        
        await self.post_message(
            f"📋 **Section {section_id} Assignment**\n\n"
            f"{agent_name}, you're up! Please generate **Section {section_id}: {section_name}**.\n\n"
            f"Use MCP tools as needed:\n"
            f"- `data_access` for sales/complaints data\n"
            f"- `statistical_tools` for calculations\n"
            f"- `visualization` for charts\n"
            f"- `collaboration` to coordinate with other agents\n\n"
            f"When complete, submit to me for QC routing.",
            to_agent=agent_name,
            message_type="normal"
        )
        
        # Update workflow
        with get_db_context() as db:
            workflow = db.query(WorkflowState).filter(
                WorkflowState.session_id == self.session_id
            ).first()
            
            if workflow:
                workflow.current_section = section_id
                workflow.current_agent = agent_name
                workflow.current_phase = "section_generation"
                
                # Update section status
                section_status = workflow.section_status or {}
                section_status[section_id] = "in_progress"
                workflow.section_status = section_status
                
                # Update agent status
                agent_status = workflow.agent_status or {}
                agent_status[agent_name] = "working"
                workflow.agent_status = agent_status
                
                db.commit()
        
        return {
            "status": "assigned",
            "section": section_id,
            "agent": agent_name
        }
    
    async def route_to_qc(self, section_id: str, author: str) -> Dict[str, Any]:
        """Route completed section to QC validator"""
        await self.post_message(
            f"✅ Section {section_id} received from {author}.\n\n"
            f"Victoria, please perform QC validation on Section {section_id}.",
            message_type="system"
        )
        
        # Update section status
        with get_db_context() as db:
            section = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.section_id == section_id
            ).first()
            
            if section:
                section.status = "in_review"
                section.qc_status = "pending"
                db.commit()
        
        return {"status": "routed_to_qc", "section": section_id}


# Factory function
def create_orchestrator(session_id: int) -> OrchestratorAgent:
    """Create orchestrator agent instance"""
    return OrchestratorAgent(session_id)
