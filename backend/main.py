"""
FastAPI Main Application
Provides REST API and WebSocket endpoints for the Multi-Agent PSUR System
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
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
from backend.sota_orchestrator import SOTAOrchestrator, AGENT_ROLES, SECTION_DEFINITIONS, WORKFLOW_ORDER
from backend.config import AGENT_CONFIGS, settings
from backend.data_processor import MasterContextExtractor

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

# Global orchestrator tracking for pause/resume functionality
active_orchestrators: Dict[int, SOTAOrchestrator] = {}

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
        
        # Build column detection diagnostics message
        columns_detected = metadata.get("columns_detected", {})
        all_columns = metadata.get("all_columns", [])
        diagnostics_lines = []
        
        if file_type == "sales":
            units_col = columns_detected.get("units")
            year_col = columns_detected.get("year")
            diagnostics_lines.append(f"Units Column: {units_col if units_col else 'NOT FOUND'}")
            diagnostics_lines.append(f"Year Column: {year_col if year_col else 'NOT FOUND'}")
            if not units_col:
                diagnostics_lines.append(f"WARNING: Could not detect units/quantity column. Available: {all_columns}")
        elif file_type == "complaints":
            severity_col = columns_detected.get("severity")
            closure_col = columns_detected.get("closure")
            type_col = columns_detected.get("type")
            root_cause_col = columns_detected.get("root_cause")
            diagnostics_lines.append(f"Severity Column: {severity_col if severity_col else 'NOT FOUND'}")
            diagnostics_lines.append(f"Closure/Status Column: {closure_col if closure_col else 'NOT FOUND'}")
            diagnostics_lines.append(f"Type Column: {type_col if type_col else 'NOT FOUND'}")
            diagnostics_lines.append(f"Root Cause Column: {root_cause_col if root_cause_col else 'NOT FOUND'}")
            if not severity_col:
                diagnostics_lines.append(f"WARNING: No severity column detected. Available: {all_columns}")
        elif file_type in ("vigilance", "maude"):
            type_col = columns_detected.get("type")
            diagnostics_lines.append(f"Event Type Column: {type_col if type_col else 'NOT FOUND'}")
        
        diagnostics_section = "\n".join(diagnostics_lines) if diagnostics_lines else ""
        record_count = metadata.get("record_count", 0)
        
        # Save analysis as a system message so agents can see it
        analysis_msg = ChatMessage(
            session_id=session_id,
            from_agent="System",
            to_agent="all",
            message=f"""Data Analysis: {file_type.upper()} ({file.filename})

**Records Found:** {record_count}
**Columns Detected:**
{diagnostics_section}

{analysis}""",
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

class MasterContextIntakeBody(BaseModel):
    denominator_scope: str = "reporting_period_only"
    inference_policy: str = "strictly_factual"
    closure_definition: str = ""
    baseline_year: Optional[int] = None
    external_vigilance_searched: bool = False
    complaint_closures_complete: bool = False
    rmf_hazard_list_available: bool = False
    intended_use_provided: bool = False


@app.patch("/api/sessions/{session_id}/intake")
async def set_master_context_intake(
    session_id: int,
    body: MasterContextIntakeBody,
    db: Session = Depends(get_db),
):
    """Set master context intake options before starting PSUR generation."""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        intake = {
            "denominator_scope": body.denominator_scope,
            "inference_policy": body.inference_policy,
            "closure_definition": body.closure_definition or None,
            "baseline_year": body.baseline_year,
            "external_vigilance_searched": body.external_vigilance_searched,
            "complaint_closures_complete": body.complaint_closures_complete,
            "rmf_hazard_list_available": body.rmf_hazard_list_available,
            "intended_use_provided": body.intended_use_provided,
        }
        setattr(session, "master_context_intake", intake)
        db.commit()
        return {"status": "ok", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/validate")
async def validate_session_data(session_id: int, db: Session = Depends(get_db)):
    """Check if uploaded data can be parsed correctly before starting generation."""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        data_files = db.query(DataFile).filter(DataFile.session_id == session_id).all()
        period_start = getattr(session, "period_start", None)
        period_end = getattr(session, "period_end", None)
        intake = getattr(session, "master_context_intake", None) or {}

        issues: List[Dict[str, str]] = []
        
        # Check for required file types
        file_types = [f.file_type for f in data_files]
        if "sales" not in file_types:
            issues.append({"severity": "warning", "message": "No sales/distribution data file uploaded. Units distributed will be 0."})
        if "complaints" not in file_types:
            issues.append({"severity": "warning", "message": "No complaints data file uploaded. Complaint analysis will be limited."})
        if len(data_files) == 0:
            issues.append({"severity": "error", "message": "No data files uploaded. Please upload at least one data file."})

        # Run extraction and report what was found
        master_context = MasterContextExtractor.extract(data_files, period_start, period_end, intake)
        
        # Check extraction results
        if master_context["exposure_denominator_value"] == 0:
            issues.append({
                "severity": "error", 
                "message": "Could not extract units distributed. Check sales file column names. Looking for: units, quantity, qty, sold, distributed, shipped, volume, amount, count"
            })
        
        if master_context["total_complaints_canonical"] > 0:
            column_mapping = master_context.get("column_mapping", {})
            complaints_mapping = column_mapping.get("complaints", {})
            if not complaints_mapping.get("severity_column"):
                issues.append({
                    "severity": "warning", 
                    "message": "Complaints found but severity column not detected. Severity analysis will be limited."
                })
            if not complaints_mapping.get("closure_column"):
                issues.append({
                    "severity": "warning", 
                    "message": "Complaints found but closure/status column not detected. Investigation status cannot be determined."
                })
        
        # Add any parsing warnings from the extractor
        for warning in master_context.get("parsing_warnings", []):
            issues.append({"severity": "warning", "message": warning})
        
        # Determine overall validity (errors = can't proceed, warnings = proceed with caution)
        has_errors = any(i["severity"] == "error" for i in issues)
        
        return {
            "valid": not has_errors,
            "issues": issues,
            "extracted_data": {
                "exposure_denominator_value": master_context["exposure_denominator_value"],
                "total_complaints_canonical": master_context["total_complaints_canonical"],
                "complaints_closed_canonical": master_context["complaints_closed_canonical"],
                "annual_units_canonical": master_context["annual_units_canonical"],
                "has_sales": master_context["has_sales"],
                "has_complaints": master_context["has_complaints"],
                "has_vigilance": master_context["has_vigilance"],
                "column_mapping": master_context.get("column_mapping", {}),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.post("/api/sessions/{session_id}/start")
async def start_generation(session_id: int, db: Session = Depends(get_db)):
    """Start PSUR generation: run master context extraction then orchestrator."""
    try:
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        data_files = db.query(DataFile).filter(DataFile.session_id == session_id).all()
        period_start = getattr(session, "period_start", None)
        period_end = getattr(session, "period_end", None)
        intake = getattr(session, "master_context_intake", None) or {}

        master_context = MasterContextExtractor.extract(
            data_files, period_start, period_end, intake
        )
        setattr(session, "master_context", master_context)
        setattr(session, "status", "running")
        db.commit()

        asyncio.create_task(run_orchestrator(session_id))

        return {
            "status": "started",
            "session_id": session_id,
            "message": "PSUR generation initiated; master context extracted.",
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
    """Get all agents with their status and model info (SOTA agent definitions)"""
    try:
        # Get status from DB
        db_agents = db.query(Agent).filter(Agent.session_id == session_id).all()
        status_map = {a.agent_id: a.status for a in db_agents}

        agents_list = []
        for agent_id, agent_info in AGENT_ROLES.items():
            config = AGENT_CONFIGS.get(agent_id)
            agents_list.append({
                "id": agent_id,
                "name": agent_info["name"],
                "role": agent_info["role"],
                "title": agent_info.get("title", agent_info["role"]),
                "expertise": agent_info.get("expertise", ""),
                "primary_section": agent_info.get("primary_section"),
                "color": agent_info.get("color", "#6366f1"),
                "ai_provider": config.ai_provider if config else "anthropic",
                "model": config.model if config else "claude-sonnet-4-20250514",
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


# ============================================================================
# INTERACTIVE WORKFLOW CONTROL ENDPOINTS
# ============================================================================

@app.post("/api/sessions/{session_id}/pause")
async def pause_workflow(session_id: int, db: Session = Depends(get_db)):
    """Pause the workflow at the next checkpoint."""
    try:
        if session_id not in active_orchestrators:
            raise HTTPException(status_code=404, detail="No active workflow for this session")
        
        orchestrator = active_orchestrators[session_id]
        success = orchestrator.request_pause()
        
        if success:
            # Broadcast pause status
            await manager.broadcast({
                "type": "workflow_paused",
                "session_id": session_id
            })
            return {"status": "pausing", "message": "Workflow will pause at next checkpoint"}
        else:
            return {"status": "not_running", "message": "Workflow is not currently running"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/resume")
async def resume_workflow(session_id: int, db: Session = Depends(get_db)):
    """Resume a paused workflow."""
    try:
        if session_id not in active_orchestrators:
            raise HTTPException(status_code=404, detail="No active workflow for this session")
        
        orchestrator = active_orchestrators[session_id]
        success = orchestrator.request_resume()
        
        if success:
            # Broadcast resume status
            await manager.broadcast({
                "type": "workflow_resumed",
                "session_id": session_id
            })
            return {"status": "resumed", "message": "Workflow has resumed"}
        else:
            return {"status": "not_paused", "message": "Workflow is not currently paused"}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class AskAgentInput(BaseModel):
    agent: str
    question: str


@app.post("/api/sessions/{session_id}/ask")
async def ask_agent(session_id: int, input: AskAgentInput, db: Session = Depends(get_db)):
    """Ask a specific agent a direct question."""
    try:
        # Validate agent exists
        if input.agent not in AGENT_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {input.agent}")
        
        # Check if session exists
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # First, post the user's question to the chat
        user_msg = ChatMessage(
            session_id=session_id,
            from_agent="User",
            to_agent=input.agent,
            message=input.question,
            message_type="normal",
            timestamp=datetime.utcnow(),
            processed=False
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        
        # Broadcast user message
        await manager.broadcast({
            "type": "new_message",
            "data": {
                "id": user_msg.id,
                "from_agent": "User",
                "to_agent": input.agent,
                "message": input.question,
                "message_type": "normal",
                "timestamp": user_msg.timestamp.isoformat() if user_msg.timestamp else None
            }
        })
        
        # Get or create orchestrator for context
        if session_id in active_orchestrators:
            orchestrator = active_orchestrators[session_id]
        else:
            orchestrator = SOTAOrchestrator(session_id)
            # Initialize context if not already done
            if orchestrator.context is None:
                await orchestrator._initialize_context()
        
        # Get agent response
        result = await orchestrator.ask_agent_directly(input.agent, input.question)
        
        # Mark user message as processed
        user_msg.processed = True
        db.commit()
        
        if result.get("error"):
            return {
                "status": "error",
                "error": result["error"],
                "agent": input.agent
            }
        
        return {
            "status": "ok",
            "response": result.get("response"),
            "agent": input.agent
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/workflow-status")
async def get_workflow_status(session_id: int, db: Session = Depends(get_db)):
    """Get current workflow status including pause state."""
    try:
        # Check if session exists
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get workflow state from database
        workflow_state = db.query(WorkflowState).filter(
            WorkflowState.session_id == session_id
        ).first()
        
        # Check if there's an active orchestrator
        orchestrator_active = session_id in active_orchestrators
        orchestrator_status = None
        
        if orchestrator_active:
            orchestrator_status = active_orchestrators[session_id].get_workflow_status()
        
        return {
            "session_id": session_id,
            "session_status": session.status,
            "orchestrator_active": orchestrator_active,
            "workflow_state": {
                "status": workflow_state.status if workflow_state else "not_started",
                "current_section": workflow_state.current_section if workflow_state else None,
                "sections_completed": workflow_state.sections_completed if workflow_state else 0,
                "total_sections": workflow_state.total_sections if workflow_state else 13,
                "paused": workflow_state.paused if workflow_state else False,
                "current_agent": workflow_state.current_agent if workflow_state else None
            } if workflow_state else None,
            "orchestrator_status": orchestrator_status
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
async def list_agents():
    """List all available agents and their roles."""
    agents = []
    for name, config in AGENT_CONFIGS.items():
        agents.append({
            "name": name,
            "role": config.role,
            "ai_provider": config.ai_provider,
            "model": config.model
        })
    return {"agents": agents}


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
    """Run SOTA orchestrator agent in background"""
    try:
        print(f"\nStarting SOTA orchestrator for session {session_id}...")
        orchestrator = SOTAOrchestrator(session_id)
        
        # Register orchestrator for pause/resume/ask functionality
        active_orchestrators[session_id] = orchestrator

        # Broadcast start
        await manager.broadcast({
            "type": "orchestrator_started",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        print(f"Executing SOTA workflow for session {session_id}...")
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
    finally:
        # Clean up orchestrator reference
        if session_id in active_orchestrators:
            del active_orchestrators[session_id]

# Expose manager for use by agents
def broadcast_message(message: dict):
    """Helper function for agents to broadcast messages"""
    asyncio.create_task(manager.broadcast(message))
