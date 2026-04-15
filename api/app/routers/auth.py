"""Auth router — register, login, JWT tokens."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import generate_api_key
from app.models.auth import ApiKey, UserAccount
from app.services.stripe_service import get_plan_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72


def _create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(UTC) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm=JWT_ALGORITHM)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ---------- Schemas -------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    company_name: str | None = None


class RegisterResponse(BaseModel):
    token: str
    user: UserInfo
    api_key: str  # plain key, shown only once


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


class UserInfo(BaseModel):
    id: int
    email: str
    plan: str
    company_name: str | None


# ---------- Endpoints -----------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RegisterResponse:
    """Create a new user account with a Flex plan API key."""
    # Check duplicate
    existing = await db.execute(
        select(UserAccount).where(UserAccount.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています")

    # Create user
    user = UserAccount(
        email=body.email,
        password_hash=_hash_password(body.password),
        plan="flex",
        company_name=body.company_name,
    )
    db.add(user)
    await db.flush()  # get user.id

    # Create initial API key
    plan_cfg = get_plan_config("flex")
    plain_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        plan="flex",
        monthly_limit=plan_cfg.monthly_limit,
        rate_per_sec=plan_cfg.rate_per_sec,
    )
    db.add(api_key)
    await db.flush()

    token = _create_token(user.id, user.email)

    return RegisterResponse(
        token=token,
        user=UserInfo(
            id=user.id,
            email=user.email,
            plan=user.plan,
            company_name=user.company_name,
        ),
        api_key=plain_key,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> LoginResponse:
    """Authenticate and return a JWT token."""
    stmt = select(UserAccount).where(UserAccount.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")

    token = _create_token(user.id, user.email)

    return LoginResponse(
        token=token,
        user=UserInfo(
            id=user.id,
            email=user.email,
            plan=user.plan,
            company_name=user.company_name,
        ),
    )
