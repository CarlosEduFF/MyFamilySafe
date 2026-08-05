from httpx import AsyncClient


async def _create_family(client: AsyncClient, headers: dict, name: str = "Familia") -> dict:
    resp = await client.post("/api/families", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_family_adds_owner_as_admin(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    family = await _create_family(client, headers)

    resp = await client.get(f"/api/families/{family['id']}/members", headers=headers)
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["user_id"] == user["user"]["id"]


async def test_join_family_with_valid_invite_code(client, register_user, auth_headers):
    owner = await register_user(email="owner@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)

    joiner = await register_user(email="joiner@example.com")
    joiner_headers = auth_headers(joiner["access_token"])

    resp = await client.post("/api/families/join",
                              json={"invite_code": family["invite_code"]},
                              headers=joiner_headers)
    assert resp.status_code == 200
    assert resp.json()["family_id"] == family["id"]


async def test_join_family_invalid_invite_code(client, register_user, auth_headers):
    user = await register_user()
    headers = auth_headers(user["access_token"])
    resp = await client.post("/api/families/join",
                              json={"invite_code": "does-not-exist"},
                              headers=headers)
    assert resp.status_code == 404


async def test_join_family_already_member_conflicts(client, register_user, auth_headers):
    owner = await register_user(email="owner2@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)

    resp = await client.post("/api/families/join",
                              json={"invite_code": family["invite_code"]},
                              headers=owner_headers)
    assert resp.status_code == 409


async def test_get_family_requires_membership(client, register_user, auth_headers):
    owner = await register_user(email="owner3@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)

    outsider = await register_user(email="outsider@example.com")
    outsider_headers = auth_headers(outsider["access_token"])

    resp = await client.get(f"/api/families/{family['id']}", headers=outsider_headers)
    assert resp.status_code == 403


async def test_remove_member_only_owner_or_self(client, register_user, auth_headers):
    owner = await register_user(email="owner4@example.com")
    owner_headers = auth_headers(owner["access_token"])
    family = await _create_family(client, owner_headers)

    member = await register_user(email="member4@example.com")
    member_headers = auth_headers(member["access_token"])
    await client.post("/api/families/join",
                       json={"invite_code": family["invite_code"]},
                       headers=member_headers)

    other = await register_user(email="other4@example.com")
    other_headers = auth_headers(other["access_token"])
    await client.post("/api/families/join",
                       json={"invite_code": family["invite_code"]},
                       headers=other_headers)

    resp = await client.delete(
        f"/api/families/{family['id']}/members/{member['user']['id']}",
        headers=other_headers,
    )
    assert resp.status_code == 403

    resp = await client.delete(
        f"/api/families/{family['id']}/members/{member['user']['id']}",
        headers=owner_headers,
    )
    assert resp.status_code == 200
