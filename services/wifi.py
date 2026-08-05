import uuid

from app.database import SessionLocal
from services.alerts import AlertsService


class WifiService:
    @staticmethod
    async def alert_unknown_wifi(family_id: uuid.UUID, user_id: uuid.UUID, ssid: str) -> None:
        async with SessionLocal() as db:
            await AlertsService.create_alert(
                db, family_id, user_id, "unknown_wifi",
                f"Conectado em rede WiFi desconhecida: {ssid}",
            )
