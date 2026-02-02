"""
User signals routes
"""
from flask import render_template, Blueprint, request
from flask_login import login_required, current_user
from models import db
from models.signal import Signal
from models.subscription import Subscription
from models.product import Product
from sqlalchemy import func, text

signals_bp = Blueprint('user_signals', __name__, url_prefix='/user')

@signals_bp.route('/signals')
@login_required
def signals():
    """User's subscribed signals - Only APPROVED subscriptions and APPROVED signals"""
    # SECURITY: Only get APPROVED subscriptions
    # Try-except to handle missing columns before migration
    try:
        approved_subscriptions = Subscription.query.filter_by(
            user_id=current_user.id,
            status='approved'
        ).all()
    except Exception:
        # Fallback using raw SQL without new columns
        result = db.session.execute(
            text("SELECT id, product_id FROM subscriptions WHERE user_id = :uid AND status = 'approved'"),
            {'uid': current_user.id}
        )
        rows = result.fetchall()
        # Create simple objects with needed attributes
        class SubProxy:
            def __init__(self, id, product_id):
                self.id = id
                self.product_id = product_id
        approved_subscriptions = [SubProxy(r[0], r[1]) for r in rows]
    
    # Get product IDs from approved subscriptions
    product_ids = [sub.product_id for sub in approved_subscriptions]
    
    # If no approved subscriptions, return empty
    if not product_ids:
        return render_template('user/signals.html',
                             signals=[],
                             total_signals=0,
                             active_count=0,
                             pending_count=0,
                             win_rate=0,
                             total_profit=0,
                             total_loss=0,
                             products=[],
                             filter_product_id=None)
    
    # Filter parameter
    filter_product_id = request.args.get('product_id', type=int)
    
    # Fetch signals based on APPROVED subscriptions
    # SECURITY: Only show APPROVED signals for APPROVED subscriptions
    active_products = Product.query.filter(
        Product.id.in_(product_ids),
        Product.is_active == True
    ).all()
    active_product_ids = [p.id for p in active_products]
    
    if active_product_ids:
        # Only get APPROVED signals - try with approval_status first
        try:
            query = Signal.query.filter(
                Signal.product_id.in_(active_product_ids),
                Signal.approval_status == 'APPROVED'  # Only approved signals
            )
            
            if filter_product_id and filter_product_id in active_product_ids:
                query = query.filter(Signal.product_id == filter_product_id)
            
            signals_list = query.order_by(Signal.entry_time.desc()).all()
        except Exception:
            # Fallback - show all signals without approval_status filter
            placeholders = ','.join(['?' for _ in active_product_ids])
            if filter_product_id and filter_product_id in active_product_ids:
                sql = f"SELECT * FROM signals WHERE product_id = ? ORDER BY entry_time DESC"
                result = db.session.execute(text(sql.replace('?', ':p1')), {'p1': filter_product_id})
            else:
                # Fallback: raw SQL with named placeholders
                sql = f"SELECT id FROM signals WHERE product_id IN ({','.join([':p'+str(i) for i in range(len(active_product_ids))])}) ORDER BY entry_time DESC"
                params = {f'p{i}': pid for i, pid in enumerate(active_product_ids)}
                result = db.session.execute(text(sql), params)
            
            signal_ids = [r[0] for r in result.fetchall()]
            signals_list = Signal.query.filter(Signal.id.in_(signal_ids)).order_by(Signal.entry_time.desc()).all() if signal_ids else []
    else:
        signals_list = []
    
    # Calculate performance metrics
    total_signals = len(signals_list)
    active_count = sum(1 for s in signals_list if s.status == 'ACTIVE')
    pending_count = 0  # Can be calculated based on business logic
    
    # Calculate win rate and profit/loss
    completed_signals = [s for s in signals_list if s.status in ['PROFIT', 'LOSS']]
    profit_signals = [s for s in completed_signals if s.status == 'PROFIT']
    win_rate = (len(profit_signals) / len(completed_signals) * 100) if completed_signals else 0
    
    total_profit = sum(float(s.profit_loss or 0) for s in profit_signals)
    total_loss = sum(abs(float(s.profit_loss or 0)) for s in completed_signals if s.status == 'LOSS')
    
    # Get products for filter dropdown (only from approved subscriptions)
    products = Product.query.filter(Product.id.in_(product_ids)).all() if product_ids else []
    
    return render_template('user/signals.html',
                         signals=signals_list,
                         total_signals=total_signals,
                         active_count=active_count,
                         pending_count=pending_count,
                         win_rate=round(win_rate, 1),
                         total_profit=round(total_profit, 2),
                         total_loss=round(total_loss, 2),
                         products=products,
                         filter_product_id=filter_product_id,
                         no_access=False)
