import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_family_member
from app.models import Geofence
from app.schemas import GeofenceCreate, GeofenceOut

router = APIRouter(prefix="/api/families", tags=["geofences"])


@router.post("/{id}/geofences", response_model=GeofenceOut,
             status_code=status.HTTP_201_CREATED)
async def create_geofence(body: GeofenceCreate,
                          family_id: uuid.UUID = Depends(require_family_member),
                          db: AsyncSession = Depends(get_db)):
    radius = body.radius if body.radius > 0 else 200  # resources.go:321
    g = Geofence(family_id=family_id, name=body.name, latitude=body.latitude,
                 longitude=body.longitude, radius=radius)
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return g


@router.get("/{id}/geofences", response_model=list[GeofenceOut])
async def get_geofences(family_id: uuid.UUID = Depends(require_family_member),
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Geofence).where(Geofence.family_id == family_id)
        .order_by(Geofence.created_at.asc())
    )
    return list(result.scalars().all())


@router.delete("/{id}/geofences/{geofence_id}")
async def delete_geofence(geofence_id: uuid.UUID,
                          family_id: uuid.UUID = Depends(require_family_member),
                          db: AsyncSession = Depends(get_db)):
    await db.execute(
        delete(Geofence).where(Geofence.id == geofence_id,
                               Geofence.family_id == family_id)
    )
    await db.commit()
    return {"message": "geofence deleted"}