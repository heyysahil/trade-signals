"""
Signal model definition
"""
from models import db
from datetime import datetime
from decimal import Decimal

class Signal(db.Model):
    """Signal model for trading signals"""
    __tablename__ = 'signals'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    symbol = db.Column(db.String(50), nullable=False)
    exchange = db.Column(db.String(50))  # NSE, COINBASE, PEPPERSTONE, etc.
    signal_type = db.Column(db.String(10), nullable=False)  # BUY or SELL
    entry_price = db.Column(db.Numeric(10, 2), nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    exit_price = db.Column(db.Numeric(10, 2))
    exit_time = db.Column(db.DateTime)
    target_price = db.Column(db.Numeric(10, 2))
    stop_loss = db.Column(db.Numeric(10, 2))
    live_price = db.Column(db.Numeric(10, 2))  # Current market price
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REJECTED, ACTIVE, PROFIT, LOSS
    approval_status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REJECTED (for admin approval)
    approved_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    profit_loss = db.Column(db.Numeric(10, 2), default=0)  # Calculated P&L
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='signals', lazy=True)
    
    def calculate_duration(self):
        """Calculate duration in hours and minutes"""
        if self.entry_time and self.exit_time:
            delta = self.exit_time - self.entry_time
            hours = delta.total_seconds() // 3600
            minutes = (delta.total_seconds() % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"
        elif self.entry_time:
            delta = datetime.utcnow() - self.entry_time
            hours = delta.total_seconds() // 3600
            minutes = (delta.total_seconds() % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"
        return "0h 0m"
    
    def calculate_profit_loss(self):
        """Calculate profit or loss"""
        if self.exit_price and self.entry_price:
            if self.signal_type == 'BUY':
                pnl = float(self.exit_price) - float(self.entry_price)
            else:  # SELL
                pnl = float(self.entry_price) - float(self.exit_price)
            return round(pnl, 2)
        return 0
    
    def __repr__(self):
        return f'<Signal {self.symbol} {self.signal_type}>'
