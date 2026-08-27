"""Application configuration — everything lives in environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Override anything via environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "AgentForge AI"
    environment: str = "development"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    api_prefix: str = "/api"

    # Database
    database_url: str = "sqlite:///./agentforge.db"

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""

    # Tools
    tavily_api_key: str = ""

    # Redis / queue (used when celery/redis enabled)
    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_minute: int = 5

    # CORS
    cors_origins: str = "*"  # comma-separated list or "*"

    # Scheduler
    scheduler_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
