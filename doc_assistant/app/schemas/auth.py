"""Authentication Pydantic v2 schemas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except ImportError:
    from typing import Annotated
    EmailStr = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        import re

        checks: list[tuple[str, str]] = [
            (r"[A-Z]", "Password must contain at least one uppercase letter."),
            (r"[a-z]", "Password must contain at least one lowercase letter."),
            (r"\d", "Password must contain at least one digit."),
            (
                r"[!@#$%^&*()_+\-=\[\]{}|;:'\",.<>?/`~\\]",
                "Password must contain at least one special character.",
            ),
        ]
        errors: list[str] = [msg for pattern, msg in checks if not re.search(pattern, value)]
        if errors:
            raise ValueError(" ".join(errors))
        return value


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token pair returned on successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token payload used internally."""

    sub: Optional[str] = None
    type: Optional[str] = None
    exp: Optional[int] = None
