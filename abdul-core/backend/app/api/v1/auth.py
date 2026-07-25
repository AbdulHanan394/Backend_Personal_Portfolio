"""Admin authentication endpoints."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.config.settings import get_settings
from app.models.user import User
from app.utils.time import utc_now

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    """Username/password login body."""

    username: str
    password: str


@router.post("/login")
async def login(request: LoginRequest, session: DbSession) -> dict:
    """Authenticate the owner and return a short-lived JWT."""

    user = await session.scalar(select(User).where(User.username == request.username))
    if user is None or not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    settings = get_settings()
    expires_at = utc_now() + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": user.username, "exp": expires_at},
        settings.app_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"data": {"access_token": token, "token_type": "bearer"}}

