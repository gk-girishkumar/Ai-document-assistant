"""Users API router."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc_assistant.app.core.database import get_db
from doc_assistant.app.core.security import get_current_user, hash_password, validate_password_strength
from doc_assistant.app.models.user import User
from doc_assistant.app.schemas.user import UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile information of the currently authenticated user."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update profile information for the current user."""
    if payload.email:
        current_user.email = payload.email.lower().strip()

    if payload.password:
        errors = validate_password_strength(payload.password)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="; ".join(errors),
            )
        current_user.hashed_password = hash_password(payload.password)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    logger.info("User profile updated", extra={"user_id": str(current_user.id)})
    return current_user
