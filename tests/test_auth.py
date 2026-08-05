from httpx import AsyncClient


async def test_register_returns_tokens_and_no_family(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "name": "Alice", "email": "alice@example.com", "password": "senha123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["family_id"] is None
    assert "password_hash" not in body["user"]


async def test_register_duplicate_email_conflicts(client: AsyncClient, register_user):
    await register_user(email="dup@example.com")
    resp = await client.post("/auth/register", json={
        "name": "Bob", "email": "dup@example.com", "password": "senha123",
    })
    assert resp.status_code == 409


async def test_login_returns_first_family_id(client: AsyncClient, register_user, auth_headers):
    user = await register_user(email="carol@example.com")
    headers = auth_headers(user["access_token"])

    resp = await client.post("/api/families", json={"name": "Familia"}, headers=headers)
    assert resp.status_code == 201
    family_id = resp.json()["id"]

    resp = await client.post("/auth/login", json={
        "email": "carol@example.com", "password": "senha123",
    })
    assert resp.status_code == 200
    assert resp.json()["family_id"] == family_id


async def test_login_invalid_credentials(client: AsyncClient, register_user):
    await register_user(email="dave@example.com")
    resp = await client.post("/auth/login", json={
        "email": "dave@example.com", "password": "errada",
    })
    assert resp.status_code == 401


async def test_refresh_token_roundtrip(client: AsyncClient, register_user):
    user = await register_user(email="erin@example.com")
    resp = await client.post("/auth/refresh", json={
        "refresh_token": user["refresh_token"],
    })
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, register_user):
    """Correção #5: o refresh não deve aceitar um access_token no lugar."""
    user = await register_user(email="frank@example.com")
    resp = await client.post("/auth/refresh", json={
        "refresh_token": user["access_token"],
    })
    assert resp.status_code == 401
