from httpx import AsyncClient
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Alert, Location
from services.geofencing import GeofencingService

LAT, LON = -23.55, -46.63


async def _create_family(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/families", json={"name": "Familia"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_update_location_persists_and_returns_it(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    resp = await client.post("/api/location", json={
        "family_id": family["id"], "latitude": LAT, "longitude": LON, "accuracy": 5,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["latitude"] == LAT


async def test_update_location_requires_membership(client, register_user, auth_headers):
    owner = await register_user(email="owner-loc@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)

    outsider = await register_user(email="outsider-loc@example.com")
    outsider_headers = auth_headers(outsider["access_token"])

    resp = await client.post("/api/location", json={
        "family_id": family["id"], "latitude": LAT, "longitude": LON, "accuracy": 5,
    }, headers=outsider_headers)
    assert resp.status_code == 403


async def test_get_family_locations_reports_last_position(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    await client.post("/api/location", json={
        "family_id": family["id"], "latitude": LAT, "longitude": LON, "accuracy": 5,
    }, headers=headers)

    resp = await client.get(f"/api/families/{family['id']}/locations", headers=headers)
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["location"]["latitude"] == LAT
    assert members[0]["is_online"] is True


async def test_geofence_transition_enter_then_exit_alerts_once_each(
    client, register_user, auth_headers,
):
    """Correção #3: só alerta na transição dentro<->fora, não em cada update."""
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)
    user_id = user["user"]["id"]

    geo_resp = await client.post(f"/api/families/{family['id']}/geofences", json={
        "name": "Casa", "latitude": LAT, "longitude": LON, "radius": 100,
    }, headers=headers)
    assert geo_resp.status_code == 201

    async def _insert_location(lat: float, lon: float) -> None:
        async with SessionLocal() as db:
            db.add(Location(user_id=user_id, latitude=lat, longitude=lon, accuracy=5))
            await db.commit()

    # 1) Primeira posição: dentro da zona -> nenhum alerta (nasce dentro).
    await _insert_location(LAT, LON)
    await GeofencingService.check_geofences(family["id"], user_id, LAT, LON)

    # 2) Segunda posição: continua dentro -> sem novo alerta.
    await _insert_location(LAT, LON)
    await GeofencingService.check_geofences(family["id"], user_id, LAT, LON)

    # 3) Terceira posição: sai da zona -> 1 alerta geofence_exit.
    far_lat, far_lon = LAT + 1, LON + 1
    await _insert_location(far_lat, far_lon)
    await GeofencingService.check_geofences(family["id"], user_id, far_lat, far_lon)

    # 4) Continua fora -> sem novo alerta.
    await _insert_location(far_lat, far_lon)
    await GeofencingService.check_geofences(family["id"], user_id, far_lat, far_lon)

    # 5) Volta para dentro -> 1 alerta geofence_enter.
    await _insert_location(LAT, LON)
    await GeofencingService.check_geofences(family["id"], user_id, LAT, LON)

    async with SessionLocal() as db:
        alerts = (await db.execute(select(Alert).order_by(Alert.created_at.asc()))).scalars().all()

    types = [a.type for a in alerts]
    assert types == ["geofence_exit", "geofence_enter"]


async def test_get_location_history_requires_shared_family(client, register_user, auth_headers):
    a = await register_user(email="hist-a@example.com")
    a_headers = auth_headers(a["access_token"])

    b = await register_user(email="hist-b@example.com")
    b_headers = auth_headers(b["access_token"])

    resp = await client.get(f"/api/members/{a['user']['id']}/location/history",
                             headers=b_headers)
    assert resp.status_code == 403

    resp = await client.get(f"/api/members/{a['user']['id']}/location/history",
                             headers=a_headers)
    assert resp.status_code == 200
