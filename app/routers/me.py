from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import UpdateMeRequest, UserOut

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("", response_model=UserOut)
async def update_me(body: UpdateMeRequest, user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    # Patch parcial: só sobrescreve o que veio. Equivale ao COALESCE/NULLIF
    # de handler.go:54 — `name` vazio não apaga o nome atual.
    if body.name:
        user.name = body.name
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.fcm_token is not None:
        user.fcm_token = body.fcm_token

    user.updated_at = func.now()
    await db.commit()
    await db.refresh(user)
    return user