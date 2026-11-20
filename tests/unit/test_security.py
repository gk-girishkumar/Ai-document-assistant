"""Unit tests for password hashing, password complexity validation, and JWT tokens."""

import uuid
import pytest
from doc_assistant.app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from fastapi import HTTPException


def test_password_hashing():
    pwd = "MySecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_password_hash_different():
    pwd = "ConsistentPassword123!"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    assert h1 != h2  # Unique salt per hash
    assert verify_password(pwd, h1)
    assert verify_password(pwd, h2)


def test_password_validation_strong():
    errors = validate_password_strength("ValidP@ssw0rd")
    assert len(errors) == 0


def test_password_validation_weak():
    # Too short
    assert any("at least 8" in err for err in validate_password_strength("Short1!"))
    # Missing uppercase
    assert any("uppercase" in err for err in validate_password_strength("lowercase123!"))
    # Missing lowercase
    assert any("lowercase" in err for err in validate_password_strength("UPPERCASE123!"))
    # Missing digit
    assert any("digit" in err for err in validate_password_strength("NoDigitsHere!"))
    # Missing special char
    assert any("special" in err for err in validate_password_strength("NoSpecialChar123"))


def test_jwt_token_creation_and_decoding():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, {"role": "admin"})
    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_refresh_token_creation():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    payload = verify_token(token, expected_type="refresh")

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_token_type_mismatch():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    with pytest.raises(HTTPException) as exc:
        verify_token(token, expected_type="refresh")
    assert exc.value.status_code == 401
