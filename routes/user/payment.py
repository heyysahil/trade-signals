"""
User payment routes
"""
from flask import render_template, request, Blueprint, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db
from models.subscription import Subscription
from models.transaction import Transaction
from models.product import Product
from utils.payment_gateway import generate_payment_reference
from datetime import datetime, timedelta

payment_bp = Blueprint('user_payment', __name__, url_prefix='/user')

@payment_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    """Payment processing"""
    if request.method == 'POST':
        # Handle payment form submission
        payment_method = request.form.get('payment_method')
        transaction_ref = request.form.get('transaction_ref', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Get subscription from session
        subscription_id = session.get('pending_subscription_id')
        if not subscription_id:
            flash('No pending subscription found. Please start a new subscription.', 'error')
            return redirect(url_for('user_products.products'))
        
        subscription = Subscription.query.get(subscription_id)
        if not subscription or subscription.user_id != current_user.id:
            flash('Invalid subscription.', 'error')
            return redirect(url_for('user_products.products'))
        
        if not transaction_ref:
            flash('Transaction reference number is required.', 'error')
            return redirect(url_for('user_payment.payment'))
        
        # Create transaction record
        try:
            amount = float(session.get('subscription_amount', 0))
            payment_ref = generate_payment_reference()
            
            transaction = Transaction(
                user_id=current_user.id,
                subscription_id=subscription.id,
                amount=amount,
                payment_method=payment_method,
                payment_reference=payment_ref,
                status='pending'  # Admin will verify and update to 'completed'
            )
            db.session.add(transaction)
            
            # Update subscription status to pending (will be approved/rejected by admin)
            subscription.status = 'pending'
            subscription.approved_by = None
            subscription.approved_at = None
            subscription.rejection_reason = None
            
            db.session.commit()
            
            # Get product for notification
            product = Product.query.get(subscription.product_id)
            
            # Notify admins of new payment
            try:
                from utils.mail import send_payment_notification
                send_payment_notification(transaction, current_user, product)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send admin notification for payment: {str(e)}", exc_info=True)
                # Don't fail payment if notification fails
            
            # Create admin notification for payment submission
            try:
                from utils.notifications import notify_payment_submitted
                notify_payment_submitted(transaction, current_user, product)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to create admin notification for payment: {str(e)}", exc_info=True)
                # Don't fail payment if notification fails
            
            # Clear session data
            session.pop('pending_subscription_id', None)
            session.pop('subscription_amount', None)
            session.pop('subscription_product_id', None)
            
            flash('Payment submitted successfully! Your subscription will be activated after admin verification.', 'success')
            return redirect(url_for('user_dashboard.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to process payment. Please try again.', 'error')
            return redirect(url_for('user_payment.payment'))
    
    # GET request - show payment page
    subscription_id = session.get('pending_subscription_id')
    if not subscription_id:
        flash('No pending subscription found. Please start a new subscription.', 'error')
        return redirect(url_for('user_products.products'))
    
    subscription = Subscription.query.get(subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        flash('Invalid subscription.', 'error')
        return redirect(url_for('user_products.products'))
    
    # Get subscription details
    product = Product.query.get(subscription.product_id)
    amount = float(session.get('subscription_amount', 0))
    
    # Calculate duration
    duration_days = (subscription.end_date - subscription.start_date).days
    
    # Determine plan name
    if amount == 0:
        plan_name = "Trial Plan"
    else:
        plan_name = "Monthly Plan"
    
    return render_template('user/payment.html',
                         subscription=subscription,
                         product=product,
                         user=current_user,
                         amount=amount,
                         duration_days=duration_days,
                         plan_name=plan_name)
