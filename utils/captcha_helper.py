"""
Custom math CAPTCHA generation and validation.
Used when reCAPTCHA is not configured; runs fully offline with PostgreSQL.
"""
import secrets
from datetime import datetime, timedelta

CAPTCHA_EXPIRY_MINUTES = 2


def create_math_captcha() -> tuple[str, str, str]:
    """
    Create a simple math CAPTCHA.
    Returns (captcha_id, question_text, correct_answer).
    """
    a = secrets.randbelow(15) + 1
    b = secrets.randbelow(15) + 1
    question = f"{a} + {b}"
    answer = str(a + b)
    captcha_id = secrets.token_urlsafe(32)
    return captcha_id, question, answer


def captcha_expires_at() -> datetime:
    """CAPTCHA valid for 2 minutes."""
    return datetime.utcnow() + timedelta(minutes=CAPTCHA_EXPIRY_MINUTES)
