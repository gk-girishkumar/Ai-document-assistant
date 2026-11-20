"""Authentication service handling user creation, verification, and token issuing."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_assistant.app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from doc_assistant.app.models.user import User


class AuthService:
    """Service handling user authentication and registration."""

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user by email."""
        result = await db.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user by UUID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @classmethod
    async def create_user(
        cls,
        db: AsyncSession,
        email: str,
        password: str,
        role: str = "user",
    ) -> User:
        """Create and persist a new user."""
        hashed = hash_password(password)
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed,
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @classmethod
    async def authenticate_user(
        cls,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Optional[User]:
        """Verify user credentials and return User if valid."""
        user = await cls.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_tokens(user_id: uuid.UUID, role: str) -> tuple[str, str]:
        """Generate access and refresh tokens for user."""
        access_token = create_access_token(
            subject=user_id,
            extra_claims={"role": role},
        )
        refresh_token = create_refresh_token(subject=user_id)
        return access_token, refresh_token

    @staticmethod
    def validate_refresh_token(token: str) -> str:
        """Validate refresh token and return the user UUID string."""
        payload = verify_token(token, expected_type="refresh")
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Invalid refresh token: missing sub")
        return sub
