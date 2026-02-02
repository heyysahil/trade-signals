"""
OTP generation and hashing for email verification.
OTPs are hashed before storage; never store plain OTP in DB.
"""
import secrets
import hashlib
from datetime import datetime, timedelta

# OTP length and expiry
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


def generate_otp() -> str:
    """Generate a secure 6-digit numeric OTP."""
    return ''.join(secrets.choice('0123456789') for _ in range(OTP_LENGTH))


def hash_otp(otp: str) -> str:
    """Hash OTP for storage. Use constant salt per app for consistency."""
    return hashlib.sha256(otp.encode('utf-8')).hexdigest()


def verify_otp(plain_otp: str, otp_hash: str) -> bool:
    """Verify a plain OTP against stored hash."""
    return hash_otp(plain_otp) == otp_hash


def otp_expires_at() -> datetime:
    """Return expiry datetime for new OTP (5 minutes from now)."""
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
