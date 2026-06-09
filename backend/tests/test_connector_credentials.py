"""Connector credential encryption-at-rest contracts."""
from __future__ import annotations

import pytest

from app.connectors.credentials import decrypt_secret, encrypt_secret
from app.core.errors import AppError


def test_secret_round_trip():
    token = encrypt_secret("sf-api-key-12345")
    assert token != "sf-api-key-12345"
    assert decrypt_secret(token) == "sf-api-key-12345"


def test_ciphertext_is_not_plaintext_and_randomized():
    a = encrypt_secret("same-secret")
    b = encrypt_secret("same-secret")
    assert "same-secret" not in a
    # Fernet uses a random IV: identical plaintexts produce distinct tokens.
    assert a != b
    assert decrypt_secret(a) == decrypt_secret(b) == "same-secret"


def test_tampered_ciphertext_raises_structured_error():
    token = encrypt_secret("secret")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(AppError) as exc:
        decrypt_secret(tampered)
    assert exc.value.code == "connector.credential_invalid"


def test_key_derivation_falls_back_to_jwt_secret():
    """Without MIQ_CREDENTIAL_KEY the key derives from MIQ_JWT_SECRET, so
    encryption works out of the box in development."""
    from app.core.config import get_settings

    assert get_settings().credential_key is None
    assert decrypt_secret(encrypt_secret("dev-secret")) == "dev-secret"
