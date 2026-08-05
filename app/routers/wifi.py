
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_family_member
from app.models import TrustedNetwork, User, WifiStatus
from app.schemas import TrustedNetworkCreate, WifiOut, WifiUpdate
from services.wifi import WifiService

router = APIRouter(prefix="/api", tags=["wifi"])



@router.post("/wifi")
async def update_wifi(body: WifiUpdate, tasks: BackgroundTasks,
                      user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    trusted = await db.execute(
        select(TrustedNetwork.id).where(
            TrustedNetwork.family_id == body.family_id,
            TrustedNetwork.bssid == body.bssid,
        )
    )
    is_trusted = trusted.first() is not None

    stmt = insert(WifiStatus).values(
        user_id=user.id, family_id=body.family_id, ssid=body.ssid,
        bssid=body.bssid, is_trusted=is_trusted, updated_at=func.now(),
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=["user_id", "family_id"],
            set_={
                "ssid": stmt.excluded.ssid,
                "bssid": stmt.excluded.bssid,
                "is_trusted": stmt.excluded.is_trusted,
                "updated_at": func.now(),
            },
        )
    )
    await db.commit()

    if not is_trusted:
        tasks.add_task(WifiService.alert_unknown_wifi, body.family_id, user.id, body.ssid)

    return {"is_trusted": is_trusted}


@router.get("/families/{id}/wifi", response_model=list[WifiOut])
async def get_family_wifi(family_id: uuid.UUID = Depends(require_family_member),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WifiStatus, User.name, User.avatar_url)
        .join(User, User.id == WifiStatus.user_id)
        .where(WifiStatus.family_id == family_id)
    )
    return [
        WifiOut(
            id=w.id, user_id=w.user_id, family_id=w.family_id, ssid=w.ssid,
            bssid=w.bssid, is_trusted=w.is_trusted, updated_at=w.updated_at,
            user_name=name, user_avatar_url=avatar,
        )
        for w, name, avatar in result.all()
    ]


@router.post("/families/{id}/wifi/trusted", status_code=201)
async def add_trusted_network(body: TrustedNetworkCreate,
                              family_id: uuid.UUID = Depends(require_family_member),
                              db: AsyncSession = Depends(get_db)):
    stmt = insert(TrustedNetwork).values(
        family_id=family_id, ssid=body.ssid, bssid=body.bssid, label=body.label
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=["family_id", "bssid"],
            set_={"ssid": stmt.excluded.ssid, "label": stmt.excluded.label},
        )
    )
    await db.commit()
    return {"message": "network added as trusted"}


@router.delete("/families/{id}/wifi/trusted")
async def remove_trusted_network(bssid: str = Query(...),
                                 family_id: uuid.UUID = Depends(require_family_member),
                                 db: AsyncSession = Depends(get_db)):
    await db.execute(
        delete(TrustedNetwork).where(
            TrustedNetwork.family_id == family_id, TrustedNetwork.bssid == bssid
        )
    )
    await db.commit()
    return {"message": "network removed"}