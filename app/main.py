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


@app.head("/ping")
@app.get("/ping")
async def ping():
    """Keep-alive para o free tier do Render, que suspende o serviço após
    ~15 min sem tráfego HTTP externo.

    Deliberadamente não toca no banco: o objetivo é só produzir tráfego de
    entrada. Bater num endpoint que consulta o Postgres a cada poucos
    minutos gastaria cota do Supabase sem necessidade.

    Precisa ser chamado de FORA do processo (cron externo ou o próprio app).
    Um self-ping interno não funciona: quando o Render suspende o serviço,
    qualquer timer interno é suspenso junto.
    """
    return {"status": "alive"}