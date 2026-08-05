import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Family, FamilyMember, User
from app.schemas import (
    AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, UserOut,
)
from app.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.config import settings
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

async def _auth_response(db: AsyncSession, user: User) -> AuthResponse:
    family_id = await AuthService.first_family_id(db, user.id)
    user_out = UserOut.model_validate(user)
    return AuthResponse(
        access_token=create_access_token(str(user.id), user.email),
        refresh_token=create_refresh_token(str(user.id), user.email),
        expires_in=settings.access_token_expire_seconds,
        user=user_out.model_copy(update={"family_id": family_id}),
        family_id=family_id,
    )


@router.post("/register", response_model=AuthResponse,
             status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(User.id).where(User.email == req.email))
    if exists.first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already in use")

    user = User(name=req.name, email=req.email,
                password_hash=hash_password(req.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _auth_response(db, user)


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return await _auth_response(db, user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token, refresh=True)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "invalid or expired refresh token") from None

    user = await db.get(User, uuid.UUID(payload["user_id"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return await _auth_response(db, user)