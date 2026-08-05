from httpx import AsyncClient


async def _create_family(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/families", json={"name": "Familia"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def test_create_geofence_default_radius(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    resp = await client.post(f"/api/families/{family['id']}/geofences", json={
        "name": "Casa", "latitude": -23.5, "longitude": -46.6, "radius": 0,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["radius"] == 200


async def test_create_geofence_custom_radius(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    resp = await client.post(f"/api/families/{family['id']}/geofences", json={
        "name": "Escola", "latitude": -23.5, "longitude": -46.6, "radius": 50,
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["radius"] == 50


async def test_list_and_delete_geofence(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    created = await client.post(f"/api/families/{family['id']}/geofences", json={
        "name": "Casa", "latitude": -23.5, "longitude": -46.6, "radius": 100,
    }, headers=headers)
    geofence_id = created.json()["id"]

    resp = await client.get(f"/api/families/{family['id']}/geofences", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.delete(
        f"/api/families/{family['id']}/geofences/{geofence_id}", headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/families/{family['id']}/geofences", headers=headers)
    assert resp.json() == []


async def test_geofences_require_membership(client, register_user, auth_headers):
    owner = await register_user(email="owner-geo@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)

    outsider = await register_user(email="outsider-geo@example.com")
    outsider_headers = auth_headers(outsider["access_token"])

    resp = await client.get(f"/api/families/{family['id']}/geofences",
                             headers=outsider_headers)
    assert resp.status_code == 403
