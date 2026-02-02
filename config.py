"""
Configuration for Trade Signals Flask app.
Production (Railway/Render): uses DATABASE_URL only; fails if missing.
Local: DATABASE_URL or DB_* fallback for backward compatibility.
"""
import os
from pathlib import Path
from datetime import timedelta
from urllib.parse import quote_plus


def _is_production():
    """True when running on Railway, Render, or explicit production."""
    return (
        os.environ.get("RENDER") == "true"
        or os.environ.get("RAILWAY_ENVIRONMENT") is not None
        or os.environ.get("FLASK_ENV") == "production"
    )


def _normalize_database_url(url):
    """Convert postgres:// to postgresql+psycopg2:// for SQLAlchemy/psycopg2."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[11:]
    if url.startswith("postgresql://") and "psycopg2" not in url:
        return "postgresql+psycopg2://" + url[13:]
    if url.startswith("postgresql+psycopg2://"):
        return url
    return url


def _get_database_uri():
    """Database URI: production = DATABASE_URL only; local = DATABASE_URL or DB_*."""
    if _is_production():
        url = os.environ.get("DATABASE_URL")
        if not url or not url.strip():
            raise RuntimeError(
                "DATABASE_URL is required in production (Railway/Render). "
                "Set it in your service environment variables."
            )
        return _normalize_database_url(url.strip())

    # Local / development: prefer DATABASE_URL, fallback to DB_* (cPanel-style)
    url = os.environ.get("DATABASE_URL")
    if url and url.strip():
        return _normalize_database_url(url.strip())

    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "sendsignals")
    user = os.environ.get("DB_USER", "sendsignals")
    password = os.environ.get("DB_PASSWORD", "")
    if password:
        password = quote_plus(password)
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in ("true", "on", "1")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    BASE_DIR = Path(__file__).parent
    INSTANCE_DIR = BASE_DIR / "instance"
    try:
        INSTANCE_DIR.mkdir(exist_ok=True)
    except OSError:
        pass
    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "on", "1")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or os.environ.get("MAIL_USERNAME") or "noreply@send.signals"

    RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY")
    RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY")

    PAYMENT_GATEWAY_API_KEY = os.environ.get("PAYMENT_GATEWAY_API_KEY")
    PAYMENT_GATEWAY_SECRET = os.environ.get("PAYMENT_GATEWAY_SECRET")
