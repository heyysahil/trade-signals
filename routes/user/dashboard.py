"""
User dashboard routes
"""
from flask import render_template, Blueprint
from flask_login import login_required, current_user
from models import db
from models.subscription import Subscription
from models.product import Product
from utils.payment_status_helper import get_subscription_payment_status

dashboard_bp = Blueprint('user_dashboard', __name__, url_prefix='/user')

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Fetch user's subscriptions with product info
    # Handle missing columns gracefully until migration is run
    try:
        subscriptions = db.session.query(Subscription, Product).join(
            Product, Subscription.product_id == Product.id
        ).filter(
            Subscription.user_id == current_user.id
        ).order_by(Subscription.created_at.desc()).all()
    except Exception as e:
        # If columns don't exist yet, use raw SQL query
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT s.*, p.* 
                FROM subscriptions s
                JOIN products p ON s.product_id = p.id
                WHERE s.user_id = :user_id
                ORDER BY s.created_at DESC
            """), {'user_id': current_user.id})
            
            # Convert to subscription objects
            subscriptions = []
            for row in result:
                sub = Subscription.query.get(row[0])  # Get by id
                prod = Product.query.get(row[6])  # Get product by id
                if sub and prod:
                    subscriptions.append((sub, prod))
        except:
            subscriptions = []
    
    # Prepare subscription data: use centralized payment status (sync from transactions if needed)
    subscription_data = []
    for sub, product in subscriptions:
        payment_status = get_subscription_payment_status(sub, sync=True)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        subscription_data.append({
            'subscription': sub,
            'product_name': product.name if product else 'Unknown Product',
            'product': product,
            'payment_status': payment_status,
        })

    return render_template('user/dashboard.html',
                         user=current_user,
                         subscriptions=subscription_data)
