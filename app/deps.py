import uuid

import jwt
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import FamilyMember, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "missing authorization header")
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "invalid or expired token") from None

    user = await db.get(User, uuid.UUID(payload["user_id"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    return user


async def is_family_member(db: AsyncSession, family_id: uuid.UUID,
                           user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(FamilyMember.user_id).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
        )
    )
    return result.first() is not None


async def require_family_member(
    id: uuid.UUID = Path(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Guard das rotas /api/families/{id}/... — devolve o family_id validado."""
    if not await is_family_member(db, id, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "not a member of this family")
    return id