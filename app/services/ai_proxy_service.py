"""AI proxy service — centralized gateway for all AI provider calls.

Handles BYOK key decryption, provider routing, cost tracking, circuit breakers,
and provider fallback per API Contract Section 4.8.
"""

import time
import uuid

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.core.security import decrypt_api_key, encrypt_api_key
from app.models.api_key import APIKey
from app.schemas.ai import AIResponse

# ---------------------------------------------------------------------------
# Task → Model mapping (defaults)
# ---------------------------------------------------------------------------
TASK_MODEL_MAP: dict[str, dict[str, str]] = {
    "scoring": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "content_resume": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "content_cl": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "content_answers": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "qa_check": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
    "copilot": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "company_intel": {"provider": "openai", "model": "gpt-4o-mini"},
}

PROVIDER_ENDPOINTS: dict[str, str] = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai": "https://api.openai.com/v1/chat/completions",
}

# Cost per token (approximate, USD)
COST_TABLE: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-haiku-4-5-20251001": {"input": 0.80 / 1_000_000, "output": 4.0 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.0 / 1_000_000},
}

FALLBACK_ORDER: dict[str, list[str]] = {
    "anthropic": ["openai"],
    "openai": ["anthropic"],
}

_TIMEOUT = httpx.Timeout(90.0, connect=5.0)


# ---------------------------------------------------------------------------
# Provider request/response formatters
# ---------------------------------------------------------------------------

def _format_anthropic_request(
    prompt: str, system_prompt: str | None, model: str, max_tokens: int, temperature: float
) -> tuple[dict, dict]:
    """Return (headers_extra, body) for Anthropic Messages API."""
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        body["system"] = system_prompt
    headers = {
        "x-api-key": "",  # placeholder, filled in call_ai
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    return headers, body


def _format_openai_request(
    prompt: str, system_prompt: str | None, model: str, max_tokens: int, temperature: float
) -> tuple[dict, dict]:
    """Return (headers_extra, body) for OpenAI Chat Completions API."""
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    headers = {
        "authorization": "",  # placeholder
        "content-type": "application/json",
    }
    return headers, body


def _parse_anthropic_response(data: dict) -> tuple[str, int, int]:
    """Extract (content, input_tokens, output_tokens) from Anthropic response."""
    content = data["content"][0]["text"]
    input_tokens = data["usage"]["input_tokens"]
    output_tokens = data["usage"]["output_tokens"]
    return content, input_tokens, output_tokens


def _parse_openai_response(data: dict) -> tuple[str, int, int]:
    """Extract (content, input_tokens, output_tokens) from OpenAI response."""
    content = data["choices"][0]["message"]["content"]
    input_tokens = data["usage"]["prompt_tokens"]
    output_tokens = data["usage"]["completion_tokens"]
    return content, input_tokens, output_tokens


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost from token counts."""
    costs = COST_TABLE.get(model, {"input": 0.0, "output": 0.0})
    return input_tokens * costs["input"] + output_tokens * costs["output"]


# ---------------------------------------------------------------------------
# Core AI call
# ---------------------------------------------------------------------------

async def call_ai(
    db: AsyncSession,
    user_id: uuid.UUID,
    task_type: str,
    prompt: str,
    system_prompt: str | None = None,
    model_override: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    _user_settings: dict | None = None,
) -> AIResponse:
    """Centralized AI gateway — all AI calls go through here.

    1. Determine provider + model from task_type (or model_override)
    2. Get user's API key for that provider
    3. Decrypt the key
    4. Check circuit breaker — if open, try fallback
    5. Format and send request
    6. Parse response, calculate cost
    7. Return AIResponse
    """
    # 1. Determine provider/model
    user_map = (_user_settings or {}).get("task_model_map", {})
    if model_override:
        # Infer provider from model name
        if "claude" in model_override:
            provider = "anthropic"
        elif "gpt" in model_override:
            provider = "openai"
        else:
            provider = "openai"
        model = model_override
    elif task_type in user_map:
        provider = user_map[task_type].get("provider", TASK_MODEL_MAP[task_type]["provider"])
        model = user_map[task_type].get("model", TASK_MODEL_MAP[task_type]["model"])
    elif task_type in TASK_MODEL_MAP:
        provider = TASK_MODEL_MAP[task_type]["provider"]
        model = TASK_MODEL_MAP[task_type]["model"]
    else:
        raise AppError(code=ErrorCode.VALIDATION_ERROR, message=f"Unknown task type: {task_type}")

    # Try primary, then fallbacks
    providers_to_try = [provider] + FALLBACK_ORDER.get(provider, [])

    last_error: Exception | None = None
    for attempt_provider in providers_to_try:
        try:
            return await _call_provider(
                db, user_id, attempt_provider, model, task_type,
                prompt, system_prompt, max_tokens, temperature,
            )
        except AppError as e:
            # Non-retryable errors: don't try fallback
            if e.code in (ErrorCode.AI_KEY_INVALID, ErrorCode.AI_PROVIDER_QUOTA_EXCEEDED):
                raise
            last_error = e
            logger.warning(f"Provider {attempt_provider} failed, trying next: {e.message}")

    # All providers failed
    if last_error:
        raise last_error
    raise AppError(code=ErrorCode.INTERNAL_ERROR, message="No AI providers available")


async def _call_provider(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    model: str,
    task_type: str,
    prompt: str,
    system_prompt: str | None,
    max_tokens: int,
    temperature: float,
) -> AIResponse:
    """Make the actual API call to a single provider."""
    # Check circuit breaker
    try:
        from app.db.redis import redis_client
        if redis_client is not None:
            from app.core.circuit_breaker import CircuitBreaker
            cb = CircuitBreaker(redis_client, f"ai:{provider}")
            if await cb.is_open():
                raise AppError(
                    code=ErrorCode.AI_PROVIDER_TIMEOUT,
                    message=f"Circuit breaker open for {provider}",
                )
    except AppError:
        raise
    except Exception:
        pass  # Redis unavailable — skip circuit breaker

    # Get and decrypt API key
    api_key_plaintext = await _get_decrypted_key(db, user_id, provider)

    # Format request
    endpoint = PROVIDER_ENDPOINTS.get(provider)
    if not endpoint:
        raise AppError(code=ErrorCode.VALIDATION_ERROR, message=f"Unsupported provider: {provider}")

    if provider == "anthropic":
        headers, body = _format_anthropic_request(prompt, system_prompt, model, max_tokens, temperature)
        headers["x-api-key"] = api_key_plaintext
    elif provider == "openai":
        headers, body = _format_openai_request(prompt, system_prompt, model, max_tokens, temperature)
        headers["authorization"] = f"Bearer {api_key_plaintext}"
    else:
        raise AppError(code=ErrorCode.VALIDATION_ERROR, message=f"Unsupported provider: {provider}")

    # Make the call
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
    except httpx.TimeoutException:
        await _record_circuit_failure(provider)
        raise AppError(
            code=ErrorCode.AI_PROVIDER_TIMEOUT,
            message=f"AI provider {provider} timed out",
        ) from None
    except httpx.ConnectError:
        await _record_circuit_failure(provider)
        raise AppError(
            code=ErrorCode.AI_PROVIDER_TIMEOUT,
            message=f"Cannot connect to AI provider {provider}",
        ) from None

    latency_ms = (time.perf_counter() - t0) * 1000

    # Handle error responses
    if resp.status_code == 401:
        raise AppError(code=ErrorCode.AI_KEY_INVALID, message="Invalid API key")
    if resp.status_code == 429:
        await _record_circuit_failure(provider)
        raise AppError(code=ErrorCode.AI_PROVIDER_QUOTA_EXCEEDED, message="Rate limit or quota exceeded")
    if resp.status_code >= 500:
        await _record_circuit_failure(provider)
        raise AppError(code=ErrorCode.AI_PROVIDER_TIMEOUT, message=f"Provider error: {resp.status_code}")
    if resp.status_code >= 400:
        raise AppError(code=ErrorCode.INTERNAL_ERROR, message=f"AI provider error: {resp.text[:200]}")

    # Parse response
    data = resp.json()
    if provider == "anthropic":
        content, input_tokens, output_tokens = _parse_anthropic_response(data)
    else:
        content, input_tokens, output_tokens = _parse_openai_response(data)

    cost_usd = _calculate_cost(model, input_tokens, output_tokens)

    # Record success on circuit breaker
    await _record_circuit_success(provider)

    return AIResponse(
        content=content,
        model_used=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=round(latency_ms, 1),
    )


async def _get_decrypted_key(db: AsyncSession, user_id: uuid.UUID, provider: str) -> str:
    """Fetch and decrypt a user's API key for a given provider."""
    result = await db.execute(
        select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.provider == provider,
            APIKey.status == "active",
        )
    )
    key_row = result.scalar_one_or_none()
    if key_row is None:
        raise AppError(
            code=ErrorCode.AI_KEY_INVALID,
            message=f"No active API key for provider {provider}. Add one via /api/v1/ai/keys.",
        )
    return decrypt_api_key(user_id, key_row.encrypted_key, key_row.key_nonce, key_row.key_tag)


async def _record_circuit_failure(provider: str) -> None:
    """Record a failure on the circuit breaker (best-effort)."""
    try:
        from app.db.redis import redis_client
        if redis_client is not None:
            from app.core.circuit_breaker import CircuitBreaker
            cb = CircuitBreaker(redis_client, f"ai:{provider}")
            await cb.record_failure()
    except Exception:
        pass


async def _record_circuit_success(provider: str) -> None:
    """Record a success on the circuit breaker (best-effort)."""
    try:
        from app.db.redis import redis_client
        if redis_client is not None:
            from app.core.circuit_breaker import CircuitBreaker
            cb = CircuitBreaker(redis_client, f"ai:{provider}")
            await cb.record_success()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# API Key management functions
# ---------------------------------------------------------------------------

async def list_api_keys(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """List all API keys for a user (masked, never expose plaintext)."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
    )
    keys = list(result.scalars().all())
    masked = []
    for k in keys:
        try:
            plain = decrypt_api_key(user_id, k.encrypted_key, k.key_nonce, k.key_tag)
            last8 = plain[-8:] if len(plain) >= 8 else plain
            masked_key = f"{'*' * 8}...{last8}"
        except Exception:
            masked_key = "***invalid***"
        masked.append({
            "id": k.id,
            "provider": k.provider,
            "status": k.status,
            "last_validated": k.last_validated,
            "masked_key": masked_key,
            "created_at": k.created_at,
        })
    return masked


async def add_api_key(
    db: AsyncSession, user_id: uuid.UUID, provider: str, plaintext_key: str
) -> APIKey:
    """Encrypt and store a new API key."""
    ciphertext, nonce, tag = encrypt_api_key(user_id, plaintext_key)
    key = APIKey(
        user_id=user_id,
        provider=provider,
        encrypted_key=ciphertext,
        key_nonce=nonce,
        key_tag=tag,
        status="active",
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)
    return key


async def delete_api_key(db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID) -> bool:
    """Delete an API key. Returns True if found."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        return False
    await db.delete(key)
    await db.flush()
    return True


async def validate_api_key(db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID) -> dict:
    """Decrypt and validate an API key by making a minimal test call."""
    from datetime import UTC, datetime

    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    )
    key_row = result.scalar_one_or_none()
    if key_row is None:
        return {"valid": False, "error": "Key not found"}

    try:
        plaintext = decrypt_api_key(user_id, key_row.encrypted_key, key_row.key_nonce, key_row.key_tag)
    except Exception:
        key_row.status = "invalid"
        await db.flush()
        return {"valid": False, "error": "Decryption failed"}

    # Make a minimal test call
    try:
        if key_row.provider == "anthropic":
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                    headers={"x-api-key": plaintext, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                )
        elif key_row.provider == "openai":
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json={"model": "gpt-4o-mini", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                    headers={"authorization": f"Bearer {plaintext}", "content-type": "application/json"},
                )
        else:
            return {"valid": False, "error": f"Unsupported provider: {key_row.provider}"}

        if resp.status_code in (200, 201):
            key_row.status = "active"
            key_row.last_validated = datetime.now(UTC)
            await db.flush()
            return {"valid": True, "error": None}
        elif resp.status_code == 401:
            key_row.status = "invalid"
            await db.flush()
            return {"valid": False, "error": "Invalid API key"}
        else:
            return {"valid": False, "error": f"Provider returned {resp.status_code}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def get_model_config(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """Get AI model configuration per task type, merging user overrides."""
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    user_map = (user.settings or {}).get("task_model_map", {}) if user else {}

    configs = []
    for task, defaults in TASK_MODEL_MAP.items():
        override = user_map.get(task, {})
        configs.append({
            "task": task,
            "provider": override.get("provider", defaults["provider"]),
            "model": override.get("model", defaults["model"]),
        })
    return configs


async def update_model_config(db: AsyncSession, user_id: uuid.UUID, task_model_map: dict) -> list[dict]:
    """Update AI model configuration in user.settings."""
    from app.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="User not found")

    settings = dict(user.settings or {})
    settings["task_model_map"] = task_model_map
    user.settings = settings
    await db.flush()
    return await get_model_config(db, user_id)


async def get_usage_stats(db: AsyncSession, user_id: uuid.UUID, period: str) -> dict:
    """Get AI usage statistics for a period. Reads from tasks table."""
    # For now, return empty stats — real implementation requires
    # tracking usage in a dedicated table or parsing task results
    return {
        "period": period,
        "total_tokens": 0,
        "total_cost": 0.0,
        "by_provider": {},
        "by_task": {},
    }
