"""
Models package for sendsignals application
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models here to ensure they're registered
from models.user import User
from models.product import Product
from models.subscription import Subscription
from models.transaction import Transaction
from models.signal import Signal
from models.admin import Admin
from models.settings import Settings
from models.email_verification import EmailVerificationOTP, CaptchaChallenge, OTPSendLog
from models.admin_notification import AdminNotification

__all__ = [
    'db',
    'User',
    'Product',
    'Subscription',
    'Transaction',
    'Signal',
    'Admin',
    'Settings',
    'EmailVerificationOTP',
    'CaptchaChallenge',
    'OTPSendLog',
    'AdminNotification',
]
