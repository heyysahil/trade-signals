"""
Subscription model definition
"""
from models import db
from datetime import datetime

class Subscription(db.Model):
    """Subscription model for user product subscriptions"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, active, expired, cancelled
    payment_status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded; synced from transactions
    approved_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='subscription', lazy=True)
    
    def __repr__(self):
        return f'<Subscription {self.id}>'
