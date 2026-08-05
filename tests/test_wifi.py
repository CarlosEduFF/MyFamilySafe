from httpx import AsyncClient
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Alert
from services.wifi import WifiService


async def _create_family(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/families", json={"name": "Familia"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_update_wifi_unknown_network_is_not_trusted(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    resp = await client.post("/api/wifi", json={
        "family_id": family["id"], "ssid": "VizinhoWifi", "bssid": "AA:BB:CC:00:00:01",
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_trusted"] is False


async def test_update_wifi_trusted_network(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    await client.post(f"/api/families/{family['id']}/wifi/trusted", json={
        "ssid": "CasaWifi", "bssid": "AA:BB:CC:00:00:02", "label": "Casa",
    }, headers=headers)

    resp = await client.post("/api/wifi", json={
        "family_id": family["id"], "ssid": "CasaWifi", "bssid": "AA:BB:CC:00:00:02",
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_trusted"] is True


async def test_alert_unknown_wifi_creates_alert(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)
    user_id = user["user"]["id"]

    await WifiService.alert_unknown_wifi(family["id"], user_id, "RedeDesconhecida")

    async with SessionLocal() as db:
        alerts = (await db.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].type == "unknown_wifi"


async def test_remove_trusted_network(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    await client.post(f"/api/families/{family['id']}/wifi/trusted", json={
        "ssid": "CasaWifi", "bssid": "AA:BB:CC:00:00:03", "label": "Casa",
    }, headers=headers)

    resp = await client.delete(
        f"/api/families/{family['id']}/wifi/trusted?bssid=AA:BB:CC:00:00:03",
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.post("/api/wifi", json={
        "family_id": family["id"], "ssid": "CasaWifi", "bssid": "AA:BB:CC:00:00:03",
    }, headers=headers)
    assert resp.json()["is_trusted"] is False
