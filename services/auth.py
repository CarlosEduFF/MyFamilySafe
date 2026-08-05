import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FamilyMember


class AuthService:
    @staticmethod
    async def first_family_id(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID | None:
        """Correção #2: o app lê user.family_id no login e o Go nunca o enviava."""
        result = await db.execute(
            select(FamilyMember.family_id)
            .where(FamilyMember.user_id == user_id)
            .order_by(FamilyMember.joined_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()
