"""
Admin subscription management routes
"""
from flask import render_template, Blueprint, request, redirect, url_for, flash
from routes.admin.auth import admin_required, get_current_admin, superadmin_required
from models import db
from models.subscription import Subscription
from models.user import User
from models.product import Product
from models.transaction import Transaction
from datetime import datetime, timedelta
from sqlalchemy import func, or_

admin_subscriptions_bp = Blueprint('admin_subscriptions', __name__, url_prefix='/admin')

@admin_subscriptions_bp.route('/subscriptions')
@admin_required
def subscriptions():
    """Subscription management page"""
    admin = get_current_admin()
    
    # Product-specific admins cannot access subscriptions
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can access subscriptions.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403
    
    # Get filter parameters
    customer_id = request.args.get('customer', type=int)
    product_id = request.args.get('product', type=int)
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    
    # Build query
    query = Subscription.query
    
    if customer_id:
        query = query.filter_by(user_id=customer_id)
    if product_id:
        query = query.filter_by(product_id=product_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search_query:
        query = query.join(User).filter(
            or_(
                User.full_name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%'),
                User.mobile.ilike(f'%{search_query}%')
            )
        )
    
    # Sort
    if sort_by == 'date':
        query = query.order_by(Subscription.created_at.desc())
    elif sort_by == 'customer':
        query = query.join(User).order_by(User.full_name)
    elif sort_by == 'product':
        query = query.join(Product).order_by(Product.name)
    
    # Handle missing columns gracefully
    try:
        subscriptions_list = query.all()
    except Exception:
        # If columns don't exist yet, use raw SQL
        from sqlalchemy import text
        try:
            sql = "SELECT id FROM subscriptions WHERE 1=1"
            params = {}
            
            if customer_id:
                sql += " AND user_id = :customer_id"
                params['customer_id'] = customer_id
            if product_id:
                sql += " AND product_id = :product_id"
                params['product_id'] = product_id
            if status_filter:
                sql += " AND status = :status"
                params['status'] = status_filter
            
            sql += " ORDER BY created_at DESC"
            
            result = db.session.execute(text(sql), params)
            subscription_ids = [row[0] for row in result.fetchall()]
            subscriptions_list = [Subscription.query.get(sid) for sid in subscription_ids]
            subscriptions_list = [s for s in subscriptions_list if s]  # Filter out None
        except Exception as e:
            print(f"Error fetching subscriptions: {e}")
            subscriptions_list = []
    
    # Group subscriptions by validity (status='approved' + end_date for active; end_date < now for expired)
    trial_subscriptions = []
    active_paid_subscriptions = []
    expired_subscriptions = []
    now_for_group = datetime.utcnow()

    for sub in subscriptions_list:
        if sub.product:
            days = (sub.end_date - sub.start_date).days
            if days == 10 and sub.status == 'approved' and sub.end_date >= now_for_group:
                trial_subscriptions.append(sub)
            elif sub.status == 'approved' and sub.end_date >= now_for_group and days in [30, 90]:
                active_paid_subscriptions.append(sub)
            elif sub.end_date < now_for_group or sub.status == 'expired':
                expired_subscriptions.append(sub)
    
    # Dashboard metrics: use global counts (ignore filters), timezone-safe UTC
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Total Customers: count DISTINCT users.id
    total_customers = db.session.query(func.count(User.id)).scalar() or 0

    # 2. Active Customers: users with at least one subscription where status='approved' AND end_date >= current date
    active_customers_count = db.session.query(Subscription.user_id).filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now
    ).distinct().count()

    # 3. Inactive Customers: total_customers - active_customers
    inactive_customers_count = total_customers - active_customers_count

    # Active subscriptions count (status='approved', end_date >= now) for any downstream use
    try:
        active_subscriptions = Subscription.query.filter(
            Subscription.status == 'approved',
            Subscription.end_date >= now
        ).count()
    except Exception:
        from sqlalchemy import text
        try:
            result = db.session.execute(text(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'approved' AND end_date >= ?"
            ), (now,))
            active_subscriptions = result.scalar() or 0
        except Exception:
            active_subscriptions = 0

    # 4. Monthly Revenue: sum transactions.amount where status='completed' (success), created_at in current month
    monthly_revenue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed',
        Transaction.created_at >= current_month_start
    ).scalar() or 0

    # 5. New This Month: new subscriptions created this month (one consistent definition)
    try:
        new_this_month = Subscription.query.filter(
            Subscription.created_at >= current_month_start
        ).count()
    except Exception:
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM subscriptions WHERE created_at >= :start_date
            """), {'start_date': current_month_start})
            new_this_month = result.scalar() or 0
        except Exception:
            new_this_month = 0
    
    # Pending renewals (subscriptions ending soon or pending payment) - handle missing columns
    try:
        pending_renewals = Subscription.query.filter(
            or_(
                Subscription.status == 'pending',
                Subscription.end_date <= datetime.utcnow() + timedelta(days=7)
            )
        ).count()
    except Exception:
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM subscriptions 
                WHERE status = 'pending' OR end_date <= datetime('now', '+7 days')
            """))
            pending_renewals = result.scalar() or 0
        except:
            pending_renewals = 0
    
    # Get filter options
    customers_list = User.query.order_by(User.full_name).all()
    products_list = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    
    return render_template('admin/subscriptions.html',
                         subscriptions=subscriptions_list,
                         trial_subscriptions=trial_subscriptions,
                         active_paid_subscriptions=active_paid_subscriptions,
                         expired_subscriptions=expired_subscriptions,
                         customers=customers_list,
                         products=products_list,
                         active_subscriptions=active_subscriptions,
                         total_customers=total_customers,
                         active_customers_count=active_customers_count,
                         inactive_customers_count=inactive_customers_count,
                         monthly_revenue=float(monthly_revenue),
                         new_this_month=new_this_month,
                         pending_renewals=pending_renewals,
                         filter_customer_id=customer_id,
                         filter_product_id=product_id,
                         filter_status=status_filter,
                         search_query=search_query,
                         sort_by=sort_by)

@admin_subscriptions_bp.route('/subscriptions/<int:subscription_id>')
@admin_required
def view_subscription(subscription_id):
    """View subscription details"""
    subscription = Subscription.query.get_or_404(subscription_id)
    transactions = Transaction.query.filter_by(subscription_id=subscription_id).order_by(Transaction.created_at.desc()).all()
    return render_template('admin/subscription_detail.html', subscription=subscription, transactions=transactions)

@admin_subscriptions_bp.route('/subscriptions/<int:subscription_id>/approve', methods=['POST'])
@admin_required
def approve_subscription(subscription_id):
    """Approve subscription - Admin only"""
    admin = get_current_admin()
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Check if there's a pending transaction
    transaction = Transaction.query.filter_by(
        subscription_id=subscription_id,
        status='pending'
    ).first()
    
    if transaction:
        # Update transaction status and keep subscription.payment_status in sync (atomic)
        transaction.status = 'completed'
        if hasattr(subscription, 'payment_status'):
            subscription.payment_status = 'completed'

    # Approve subscription
    subscription.status = 'approved'
    subscription.approved_by = admin.id if admin else None
    subscription.approved_at = datetime.utcnow()
    subscription.rejection_reason = None  # Clear any previous rejection reason

    # If we did not update a transaction, sync payment_status from any completed transaction (fallback)
    if not transaction and hasattr(subscription, 'payment_status'):
        from utils.payment_status_helper import sync_subscription_payment_status
        sync_subscription_payment_status(subscription)

    try:
        db.session.commit()
        
        # Create audit notification for approval
        try:
            from utils.notifications import notify_approval_action
            notify_approval_action('approve', 'subscription', subscription_id, success=True)
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Failed to create approval notification: {str(e)}", exc_info=True)
        
        flash(f'Subscription #{subscription_id} approved successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        
        # Create audit notification for failed approval
        try:
            from utils.notifications import notify_approval_action
            notify_approval_action('approve', 'subscription', subscription_id, success=False, error_message=str(e))
        except:
            pass
        
        flash(f'Error approving subscription: {e}', 'error')
    
    return redirect(url_for('admin_subscriptions.view_subscription', subscription_id=subscription_id))

@admin_subscriptions_bp.route('/subscriptions/<int:subscription_id>/reject', methods=['POST'])
@admin_required
def reject_subscription(subscription_id):
    """Reject subscription - Admin only"""
    admin = get_current_admin()
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Get rejection reason from form
    rejection_reason = request.form.get('rejection_reason', '').strip()
    
    # Reject subscription
    subscription.status = 'rejected'
    subscription.approved_by = None  # Clear approval if previously approved
    subscription.approved_at = None
    subscription.rejection_reason = rejection_reason if rejection_reason else None
    
    try:
        db.session.commit()
        
        # Create audit notification for rejection
        try:
            from utils.notifications import notify_approval_action
            notify_approval_action('reject', 'subscription', subscription_id, success=True)
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Failed to create rejection notification: {str(e)}", exc_info=True)
        
        flash(f'Subscription #{subscription_id} rejected.', 'success')
    except Exception as e:
        db.session.rollback()
        
        # Create audit notification for failed rejection
        try:
            from utils.notifications import notify_approval_action
            notify_approval_action('reject', 'subscription', subscription_id, success=False, error_message=str(e))
        except:
            pass
        
        flash(f'Error rejecting subscription: {e}', 'error')
    
    return redirect(url_for('admin_subscriptions.view_subscription', subscription_id=subscription_id))

@admin_subscriptions_bp.route('/subscriptions/<int:subscription_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_subscription(subscription_id):
    """Edit subscription"""
    subscription = Subscription.query.get_or_404(subscription_id)
    
    if request.method == 'POST':
        status = request.form.get('status', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        
        errors = []
        
        if status not in ['active', 'pending', 'expired', 'cancelled']:
            errors.append('Invalid status.')
        
        if not start_date:
            errors.append('Start date is required.')
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            except:
                errors.append('Invalid start date format.')
        
        if not end_date:
            errors.append('End date is required.')
        else:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except:
                errors.append('Invalid end date format.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            products = Product.query.filter_by(is_active=True).all()
            return render_template('admin/subscription_form.html', subscription=subscription, products=products)
        
        subscription.status = status
        subscription.start_date = start_date
        subscription.end_date = end_date
        
        try:
            db.session.commit()
            flash(f'Subscription #{subscription_id} updated successfully!', 'success')
            return redirect(url_for('admin_subscriptions.view_subscription', subscription_id=subscription_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating subscription: {e}', 'error')
    
    products = Product.query.filter_by(is_active=True).all()
    return render_template('admin/subscription_form.html', subscription=subscription, products=products)

@admin_subscriptions_bp.route('/subscriptions/<int:subscription_id>/delete', methods=['POST'])
@admin_required
def delete_subscription(subscription_id):
    """Delete subscription"""
    subscription = Subscription.query.get_or_404(subscription_id)
    
    try:
        db.session.delete(subscription)
        db.session.commit()
        flash(f'Subscription #{subscription_id} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting subscription: {e}', 'error')
    
    return redirect(url_for('admin_subscriptions.subscriptions'))

@admin_subscriptions_bp.route('/subscriptions/start', methods=['GET', 'POST'])
@admin_required
def start_subscription():
    """Manually start a subscription for a customer"""
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        product_id = request.form.get('product_id', type=int)
        start_date = request.form.get('start_date', '').strip()
        duration_days = request.form.get('duration_days', type=int)
        
        errors = []
        
        if not user_id:
            errors.append('Please select a customer.')
        if not product_id:
            errors.append('Please select a product.')
        if not start_date:
            errors.append('Start date is required.')
        if not duration_days or duration_days <= 0:
            errors.append('Valid duration is required.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            users = User.query.order_by(User.full_name).all()
            products = Product.query.filter_by(is_active=True).all()
            return render_template('admin/subscription_form.html', users=users, products=products, form=request.form)
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = start_date + timedelta(days=duration_days)
        except:
            flash('Invalid date format.', 'error')
            users = User.query.order_by(User.full_name).all()
            products = Product.query.filter_by(is_active=True).all()
            return render_template('admin/subscription_form.html', users=users, products=products, form=request.form)
        
        # Create subscription (admin-created subscriptions are auto-approved)
        admin = get_current_admin()
        new_subscription = Subscription(
            user_id=user_id,
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
            status='approved',
            approved_by=admin.id,
            approved_at=datetime.utcnow()
        )
        
        try:
            db.session.add(new_subscription)
            db.session.commit()
            flash('Subscription started successfully!', 'success')
            return redirect(url_for('admin_subscriptions.subscriptions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error starting subscription: {e}', 'error')
    
    users = User.query.order_by(User.full_name).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template('admin/subscription_form.html', users=users, products=products)
