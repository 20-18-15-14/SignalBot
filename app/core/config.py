from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./signal_osint.db"
    default_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    openai_embedding_model: str = "text-embedding-3-small"
    signal_api_base_url: str = "http://localhost:8080"
    signal_bot_number: str = ""
    enable_group_auto_reply: bool = False
    group_auto_reply_only_authorized: bool = True
    group_auto_reply_require_question: bool = False
    enable_dm_ephemeral_memory: bool = True
    enable_dm_storage_minimal: bool = True
    auth_membership_ttl_days: int = 30
    web_search_enabled: bool = True
    web_search_max_results: int = 5
    web_search_timeout_seconds: int = 15
    openai_request_timeout_seconds: int = 45
    signal_webhook_secret: str = ""
    admin_api_token: str = ""
    admin_api_tokens: str = ""
    embedding_dimensions: int = Field(default=1536)
    dm_rate_limit_count: int = 5
    dm_rate_limit_window_seconds: int = 60
    group_rate_limit_count: int = 2
    group_rate_limit_window_seconds: int = 60
    chunk_max_chars: int = 3500
    chunk_max_messages: int = 50
    knowledge_chunk_max_chars: int = 2000
    ingestion_worker_enabled: bool = True
    ingestion_worker_poll_seconds: int = 3
    ingestion_worker_batch_size: int = 5

    def admin_token_list(self) -> list[str]:
        raw = self.admin_api_tokens or self.admin_api_token
        return [token.strip() for token in raw.split(",") if token.strip()]

    def group_auto_reply_scopes(self) -> list[str]:
        return ["global", "group"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
