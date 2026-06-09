"""User endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import CurrentUser
from app.schemas.auth import MeResponse, UserResponse
from app.services import auth_service

router = APIRouter()


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> MeResponse:
    memberships = await auth_service.memberships_for(db, user.id)
    return MeResponse(user=UserResponse.model_validate(user), memberships=memberships)
