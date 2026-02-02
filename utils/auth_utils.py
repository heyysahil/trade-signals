"""
Authentication utility functions
"""
import hmac
import base64
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app

def hash_password(password):
    """Generate password hash"""
    return generate_password_hash(password)

def verify_password(password_hash, password):
    """Verify password against hash"""
    return check_password_hash(password_hash, password)

# Password reset token lifetime: 1 hour
RESET_TOKEN_LIFETIME_SECONDS = 60 * 60

def generate_reset_token(user):
    """
    Generate password reset token for user.
    Returns a signed token that expires in 1 hour.
    """
    expiry = int(time.time()) + RESET_TOKEN_LIFETIME_SECONDS
    payload = f"{user.id}|{user.email.strip().lower()}|{expiry}"
    key = current_app.config.get("SECRET_KEY", "").encode("utf-8")
    sig = hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()
    raw = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")

def verify_reset_token(token):
    """
    Verify password reset token and return user ID if valid, else None.
    Checks signature and expiry.
    """
    from models.user import User
    
    if not token or not isinstance(token, str):
        return None
    
    try:
        # Decode token
        raw = base64.urlsafe_b64decode(token + "==").decode("utf-8")
        parts = raw.rsplit("|", 1)
        if len(parts) != 2:
            return None
        
        payload, sig = parts
        key = current_app.config.get("SECRET_KEY", "").encode("utf-8")
        expected = hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()
        
        # Verify signature
        if not hmac.compare_digest(sig, expected):
            return None
        
        # Extract user_id, email, and expiry
        user_id_str, email, expiry_str = payload.split("|", 2)
        
        # Check expiry
        if int(expiry_str) < int(time.time()):
            return None
        
        # Verify user exists and email matches
        user = User.query.get(int(user_id_str))
        if not user or user.email.strip().lower() != email:
            return None
        
        return user
    except Exception:
        return None
