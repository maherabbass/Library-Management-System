from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = "postgresql+asyncpg://postgres:testPostgres@localhost:5433/library"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # FRONTEND_URL is used for the OAuth callback redirect and as the default
    # CORS origin.  Set it to the primary deployed frontend URL.
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # Optional extra CORS origins, comma-separated.
    # Useful to allow localhost during development alongside a deployed frontend.
    # Example: "http://localhost:5173,http://localhost:4173"
    EXTRA_CORS_ORIGINS: str = ""

    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        """All allowed CORS origins: FRONTEND_URL + any EXTRA_CORS_ORIGINS."""
        origins = [self.FRONTEND_URL]
        for origin in self.EXTRA_CORS_ORIGINS.split(","):
            stripped = origin.strip()
            if stripped and stripped not in origins:
                origins.append(stripped)
        return origins


settings = Settings()
