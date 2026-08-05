from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, auth, families, geofences, locations, me, wifi

app = FastAPI(title="MyFamilySafe API", version="1.0.0")

# Correção #4: o Go usava Allow-Origin "*" (middleware.go:55).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(families.router)
app.include_router(locations.router)
app.include_router(wifi.router)
app.include_router(geofences.router)
app.include_router(alerts.router)
app.include_router(me.router)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}