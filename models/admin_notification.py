"""
Admin Notification model definition
"""
from models import db
from datetime import datetime

class AdminNotification(db.Model):
    """Admin Notification model for tracking admin notifications"""
    __tablename__ = 'admin_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # subscription, signal, user, system
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_id = db.Column(db.Integer, nullable=True)  # subscription_id, signal_id, user_id
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdminNotification {self.id}: {self.type}>'
    
    def to_dict(self):
        """Convert notification to dictionary for JSON responses"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'related_id': self.related_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
