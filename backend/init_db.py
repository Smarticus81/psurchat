"""
Database Initialization Script
Creates all tables and loads initial data
"""

from backend.database.models import Base, Agent
from backend.database.session import engine, get_db_context
from backend.config import AGENT_CONFIGS, print_provider_status
from datetime import datetime

def init_database():
    """Initialize database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")
    
    # Show provider status
    print_provider_status()

def seed_agents(session_id: int):
    """Seed agent definitions for a session with automatic provider fallback"""
    print(f"\nSeeding agents for session {session_id}...")
    
    with get_db_context() as db:
        for agent_id, config in AGENT_CONFIGS.items():
            # Get actual provider (with fallback if needed)
            actual_provider, actual_model = config.get_active_provider()
            
            agent = Agent(
                session_id=session_id,
                agent_id=agent_id,
                name=config.name,
                role=config.role,
                ai_provider=actual_provider,  # Use fallback provider if needed
                model=actual_model,  # Use fallback model if needed
                status="idle",
                last_activity=datetime.utcnow()
            )
            db.add(agent)
            
            # Show if fallback was used
            if actual_provider != config.ai_provider:
                print(f"  ⚠️  {config.name} ({config.role}): {config.ai_provider} → {actual_provider}")
            else:
                print(f"  ✅ {config.name} ({config.role}): {actual_provider}")
        
        db.commit()
    
    print(f"✓ All {len(AGENT_CONFIGS)} agents seeded successfully\n")

if __name__ == "__main__":
    init_database()
    print("\n✅ Database initialized successfully!")
    print("Run 'python -m backend.main' to start the API server")
