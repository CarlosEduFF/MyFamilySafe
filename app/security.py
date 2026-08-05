from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.config import settings

# Os hashes gerados pelo bcrypt do Go são lidos por este contexto sem alteração —
# nenhum usuário precisa resetar a senha.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(user_id: str, email: str, secret: str, expires_in: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_access_token(user_id: str, email: str) -> str:
    return _encode(user_id, email, settings.jwt_secret,
                   settings.access_token_expire_seconds)


def create_refresh_token(user_id: str, email: str) -> str:
    return _encode(user_id, email, settings.jwt_refresh_secret,
                   settings.refresh_token_expire_seconds)


def decode_token(token: str, *, refresh: bool = False) -> dict:
    """Levanta jwt.PyJWTError se inválido/expirado.

    algorithms=[ALGORITHM] fecha a correção #5: o RefreshToken do Go (auth.go:131)
    não validava o método de assinatura.
    """
    secret = settings.jwt_refresh_secret if refresh else settings.jwt_secret
    return jwt.decode(token, secret, algorithms=[ALGORITHM])