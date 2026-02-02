"""
Database models for Multi-Agent PSUR System
SQLAlchemy ORM models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PSURSession(Base):
    """Tracks PSUR generation sessions"""
    __tablename__ = "psur_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String(255), nullable=False)
    udi_di = Column(String(255))
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    status = Column(String(50), default="initializing")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    sections = relationship("SectionDocument", back_populates="session", cascade="all, delete-orphan")
    data_files = relationship("DataFile", back_populates="session", cascade="all, delete-orphan")
    workflow_state = relationship("WorkflowState", back_populates="session", uselist=False, cascade="all, delete-orphan")


class Agent(Base):
    """Stores agent instances and their status"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("psur_sessions.id"), nullable=False)
    agent_id = Column(String(50), nullable=False)  # e.g., "orchestrator", "device_id"
    name = Column(String(100), nullable=False)  # e.g., "Alex", "Diana"
    role = Column(String(255), nullable=False)
    ai_provider = Column(String(50), nullable=False)  # openai, anthropic, google, perplexity
    model = Column(String(100), nullable=False)
    status = Column(String(50), default="idle")  # idle, working, complete, waiting, error
    last_activity = Column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("PSURSession", back_populates="agents")


class ChatMessage(Base):
    """Stores agent discussion messages"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("psur_sessions.id"), nullable=False)
    
    from_agent = Column(String(50), nullable=False)
    to_agent = Column(String(50), default="all")
    message = Column(Text, nullable=False)
    message_type = Column(String(50), default="normal")  # normal, system, error, success
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Metadata for tool calls, data refs, etc.
    message_metadata = Column(JSON, nullable=True)
    
    # Relationships
    session = relationship("PSURSession", back_populates="messages")


class SectionDocument(Base):
    """Stores generated PSUR sections"""
    __tablename__ = "section_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("psur_sessions.id"), nullable=False)
    
    section_id = Column(String(10), nullable=False)  # A, B, C, etc.
    section_name = Column(String(255), nullable=False)
    author_agent = Column(String(50), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(50), default="draft")  # draft, in_review, approved, rejected
    
    qc_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Section metadata (stats, counts, sources)
    section_metadata = Column(JSON, nullable=True)
    
    # Relationships
    session = relationship("PSURSession", back_populates="sections")


class WorkflowState(Base):
    """Tracks current workflow state"""
    __tablename__ = "workflow_states"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("psur_sessions.id"), nullable=False, unique=True)
    
    current_section = Column(String(10), nullable=True)
    sections_completed = Column(Integer, default=0)
    total_sections = Column(Integer, default=13)
    status = Column(String(50), default="initialized")  # initialized, running, complete, error
    summary = Column(Text, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("PSURSession", back_populates="workflow_state")


class DataFile(Base):
    """Stores uploaded data files"""
    __tablename__ = "data_files"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("psur_sessions.id"), nullable=False)
    
    file_type = Column(String(50), nullable=False)  # sales, complaints, pmcf, etc.
    filename = Column(String(255), nullable=False)
    file_data = Column(LargeBinary, nullable=False)  # BLOB storage
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("PSURSession", back_populates="data_files")
