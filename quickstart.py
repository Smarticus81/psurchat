#!/usr/bin/env python3
"""
Quick Start Script for Multi-Agent PSUR System
Initializes DB and seeds a test session
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.init_db import init_database, seed_agents
from backend.database.session import get_db_context
from backend.database.models import PSURSession, WorkflowState
from datetime import datetime

def create_test_session():
    """Create a test PSUR session"""
    with get_db_context() as db:
        # Create test session with date range
        from datetime import timedelta
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=365)  # 1 year period
        
        session = PSURSession(
            device_name="SAGE 1-Step Medium",
            udi_di="00810185020304",
            period_start=start_date,
            period_end=end_date,
            status="initialized",
            created_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Create workflow state
        workflow = WorkflowState(
            session_id=session.id,
            current_section="A",
            sections_completed=0,
            total_sections=13,
            status="ready"
        )
        db.add(workflow)
        db.commit()
        
        #  Seed agents for this session
        seed_agents(session.id)
        
        return session.id

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Multi-Agent PSUR System - Quick Start")
    print("=" * 60)
    print()
    
    # Initialize database
    init_database()
    print()
    
    # Create test session
    print("Creating test session...")
    session_id = create_test_session()
    print(f"✓ Test session created (ID: {session_id})")
    print()
    
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start Backend:  uvicorn backend.main:app --reload --port 8000")
    print("2. Start Frontend: cd frontend && npm run dev")
    print("3. Open Browser:   http://localhost:3000")
    print()
    print(f"📌 Session ID: {session_id}")
    print("=" * 60)
