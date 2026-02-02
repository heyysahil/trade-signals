"""
Admin model definition
"""
from models import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Admin(db.Model):
    """Admin model for staff/admin accounts"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='staff')  # superadmin, admin (product-specific)
    product_category = db.Column(db.String(100), nullable=True)  # Product category for product-specific admins
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'
