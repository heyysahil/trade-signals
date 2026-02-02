"""
Transaction model definition
"""
from models import db
from datetime import datetime

class Transaction(db.Model):
    """Transaction model for payment records"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Transaction {self.id}>'
