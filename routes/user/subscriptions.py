"""
User subscription routes
"""
from flask import render_template, Blueprint, request, abort, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db
from models.product import Product
from models.subscription import Subscription
from datetime import datetime, timedelta

subscriptions_bp = Blueprint('user_subscriptions', __name__, url_prefix='/user')

@subscriptions_bp.route('/subscriptions/confirm', methods=['GET', 'POST'])
@login_required
def subscription_confirm():
    """Subscription confirmation page and processing"""
    if request.method == 'POST':
        # Handle form submission
        product_id = request.form.get('product_id', type=int)
        plan_type = request.form.get('plan_type', 'monthly')
        agree_terms = request.form.get('agree_terms')
        
        if not product_id:
            flash('Product ID is required.', 'error')
            return redirect(url_for('user_products.products'))
        
        if not agree_terms:
            flash('You must agree to the Terms of Service and Privacy Policy.', 'error')
            return redirect(url_for('user_subscriptions.subscription_confirm', 
                                  product_id=product_id, plan_type=plan_type))
        
        product = Product.query.get_or_404(product_id)
        if not product.is_active:
            flash('Product is not available.', 'error')
            return redirect(url_for('user_products.products'))
        
        # Calculate plan details
        if plan_type == 'trial':
            price = 0
            duration_days = 3
            plan_name = "Trial Plan"
        else:
            price = float(product.price) if product.price > 0 else 3000
            duration_days = product.duration_days if product.duration_days > 0 else 30
            plan_name = "Monthly Plan"
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=duration_days)
        
        # Create subscription
        try:
            new_subscription = Subscription(
                user_id=current_user.id,
                product_id=product.id,
                start_date=start_date,
                end_date=end_date,
                status='pending'  # Will be activated after payment verification
            )
            db.session.add(new_subscription)
            db.session.flush()  # Get the subscription ID
            
            # Store subscription ID in session for payment page
            session['pending_subscription_id'] = new_subscription.id
            session['subscription_amount'] = price
            session['subscription_product_id'] = product.id
            
            db.session.commit()
            
            # Notify admins of new subscription
            try:
                from utils.mail import send_new_subscription_notification
                send_new_subscription_notification(new_subscription, current_user, product)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send admin notification for new subscription: {str(e)}", exc_info=True)
                # Don't fail subscription creation if notification fails
            
            # Create admin notification for pending subscription
            try:
                from utils.notifications import notify_new_subscription
                notify_new_subscription(new_subscription, current_user, product)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to create admin notification for new subscription: {str(e)}", exc_info=True)
                # Don't fail subscription creation if notification fails
            
            flash('Subscription created successfully. Please complete the payment.', 'success')
            return redirect(url_for('user_payment.payment'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to create subscription. Please try again.', 'error')
            return redirect(url_for('user_products.product_detail', product_id=product_id))
    
    # GET request - show confirmation page
    product_id = request.args.get('product_id', type=int)
    plan_type = request.args.get('plan_type', 'monthly')
    
    if not product_id:
        abort(400, "Product ID is required")
    
    product = Product.query.get_or_404(product_id)
    if not product.is_active:
        abort(404)
    
    # Calculate plan details
    if plan_type == 'trial':
        price = 0
        duration_days = 3
        plan_name = "Trial Plan"
    else:
        price = float(product.price) if product.price > 0 else 3000
        duration_days = product.duration_days if product.duration_days > 0 else 30
        plan_name = "Monthly Plan"
    
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=duration_days)
    
    return render_template('user/subscription_confirm.html', 
                         product=product,
                         plan_type=plan_type,
                         plan_name=plan_name,
                         price=price,
                         duration_days=duration_days,
                         start_date=start_date,
                         end_date=end_date,
                         user=current_user)

@subscriptions_bp.route('/subscriptions/<int:subscription_id>')
@login_required
def view_subscription(subscription_id):
    """View subscription details - User only"""
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # SECURITY: Ensure user can only view their own subscriptions
    if subscription.user_id != current_user.id:
        abort(403)
    
    # Get transaction info
    from models.transaction import Transaction
    from utils.payment_status_helper import get_subscription_payment_status

    transactions = Transaction.query.filter_by(
        subscription_id=subscription_id
    ).order_by(Transaction.created_at.desc()).all()

    latest_transaction = transactions[0] if transactions else None

    # Use centralized payment status (sync from transactions if needed)
    payment_status = get_subscription_payment_status(subscription, sync=True)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Determine plan name
    if subscription.product:
        if subscription.product.price == 0:
            plan_name = "Trial Plan"
        else:
            days = (subscription.end_date - subscription.start_date).days
            if days == 30:
                plan_name = "1 Month Plan"
            elif days == 90:
                plan_name = "3 Months Plan"
            else:
                plan_name = f"{days} Days Plan"
    else:
        plan_name = "N/A"
    
    return render_template('user/subscription_detail.html',
                         subscription=subscription,
                         transactions=transactions,
                         latest_transaction=latest_transaction,
                         payment_status=payment_status,
                         plan_name=plan_name)
