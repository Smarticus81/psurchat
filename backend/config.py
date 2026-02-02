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
    
    # Model configs - See: https://platform.openai.com/docs/models, https://docs.x.ai/docs/models
    openai_model_default: str = "gpt-5.2"  # Latest: gpt-5.2, gpt-5-mini, gpt-5-nano, gpt-4.1
    anthropic_model_orchestrator: str = "claude-3-5-sonnet-20241022"
    anthropic_model_synthesis: str = "claude-3-5-sonnet-20241022"
    anthropic_model_fast: str = "claude-3-5-haiku-20241022"
    google_model_default: str = "gemini-2.0-flash-exp"
    xai_model_default: str = "grok-4-1-fast-non-reasoning"  # Latest: grok-4-1-fast-*, grok-4-fast-*, grok-4
    
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
        available["anthropic"] = settings.anthropic_model_orchestrator
    
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


# Agent configurations with preferred providers
AGENT_CONFIGS = {
    "orchestrator": AgentConfig(
        name="Alex",
        role="Orchestrator",
        ai_provider="anthropic",
        model=settings.anthropic_model_orchestrator,
        temperature=0.5,
    ),
    "device_id": AgentConfig(
        name="Diana",
        role="Device Identification",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "scope": AgentConfig(
        name="Sam",
        role="Scope & Documentation",
        ai_provider="google",
        model=settings.google_model_default,
    ),
    "sales": AgentConfig(
        name="Raj",
        role="Sales Analysis",
        ai_provider="anthropic",
        model=settings.anthropic_model_fast,
    ),
    "vigilance": AgentConfig(
        name="Vera",
        role="Vigilance Monitor",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "complaints": AgentConfig(
        name="Carla",
        role="Complaint Classifier",
        ai_provider="google",
        model=settings.google_model_default,
    ),
    "trending": AgentConfig(
        name="Tara",
        role="Trend Detective",
        ai_provider="anthropic",
        model=settings.anthropic_model_synthesis,
    ),
    "fsca": AgentConfig(
        name="Frank",
        role="FSCA Coordinator",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "capa": AgentConfig(
        name="Cameron",
        role="CAPA Verifier",
        ai_provider="google",
        model=settings.google_model_default,
    ),
    "risk": AgentConfig(
        name="Rita",
        role="Risk Specialist",
        ai_provider="anthropic",
        model=settings.anthropic_model_orchestrator,
    ),
    "benefit_risk": AgentConfig(
        name="Brianna",
        role="Benefit-Risk Evaluator",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "external_db": AgentConfig(
        name="Eddie",
        role="External DB Investigator",
        ai_provider="perplexity",
        model="sonar",
    ),
    "pmcf": AgentConfig(
        name="Clara",
        role="PMCF Specialist",
        ai_provider="google",
        model=settings.google_model_default,
    ),
    "synthesis": AgentConfig(
        name="Marcus",
        role="Synthesis Expert",
        ai_provider="anthropic",
        model=settings.anthropic_model_synthesis,
        max_tokens=8000,
    ),
    "statistical": AgentConfig(
        name="Statler",
        role="Statistical Calculator",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "charts": AgentConfig(
        name="Charley",
        role="Chart Generator",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "data_quality": AgentConfig(
        name="Quincy",
        role="Data Quality Auditor",
        ai_provider="openai",
        model=settings.openai_model_default,
    ),
    "qc": AgentConfig(
        name="Victoria",
        role="QC Validator",
        ai_provider="openai",
        model=settings.openai_model_default,
        temperature=0.3,
    ),
}


# Section mapping
SECTIONS = {
    "A": {"title": "Device Identification", "agent": "Diana"},
    "B": {"title": "Scope & Documentation", "agent": "Sam"},
    "C": {"title": "Sales & Distribution", "agent": "Raj"},
    "D": {"title": "Vigilance Data", "agent": "Vera"},
    "E": {"title": "Complaint Analysis", "agent": "Carla"},
    "F": {"title": "Trending Analysis", "agent": "Tara"},
    "G": {"title": "FSCA Summary", "agent": "Frank"},
    "H": {"title": "CAPA Actions", "agent": "Cameron"},
    "I": {"title": "Risk Management", "agent": "Rita"},
    "J": {"title": "Benefit-Risk Evaluation", "agent": "Brianna"},
    "K": {"title": "External Database Search", "agent": "Eddie"},
    "L": {"title": "PMCF Activities", "agent": "Clara"},
    "M": {"title": "Final Synthesis", "agent": "Marcus"},
}


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
