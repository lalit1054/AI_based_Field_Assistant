from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: str = "dev"
    debug: bool = True
    secret_key: str = "change-me-to-a-random-64-char-string"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/troubleshoot"
    database_url_sync: str = "postgresql+psycopg://app:app@localhost:5432/troubleshoot"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- JWT ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # --- MinIO / S3 ---
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_region: str = "us-east-1"
    minio_bucket_attachments: str = "attachments"
    minio_bucket_log_bundles: str = "log-bundles"
    minio_bucket_kb_sources: str = "kb-sources"
    minio_bucket_qr_sheets: str = "qr-sheets"
    minio_presigned_url_expire_seconds: int = 600

    # --- Loki ---
    loki_url: str = "http://localhost:3100"
    loki_fake: bool = True

    # --- LLM ---
    openai_api_key: str = ""
    triage_model: str = "gpt-4o-mini"
    diagnosis_model: str = "gpt-4o"
    policy_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1024
    embedding_fake: bool = True

    # --- Langfuse ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # --- Notifications ---
    notify_provider: str = "console"
    msg91_auth_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"

    # --- Agent heartbeat auth ---
    agent_heartbeat_keys: str = "DEV-PLANT:dev-agent-key-change-me"

    # --- QR ---
    qr_base_url: str = "http://localhost:5173/a"

    @property
    def agent_heartbeat_key_map(self) -> dict[str, str]:
        """Parse 'PLANT_CODE:key,PLANT_CODE2:key2' into a dict."""
        pairs = [p.strip() for p in self.agent_heartbeat_keys.split(",") if p.strip()]
        return dict(p.split(":", 1) for p in pairs)


@lru_cache
def get_settings() -> Settings:
    return Settings()
