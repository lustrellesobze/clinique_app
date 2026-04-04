from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/clinique_db"
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MTN_MOMO_API_KEY: str = ""
    ORANGE_MONEY_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587


settings = Settings()
