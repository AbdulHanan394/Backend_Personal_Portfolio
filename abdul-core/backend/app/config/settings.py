"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Runtime configuration for the Abdul Core service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(min_length=16)
    api_v1_prefix: str = "/api/v1"
    cors_allowed_origins: str

    database_url: str
    database_url_sync: str
    redis_url: str

    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "abdul_activities"

    portfolio_api_key: str = Field(min_length=8)
    admin_username: str = "abdul"
    admin_password_hash: str = Field(min_length=1)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    github_token: str = ""
    github_username: str = "AbdulHanan394"

    # ---------- GitHub ----------
    github_api_url: str = "https://api.github.com"
    github_max_pages: int = 5
    github_events_per_page: int = 100
 # ---------- GitHub Model ----------
 

    github_models_api_key: str = ""
    github_models_endpoint: str = "https://models.inference.ai.azure.com"
    github_llm_model: str = "gpt-4o"

    x_bearer_token: str = ""
    x_username: str = "AbdulHanan394"
    linkedin_enabled: bool = False

    gemini_api_key: str | None = None
    llm_provider: str = "gemini"

    anthropic_api_key: str = ""
    llm_model: str = "gemini-3.5-flash"
    llm_max_tokens: int = 1000

    # ---------- AI ----------
    ai_enabled: bool = True
    ai_summary_max_length: int = 400

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ---------- Embeddings ----------
    embedding_enabled: bool = True
    embedding_chunk_size: int = 1000

    # ---------- RAG ----------
    rag_search_limit: int = 8
    rag_fetch_multiplier: int = 2
    rag_max_distance: float = 4.0

    # github_sync_cron: str = "0 */6 * * *" real one
    github_sync_cron: str = "*/5 * * * *"  #testing one

    x_sync_cron: str = "0 */6 * * *"
    scheduler_timezone: str = "Asia/Karachi"

    rate_limit_per_minute: int = 60

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        """Return comma-separated CORS origins as a list."""

        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()