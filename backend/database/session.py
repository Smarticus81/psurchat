"""
Database session management
Creates and manages SQLAlchemy database connections
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from backend.config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function for FastAPI endpoints
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions
    Usage: with get_db_context() as db: ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables and add any missing columns to existing tables."""
    from backend.database.models import Base
    Base.metadata.create_all(bind=engine)
    _add_psur_session_columns_if_missing()
    print("✓ Database initialized successfully")


def _add_psur_session_columns_if_missing():
    """Add master_context and master_context_intake to psur_sessions if missing (SQLite)."""
    if "sqlite" not in (engine.url.drivername or ""):
        return
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('psur_sessions') WHERE name='master_context'"
            ))
            if r.scalar() == 0:
                with conn.begin():
                    conn.execute(text(
                        "ALTER TABLE psur_sessions ADD COLUMN master_context TEXT"
                    ))
            r = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('psur_sessions') WHERE name='master_context_intake'"
            ))
            if r.scalar() == 0:
                with conn.begin():
                    conn.execute(text(
                        "ALTER TABLE psur_sessions ADD COLUMN master_context_intake TEXT"
                    ))
    except Exception as e:
        print(f"Note: migration check skipped ({e})")
