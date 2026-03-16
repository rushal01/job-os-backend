import os
import uuid

import pytest

# Set test encryption key before importing security module
os.environ["MASTER_ENCRYPTION_KEY"] = "a" * 64  # 32-byte hex key


class TestBYOKEncryption:
    """Test AES-256-GCM + HKDF per-user encryption for BYOK API keys."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypting then decrypting should return the original key."""
        from app.core.security import decrypt_api_key, encrypt_api_key

        user_id = uuid.uuid4()
        plaintext = "sk-ant-api03-test-key-12345"

        ciphertext, nonce, tag = encrypt_api_key(user_id, plaintext)
        result = decrypt_api_key(user_id, ciphertext, nonce, tag)

        assert result == plaintext

    def test_different_users_produce_different_ciphertexts(self) -> None:
        """Same plaintext encrypted for different users should produce different ciphertexts."""
        from app.core.security import encrypt_api_key

        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        plaintext = "sk-shared-key-abc123"

        ct_a, nonce_a, tag_a = encrypt_api_key(user_a, plaintext)
        ct_b, nonce_b, tag_b = encrypt_api_key(user_b, plaintext)

        assert ct_a != ct_b or nonce_a != nonce_b

    def test_per_user_key_isolation(self) -> None:
        """Decrypting with wrong user_id should fail."""
        from app.core.exceptions import AppError
        from app.core.security import decrypt_api_key, encrypt_api_key

        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        plaintext = "sk-user-a-key-xyz"

        ciphertext, nonce, tag = encrypt_api_key(user_a, plaintext)

        with pytest.raises(AppError) as exc_info:
            decrypt_api_key(user_b, ciphertext, nonce, tag)
        assert exc_info.value.code.value == "AI_KEY_INVALID"

    def test_tamper_detection(self) -> None:
        """Modifying ciphertext should be detected."""
        from app.core.exceptions import AppError
        from app.core.security import decrypt_api_key, encrypt_api_key

        user_id = uuid.uuid4()
        plaintext = "sk-tamper-test-key"

        ciphertext, nonce, tag = encrypt_api_key(user_id, plaintext)

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF
        tampered_bytes = bytes(tampered)

        with pytest.raises(AppError) as exc_info:
            decrypt_api_key(user_id, tampered_bytes, nonce, tag)
        assert exc_info.value.code.value == "AI_KEY_INVALID"

    def test_tamper_detection_on_tag(self) -> None:
        """Modifying tag should be detected."""
        from app.core.exceptions import AppError
        from app.core.security import decrypt_api_key, encrypt_api_key

        user_id = uuid.uuid4()
        plaintext = "sk-tag-tamper-key"

        ciphertext, nonce, tag = encrypt_api_key(user_id, plaintext)

        tampered_tag = bytearray(tag)
        tampered_tag[0] ^= 0xFF

        with pytest.raises(AppError):
            decrypt_api_key(user_id, ciphertext, nonce, bytes(tampered_tag))

    def test_encrypt_returns_bytes(self) -> None:
        """encrypt_api_key should return (bytes, bytes, bytes)."""
        from app.core.security import encrypt_api_key

        user_id = uuid.uuid4()
        ciphertext, nonce, tag = encrypt_api_key(user_id, "test-key")

        assert isinstance(ciphertext, bytes)
        assert isinstance(nonce, bytes)
        assert isinstance(tag, bytes)
        assert len(nonce) == 12  # AES-GCM uses 96-bit nonce
        assert len(tag) == 16  # AES-GCM uses 128-bit tag

    def test_empty_key_roundtrip(self) -> None:
        """Even empty string should encrypt/decrypt correctly."""
        from app.core.security import decrypt_api_key, encrypt_api_key

        user_id = uuid.uuid4()
        plaintext = ""

        ciphertext, nonce, tag = encrypt_api_key(user_id, plaintext)
        result = decrypt_api_key(user_id, ciphertext, nonce, tag)
        assert result == plaintext

    def test_long_key_roundtrip(self) -> None:
        """Long API keys should encrypt/decrypt correctly."""
        from app.core.security import decrypt_api_key, encrypt_api_key

        user_id = uuid.uuid4()
        plaintext = "sk-" + "x" * 500  # Long key

        ciphertext, nonce, tag = encrypt_api_key(user_id, plaintext)
        result = decrypt_api_key(user_id, ciphertext, nonce, tag)
        assert result == plaintext
