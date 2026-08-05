from httpx import AsyncClient

from services.alerts import AlertsService
from app.database import SessionLocal


async def _create_family(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/families", json={"name": "Familia"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_get_alerts_lists_family_alerts(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)
    user_id = user["user"]["id"]

    async with SessionLocal() as db:
        await AlertsService.create_alert(db, family["id"], user_id,
                                          "unknown_wifi", "Rede desconhecida")

    resp = await client.get(f"/api/families/{family['id']}/alerts", headers=headers)
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "unknown_wifi"
    assert alerts[0]["is_read"] is False


async def test_mark_alert_read_requires_family_membership(client, register_user, auth_headers):
    """Correção #6: o Go marcava qualquer alerta como lido, sem checar nada."""
    owner = await register_user(email="owner-alert@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)
    owner_id = owner["user"]["id"]

    async with SessionLocal() as db:
        await AlertsService.create_alert(db, family["id"], owner_id,
                                          "unknown_wifi", "Rede desconhecida")

    listed = await client.get(f"/api/families/{family['id']}/alerts", headers=owner_headers)
    alert_id = listed.json()[0]["id"]

    outsider = await register_user(email="outsider-alert@example.com")
    outsider_headers = auth_headers(outsider["access_token"])

    resp = await client.put(f"/api/alerts/{alert_id}/read", headers=outsider_headers)
    assert resp.status_code == 403

    resp = await client.put(f"/api/alerts/{alert_id}/read", headers=owner_headers)
    assert resp.status_code == 200

    listed = await client.get(f"/api/families/{family['id']}/alerts", headers=owner_headers)
    assert listed.json()[0]["is_read"] is True


async def test_mark_alert_read_not_found(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    resp = await client.put(
        "/api/alerts/00000000-0000-0000-0000-000000000000/read", headers=headers,
    )
    assert resp.status_code == 404
