"""
User product routes
"""
from flask import render_template, Blueprint, abort
from flask_login import login_required, current_user
from models import db
from models.product import Product

products_bp = Blueprint('user_products', __name__, url_prefix='/user')

@products_bp.route('/products')
@login_required
def products():
    """List all active products"""
    # Fetch all active products
    products_list = Product.query.filter_by(is_active=True).order_by(Product.created_at).all()
    
    # Check user's active subscriptions to show which products they already have
    from models.subscription import Subscription
    try:
        user_subscriptions = Subscription.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).all()
        subscribed_product_ids = [sub.product_id for sub in user_subscriptions]
    except Exception:
        # If columns don't exist yet, use raw SQL query
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT product_id 
                FROM subscriptions 
                WHERE user_id = :user_id AND status = 'active'
            """), {'user_id': current_user.id})
            subscribed_product_ids = [row[0] for row in result.fetchall()]
        except:
            subscribed_product_ids = []
    
    return render_template('user/products.html', 
                         products=products_list,
                         subscribed_product_ids=subscribed_product_ids)

@products_bp.route('/products/<int:product_id>')
@login_required
def product_detail(product_id):
    """Product detail page"""
    product = Product.query.get_or_404(product_id)
    if not product.is_active:
        abort(404)
    return render_template('user/product_detail.html', product=product)
