"""
MCP Collaboration Server
Manages agent-to-agent communication and collaboration
Broadcasts messages via WebSocket and maintains chat history
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from mcp.server import Server
from backend.database.session import get_db_context
from backend.database.models import ChatMessage, WorkflowState, SectionDocument


class CollaborationServer:
    """MCP Server for agent collaboration and messaging"""
    
    def __init__(self):
        self.server = Server("collaboration")
        self.websocket_clients = []  # Will hold WebSocket connections
        self.register_tools()
    
    def register_tools(self):
        """Register all collaboration tools"""
        
        @self.server.tool()
        async def post_message(
            session_id: int,
            from_agent: str,
            message: str,
            to_agent: str = "all",
            message_type: str = "normal",
            visibility: str = "public",
            metadata: Optional[Dict] = None
        ) -> Dict[str, Any]:
            """
            Post a message to the discussion forum
            
            Args:
                session_id: PSUR session ID
                from_agent: Sending agent name
                message: Message content
                to_agent: Target agent (default: "all" for broadcast)
                message_type: Type (normal, system, error, warning, success)
                visibility: Visibility (public, private)
                metadata: Optional metadata (tool calls, data, etc.)
            
            Returns:
                Dict with message ID and timestamp
            """
            # Save to database
            with get_db_context() as db:
                chat_msg = ChatMessage(
                    session_id=session_id,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    message=message,
                    message_type=message_type,
                    visibility=visibility,
                    metadata=metadata,
                    timestamp=datetime.utcnow()
                )
                db.add(chat_msg)
                db.commit()
                message_id = chat_msg.id
                timestamp = chat_msg.timestamp
            
            # Broadcast to WebSocket clients (placeholder - will implement in API layer)
            await self._broadcast_to_websockets({
                "type": "chat_message",
                "session_id": session_id,
                "message_id": message_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message": message,
                "message_type": message_type,
                "timestamp": timestamp.isoformat()
            })
            
            return {
                "status": "success",
                "message_id": message_id,
                "timestamp": timestamp.isoformat(),
                "broadcast": to_agent == "all"
            }
        
        @self.server.tool()
        async def request_peer_review(
            session_id: int,
            from_agent: str,
            reviewer_agent: str,
            content_type: str,
            content_preview: str,
            full_content_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Request another agent to review content
            
            Args:
                session_id: PSUR session ID
                from_agent: Requesting agent name
                reviewer_agent: Name of reviewing agent
                content_type: Type of content (section, calculation, chart, etc.)
                content_preview: Preview/summary of content (max 500 chars)
                full_content_id: Optional database ID for full content
            
            Returns:
                Dict with request ID and status
            """
            # Post review request message
            message = (
                f"📋 **Peer Review Request**\n\n"
                f"@{reviewer_agent}, {from_agent} is requesting your review:\n\n"
                f"**Content Type:** {content_type}\n"
                f"**Preview:**\n{content_preview[:500]}\n\n"
                f"Please provide your feedback."
            )
            
            result = await post_message(
                session_id=session_id,
                from_agent=from_agent,
                message=message,
                to_agent=reviewer_agent,
                message_type="normal",
                metadata={
                    "request_type": "peer_review",
                    "content_type": content_type,
                    "full_content_id": full_content_id
                }
            )
            
            return {
                "status": "review_requested",
                "request_message_id": result["message_id"],
                "reviewer": reviewer_agent
            }
        
        @self.server.tool()
        async def get_workflow_state(
            session_id: int
        ) -> Dict[str, Any]:
            """
            Get current workflow state
            
            Args:
                session_id: PSUR session ID
            
            Returns:
                Dict with current phase, agent, section status, etc.
            """
            with get_db_context() as db:
                workflow = db.query(WorkflowState).filter(
                    WorkflowState.session_id == session_id
                ).first()
                
                if not workflow:
                    return {
                        "error": "Workflow state not found",
                        "status": "error"
                    }
                
                return {
                    "status": "success",
                    "current_phase": workflow.current_phase,
                    "current_agent": workflow.current_agent,
                    "current_section": workflow.current_section,
                    "paused": workflow.paused,
                    "paused_reason": workflow.paused_reason,
                    "section_status": workflow.section_status or {},
                    "agent_status": workflow.agent_status or {},
                    "updated_at": workflow.updated_at.isoformat()
                }
        
        @self.server.tool()
        async def submit_for_qc(
            session_id: int,
            section_id: str,
            author_agent: str
        ) -> Dict[str, Any]:
            """
            Submit a section for QC validation
            
            Args:
                session_id: PSUR session ID
                section_id: Section identifier (A, B, C, etc.)
                author_agent: Name of authoring agent
            
            Returns:
                Dict with submission status
            """
            # Update section status
            with get_db_context() as db:
                section = db.query(SectionDocument).filter(
                    SectionDocument.session_id == session_id,
                    SectionDocument.section_id == section_id,
                    SectionDocument.author_agent == author_agent
                ).first()
                
                if not section:
                    return {
                        "error": f"Section {section_id} not found",
                        "status": "error"
                    }
                
                # Update status
                section.status = "in_review"
                section.qc_status = "pending"
                db.commit()
            
            # Post notification
            message = (
                f"✅ **Section {section_id} Submitted for QC**\n\n"
                f"{author_agent} has completed Section {section_id}: {section.section_name}\n"
                f"Word count: {len(section.content.split())}\n\n"
                f"@Victoria, please perform QC validation."
            )
            
            await post_message(
                session_id=session_id,
                from_agent=author_agent,
                message=message,
                to_agent="Victoria",
                message_type="system",
                metadata={
                    "action": "qc_submission",
                    "section_id": section_id
                }
            )
            
            return {
                "status": "submitted_for_qc",
                "section_id": section_id,
                "qc_agent": "Victoria"
            }
        
        @self.server.tool()
        async def get_chat_history(
            session_id: int,
            limit: int = 100,
            offset: int = 0,
            agent_filter: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Retrieve chat message history
            
            Args:
                session_id: PSUR session ID
                limit: Maximum messages to return
                offset: Pagination offset
                agent_filter: Optional filter by agent name
            
            Returns:
                Dict with messages list and metadata
            """
            with get_db_context() as db:
                query = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                )
                
                if agent_filter:
                    query = query.filter(
                        (ChatMessage.from_agent == agent_filter) |
                        (ChatMessage.to_agent == agent_filter) |
                        (ChatMessage.to_agent == "all")
                    )
                
                total_count = query.count()
                
                messages = query.order_by(
                    ChatMessage.timestamp.asc()
                ).offset(offset).limit(limit).all()
                
                return {
                    "status": "success",
                    "total_messages": total_count,
                    "returned": len(messages),
                    "offset": offset,
                    "messages": [
                        {
                            "id": msg.id,
                            "from_agent": msg.from_agent,
                            "to_agent": msg.to_agent,
                            "message": msg.message,
                            "message_type": msg.message_type,
                            "timestamp": msg.timestamp.isoformat(),
                            "metadata": msg.metadata
                        }
                        for msg in messages
                    ]
                }
        
        @self.server.tool()
        async def update_agent_status(
            session_id: int,
            agent_name: str,
            status: str
        ) -> Dict[str, Any]:
            """
            Update an agent's status
            
            Args:
                session_id: PSUR session ID
                agent_name: Agent name
                status: Status (idle, working, waiting, complete)
            
            Returns:
                Dict with updated status
            """
            with get_db_context() as db:
                workflow = db.query(WorkflowState).filter(
                    WorkflowState.session_id == session_id
                ).first()
                
                if not workflow:
                    return {
                        "error": "Workflow not found",
                        "status": "error"
                    }
                
                # Update agent status
                agent_status = workflow.agent_status or {}
                agent_status[agent_name] = status
                workflow.agent_status = agent_status
                db.commit()
            
            # Broadcast status update
            await self._broadcast_to_websockets({
                "type": "agent_status_update",
                "session_id": session_id,
                "agent_name": agent_name,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "status": "success",
                "agent_name": agent_name,
                "new_status": status
            }
    
    async def _broadcast_to_websockets(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected WebSocket clients
        (Will be fully implemented in API layer)
        """
        # Placeholder for WebSocket broadcasting
        # In full implementation, this would use Socket.IO or similar
        pass
    
    def register_websocket_client(self, client):
        """Register a WebSocket client for broadcasts"""
        self.websocket_clients.append(client)
    
    def unregister_websocket_client(self, client):
        """Unregister a WebSocket client"""
        if client in self.websocket_clients:
            self.websocket_clients.remove(client)
    
    async def start(self, host: str = "localhost", port: int = 8006):
        """Start the MCP server"""
        await self.server.run(host=host, port=port)


# Server instance
collaboration_server = CollaborationServer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(collaboration_server.start())
