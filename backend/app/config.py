from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from sqlalchemy.engine import URL, make_url


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(RuntimeError):
    """Raised when a deployment setting is unsafe or internally inconsistent."""


def _read_secret(*, value_env: str, file_env: str, default: str = "") -> str:
    direct = os.getenv(value_env)
    file_name = os.getenv(file_env)
    if direct and file_name:
        raise ConfigurationError(f"Set only one of {value_env} or {file_env}, not both.")
    if file_name:
        path = Path(file_name)
        if not path.is_file():
            raise ConfigurationError(f"Secret file configured by {file_env} does not exist: {path}")
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise ConfigurationError(f"Secret file configured by {file_env} is empty.")
        return value
    return direct if direct is not None else default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalise_database_url(raw: str) -> str:
    """Validate and normalise a supplied SQLAlchemy URL.

    Raw passwords containing reserved URI characters must be percent-encoded.
    Production Compose avoids this class of error by passing discrete DB fields
    and building the URL with SQLAlchemy's URL.create().
    """
    try:
        parsed = make_url(raw)
    except Exception as exc:  # pragma: no cover - SQLAlchemy provides detail
        raise ConfigurationError("DATABASE_URL is not a valid SQLAlchemy database URL.") from exc
    host = parsed.host or ""
    if any(character in host for character in ("@", "#", "/", " ")):
        raise ConfigurationError(
            "DATABASE_URL was parsed with reserved password characters in the host. "
            "Use UMOJA_DB_* settings or percent-encode @ as %40 and # as %23."
        )
    return parsed.render_as_string(hide_password=False)


def _database_url_from_environment(default: str) -> str:
    raw_url = os.getenv("DATABASE_URL")
    if raw_url:
        return _normalise_database_url(raw_url)

    host = os.getenv("UMOJA_DB_HOST")
    if not host:
        return default

    password = _read_secret(
        value_env="UMOJA_DB_PASSWORD",
        file_env="UMOJA_DB_PASSWORD_FILE",
    )
    if not password:
        raise ConfigurationError("A database password is required when UMOJA_DB_HOST is configured.")

    url = URL.create(
        drivername=os.getenv("UMOJA_DB_DRIVER", "postgresql+psycopg"),
        username=os.getenv("UMOJA_DB_USER", "umoja"),
        password=password,
        host=host,
        port=int(os.getenv("UMOJA_DB_PORT", "5432")),
        database=os.getenv("UMOJA_DB_NAME", "umoja_afya"),
        query={"sslmode": os.getenv("UMOJA_DB_SSLMODE", "prefer")},
    )
    return url.render_as_string(hide_password=False)


class Settings(BaseModel):
    app_name: str = "Umoja Afya Enterprise EHR"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'umoja_afya.db'}"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    seed_demo_data: bool = True
    schema_auto_create: bool = True
    audit_enabled: bool = True
    default_facility: str = "MNH-UPANGA"
    session_timeout_minutes: int = 20
    security_secret: str = "change-this-in-production"
    enforce_auth: bool = False
    enforce_rbac: bool = False
    demo_credentials_enabled: bool = False
    demo_patient_count: int = 10000
    rate_limit_per_minute: int = 240
    login_rate_limit_per_minute: int = 10
    max_request_bytes: int = 25 * 1024 * 1024
    api_docs_enabled: bool = True
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    transcription_endpoint: str | None = None
    transcription_required: bool = False
    transcription_timeout_seconds: int = 180
    transcription_max_audio_bytes: int = 50 * 1024 * 1024
    transcription_min_confidence: float = 0.55
    retain_raw_clinical_audio: bool = False
    offline_access_enabled: bool = True
    offline_lease_hours: int = 24
    offline_max_pending: int = 1000

    def validate_runtime(self) -> None:
        environment = self.environment.lower()
        if environment not in {"development", "test", "review", "staging", "production"}:
            raise ConfigurationError(f"Unsupported UMOJA_ENVIRONMENT: {self.environment}")
        if not 1 <= self.offline_lease_hours <= 72:
            raise ConfigurationError("UMOJA_OFFLINE_LEASE_HOURS must be between 1 and 72.")
        if not 1 <= self.offline_max_pending <= 5000:
            raise ConfigurationError("UMOJA_OFFLINE_MAX_PENDING must be between 1 and 5000.")
        if environment in {"staging", "production"}:
            if self.database_url.startswith("sqlite"):
                raise ConfigurationError("SQLite is not permitted for staging or production.")
            if len(self.security_secret) < 64:
                raise ConfigurationError("UMOJA_SECURITY_SECRET must contain at least 64 characters in staging/production.")
            if self.security_secret in {"change-this-in-production", "development-only-secret-change-me"}:
                raise ConfigurationError("A placeholder UMOJA_SECURITY_SECRET cannot be used in staging/production.")
            if not self.enforce_auth or not self.enforce_rbac:
                raise ConfigurationError("Authentication and RBAC must both be enforced in staging/production.")
            if self.demo_credentials_enabled or self.seed_demo_data:
                raise ConfigurationError("Demonstration credentials and seed data must be disabled in staging/production.")
            if "*" in self.cors_origins:
                raise ConfigurationError("Wildcard CORS is not permitted in staging/production.")
            if "*" in self.allowed_hosts:
                raise ConfigurationError("Wildcard trusted hosts are not permitted in staging/production.")
            if self.schema_auto_create:
                raise ConfigurationError("Automatic schema creation is not permitted in staging/production; use Alembic migrations.")
            if self.transcription_required and not self.transcription_endpoint:
                raise ConfigurationError("UMOJA_TRANSCRIPTION_REQUIRED is enabled but UMOJA_TRANSCRIPTION_ENDPOINT is not configured.")
        elif environment == "review":
            if len(self.security_secret) < 32:
                raise ConfigurationError("UMOJA_SECURITY_SECRET must contain at least 32 characters in review.")
            if not self.enforce_auth or not self.enforce_rbac:
                raise ConfigurationError("Authentication and RBAC must be enabled in review.")


def _deep_get(data: dict[str, Any], path: list[str], default: Any) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    config_path = PROJECT_ROOT / "application.yml"
    data: dict[str, Any] = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    app = data.get("application", {})
    database = data.get("database", {})
    security = data.get("security", {})
    environment = os.getenv("UMOJA_ENVIRONMENT", app.get("environment", "development"))

    cors_env = os.getenv("UMOJA_CORS_ORIGINS")
    cors_origins = [x.strip() for x in cors_env.split(",") if x.strip()] if cors_env else security.get("cors_origins", ["*"])
    hosts_env = os.getenv("UMOJA_ALLOWED_HOSTS")
    allowed_hosts = [x.strip() for x in hosts_env.split(",") if x.strip()] if hosts_env else security.get("allowed_hosts", ["*"])

    default_database_url = database.get("url", f"sqlite:///{PROJECT_ROOT / 'umoja_afya.db'}")
    database_url = _database_url_from_environment(default_database_url)
    security_secret = _read_secret(
        value_env="UMOJA_SECURITY_SECRET",
        file_env="UMOJA_SECURITY_SECRET_FILE",
        default=security.get("secret", "change-this-in-production"),
    )
    default_schema_create = environment.lower() in {"development", "test"}
    return Settings(
        app_name=app.get("name", "Umoja Afya Enterprise EHR"),
        environment=environment,
        api_prefix=app.get("api_prefix", "/api/v1"),
        database_url=database_url,
        cors_origins=cors_origins,
        allowed_hosts=allowed_hosts,
        seed_demo_data=_bool_env("UMOJA_SEED_DEMO_DATA", app.get("seed_demo_data", default_schema_create)),
        schema_auto_create=_bool_env("UMOJA_SCHEMA_AUTO_CREATE", default_schema_create),
        audit_enabled=security.get("audit_enabled", True),
        default_facility=app.get("default_facility", "MNH-UPANGA"),
        session_timeout_minutes=int(os.getenv("UMOJA_SESSION_TIMEOUT_MINUTES", security.get("session_timeout_minutes", 20))),
        security_secret=security_secret,
        enforce_auth=_bool_env("UMOJA_ENFORCE_AUTH", security.get("enforce_auth", False)),
        enforce_rbac=_bool_env("UMOJA_ENFORCE_RBAC", security.get("enforce_rbac", False)),
        demo_credentials_enabled=_bool_env("UMOJA_DEMO_CREDENTIALS", security.get("demo_credentials_enabled", False)),
        demo_patient_count=int(os.getenv("UMOJA_DEMO_PATIENT_COUNT", app.get("demo_patient_count", 10000))),
        rate_limit_per_minute=int(os.getenv("UMOJA_RATE_LIMIT_PER_MINUTE", security.get("rate_limit_per_minute", 240))),
        login_rate_limit_per_minute=int(os.getenv("UMOJA_LOGIN_RATE_LIMIT_PER_MINUTE", security.get("login_rate_limit_per_minute", 10))),
        max_request_bytes=int(os.getenv("UMOJA_MAX_REQUEST_BYTES", security.get("max_request_bytes", 25 * 1024 * 1024))),
        api_docs_enabled=_bool_env("UMOJA_API_DOCS_ENABLED", environment.lower() != "production"),
        db_pool_size=int(os.getenv("UMOJA_DB_POOL_SIZE", database.get("pool_size", 10))),
        db_max_overflow=int(os.getenv("UMOJA_DB_MAX_OVERFLOW", database.get("max_overflow", 20))),
        db_pool_timeout_seconds=int(os.getenv("UMOJA_DB_POOL_TIMEOUT", database.get("pool_timeout_seconds", 30))),
        db_pool_recycle_seconds=int(os.getenv("UMOJA_DB_POOL_RECYCLE", database.get("pool_recycle_seconds", 1800))),
        transcription_endpoint=(os.getenv("UMOJA_TRANSCRIPTION_ENDPOINT") or security.get("transcription_endpoint") or None),
        transcription_required=_bool_env("UMOJA_TRANSCRIPTION_REQUIRED", security.get("transcription_required", False)),
        transcription_timeout_seconds=int(os.getenv("UMOJA_TRANSCRIPTION_TIMEOUT_SECONDS", security.get("transcription_timeout_seconds", 180))),
        transcription_max_audio_bytes=int(os.getenv("UMOJA_TRANSCRIPTION_MAX_AUDIO_BYTES", security.get("transcription_max_audio_bytes", 50 * 1024 * 1024))),
        transcription_min_confidence=float(os.getenv("UMOJA_TRANSCRIPTION_MIN_CONFIDENCE", security.get("transcription_min_confidence", 0.55))),
        retain_raw_clinical_audio=_bool_env("UMOJA_RETAIN_RAW_CLINICAL_AUDIO", security.get("retain_raw_clinical_audio", False)),
        offline_access_enabled=_bool_env("UMOJA_OFFLINE_ACCESS_ENABLED", security.get("offline_access_enabled", True)),
        offline_lease_hours=int(os.getenv("UMOJA_OFFLINE_LEASE_HOURS", security.get("offline_lease_hours", 24))),
        offline_max_pending=int(os.getenv("UMOJA_OFFLINE_MAX_PENDING", security.get("offline_max_pending", 1000))),
    )
