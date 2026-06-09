"""Test fixtures. Most tests run against the deterministic local stub provider
and a SQLite-compatible substitute is not used; tests requiring DB are integration
tests run against the docker-compose Postgres."""
from __future__ import annotations

import os

os.environ.setdefault("MIQ_JWT_SECRET", "test-secret-please-change-test-secret-please-change")
os.environ.setdefault("MIQ_DATABASE_URL", "postgresql+asyncpg://missioniq:missioniq_dev_password@localhost:5432/missioniq")
os.environ.setdefault("MIQ_DATABASE_URL_SYNC", "postgresql+psycopg://missioniq:missioniq_dev_password@localhost:5432/missioniq")
os.environ.setdefault("MIQ_LLM_PROVIDER_ORDER", "local_stub")
os.environ.setdefault("MIQ_EMBEDDING_PROVIDER", "local_stub")
os.environ.setdefault("MIQ_ENV", "test")
