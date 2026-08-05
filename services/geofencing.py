import uuid

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Geofence, Location
from app.utils import haversine_distance
from services.alerts import AlertsService


class GeofencingService:
    @staticmethod
    async def check_geofences(family_id: uuid.UUID, user_id: uuid.UUID,
                               lat: float, lon: float) -> None:
        """Correção #3.

        O Go alertava a cada update enquanto o usuário estivesse fora do raio, e nunca
        emitia geofence_enter. Aqui comparamos com a penúltima localização gravada e só
        alertamos na transição dentro↔fora.

        Roda em BackgroundTasks com sessão própria — a do request já foi fechada.
        """
        async with SessionLocal() as db:
            geofences = (
                await db.execute(select(Geofence).where(Geofence.family_id == family_id))
            ).scalars().all()
            if not geofences:
                return

            # offset(1) = a posição anterior; a atual acabou de ser inserida.
            previous = (
                await db.execute(
                    select(Location)
                    .where(Location.user_id == user_id)
                    .order_by(Location.created_at.desc())
                    .offset(1).limit(1)
                )
            ).scalar_one_or_none()

            for g in geofences:
                inside_now = haversine_distance(lat, lon, g.latitude, g.longitude) <= g.radius

                if previous is None:
                    # Primeira posição conhecida: só alerta se já nasce fora.
                    if not inside_now:
                        await AlertsService.create_alert(
                            db, family_id, user_id, "geofence_exit",
                            f"Saiu da zona segura: {g.name}",
                        )
                    continue

                inside_before = haversine_distance(
                    previous.latitude, previous.longitude, g.latitude, g.longitude
                ) <= g.radius

                if inside_before and not inside_now:
                    await AlertsService.create_alert(
                        db, family_id, user_id, "geofence_exit",
                        f"Saiu da zona segura: {g.name}",
                    )
                elif not inside_before and inside_now:
                    await AlertsService.create_alert(
                        db, family_id, user_id, "geofence_enter",
                        f"Chegou na zona segura: {g.name}",
                    )
