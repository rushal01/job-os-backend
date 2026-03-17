import os
import threading
import time
import uuid

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from jose import JWTError, jwt

from app.config import settings
from app.core.exceptions import AppError, ErrorCode

# ---------------------------------------------------------------------------
# JWKS cache (for ES256 / asymmetric algorithms)
# ---------------------------------------------------------------------------
_jwks_cache: dict | None = None
_jwks_cache_time: float = 0.0
_jwks_lock = threading.Lock()
_JWKS_TTL = 3600  # re-fetch every hour


def _fetch_jwks() -> dict:
    """Fetch the JWKS from Supabase and cache it."""
    global _jwks_cache, _jwks_cache_time
    from loguru import logger

    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < _JWKS_TTL:
        return _jwks_cache

    with _jwks_lock:
        # Double-check after acquiring lock
        if _jwks_cache and (time.time() - _jwks_cache_time) < _JWKS_TTL:
            return _jwks_cache

        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        logger.info("Fetching JWKS from {}", jwks_url)
        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = time.time()
        logger.info("JWKS fetched: {} key(s)", len(_jwks_cache.get("keys", [])))
        return _jwks_cache


def _get_signing_key_from_jwks(token: str) -> str:
    """Extract the matching public key from JWKS for the given token."""
    jwks_data = _fetch_jwks()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    for key_data in jwks_data.get("keys", []):
        if kid and key_data.get("kid") != kid:
            continue
        # Return the JWK dict — python-jose can use it directly
        return key_data

    raise AppError(
        code=ErrorCode.AUTH_INVALID_TOKEN,
        message="No matching key found in JWKS",
    )


def verify_jwt(token: str) -> dict:
    """Verify a Supabase JWT and return the decoded payload.

    Supports both symmetric (HS256) and asymmetric (ES256) algorithms.
    For HS256: uses SUPABASE_JWT_SECRET directly.
    For ES256: fetches the public key from Supabase's JWKS endpoint.
    """
    from loguru import logger

    # Determine algorithm from token header
    try:
        header = jwt.get_unverified_header(token)
        token_alg = header.get("alg", "HS256")
        logger.debug("JWT header: alg={} kid={}", token_alg, header.get("kid"))
    except Exception as e:
        logger.warning("Cannot parse JWT header: {}", e)
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid or malformed token",
        ) from e

    # Pick the right key based on algorithm
    if token_alg.startswith("ES") or token_alg.startswith("RS") or token_alg.startswith("PS"):
        # Asymmetric — use JWKS public key
        logger.debug("Using JWKS public key for {} verification", token_alg)
        key = _get_signing_key_from_jwks(token)
    else:
        # Symmetric (HS*) — use shared secret
        logger.debug("Using JWT secret for {} verification", token_alg)
        key = settings.SUPABASE_JWT_SECRET

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[token_alg],
            audience="authenticated",
        )
        if "sub" not in payload:
            raise AppError(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Invalid token: missing subject claim",
            )
        logger.info("JWT verified OK for sub={}", payload["sub"][:8] + "...")
        return payload
    except JWTError as e:
        error_message = str(e).lower()
        logger.error("JWT verification FAILED (alg={}): {}", token_alg, str(e))
        if "expired" in error_message:
            raise AppError(
                code=ErrorCode.AUTH_TOKEN_EXPIRED,
                message="Token has expired",
            ) from e
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid or malformed token",
        ) from e


def _derive_user_key(user_id: uuid.UUID) -> bytes:
    """Derive a per-user encryption key from the master key using HKDF."""
    master_key = bytes.fromhex(settings.MASTER_ENCRYPTION_KEY)
    hkdf = HKDF(
        algorithm=SHA256(),
        length=32,
        salt=user_id.bytes,
        info=b"byok-encryption",
    )
    return hkdf.derive(master_key)


def encrypt_api_key(
    user_id: uuid.UUID, plaintext_key: str
) -> tuple[bytes, bytes, bytes]:
    """Encrypt a user's API key with AES-256-GCM using per-user derived key.

    Returns (ciphertext, nonce, tag).
    Note: AESGCM appends the tag to the ciphertext, so we split them.
    """
    derived_key = _derive_user_key(user_id)
    aesgcm = AESGCM(derived_key)
    nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
    ct_with_tag = aesgcm.encrypt(nonce, plaintext_key.encode("utf-8"), None)
    # AES-GCM tag is the last 16 bytes
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    return ciphertext, nonce, tag


def decrypt_api_key(
    user_id: uuid.UUID,
    ciphertext: bytes,
    nonce: bytes,
    tag: bytes,
) -> str:
    """Decrypt a user's API key with AES-256-GCM using per-user derived key."""
    derived_key = _derive_user_key(user_id)
    aesgcm = AESGCM(derived_key)
    # Reconstruct ciphertext + tag as expected by AESGCM
    ct_with_tag = ciphertext + tag
    try:
        plaintext = aesgcm.decrypt(nonce, ct_with_tag, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise AppError(
            code=ErrorCode.AI_KEY_INVALID,
            message="Failed to decrypt API key — possible tampering or wrong user",
        ) from e
