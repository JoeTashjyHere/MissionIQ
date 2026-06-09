"""Application configuration sourced from environment variables.

All settings are validated by Pydantic. If the platform cannot start safely,
this module raises before any HTTP route is mounted.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: Literal["development", "test", "staging", "production"] = Field(
        default="development", alias="MIQ_ENV"
    )
    log_level: str = Field(default="INFO", alias="MIQ_LOG_LEVEL")
    backend_host: str = Field(default="0.0.0.0", alias="MIQ_BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="MIQ_BACKEND_PORT")
    frontend_origin: str = Field(
        default="http://localhost:3000", alias="MIQ_FRONTEND_ORIGIN"
    )

    database_url: str = Field(alias="MIQ_DATABASE_URL")
    database_url_sync: str = Field(alias="MIQ_DATABASE_URL_SYNC")

    jwt_secret: str = Field(alias="MIQ_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="MIQ_JWT_ALGORITHM")
    access_token_ttl_minutes: int = Field(default=30, alias="MIQ_ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=14, alias="MIQ_REFRESH_TOKEN_TTL_DAYS")

    blob_store: Literal["local", "s3"] = Field(default="local", alias="MIQ_BLOB_STORE")
    blob_local_root: str = Field(default="./var/blobs", alias="MIQ_BLOB_LOCAL_ROOT")
    s3_bucket: str | None = Field(default=None, alias="MIQ_S3_BUCKET")
    s3_region: str | None = Field(default=None, alias="MIQ_S3_REGION")
    s3_prefix: str = Field(default="missioniq/", alias="MIQ_S3_PREFIX")

    llm_provider_order: str = Field(
        default="local_stub,openai,anthropic", alias="MIQ_LLM_PROVIDER_ORDER"
    )
    llm_default_model: str = Field(default="auto", alias="MIQ_LLM_DEFAULT_MODEL")
    embedding_provider: str = Field(default="local_stub", alias="MIQ_EMBEDDING_PROVIDER")
    embedding_dim: int = Field(default=1536, alias="MIQ_EMBEDDING_DIM")

    openai_training_opt_out_ack: bool = Field(
        default=True, alias="MIQ_OPENAI_TRAINING_OPT_OUT_ACK"
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_default_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_DEFAULT_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_default_model: str = Field(
        default="claude-3-5-sonnet-latest", alias="ANTHROPIC_DEFAULT_MODEL"
    )

    aws_bedrock_region: str = Field(default="us-east-1", alias="AWS_BEDROCK_REGION")
    aws_bedrock_default_model: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        alias="AWS_BEDROCK_DEFAULT_MODEL",
    )
    aws_bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0", alias="AWS_BEDROCK_EMBEDDING_MODEL"
    )

    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(
        default="2024-10-21", alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_chat_deployment: str | None = Field(
        default=None, alias="AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    azure_openai_embedding_deployment: str | None = Field(
        default=None, alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    )

    sam_gov_api_key: str | None = Field(default=None, alias="SAM_GOV_API_KEY")
    sam_gov_base_url: str = Field(default="https://api.sam.gov", alias="SAM_GOV_BASE_URL")

    # Connector credential encryption key (urlsafe base64, 32 bytes). When
    # unset, a key is derived from MIQ_JWT_SECRET (dev convenience; set a
    # dedicated key in production so secrets and signing keys rotate apart).
    credential_key: str | None = Field(default=None, alias="MIQ_CREDENTIAL_KEY")

    max_upload_bytes: int = Field(default=52_428_800, alias="MIQ_MAX_UPLOAD_BYTES")
    workspace_storage_quota_bytes: int = Field(
        default=5_368_709_120, alias="MIQ_WORKSPACE_STORAGE_QUOTA_BYTES"
    )

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if not value or len(value) < 16:
            raise ValueError(
                "MIQ_JWT_SECRET must be set to a long random string (>= 16 chars)."
            )
        return value

    @property
    def provider_order(self) -> list[str]:
        return [p.strip() for p in self.llm_provider_order.split(",") if p.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_origin] if self.frontend_origin else []


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
