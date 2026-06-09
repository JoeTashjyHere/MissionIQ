"""Password hashing + JWT round-trip tests (no DB required)."""
from __future__ import annotations

import uuid

import jwt
import pytest

from app.core.security import (
    decode_access_token,
    hash_password,
    issue_access_token,
    issue_refresh_token,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("MissionIQ!Demo2026")
    assert verify_password("MissionIQ!Demo2026", h) is True
    assert verify_password("wrong-password", h) is False


def test_issue_and_decode_access_token():
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    token, exp = issue_access_token(user_id=user_id, workspace_ids=[ws_id])
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["ws"] == [str(ws_id)]
    assert payload["typ"] == "access"


def test_issue_refresh_token_is_long_and_unique():
    a, _ = issue_refresh_token()
    b, _ = issue_refresh_token()
    assert a != b
    assert len(a) >= 40


def test_decode_rejects_tampered_token():
    user_id = uuid.uuid4()
    token, _ = issue_access_token(user_id=user_id, workspace_ids=[])
    tampered = token[:-4] + "abcd"
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)
