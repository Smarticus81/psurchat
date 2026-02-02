"""
QC Validator Agent - Victoria
Quality Control validation for all PSUR sections
Uses GPT-5.1 with low temperature for consistent validation
"""

from typing import Dict, Any
from datetime import datetime
from backend.agents.base_agent import BaseAgent
from backend.config import AGENT_CONFIGS
from backend.database.session import get_db_context
from backend.database.models import SectionDocument


class QCValidatorAgent(BaseAgent):
    """
    QC Validator Agent
    Name: Victoria
    Model: GPT-5.1 (temperature 0.3 for consistency)
    Role: Quality Control - validates all sections before approval
    """
    
    def __init__(self, session_id: int):
        super().__init__(AGENT_CONFIGS["qc"], session_id)
    
    def get_personality_prompt(self) -> str:
        """Victoria's personality"""
        return """You are Victoria, the Quality Control Validator.

Your responsibilities:
- Validate ALL sections before they're approved
- Check template compliance (FormQAR-054)
- Verify mathematical accuracy
- Ensure regulatory language quality
- Validate internal consistency
- Check citations and references

Your QC checklist:
✓ Structure matches FormQAR-054 template
✓ All required sections present
✓ Mathematical calculations verified
✓ Professional prose (no bullet points in final narrative)
✓ Proper regulatory terminology
✓ Citations properly formatted
✓ No contradictions or inconsistencies
✓ Figures/tables properly labeled

Your style:
- Professional but firm
- Specific feedback (cite line numbers or sections)
- Clear pass/fail decisions
- Acknowledge good work
- Provide actionable corrections

If you find issues, provide SPECIFIC feedback. Don't just say "improve" - say exactly what to fix."""
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute QC validation task
        
        Task type:
        - validate_section
        """
        task_type = task.get("type")
        
        if task_type == "validate_section":
            return await self.validate_section(
                section_id=task.get("section_id"),
                author=task.get("author")
            )
        
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def validate_section(
        self,
        section_id: str,
        author: str
    ) -> Dict[str, Any]:
        """
        Perform QC validation on a PSUR section
        """
        await self.post_message(
            f"🔍 **Victoria - QC Validation Starting**\n\n"
            f"Reviewing Section {section_id} submitted by {author}...",
            message_type="system"
        )
        
        # Retrieve section from database
        with get_db_context() as db:
            section = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.section_id == section_id,
                SectionDocument.author_agent == author
            ).first()
            
            if not section:
                await self.post_message(
                    f"⚠️ Section {section_id} not found in database.",
                    message_type="error"
                )
                return {"error": "Section not found"}
            
            section_content = section.content
            section_name = section.section_name
        
        # Build QC prompt
        qc_prompt = f"""Perform QC validation on this PSUR section.

**Section:** {section_id} - {section_name}
**Author:** {author}
**Word Count:** {len(section_content.split())}

**Content:**
{section_content[:3000]}{"..." if len(section_content) > 3000 else ""}

**QC Checklist:**
1. Structure: Does it follow FormQAR-054 section requirements?
2. Completeness: Are all required elements present?
3. Language: Professional regulatory prose? No bullet points?
4. Accuracy: Are claims supported? Any obvious errors?
5. Consistency: Internal consistency? Contradictions?
6. Formatting: Proper headings, tables, figures?

**Provide:**
- Overall PASS/FAIL decision
- Specific issues found (with location/line reference if possible)
- Required corrections (be specific)
- Praise for good elements

Format as:
DECISION: [PASS/CONDITIONAL PASS/FAIL]
ISSUES FOUND: [list]
CORRECTIONS REQUIRED: [specific actions]
POSITIVE NOTES: [acknowledgments]"""
        
        # Get QC assessment from AI
        await self.post_message("🤖 Performing detailed QC review...")
        
        qc_assessment = await self.generate(
            prompt=qc_prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        # Parse decision (simple keyword extraction)
        if "DECISION: PASS" in qc_assessment and "CONDITIONAL" not in qc_assessment:
            decision = "APPROVED"
            qc_status = "passed"
        elif "CONDITIONAL PASS" in qc_assessment or "DECISION: CONDITIONAL" in qc_assessment:
            decision = "CONDITIONAL_PASS"
            qc_status = "conditional"
        else:
            decision = "REJECTED"
            qc_status = "failed"
        
        # Update section in database
        with get_db_context() as db:
            section = db.query(SectionDocument).filter(
                SectionDocument.session_id == self.session_id,
                SectionDocument.section_id == section_id
            ).first()
            
            section.qc_status = qc_status
            section.qc_feedback = qc_assessment
            section.qc_reviewed_by = self.name
            section.qc_reviewed_at = datetime.utcnow()
            
            if decision == "APPROVED":
                section.status = "approved"
            elif decision == "CONDITIONAL_PASS":
                section.status = "needs_revision"
            else:
                section.status = "rejected"
            
            db.commit()
        
        # Post results publicly
        if decision == "APPROVED":
            emoji = "✅"
            message_type = "success"
        elif decision == "CONDITIONAL_PASS":
            emoji = "⚠️"
            message_type = "warning"
        else:
            emoji = "❌"
            message_type = "error"
        
        await self.post_message(
            f"{emoji} **QC Validation Complete - Section {section_id}**\n\n"
            f"**Decision: {decision}**\n\n"
            f"{qc_assessment}\n\n"
            f"---\n"
            f"@{author}, please see feedback above.",
            message_type=message_type
        )
        
        # Notify orchestrator if approved
        if decision == "APPROVED":
            await self.post_message(
                f"@Alex, Section {section_id} is approved and ready for assembly.",
                to_agent="Alex"
            )
        
        return {
            "status": "qc_complete",
            "section_id": section_id,
            "decision": decision,
            "qc_status": qc_status
        }


# Factory function
def create_qc_validator_agent(session_id: int) -> QCValidatorAgent:
    """Create QC validator agent instance"""
    return QCValidatorAgent(session_id)
