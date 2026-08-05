from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# NÃO copie o pool_size=25 do Go (database.go:30): lá era um processo só, contra
# conexão direta. No Render + Supabase o orçamento de conexões é compartilhado
# entre workers e o free tier do Supabase dá ~60 no total. Ver "Deploy" no plano.
#
# pool_recycle=300: o pooler do Supabase derruba conexões ociosas, e uma conexão
# morta no pool causa erro na primeira request depois de um período parado.
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "ssl": None if settings.db_ssl == "disable" else settings.db_ssl,
        # O Supabase faz cache de plano no lado do servidor; nomes estáticos de
        # prepared statement colidem entre conexões do pooler.
        "statement_cache_size": 0,
        "server_settings": {"application_name": "myfamilysafe-api"},
    },
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session