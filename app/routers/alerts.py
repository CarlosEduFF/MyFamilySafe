import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, is_family_member, require_family_member
from app.models import Alert, User
from app.schemas import AlertOut

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/families/{id}/alerts", response_model=list[AlertOut])
async def get_alerts(family_id: uuid.UUID = Depends(require_family_member),
                     db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Alert, User.name, User.avatar_url)
        .join(User, User.id == Alert.user_id)
        .where(Alert.family_id == family_id)
        .order_by(Alert.created_at.desc())
        .limit(50)
    )
    return [
        AlertOut(
            id=a.id, family_id=a.family_id, user_id=a.user_id, type=a.type,
            message=a.message, is_read=a.is_read, created_at=a.created_at,
            user_name=name, user_avatar_url=avatar,
        )
        for a, name, avatar in result.all()
    ]


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: uuid.UUID,
                          user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    """Correção #6: o Go marcava qualquer alerta como lido, sem checar nada."""
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "alert not found")
    if not await is_family_member(db, alert.family_id, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized")

    alert.is_read = True
    await db.commit()
    return {"message": "alert marked as read"}