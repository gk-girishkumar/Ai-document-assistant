"""User Pydantic v2 schemas."""

from __future__ import annotations

import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, Field

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except ImportError:
    from typing import Annotated
    EmailStr = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class UserResponse(BaseModel):
    """Public representation of a user (never exposes password)."""

    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Fields a user (or admin) may update."""

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    role: Optional[str] = None
    is_active: Optional[bool] = None
