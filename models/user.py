"""
User model definition
"""
from models import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """User model for customer accounts"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=True)  # True preserves existing users/signup flow

    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.full_name}>'
