"""
Configuration module for Multi-Agent PSUR System
Manages environment variables and application settings with intelligent API key fallbacks
"""

from dataclasses import dataclass
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=False,
        extra='ignore'  # Ignore extra fields in .env
    )
    
    # Application
    app_name: str = "Multi-Agent PSUR System"
    debug: bool = False
    
    # API Keys - With Optional support for fallback
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None  # Grok API
    perplexity_api_key: Optional[str] = None
    
    # Model configs - Reasoning models for all agents
    openai_model_default: str = "gpt-5.2-2025-12-11"
    anthropic_model_default: str = "claude-opus-4-5-20250220"
    google_model_default: str = "gemini-2.5-pro"
    xai_model_default: str = "grok-4-1-fast-reasoning"
    
    # Database
    database_url: str = "sqlite:///./psur_system.db"
    database_echo: bool = False
    
    def get_cors_origins(self) -> list[str]:
        """CORS origins - hardcoded for local development"""
        return ["http://localhost:3000", "http://localhost:5173"]


# Global settings instance
settings = Settings()


def get_available_providers() -> dict[str, str]:
    """
    Check which AI providers are available based on API keys.
    Returns dict mapping provider name to primary model.
    """
    available = {}
    
    if settings.openai_api_key:
        available["openai"] = settings.openai_model_default
    
    if settings.anthropic_api_key:
        available["anthropic"] = settings.anthropic_model_default
    
    if settings.google_api_key:
        available["google"] = settings.google_model_default
    
    if settings.xai_api_key:
        available["xai"] = settings.xai_model_default
    
    if settings.perplexity_api_key:
        available["perplexity"] = "sonar"
    
    return available


def get_fallback_provider(preferred_provider: str) -> tuple[str, str]:
    """
    Get fallback provider if preferred is unavailable.
    Returns (provider_name, model_name).
    
    Priority chain:
    1. Preferred provider (if available)
    2. OpenAI (most versatile, reliable)
    3. xAI/Grok (fast, good quality)
    4. Google (good alternative)
    5. Anthropic (may have billing issues)
    6. Perplexity (last resort)
    """
    available = get_available_providers()
    
    # If preferred is available, use it
    if preferred_provider in available:
        return preferred_provider, available[preferred_provider]
    
    # Fallback chain - OpenAI first, then xAI, then Google, Anthropic last due to billing
    fallback_chain = ["openai", "xai", "google", "anthropic", "perplexity"]
    
    for provider in fallback_chain:
        if provider in available:
            print(f"⚠️  {preferred_provider} not available, using {provider} instead")
            return provider, available[provider]
    
    raise RuntimeError(
        "No AI providers available! Please set at least one API key:\n"
        "  - OPENAI_API_KEY (recommended)\n"
        "  - XAI_API_KEY (Grok)\n"
        "  - GOOGLE_API_KEY\n"
        "  - ANTHROPIC_API_KEY\n"
        "  - PERPLEXITY_API_KEY"
    )


@dataclass
class AgentConfig:
    """Configuration for individual agents with automatic fallback"""
    name: str
    role: str
    ai_provider: str  # Preferred provider
    model: str  # Preferred model
    temperature: float = 0.7
    max_tokens: int = 4000
    
    def get_active_provider(self) -> tuple[str, str]:
        """Get the actual provider and model to use (with fallback)"""
        return get_fallback_provider(self.ai_provider)


# SOTA Agent configurations - Aligned with MDCG 2022-21 and FormQAR-054
# Each agent has specific expertise and section responsibility
# All agents use reasoning models for higher quality output
AGENT_CONFIGS = {
    # Orchestrator - Workflow coordination
    "Alex": AgentConfig(
        name="Alex",
        role="Orchestrator",
        ai_provider="anthropic",
        model=settings.anthropic_model_default,
        temperature=0.5,
        max_tokens=8000,
    ),

    # Section A - Executive Summary (synthesizes all findings)
    "Marcus": AgentConfig(
        name="Marcus",
        role="Executive Summary Specialist",
        ai_provider="anthropic",
        model=settings.anthropic_model_default,
        temperature=0.6,
        max_tokens=16000,
    ),

    # Section B, C - Scope & Sales Data
    "Greta": AgentConfig(
        name="Greta",
        role="Sales & Market Data Analyst",
        ai_provider="openai",
        model=settings.openai_model_default,
        temperature=0.5,
        max_tokens=8000,
    ),

    # Section D - Serious Incidents & Vigilance
    "David": AgentConfig(
        name="David",
        role="Vigilance Specialist",
        ai_provider="anthropic",
        model=settings.anthropic_model_default,
        temperature=0.4,
        max_tokens=8000,
    ),

    # Sections E, F - Customer Feedback & Complaints Management
    "Emma": AgentConfig(
        name="Emma",
        role="Complaint Classifier",
        ai_provider="openai",
        model=settings.openai_model_default,
        temperature=0.5,
        max_tokens=8000,
    ),

    # Section G - Trends & Statistical Analysis
    "Diana": AgentConfig(
        name="Diana",
        role="Trend Detective",
        ai_provider="anthropic",
        model=settings.anthropic_model_default,
        temperature=0.4,
        max_tokens=8000,
    ),

    # Section H - Field Safety Corrective Actions
    "Lisa": AgentConfig(
        name="Lisa",
        role="FSCA Coordinator",
        ai_provider="google",
        model=settings.google_model_default,
        temperature=0.5,
        max_tokens=8000,
    ),

    # Section I - CAPA Implementation
    "Tom": AgentConfig(
        name="Tom",
        role="CAPA Verifier",
        ai_provider="openai",
        model=settings.openai_model_default,
        temperature=0.5,
        max_tokens=8000,
    ),

    # Sections J, K - Literature & External Databases
    "James": AgentConfig(
        name="James",
        role="Literature Reviewer",
        ai_provider="google",
        model=settings.google_model_default,
        temperature=0.6,
        max_tokens=8000,
    ),

    # Section L - PMCF Activities
    "Sarah": AgentConfig(
        name="Sarah",
        role="PMCF Specialist",
        ai_provider="google",
        model=settings.google_model_default,
        temperature=0.5,
        max_tokens=8000,
    ),

    # Section M - Benefit-Risk & Conclusions
    "Robert": AgentConfig(
        name="Robert",
        role="Risk Specialist",
        ai_provider="anthropic",
        model=settings.anthropic_model_default,
        temperature=0.4,
        max_tokens=16000,
    ),

    # QC Validator - Reviews all sections
    "Victoria": AgentConfig(
        name="Victoria",
        role="QC Expert",
        ai_provider="openai",
        model=settings.openai_model_default,
        temperature=0.3,
        max_tokens=8000,
    ),
}


# SOTA Section mapping - Aligned with FormQAR-054 and MDCG 2022-21
# Workflow order is based on dependency hierarchy
SECTIONS = {
    "A": {"title": "Executive Summary", "agent": "Marcus", "number": 1, "mdcg_ref": "1.1"},
    "B": {"title": "Scope and Device Description", "agent": "Greta", "number": 2, "mdcg_ref": "1.2"},
    "C": {"title": "Post-Market Data: Units Distributed", "agent": "Greta", "number": 3, "mdcg_ref": "2.1"},
    "D": {"title": "Serious Incidents and Trends", "agent": "David", "number": 4, "mdcg_ref": "2.2"},
    "E": {"title": "Post-Market Surveillance: Customer Feedback", "agent": "Emma", "number": 5, "mdcg_ref": "2.3"},
    "F": {"title": "Complaints Management", "agent": "Emma", "number": 6, "mdcg_ref": "2.4"},
    "G": {"title": "Trends and Performance Analysis", "agent": "Diana", "number": 7, "mdcg_ref": "3"},
    "H": {"title": "Field Safety Corrective Actions (FSCA)", "agent": "Lisa", "number": 8, "mdcg_ref": "2.5"},
    "I": {"title": "Corrective and Preventive Actions (CAPA)", "agent": "Tom", "number": 9, "mdcg_ref": "1.4"},
    "J": {"title": "Literature Review and External Data", "agent": "James", "number": 10, "mdcg_ref": "1.3"},
    "K": {"title": "External Adverse Event Databases", "agent": "James", "number": 11, "mdcg_ref": "2.6"},
    "L": {"title": "Post-Market Clinical Follow-up (PMCF)", "agent": "Sarah", "number": 12, "mdcg_ref": "1.5"},
    "M": {"title": "Overall Findings and Conclusions", "agent": "Robert", "number": 13, "mdcg_ref": "1.6"},
}

# Workflow generation order (dependency-based per SOTA spec)
WORKFLOW_ORDER = [
    "C",   # Phase 1: DATA FOUNDATION - Sales/Exposure (Greta)
    "D",   # Phase 2: ADVERSE EVENT ANALYSIS - Serious Incidents (David)
    "E",   # Phase 2: Customer Feedback (Emma)
    "F",   # Phase 2: Complaints Management (Emma)
    "G",   # Phase 3: ANALYTICAL - Trends & Analysis (Diana)
    "H",   # Phase 3: FSCA (Lisa)
    "I",   # Phase 3: CAPA (Tom)
    "J",   # Phase 4: EXTERNAL CONTEXT - Literature Review (James)
    "K",   # Phase 4: External Databases (James)
    "L",   # Phase 5: CLINICAL EVIDENCE - PMCF (Sarah)
    "B",   # Phase 6: CHARACTERIZATION - Scope & Description (Greta)
    "M",   # Phase 7: SYNTHESIS - Findings & Conclusions (Robert)
    "A",   # Phase 7: Executive Summary (Marcus)
]


def get_ai_client(provider: str):
    """
    Get AI client and model for a given provider.
    Returns (client, model_name) tuple.
    """
    actual_provider, model = get_fallback_provider(provider)

    if actual_provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return client, model

    elif actual_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        return client, model

    elif actual_provider == "google":
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        return genai, model

    elif actual_provider == "xai":
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.xai_api_key,
            base_url="https://api.x.ai/v1"
        )
        return client, model

    elif actual_provider == "perplexity":
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )
        return client, model

    else:
        raise ValueError(f"Unknown provider: {actual_provider}")


def print_provider_status():
    """Print which AI providers are available"""
    available = get_available_providers()
    
    print("\n" + "="*60)
    print("AI Provider Status:")
    print("="*60)
    
    providers = [
        ("OpenAI", "openai", settings.openai_api_key),
        ("xAI (Grok)", "xai", settings.xai_api_key),
        ("Anthropic", "anthropic", settings.anthropic_api_key),
        ("Google", "google", settings.google_api_key),
        ("Perplexity", "perplexity", settings.perplexity_api_key),
    ]
    
    for name, key, api_key in providers:
        if api_key:
            print(f"✅ {name:12} - Available ({available.get(key, 'N/A')})")
        else:
            print(f"⚠️  {name:12} - Not configured (will fallback)")
    
    print("="*60)
    
    if not available:
        print("\n❌ ERROR: No AI providers configured!")
        print("   Please add at least OPENAI_API_KEY or XAI_API_KEY to .env")
        print("="*60 + "\n")
    else:
        print(f"\n✅ {len(available)} provider(s) available - System ready!")
        print("="*60 + "\n")
