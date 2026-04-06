from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def verify_password(plain: str, hashed: str) -> bool:
    """Retourne False si le hash est absent ou illisible (évite un 500 au login)."""
    if not hashed or not isinstance(hashed, str):
        return False
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["type"] = ACCESS_TOKEN_TYPE
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = int(expire.timestamp())
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["type"] = REFRESH_TOKEN_TYPE
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode["exp"] = int(expire.timestamp())
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise ValueError("Token invalide ou expiré")


def decode_access_token(token: str) -> dict:
    """JWT d’accès (pas un refresh). Les anciens tokens sans claim `type` restent acceptés."""
    payload = decode_token(token)
    t = payload.get("type")
    if t == REFRESH_TOKEN_TYPE:
        raise ValueError("Token d’accès requis")
    if t is not None and t != ACCESS_TOKEN_TYPE:
        raise ValueError("Type de token invalide")
    return payload


def decode_refresh_token_payload(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise ValueError("Refresh token invalide")
    return payload
