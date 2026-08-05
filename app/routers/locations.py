import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, is_family_member, require_family_member
from app.models import FamilyMember, Location, User
from app.schemas import LocationCreate, LocationOut, MemberLocationOut, UserOut
from services.geofencing import GeofencingService

router = APIRouter(prefix="/api", tags=["locations"])

FAMILY_LOCATIONS_SQL = text("""
    SELECT u.id, u.name, u.email, u.avatar_url, u.created_at, u.updated_at,
           l.id AS loc_id, l.latitude, l.longitude, l.accuracy,
           l.address, l.created_at AS loc_created_at
    FROM family_members fm
    JOIN users u ON u.id = fm.user_id
    LEFT JOIN LATERAL (
        SELECT * FROM locations WHERE user_id = u.id
        ORDER BY created_at DESC LIMIT 1
    ) l ON TRUE
    WHERE fm.family_id = :family_id
    ORDER BY u.name ASC
""")



@router.post("/location", response_model=LocationOut,
             status_code=status.HTTP_201_CREATED)
async def update_location(body: LocationCreate, tasks: BackgroundTasks,
                          user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    if not await is_family_member(db, body.family_id, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "not a member of this family")

    loc = Location(user_id=user.id, latitude=body.latitude, longitude=body.longitude,
                   accuracy=body.accuracy, address=body.address)
    db.add(loc)
    await db.commit()
    await db.refresh(loc)

    tasks.add_task(GeofencingService.check_geofences, body.family_id, user.id,
                   body.latitude, body.longitude)
    return loc


@router.get("/families/{id}/locations", response_model=list[MemberLocationOut])
async def get_family_locations(family_id: uuid.UUID = Depends(require_family_member),
                               db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(FAMILY_LOCATIONS_SQL, {"family_id": family_id})).mappings()
    threshold = datetime.now(UTC) - timedelta(seconds=settings.online_threshold_seconds)

    out: list[MemberLocationOut] = []
    for r in rows:
        member = MemberLocationOut(
            user=UserOut(
                id=r["id"], name=r["name"], email=r["email"],
                avatar_url=r["avatar_url"],
                created_at=r["created_at"], updated_at=r["updated_at"],
            )
        )
        if r["loc_id"] is not None:
            member.location = LocationOut(
                id=r["loc_id"], user_id=r["id"],
                latitude=r["latitude"], longitude=r["longitude"],
                accuracy=r["accuracy"], address=r["address"],
                created_at=r["loc_created_at"],
            )
            member.last_seen = r["loc_created_at"]
            member.is_online = r["loc_created_at"] > threshold
        out.append(member)
    return out


@router.get("/members/{user_id}/location/history", response_model=list[LocationOut])
async def get_location_history(user_id: uuid.UUID,
                               user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    if user_id != user.id:
        # Precisam compartilhar ao menos uma família (resources.go:126).
        a, b = FamilyMember.__table__.alias("a"), FamilyMember.__table__.alias("b")
        shared = await db.execute(
            select(a.c.family_id)
            .join(b, a.c.family_id == b.c.family_id)
            .where(a.c.user_id == user.id, b.c.user_id == user_id)
            .limit(1)
        )
        if shared.first() is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized")

    result = await db.execute(
        select(Location).where(Location.user_id == user_id)
        .order_by(Location.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())
