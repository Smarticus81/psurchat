"""
FastAPI Main Application
Provides REST API and WebSocket endpoints for the Multi-Agent PSUR System
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import asyncio
import json
import traceback
from datetime import datetime

from backend.database.session import get_db_context, get_db, init_db
from backend.database.models import (
    PSURSession, Agent, ChatMessage, SectionDocument, 
    WorkflowState, DataFile
)
from backend.orchestrator import OrchestratorAgent
from backend.config import AGENT_CONFIGS, settings

# Initialize FastAPI
app = FastAPI(
    title="Multi-Agent PSUR System API",
    description="REST API and WebSocket for AI-powered PSUR generation",
    version="1.0.0"
)

# CORS Configuration - must be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")

manager = ConnectionManager()

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Multi-Agent PSUR System",
        "version": "1.0.0"
    }

@app.post("/api/sessions")
async def create_session(
    device_name: str,
    udi_di: str,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    """Create a new PSUR generation session"""
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        session = PSURSession(
            device_name=device_name,
            udi_di=udi_di,
            period_start=start,
            period_end=end,
            status="initializing",
            created_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Initialize workflow state
        workflow = WorkflowState(
            session_id=session.id,
            current_section="A",
            sections_completed=0,
            total_sections=13,
            status="initialized"
        )
        db.add(workflow)
        db.commit()

        return {
            "session_id": session.id,
            "device_name": device_name,
            "status": "initialized"
        }
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """List all sessions"""
    try:
        sessions = db.query(PSURSession).order_by(PSURSession.created_at.desc()).all()
        
        result = []
        for session in sessions:
            workflow = db.query(WorkflowState).filter(WorkflowState.session_id == session.id).first()
            result.append({
                "id": session.id,
                "device_name": session.device_name,
                "udi_di": session.udi_di,
                "period_start": session.period_start.isoformat() if session.period_start else None,
                "period_end": session.period_end.isoformat() if session.period_end else None,
                "status": session.status,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "workflow": {
                    "sections_completed": workflow.sections_completed if workflow else 0,
                    "total_sections": workflow.total_sections if workflow else 13,
                } if workflow else None
            })
        
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a session and all associated data"""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete related records in correct order (foreign key dependencies)
        db.query(Agent).filter(Agent.session_id == session_id).delete(synchronize_session='fetch')
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session='fetch')
        db.query(SectionDocument).filter(SectionDocument.session_id == session_id).delete(synchronize_session='fetch')
        db.query(WorkflowState).filter(WorkflowState.session_id == session_id).delete(synchronize_session='fetch')
        db.query(DataFile).filter(DataFile.session_id == session_id).delete(synchronize_session='fetch')
        
        # Now delete the session
        db.delete(session)
        db.commit()
        
        return {"status": "success", "message": f"Session {session_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get session details"""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        workflow = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
        
        return {
            "id": session.id,
            "device_name": session.device_name,
            "udi_di": session.udi_di,
            "start_date": session.period_start.isoformat() if session.period_start else None,
            "end_date": session.period_end.isoformat() if session.period_end else None,
            "status": session.status,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "workflow": {
                "current_section": workflow.current_section if workflow else None,
                "sections_completed": workflow.sections_completed if workflow else 0,
                "total_sections": workflow.total_sections if workflow else 13,
                "status": workflow.status if workflow else "unknown"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from backend.data_processor import DataProcessor

@app.post("/api/sessions/{session_id}/upload")
async def upload_file(
    session_id: int,
    file: UploadFile = File(...),
    file_type: str = "sales",
    db: Session = Depends(get_db)
):
    """Upload data file (sales, complaints, etc.)"""
    try:
        content = await file.read()
        
        # Save to database
        data_file = DataFile(
            session_id=session_id,
            file_type=file_type,
            filename=file.filename,
            file_data=content,
            uploaded_at=datetime.utcnow()
        )
        db.add(data_file)
        
        # Process file data
        result = DataProcessor.process_file(content, file.filename, file_type)
        analysis = result["summary"]
        metadata = result["metadata"]
        
        # Save analysis as a system message so agents can see it
        analysis_msg = ChatMessage(
            session_id=session_id,
            from_agent="System",
            to_agent="all",
            message=f"Data Analysis: {file_type.upper()}\n\n{analysis}",
            message_type="system"
        )
        db.add(analysis_msg)
        
        # If UDI-DI is found in metadata, update the session
        if "udi_di" in metadata:
            session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
            if session and (not session.udi_di or session.udi_di == "Pending Extraction"):
                session.udi_di = metadata["udi_di"]
                # Also notify agents
                udi_msg = ChatMessage(
                    session_id=session_id,
                    from_agent="System",
                    to_agent="all",
                    message=f"Metadata Detected: Detected UDI-DI: {metadata['udi_di']} from {file.filename}",
                    message_type="success"
                )
                db.add(udi_msg)
        
        db.commit()
        db.refresh(data_file)
        
        return {
            "file_id": data_file.id,
            "filename": file.filename,
            "file_type": file_type,
            "size": len(content),
            "status": "uploaded",
            "analysis_preview": (analysis or "")[:100] + ("..." if len(analysis or "") > 100 else "")
        }
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/files")
async def get_session_files(session_id: int, db: Session = Depends(get_db)):
    """Get all uploaded files for a session"""
    try:
        files = db.query(DataFile).filter(DataFile.session_id == session_id).all()
        
        return [
            {
                "id": f.id,
                "filename": f.filename,
                "file_type": f.file_type,
                "size": len(f.file_data) if f.file_data else 0,
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None
            }
            for f in files
        ]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/start")
async def start_generation(session_id: int, db: Session = Depends(get_db)):
    """Start PSUR generation process"""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update session status
        session.status = "running"
        db.commit()

        # Start orchestrator in background
        asyncio.create_task(run_orchestrator(session_id))

        return {
            "status": "started",
            "session_id": session_id,
            "message": "PSUR generation initiated"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get chat messages for a session"""
    try:
        messages = db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_id)\
            .order_by(ChatMessage.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                "id": m.id,
                "from_agent": m.from_agent,
                "to_agent": m.to_agent,
                "message": m.message,
                "message_type": m.message_type,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in reversed(messages)
        ]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/agents")
async def get_agents(session_id: int, db: Session = Depends(get_db)):
    """Get all agents with their status and model info"""
    try:
        # Get status from DB
        db_agents = db.query(Agent).filter(Agent.session_id == session_id).all()
        status_map = {a.agent_id: a.status for a in db_agents}
        
        agents_list = []
        for agent_id, config in AGENT_CONFIGS.items():
            agents_list.append({
                "id": agent_id,
                "name": config.name,
                "role": config.role,
                "ai_provider": config.ai_provider,
                "model": config.model,
                "status": status_map.get(agent_id, "idle")
            })
            
        return agents_list
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/sections")
async def get_sections(session_id: int, db: Session = Depends(get_db)):
    """Get all section documents"""
    try:
        sections = db.query(SectionDocument)\
            .filter(SectionDocument.session_id == session_id)\
            .order_by(SectionDocument.section_id)\
            .all()
        
        return [
            {
                "section_id": s.section_id,
                "section_name": s.section_name,
                "author_agent": s.author_agent,
                "status": s.status,
                "word_count": len(s.content.split()) if s.content else 0,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "qc_feedback": s.qc_feedback
            }
            for s in sections
        ]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/sections/{section_id}")
async def get_section_content(
    session_id: int,
    section_id: str,
    db: Session = Depends(get_db)
):
    """Get full content of a specific section"""
    try:
        section = db.query(SectionDocument)\
            .filter(
                SectionDocument.session_id == session_id,
                SectionDocument.section_id == section_id
            )\
            .first()
        
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")
        
        return {
            "section_id": section.section_id,
            "section_name": section.section_name,
            "author_agent": section.author_agent,
            "content": section.content,
            "status": section.status,
            "qc_feedback": section.qc_feedback,
            "created_at": section.created_at.isoformat() if section.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/document")
async def get_complete_document(session_id: int, db: Session = Depends(get_db)):
    """Get the complete PSUR document with all sections"""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sections = db.query(SectionDocument)\
            .filter(SectionDocument.session_id == session_id)\
            .order_by(SectionDocument.section_id)\
            .all()
        
        return {
            "session_id": session_id,
            "device_name": session.device_name,
            "udi_di": session.udi_di,
            "period_start": session.period_start.isoformat() if session.period_start else None,
            "period_end": session.period_end.isoformat() if session.period_end else None,
            "status": session.status,
            "sections": [
                {
                    "section_id": s.section_id,
                    "section_name": s.section_name,  
                    "author_agent": s.author_agent,
                    "content": s.content,
                    "word_count": len(s.content.split()) if s.content else 0
                }
                for s in sections
            ],
            "total_sections": len(sections)
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class MessageInput(BaseModel):
    message: str
    from_agent: str = "User"
    to_agent: str = "all" 
    message_type: str = "normal"

@app.post("/api/sessions/{session_id}/messages")
async def create_message(
    session_id: int,
    input: MessageInput,
    db: Session = Depends(get_db)
):
    """Post a new message to the session"""
    try:
        msg = ChatMessage(
            session_id=session_id,
            from_agent=input.from_agent,
            to_agent=input.to_agent,
            message=input.message,
            message_type=input.message_type,
            timestamp=datetime.utcnow()
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        
        # Notify clients via WebSocket
        await manager.broadcast({
            "type": "new_message",
            "data": {
                "id": msg.id,
                "from_agent": msg.from_agent,
                "message": msg.message,
                "message_type": msg.message_type,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            }
        })
        
        return {"status": "ok", "message_id": msg.id}
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/document/download")
async def download_document(session_id: int, db: Session = Depends(get_db)):
    """Download complete PSUR as DOCX"""
    try:
        from fastapi.responses import FileResponse
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        import tempfile
        import os
        
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sections = db.query(SectionDocument)\
            .filter(SectionDocument.session_id == session_id)\
            .order_by(SectionDocument.section_id)\
            .all()
        
        # Create Word Doc
        doc = Document()
        
        # Styles
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(11)
        
        # Title Page
        doc.add_heading('PERIODIC SAFETY UPDATE REPORT (PSUR)', 0)
        
        p = doc.add_paragraph()
        p.add_run(f"Device: {session.device_name}\n").bold = True
        p.add_run(f"UDI-DI: {session.udi_di}\n")
        p.add_run(f"Period: {session.period_start.strftime('%Y-%m-%d') if session.period_start else 'N/A'} to {session.period_end.strftime('%Y-%m-%d') if session.period_end else 'N/A'}\n")
        p.add_run(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d')} UTC")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_page_break()
        
        # Content
        for section in sections:
            doc.add_heading(f"SECTION {section.section_id}: {section.section_name}", level=1)
            
            # Clean markdown basics
            content = section.content or "[No content]"
            
            # Remove </thinking> blocks if they leaked
            if "</thinking>" in content:
                content = content.split("</thinking>")[-1].strip()
                
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                elif line.startswith('- ') or line.startswith('* '):
                    doc.add_paragraph(line[2:], style='List Bullet')
                else:
                    doc.add_paragraph(line)
            
            doc.add_page_break()
        
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        filename = f"PSUR_{session.device_name.replace(' ', '_')}_{session_id}.docx"
        filepath = os.path.join(temp_dir, filename)
        doc.save(filepath)
        
        return FileResponse(
            path=filepath, 
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/workflow")
async def get_workflow(session_id: int, db: Session = Depends(get_db)):
    """Get workflow state"""
    try:
        workflow = db.query(WorkflowState)\
            .filter(WorkflowState.session_id == session_id)\
            .first()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "current_section": workflow.current_section,
            "sections_completed": workflow.sections_completed,
            "total_sections": workflow.total_sections,
            "status": workflow.status,
            "summary": workflow.summary
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Echo back for heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def run_orchestrator(session_id: int):
    """Run orchestrator agent in background"""
    try:
        print(f"\nStarting orchestrator for session {session_id}...")
        orchestrator = OrchestratorAgent(session_id)
        
        # Broadcast start
        await manager.broadcast({
            "type": "orchestrator_started",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"Executing workflow for session {session_id}...")
        # Execute workflow
        result = await orchestrator.execute_workflow()
        
        print(f"Workflow complete for session {session_id}: {result}")
        # Broadcast completion
        await manager.broadcast({
            "type": "orchestrator_complete",
            "session_id": session_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Orchestrator error for session {session_id}: {e}")
        traceback.print_exc()
        await manager.broadcast({
            "type": "error",
            "session_id": session_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

# Expose manager for use by agents
def broadcast_message(message: dict):
    """Helper function for agents to broadcast messages"""
    asyncio.create_task(manager.broadcast(message))
