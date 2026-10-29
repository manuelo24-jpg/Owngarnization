import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "dev-secret-key-owngarnization-2026-replace-in-prod"
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./owngarnization.db"
    PORT: int = 8000
    VAPID_PUBLIC_KEY: str = "BO6Wk9w1uBqq5R6qSIUAejta9KJ3cmw7XNzw6t3ilj-AfFnLGxEzg5KB7yy8fq_3o8fXvXwkRwv3FM0GqjTvxSo"
    VAPID_PRIVATE_KEY: str = "oNVcwaHQIQmxNVngytU9w_5takwW4_iVYwxijN7K2Ag"
    VAPID_SUBJECT: str = "mailto:admin@owngarnization.example.com"
    CRON_SECRET: str = "dev-cron-secret-owngarnization"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def normalized_database_url(self) -> str:
        # Render / Heroku / Neon might provide postgres:// instead of postgresql://
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
