"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Re-export for older imports.
__all__ = ["BASE_DIR", "Settings", "get_settings", "reset_settings_cache"]


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_base_url: str
    database_url: str
    secret_key: str
    auth_mode: str
    supabase_url: str
    supabase_publishable_key: str
    supabase_service_role_key: str
    supabase_storage_bucket: str
    openai_api_key: str
    openai_food_model: str
    cookie_secure: bool
    allowed_hosts: tuple[str, ...]
    session_cookie_name: str
    csrf_cookie_name: str
    session_ttl_days: int
    signed_url_ttl_seconds: int
    max_upload_bytes: int
    max_image_pixels: int
    local_upload_dir: Path

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def uses_cloud_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_storage_bucket and self.supabase_service_role_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = _env("APP_ENV", "development")
    database_url = _env("DATABASE_URL")
    if not database_url:
        if app_env.lower() in {"prod", "production"}:
            raise RuntimeError("生产环境必须配置 DATABASE_URL（PostgreSQL）。")
        database_url = f"sqlite:///{BASE_DIR / 'health_tracker.db'}"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    secret_key = _env("SECRET_KEY")
    if not secret_key:
        if app_env.lower() in {"prod", "production"}:
            raise RuntimeError("生产环境必须配置 SECRET_KEY。")
        secret_key = "dev-only-insecure-secret-key"

    auth_mode = _env("AUTH_MODE", "supabase").lower()
    if auth_mode not in {"supabase", "local"}:
        raise RuntimeError("AUTH_MODE 只能是 supabase 或 local。")

    supabase_url = _env("SUPABASE_URL")
    supabase_publishable_key = _env("SUPABASE_PUBLISHABLE_KEY") or _env("SUPABASE_ANON_KEY")
    supabase_service_role_key = _env("SUPABASE_SERVICE_ROLE_KEY")
    supabase_storage_bucket = _env("SUPABASE_STORAGE_BUCKET", "meal-photos")

    if app_env.lower() in {"prod", "production"}:
        if auth_mode != "supabase":
            raise RuntimeError("生产环境 AUTH_MODE 必须为 supabase。")
        missing = [
            name
            for name, value in {
                "SUPABASE_URL": supabase_url,
                "SUPABASE_PUBLISHABLE_KEY": supabase_publishable_key,
                "SUPABASE_SERVICE_ROLE_KEY": supabase_service_role_key,
                "SUPABASE_STORAGE_BUCKET": supabase_storage_bucket,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"生产环境缺少必要配置：{', '.join(missing)}")
        if database_url.startswith("sqlite"):
            raise RuntimeError("生产环境禁止使用 SQLite。")

    cookie_secure_raw = _env("COOKIE_SECURE")
    if cookie_secure_raw:
        cookie_secure = _env_bool("COOKIE_SECURE", False)
    else:
        cookie_secure = app_env.lower() in {"prod", "production"}

    allowed_hosts = tuple(
        host.strip()
        for host in _env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
        if host.strip()
    )

    return Settings(
        app_env=app_env,
        app_base_url=_env("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        database_url=database_url,
        secret_key=secret_key,
        auth_mode=auth_mode,
        supabase_url=supabase_url.rstrip("/"),
        supabase_publishable_key=supabase_publishable_key,
        supabase_service_role_key=supabase_service_role_key,
        supabase_storage_bucket=supabase_storage_bucket,
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_food_model=_env("OPENAI_FOOD_MODEL", "gpt-4.1-mini"),
        cookie_secure=cookie_secure,
        allowed_hosts=allowed_hosts,
        session_cookie_name=_env("SESSION_COOKIE_NAME", "cutnbulk_session"),
        csrf_cookie_name=_env("CSRF_COOKIE_NAME", "cutnbulk_csrf"),
        session_ttl_days=int(_env("SESSION_TTL_DAYS", "14") or "14"),
        signed_url_ttl_seconds=int(_env("SIGNED_URL_TTL_SECONDS", "300") or "300"),
        max_upload_bytes=int(_env("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)) or str(8 * 1024 * 1024)),
        max_image_pixels=int(_env("MAX_IMAGE_PIXELS", str(4096 * 4096)) or str(4096 * 4096)),
        local_upload_dir=BASE_DIR / "app" / "uploads",
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()
