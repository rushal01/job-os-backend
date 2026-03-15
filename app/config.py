from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    SUPABASE_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:6543/dbname"

    @model_validator(mode="after")
    def _fix_db_url_scheme(self) -> "Settings":
        """Ensure the DB URL uses the asyncpg driver."""
        url = self.SUPABASE_DB_URL
        if url.startswith("postgresql://"):
            self.SUPABASE_DB_URL = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            self.SUPABASE_DB_URL = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return self
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_SERVICE_ROLE_KEY: str = "your-service-role-key"
    SUPABASE_JWT_SECRET: str = "your-jwt-secret"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Storage (Cloudflare R2)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "jobapp-files"
    R2_ENDPOINT_URL: str = ""

    # Encryption
    MASTER_ENCRYPTION_KEY: str = ""

    # Monitoring
    SENTRY_DSN: str = ""

    # Application
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"
    API_VERSION: str = "v1"
    LOG_LEVEL: str = "DEBUG"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="Default rate limit per user per minute")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
