"""Connector credential encryption — Fernet (AES-128-CBC + HMAC) at rest.

Key resolution order:
1. ``MIQ_CREDENTIAL_KEY`` — a urlsafe-base64 32-byte key (``Fernet.generate_key()``).
2. Derived from ``MIQ_JWT_SECRET`` via SHA-256 (dev convenience). Production
   deployments should set a dedicated key so credentials and signing keys
   rotate independently.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import AppError


def _fernet() -> Fernet:
    settings = get_settings()
    if settings.credential_key:
        return Fernet(settings.credential_key.encode("utf-8"))
    derived = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(secret_encrypted: str) -> str:
    try:
        return _fernet().decrypt(secret_encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise AppError(
            "Stored connector credential could not be decrypted — the "
            "credential key has changed. Rotate the connector credential.",
            status_code=409,
            code="connector.credential_invalid",
        ) from exc
