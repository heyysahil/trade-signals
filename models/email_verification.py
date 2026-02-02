"""
Email verification OTP and CAPTCHA models (PostgreSQL-compatible).
Used for OTP-based email verification with CAPTCHA protection.
"""
from models import db
from datetime import datetime


class EmailVerificationOTP(db.Model):
    """
    Stores hashed OTP for email verification.
    One active record per email; replaced on new send.
    """
    __tablename__ = 'email_verification_otp'

    email = db.Column(db.String(120), primary_key=True)
    otp_hash = db.Column(db.String(255), nullable=False)
    otp_expires_at = db.Column(db.DateTime, nullable=False)
    otp_attempts = db.Column(db.Integer, default=0)
    email_verified = db.Column(db.Integer, default=0)  # 1 when OTP was used to verify
    otp_sent_at = db.Column(db.DateTime, nullable=True)  # for rate-limit: resend only after 30s
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        return datetime.utcnow() >= self.otp_expires_at

    def attempts_exceeded(self):
        return self.otp_attempts >= 5

    def __repr__(self):
        return f'<EmailVerificationOTP {self.email}>'


class CaptchaChallenge(db.Model):
    """
    Custom math CAPTCHA challenges. One-time use, 2-minute expiry.
    """
    __tablename__ = 'captcha_challenge'

    captcha_id = db.Column(db.String(64), primary_key=True)
    captcha_answer = db.Column(db.String(32), nullable=False)
    captcha_expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Integer, default=0)  # 1 after successful use

    def is_expired(self):
        return datetime.utcnow() >= self.captcha_expires_at

    def __repr__(self):
        return f'<CaptchaChallenge {self.captcha_id[:8]}...>'


class OTPSendLog(db.Model):
    """Log of OTP sends per email for rate limiting (e.g. max 5 per hour)."""
    __tablename__ = 'otp_send_log'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
