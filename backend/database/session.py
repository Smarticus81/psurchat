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
    """Add master_context, master_context_intake, template_id to psur_sessions if missing (SQLite)."""
    if "sqlite" not in (engine.url.drivername or ""):
        return
    from sqlalchemy import text
    _columns_to_add = [
        ("master_context", "TEXT"),
        ("master_context_intake", "TEXT"),
        ("template_id", "VARCHAR(50) DEFAULT 'eu_uk_mdr'"),
        ("context_snapshot", "TEXT"),
    ]
    try:
        with engine.connect() as conn:
            for col_name, col_type in _columns_to_add:
                r = conn.execute(text(
                    f"SELECT COUNT(*) FROM pragma_table_info('psur_sessions') WHERE name='{col_name}'"
                ))
                if r.scalar() == 0:
                    with conn.begin():
                        conn.execute(text(
                            f"ALTER TABLE psur_sessions ADD COLUMN {col_name} {col_type}"
                        ))
    except Exception as e:
        print(f"Note: migration check skipped ({e})")
