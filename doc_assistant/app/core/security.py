"""Security utilities — password hashing, JWT tokens, FastAPI dependencies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable, Optional

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_assistant.app.core.config import settings
from doc_assistant.app.core.database import get_db

logger = logging.getLogger(__name__)

# ── Password hashing (passlib with secure PBKDF2/HMAC fallback) ───────────────
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        try:
            return pwd_context.hash(password)
        except Exception:
            return _fallback_hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            if hashed_password.startswith("pbkdf2_sha256$"):
                return _fallback_verify(plain_password, hashed_password)
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return _fallback_verify(plain_password, hashed_password)

except ImportError:
    pwd_context = None

    def hash_password(password: str) -> str:
        return _fallback_hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return _fallback_verify(plain_password, hashed_password)


def _fallback_hash(password: str) -> str:
    import secrets
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256${salt}${key.hex()}"


def _fallback_verify(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        _, salt, expected_hex = parts
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False


# ── Password‑strength validation ───────────────────────────────────────────
_PASSWORD_RULES: list[tuple[str, str]] = [
    (r".{8,}", "Password must be at least 8 characters long."),
    (r"[A-Z]", "Password must contain at least one uppercase letter."),
    (r"[a-z]", "Password must contain at least one lowercase letter."),
    (r"\d", "Password must contain at least one digit."),
    (r"[!@#$%^&*()_+\-=\[\]{}|;:'\",.<>?/`~\\]", "Password must contain at least one special character."),
]


def validate_password_strength(password: str) -> list[str]:
    """Return a list of validation error messages (empty when valid)."""
    errors: list[str] = []
    for pattern, message in _PASSWORD_RULES:
        if not re.search(pattern, password):
            errors.append(message)
    return errors


# ── JWT helpers (jose with standard HMAC-SHA256 fallback) ────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

try:
    from jose import JWTError, jwt as jose_jwt
    _use_jose = True
except ImportError:
    _use_jose = False
    JWTError = Exception


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def _py_encode_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h_bytes = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_bytes = _b64url_encode(json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"))
    signing_input = f"{h_bytes}.{p_bytes}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_bytes = _b64url_encode(sig)
    return f"{h_bytes}.{p_bytes}.{s_bytes}"


def _py_decode_jwt(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    h_b64, p_b64, s_b64 = parts
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(s_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("JWT signature verification failed")
    payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
    if "exp" in payload and payload["exp"] < datetime.now(timezone.utc).timestamp():
        raise ValueError("JWT has expired")
    return payload


def create_access_token(
    subject: str | uuid.UUID,
    extra_claims: dict | None = None,
) -> str:
    """Create a short‑lived access JWT."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "type": "access",
    }
    if extra_claims:
        claims.update(extra_claims)
    if _use_jose:
        return jose_jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return _py_encode_jwt(claims, settings.SECRET_KEY)


def create_refresh_token(subject: str | uuid.UUID) -> str:
    """Create a long‑lived refresh JWT."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
        "type": "refresh",
    }
    if _use_jose:
        return jose_jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return _py_encode_jwt(claims, settings.SECRET_KEY)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT, raising on failure."""
    try:
        if _use_jose:
            return jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return _py_decode_jwt(token, settings.SECRET_KEY)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Decode a JWT and assert its type claim matches expected_type."""
    payload = decode_token(token)
    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type. Expected '{expected_type}'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ── FastAPI dependencies ────────────────────────────────────────────────────
async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    access_token: Annotated[Optional[str], Cookie(alias="access_token")] = None,
    db: AsyncSession = Depends(get_db),
):
    """Extract authenticated user from Bearer header or cookie."""
    from doc_assistant.app.models.user import User

    raw_token = token or access_token
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(raw_token, expected_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return user


def require_role(*allowed_roles: str) -> Callable:
    """Dependency factory restricting access to users with specific roles."""
    async def _role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted.",
            )
        return current_user

    return _role_checker
