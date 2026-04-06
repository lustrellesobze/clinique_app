from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Toujours backend/.env, même si Uvicorn est lancé depuis un autre répertoire.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MySQL / MariaDB (WAMP) — utilisateur root, mot de passe souvent vide (voir .env.example)
    DATABASE_URL: str = (
        "mysql+pymysql://root@127.0.0.1:3306/clinique_db?charset=utf8mb4"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        return v.strip().removeprefix("\ufeff")

    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MTN_MOMO_API_KEY: str = ""
    ORANGE_MONEY_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587


settings = Settings()
