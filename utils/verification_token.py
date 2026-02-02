"""
Short-lived token proving an email was just verified (e.g. for registration).
Token is issued after successful OTP verify and accepted by the register endpoint.
"""
import hmac
import base64
import time
from flask import current_app

REGISTRATION_TOKEN_LIFETIME_SECONDS = 15 * 60  # 15 minutes


def create_registration_verification_token(email):
    """Create a signed token for verified email. Used after OTP verify success."""
    expiry = int(time.time()) + REGISTRATION_TOKEN_LIFETIME_SECONDS
    payload = f"{email.strip().lower()}|{expiry}"
    key = current_app.config.get("SECRET_KEY", "").encode("utf-8")
    sig = hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()
    raw = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")


def verify_registration_verification_token(token):
    """
    Verify token and return email if valid, else None.
    Checks signature and expiry.
    """
    if not token or not isinstance(token, str):
        return None
    try:
        raw = base64.urlsafe_b64decode(token + "==").decode("utf-8")
        parts = raw.rsplit("|", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        key = current_app.config.get("SECRET_KEY", "").encode("utf-8")
        expected = hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        email, expiry_str = payload.split("|", 1)
        if int(expiry_str) < int(time.time()):
            return None
        return email.strip().lower()
    except Exception:
        return None
