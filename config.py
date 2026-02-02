"""
Configuration settings for sendsignals application
PostgreSQL database; credentials via environment variables (cPanel: Application Setup > Environment Variables).
"""
import os
from pathlib import Path
from datetime import timedelta
from urllib.parse import quote_plus


def _get_database_uri():
    """Build PostgreSQL URI from environment variables.
    cPanel: Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in Python App > Environment Variables.
    """
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    name = os.environ.get('DB_NAME', 'sendsignals')
    user = os.environ.get('DB_USER', 'sendsignals')
    password = os.environ.get('DB_PASSWORD', '')
    if password:
        password = quote_plus(password)
    return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}'


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8 hour session timeout
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ['true', 'on', '1']  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True  # Prevent XSS attacks
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    
    # Database configuration (PostgreSQL)
    BASE_DIR = Path(__file__).parent
    INSTANCE_DIR = BASE_DIR / 'instance'
    INSTANCE_DIR.mkdir(exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration (SMTP for OTP verification emails)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME') or 'noreply@send.signals'

    # reCAPTCHA v2 (optional; if not set, custom math CAPTCHA is used)
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

    # Payment gateway configuration
    PAYMENT_GATEWAY_API_KEY = os.environ.get('PAYMENT_GATEWAY_API_KEY')
    PAYMENT_GATEWAY_SECRET = os.environ.get('PAYMENT_GATEWAY_SECRET')
