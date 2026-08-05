from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert


class AlertsService:
    @staticmethod
    async def create_alert(db: AsyncSession, family_id, user_id,
                            alert_type: str, message: str) -> None:
        db.add(Alert(family_id=family_id, user_id=user_id,
                      type=alert_type, message=message))
        await db.commit()
