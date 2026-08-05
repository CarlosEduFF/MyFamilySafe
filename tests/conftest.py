import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "myfamilysafe")
os.environ.setdefault("DB_SSL", "disable")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret")

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _reset_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def register_user(client: AsyncClient):
    async def _register(name: str = "Alice", email: str | None = None,
                         password: str = "senha123"):
        email = email or f"{uuid.uuid4().hex[:10]}@example.com"
        resp = await client.post("/auth/register", json={
            "name": name, "email": email, "password": password,
        })
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _register


@pytest.fixture
def auth_headers():
    def _headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return _headers
