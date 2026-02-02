@app.get("/api/sessions/{session_id}/document")
async def get_document(session_id: int, db: Session = Depends(get_db)):
    """Get the complete PSUR document"""
    try:
        # Get session
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all sections
        sections = db.query(SectionDocument)\
            .filter(SectionDocument.session_id == session_id)\
            .order_by(SectionDocument.section_id)\
            .all()
        
        # Build document
        document = {
            "session_id": session_id,
            "device_name": session.device_name,
            "udi_di": session.udi_di,
            "period_start": session.period_start.isoformat(),
            "period_end": session.period_end.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "sections": [
                {
                    "section_id": s.section_id,
                    "section_name": s.section_name,
                    "author_agent": s.author_agent,
                    "content": s.content,
                    "status": s.status,
                    "created_at": s.created_at.isoformat()
                }
                for s in sections
            ],
            "total_sections": len(sections)
        }
        
        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/document/download")
async def download_document(session_id: int, db: Session = Depends(get_db)):
    """Download PSUR document as text file"""
    try:
        # Get session and sections
        session = db.query(PSURSession).filter(PSURSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sections = db.query(SectionDocument)\
            .filter(SectionDocument.session_id == session_id)\
            .order_by(SectionDocument.section_id)\
            .all()
        
        # Build text document
        doc_text = f"""
{'='*80}
PERIODIC SAFETY UPDATE REPORT (PSUR)
{'='*80}

Device:           {session.device_name}
UDI-DI:          {session.udi_di}
Coverage Period: {session.period_start.strftime('%Y-%m-%d')} to {session.period_end.strftime('%Y-%m-%d')}
Generated:       {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
System:          Multi-Agent PSUR Generation System

{'='*80}

"""
        
        for section in sections:
            doc_text += f"\n\n{'='*80}\n"
            doc_text += f"SECTION {section.section_id}: {section.section_name.upper()}\n"
            doc_text += f"{'='*80}\n"
            doc_text += f"Author: {section.author_agent}\n"
            doc_text += f"Status: {section.status}\n"
            doc_text += f"{'-'*80}\n\n"
            doc_text += section.content or "[Content not generated]"
            doc_text += "\n\n"
        
        doc_text += f"\n\n{'='*80}\n"
        doc_text += f"END OF PSUR DOCUMENT\n"
        doc_text += f"{'='*80}\n"
        
        from fastapi.responses import PlainTextResponse
        
        return PlainTextResponse(
            content=doc_text,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=PSUR_{session.device_name.replace(' ', '_')}_{session_id}.txt"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
