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


# =============================================================================
# Discussion Panel Architecture: 18-Agent AGENT_CONFIGS
# =============================================================================
# Orchestrator (1) + Section Agents (13) + Analytical Support (3) + QC (1)

AGENT_CONFIGS = {
    # === ORCHESTRATOR ===
    "Alex": AgentConfig(
        name="Alex", role="Orchestrator",
        ai_provider="anthropic", model="claude-sonnet-4-5-20250514",
        temperature=0.5, max_tokens=2000,
    ),

    # === SECTION AGENTS (13) ===
    # max_tokens STRICTLY capped: 800 words ~= 1100 tokens, with buffer.
    # Total PSUR target: ~30 pages across 13 sections.

    # Section A: Executive Summary (written last)
    "Diana": AgentConfig(
        name="Diana", role="Device Identification Specialist",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.4, max_tokens=2000,
    ),
    # Section B: Scope & Documents
    "Sam": AgentConfig(
        name="Sam", role="Scope & Documentation Curator",
        ai_provider="google", model=settings.google_model_default,
        temperature=0.5, max_tokens=1500,
    ),
    # Section C: Sales & Distribution
    "Raj": AgentConfig(
        name="Raj", role="Sales Analyst",
        ai_provider="anthropic", model="claude-haiku-4-5-20250514",
        temperature=0.4, max_tokens=1500,
    ),
    # Section D: Vigilance / Serious Incidents
    "Vera": AgentConfig(
        name="Vera", role="Vigilance Monitor",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.3, max_tokens=2000,
    ),
    # Sections E+F: Complaints
    "Carla": AgentConfig(
        name="Carla", role="Complaint Classifier",
        ai_provider="google", model=settings.google_model_default,
        temperature=0.5, max_tokens=2500,
    ),
    # Section G: Trends
    "Tara": AgentConfig(
        name="Tara", role="Trend Detective",
        ai_provider="anthropic", model=settings.anthropic_model_default,
        temperature=0.4, max_tokens=2000,
    ),
    # Section H: FSCA
    "Frank": AgentConfig(
        name="Frank", role="FSCA Coordinator",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.5, max_tokens=1500,
    ),
    # Section I: CAPA
    "Cameron": AgentConfig(
        name="Cameron", role="CAPA Effectiveness Verifier",
        ai_provider="google", model=settings.google_model_default,
        temperature=0.5, max_tokens=1500,
    ),
    # Risk Tables
    "Rita": AgentConfig(
        name="Rita", role="Risk Reassessment Specialist",
        ai_provider="anthropic", model="claude-sonnet-4-5-20250514",
        temperature=0.4, max_tokens=1500,
    ),
    # Section J: Benefit-Risk
    "Brianna": AgentConfig(
        name="Brianna", role="Benefit-Risk Evaluator",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.5, max_tokens=2000,
    ),
    # Section K: External Databases
    "Eddie": AgentConfig(
        name="Eddie", role="External Database Investigator",
        ai_provider="google", model=settings.google_model_default,
        temperature=0.6, max_tokens=1500,
    ),
    # Section L: PMCF
    "Clara": AgentConfig(
        name="Clara", role="Clinical Follow-Up Specialist",
        ai_provider="google", model=settings.google_model_default,
        temperature=0.5, max_tokens=1500,
    ),
    # Section M: Conclusions
    "Marcus": AgentConfig(
        name="Marcus", role="Synthesis & Conclusions Expert",
        ai_provider="anthropic", model=settings.anthropic_model_default,
        temperature=0.6, max_tokens=3000,
    ),

    # === ANALYTICAL SUPPORT AGENTS (3) ===

    "Statler": AgentConfig(
        name="Statler", role="Statistical Calculator",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.1, max_tokens=2000,
    ),
    "Charley": AgentConfig(
        name="Charley", role="Chart & Table Generator",
        ai_provider="google", model=settings.google_model_default,
        temperature=0.3, max_tokens=2000,
    ),
    "Quincy": AgentConfig(
        name="Quincy", role="Data Quality Auditor",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.2, max_tokens=2000,
    ),

    # === QUALITY CONTROL ===

    "Victoria": AgentConfig(
        name="Victoria", role="QC Validator",
        ai_provider="openai", model=settings.openai_model_default,
        temperature=0.3, max_tokens=2000,
    ),
}


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
