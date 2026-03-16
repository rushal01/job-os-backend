import os
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from jose import JWTError, jwt

from app.config import settings
from app.core.exceptions import AppError, ErrorCode


def verify_jwt(token: str) -> dict:
    """Verify a Supabase JWT and return the decoded payload.

    Extracts the 'sub' claim as supabase_uid.
    """
    from loguru import logger

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        if "sub" not in payload:
            raise AppError(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Invalid token: missing subject claim",
            )
        return payload
    except JWTError as e:
        error_message = str(e).lower()
        logger.warning("JWT verification failed: {}", error_message)
        if "expired" in error_message:
            raise AppError(
                code=ErrorCode.AUTH_TOKEN_EXPIRED,
                message="Token has expired",
            )
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid or malformed token",
        )


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
    except Exception:
        raise AppError(
            code=ErrorCode.AI_KEY_INVALID,
            message="Failed to decrypt API key — possible tampering or wrong user",
        )
