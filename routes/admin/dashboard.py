"""
Admin dashboard routes
"""
from flask import render_template, Blueprint, session, redirect, url_for, flash
from routes.admin.auth import admin_required, get_current_admin
from models import db
from models.user import User
from models.subscription import Subscription
from models.transaction import Transaction
from models.signal import Signal
from models.product import Product
from datetime import datetime, timedelta
from sqlalchemy import func, case

admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

@admin_dashboard_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard - Superadmin only"""
    admin = get_current_admin()
    
    # Product-specific admins should go to their signals page
    if admin and admin.role != 'superadmin':
        flash('Welcome! You can manage signals for your assigned product category.', 'info')
        return redirect(url_for('admin_signals.signals'))
    
    # Timezone-safe: use UTC for all date comparisons
    now = datetime.utcnow()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Get summary statistics
    total_customers = User.query.count()
    today_customers = User.query.filter(
        func.date(User.created_at) == datetime.utcnow().date()
    ).count()

    # Active customer = user with at least one ACTIVE subscription:
    # subscription.status = 'approved' AND end_date >= today (do NOT use user.status)
    active_customer_ids = db.session.query(Subscription.user_id).filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now
    ).distinct().all()
    active_customer_ids = [uid[0] for uid in active_customer_ids]
    active_customers_count = len(active_customer_ids)

    # Active customers today = users who got their first approved subscription today
    active_customers_today = db.session.query(Subscription.user_id).filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now,
        func.date(Subscription.approved_at) == datetime.utcnow().date()
    ).distinct().count()

    # Active customers this week
    active_customers_week = db.session.query(Subscription.user_id).filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now,
        Subscription.approved_at >= week_start
    ).distinct().count()

    # Inactive customers = users with NO active subscriptions (total - active)
    inactive_customers_count = total_customers - active_customers_count
    
    # Subscription metrics
    total_subscriptions = Subscription.query.count()
    today_subscriptions = Subscription.query.filter(
        func.date(Subscription.created_at) == datetime.utcnow().date()
    ).count()

    # Pending subscriptions: status = 'pending'
    pending_subscriptions_count = Subscription.query.filter_by(status='pending').count()
    pending_subscriptions_today = Subscription.query.filter(
        Subscription.status == 'pending',
        func.date(Subscription.created_at) == datetime.utcnow().date()
    ).count()
    pending_subscriptions_week = Subscription.query.filter(
        Subscription.status == 'pending',
        Subscription.created_at >= week_start
    ).count()

    # Active subscriptions: status = 'approved' AND end_date >= current date
    active_subscriptions_count = Subscription.query.filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now
    ).count()
    active_subscriptions_today = Subscription.query.filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now,
        func.date(Subscription.approved_at) == datetime.utcnow().date()
    ).count()
    active_subscriptions_week = Subscription.query.filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now,
        Subscription.approved_at >= week_start
    ).count()

    # Expired subscriptions: end_date < current date
    expired_subscriptions_count = Subscription.query.filter(
        Subscription.end_date < now
    ).count()
    expired_subscriptions_today = Subscription.query.filter(
        Subscription.end_date < now,
        func.date(Subscription.end_date) == datetime.utcnow().date()
    ).count()
    expired_subscriptions_week = Subscription.query.filter(
        Subscription.end_date < now,
        Subscription.end_date >= week_start
    ).count()
    
    # Total revenue: sum only successful transactions (payment_status = success → status = 'completed')
    total_revenue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed'
    ).scalar() or 0
    total_revenue = float(total_revenue)

    revenue_today = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed',
        func.date(Transaction.created_at) == datetime.utcnow().date()
    ).scalar() or 0
    revenue_today = float(revenue_today)

    revenue_week = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed',
        Transaction.created_at >= week_start
    ).scalar() or 0
    revenue_week = float(revenue_week)

    # Signals generated: count by created_at (today and this week)
    total_signals = Signal.query.count()
    signals_today = Signal.query.filter(
        func.date(Signal.created_at) == datetime.utcnow().date()
    ).count()
    signals_week = Signal.query.filter(
        Signal.created_at >= week_start
    ).count()
    
    # Pending admin actions (pending subscriptions + pending signals)
    pending_signals_count = Signal.query.filter_by(approval_status='PENDING').count()
    pending_admin_actions = pending_subscriptions_count + pending_signals_count
    pending_admin_actions_today = pending_subscriptions_today + Signal.query.filter(
        Signal.approval_status == 'PENDING',
        func.date(Signal.created_at) == datetime.utcnow().date()
    ).count()
    pending_admin_actions_week = pending_subscriptions_week + Signal.query.filter(
        Signal.approval_status == 'PENDING',
        Signal.created_at >= week_start
    ).count()
    
    # Get signals by product - handle case where signals table might be empty
    try:
        signals_by_product = db.session.query(
            Product.name,
            func.count(Signal.id).label('total_signals'),
            func.sum(case((Signal.status == 'PROFIT', 1), else_=0)).label('winners'),
            func.sum(case((Signal.status == 'LOSS', 1), else_=0)).label('losers'),
            func.sum(case((Signal.status == 'ACTIVE', 1), else_=0)).label('in_progress'),
            func.sum(case((Signal.status == 'PROFIT', Signal.profit_loss), else_=0)).label('total_profit')
        ).outerjoin(
            Signal, Product.id == Signal.product_id
        ).group_by(Product.id, Product.name).all()
    except Exception as e:
        # If there's an error (e.g., no signals yet), return empty list
        print(f"Error fetching signals by product: {e}")
        signals_by_product = []
    
    # Get pending subscriptions - handle missing columns
    try:
        pending_subscriptions = Subscription.query.filter_by(
            status='pending'
        ).order_by(Subscription.created_at.desc()).limit(10).all()
    except Exception:
        # If columns don't exist yet, use raw SQL
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT id FROM subscriptions 
                WHERE status = 'pending' 
                ORDER BY created_at DESC 
                LIMIT 10
            """))
            subscription_ids = [row[0] for row in result.fetchall()]
            pending_subscriptions = [Subscription.query.get(sid) for sid in subscription_ids if Subscription.query.get(sid)]
        except:
            pending_subscriptions = []
    
    return render_template('admin/dashboard.html',
                         total_customers=total_customers,
                         today_customers=today_customers,
                         active_customers_count=active_customers_count,
                         active_customers_today=active_customers_today,
                         active_customers_week=active_customers_week,
                         inactive_customers_count=inactive_customers_count,
                         total_subscriptions=total_subscriptions,
                         today_subscriptions=today_subscriptions,
                         pending_subscriptions_count=pending_subscriptions_count,
                         pending_subscriptions_today=pending_subscriptions_today,
                         pending_subscriptions_week=pending_subscriptions_week,
                         active_subscriptions_count=active_subscriptions_count,
                         active_subscriptions_today=active_subscriptions_today,
                         active_subscriptions_week=active_subscriptions_week,
                         expired_subscriptions_count=expired_subscriptions_count,
                         expired_subscriptions_today=expired_subscriptions_today,
                         expired_subscriptions_week=expired_subscriptions_week,
                         total_revenue=total_revenue,
                         revenue_today=revenue_today,
                         revenue_week=revenue_week,
                         total_signals=total_signals,
                         signals_today=signals_today,
                         signals_week=signals_week,
                         pending_admin_actions=pending_admin_actions,
                         pending_admin_actions_today=pending_admin_actions_today,
                         pending_admin_actions_week=pending_admin_actions_week,
                         signals_by_product=signals_by_product,
                         pending_subscriptions=pending_subscriptions,
                         is_superadmin=(admin and admin.role == 'superadmin'))
