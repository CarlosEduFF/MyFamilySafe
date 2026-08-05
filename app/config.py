from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8080

    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    db_ssl: str = "require"   # 'disable' para o Postgres local do compose
    db_pool_size: int = 5

    jwt_secret: str
    jwt_refresh_secret: str

    access_token_expire_seconds: int = 3600        # 1h, como o Go
    refresh_token_expire_seconds: int = 30 * 86400  # 30 dias

    online_threshold_seconds: int = 300  # resources.go:85
    cors_origins: str = ""

    @property
    def database_url(self) -> str:
        # quote_plus: senhas do Supabase costumam ter @ / # / ? etc., que quebram
        # o parsing da URL se não forem escapadas.
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()