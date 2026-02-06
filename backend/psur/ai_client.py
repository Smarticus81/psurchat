"""
Unified AI Client - Provider abstraction with automatic fallback.

Supports: Anthropic, OpenAI, Google GenAI, xAI (Grok).
Each call attempts the configured provider first, then falls back
to others in priority order until one succeeds.
"""

import asyncio
from typing import Optional, List

from backend.config import AGENT_CONFIGS, get_ai_client


# Provider priority for fallback
FALLBACK_ORDER = ["anthropic", "openai", "google", "xai"]


def _call_anthropic(client: object, model: str, system_prompt: str,
                    user_prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
    messages_api = getattr(client, "messages", None)
    if messages_api is None:
        return None
    response = messages_api.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    content_list = getattr(response, "content", None) or []
    first_block = content_list[0] if content_list else None
    return getattr(first_block, "text", str(first_block) if first_block else "")


def _call_openai_compat(client: object, model: str, system_prompt: str,
                        user_prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
    """Works for OpenAI and xAI (both use chat.completions)."""
    chat_api = getattr(client, "chat", None)
    if chat_api is None:
        return None
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        response = chat_api.completions.create(
            model=model, max_completion_tokens=max_tokens,
            temperature=temperature, messages=messages,
        )
    except Exception as e:
        if "max_completion_tokens" in str(e).lower():
            response = chat_api.completions.create(
                model=model, max_tokens=max_tokens,
                temperature=temperature, messages=messages,
            )
        else:
            raise
    choices = getattr(response, "choices", None) or []
    first = choices[0] if choices else None
    msg = getattr(first, "message", None) if first else None
    return getattr(msg, "content", None) if msg else None


def _call_google(model_name: str, system_prompt: str,
                 user_prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
    import google.generativeai as genai
    model_obj = genai.GenerativeModel(model_name)
    response = model_obj.generate_content(
        f"{system_prompt}\n\n{user_prompt}",
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return getattr(response, "text", str(response))


def _dispatch(provider: str, client: object, model: str,
              system_prompt: str, user_prompt: str,
              max_tokens: int, temperature: float) -> Optional[str]:
    if provider == "anthropic":
        return _call_anthropic(client, model, system_prompt, user_prompt, max_tokens, temperature)
    elif provider == "google":
        return _call_google(model, system_prompt, user_prompt, max_tokens, temperature)
    else:  # openai, xai
        return _call_openai_compat(client, model, system_prompt, user_prompt, max_tokens, temperature)


def call_ai_sync(agent_name: str, system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Synchronous AI call with automatic fallback across providers.
    Looks up agent config for provider, model, temperature, max_tokens.
    Falls back through FALLBACK_ORDER on failure.
    """
    config = AGENT_CONFIGS.get(agent_name, AGENT_CONFIGS.get("Alex"))
    if not config:
        return None

    # Attempt primary provider
    try:
        client, model = get_ai_client(config.ai_provider)
        result = _dispatch(config.ai_provider, client, model,
                           system_prompt, user_prompt,
                           config.max_tokens, config.temperature)
        if result:
            return result
    except Exception as e:
        print(f"[ai_client] Primary provider {config.ai_provider} failed for {agent_name}: {e}")

    # Fallback
    for provider in FALLBACK_ORDER:
        if provider == config.ai_provider:
            continue
        try:
            client, model = get_ai_client(provider)
            result = _dispatch(provider, client, model,
                               system_prompt, user_prompt,
                               min(config.max_tokens, 4096), config.temperature)
            if result:
                print(f"[ai_client] Fallback to {provider} succeeded for {agent_name}")
                return result
        except Exception as fb_err:
            print(f"[ai_client] Fallback {provider} also failed for {agent_name}: {fb_err}")
            continue

    return None


async def call_ai(agent_name: str, system_prompt: str, user_prompt: str) -> Optional[str]:
    """Async wrapper: runs call_ai_sync in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, call_ai_sync, agent_name, system_prompt, user_prompt)
