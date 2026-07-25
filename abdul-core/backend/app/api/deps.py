"""Shared FastAPI dependencies for auth, sessions, and pagination."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_db_session
from app.models.user import User
from app.schemas.common import PaginationParams

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Pagination = Annotated[PaginationParams, Depends()]


class CurrentUser(BaseModel):
    """Authenticated admin user context."""

    id: UUID
    username: str
    role: str


async def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Require the portfolio API key for public read endpoints."""

    settings = get_settings()
    if x_api_key != settings.portfolio_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


async def require_admin(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Require a valid admin JWT."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    user = await session.scalar(select(User).where(User.username == username))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(id=user.id, username=user.username, role=user.role)

