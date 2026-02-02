"""
Admin product management routes
"""
from flask import render_template, request, Blueprint, redirect, url_for, flash
from routes.admin.auth import admin_required, get_current_admin
from models import db
from models.product import Product
from models.subscription import Subscription
from datetime import datetime

admin_products_bp = Blueprint('admin_products', __name__, url_prefix='/admin')

@admin_products_bp.route('/products')
@admin_required
def products():
    """Product management page"""
    admin = get_current_admin()
    
    # Product-specific admin: only show their assigned category
    if admin and admin.role != 'superadmin' and admin.product_category:
        products_list = Product.query.filter_by(name=admin.product_category, is_active=True).order_by(Product.created_at.desc()).all()
    else:
        products_list = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products_list)

@admin_products_bp.route('/products/<int:product_id>')
@admin_required
def view_product(product_id):
    """View product details"""
    product = Product.query.get_or_404(product_id)
    subscriptions_count = Subscription.query.filter_by(product_id=product_id).count()
    active_subscriptions = Subscription.query.filter_by(product_id=product_id, status='active').count()
    return render_template('admin/product_detail.html', 
                         product=product, 
                         subscriptions_count=subscriptions_count,
                         active_subscriptions=active_subscriptions)

@admin_products_bp.route('/products/create', methods=['GET', 'POST'])
@admin_required
def create_product():
    """Create new product"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        duration_days = request.form.get('duration_days', type=int)
        is_active = request.form.get('is_active') == 'on'
        
        errors = []
        
        if not name:
            errors.append('Product name is required.')
        if not description:
            errors.append('Product description is required.')
        if price is None or price < 0:
            errors.append('Valid price is required.')
        if duration_days is None or duration_days <= 0:
            errors.append('Valid duration (days) is required.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/product_form.html', form=request.form)
        
        # Create new product
        product = Product(
            name=name,
            description=description,
            price=price,
            duration_days=duration_days,
            is_active=is_active
        )
        
        try:
            db.session.add(product)
            db.session.commit()
            flash(f'Product "{name}" created successfully!', 'success')
            return redirect(url_for('admin_products.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating product: {e}', 'error')
    
    return render_template('admin/product_form.html')

@admin_products_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Edit product"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        duration_days = request.form.get('duration_days', type=int)
        is_active = request.form.get('is_active') == 'on'
        
        errors = []
        
        if not name:
            errors.append('Product name is required.')
        if not description:
            errors.append('Product description is required.')
        if price is None or price < 0:
            errors.append('Valid price is required.')
        if duration_days is None or duration_days <= 0:
            errors.append('Valid duration (days) is required.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/product_form.html', product=product, form=request.form)
        
        # Check if deactivating product with active subscriptions
        was_active = product.is_active
        if was_active and not is_active:
            active_subscriptions = Subscription.query.filter_by(
                product_id=product_id,
                status='active'
            ).count()
            
            if active_subscriptions > 0:
                flash(f'Warning: This product has {active_subscriptions} active subscription(s). The product will be deactivated, but existing subscriptions will remain active until they expire.', 'warning')
        
        # Update product
        product.name = name
        product.description = description
        product.price = price
        product.duration_days = duration_days
        product.is_active = is_active
        product.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            
            # If product was deactivated, log it for tracking
            if was_active and not is_active:
                active_subscriptions = Subscription.query.filter_by(
                    product_id=product_id,
                    status='active'
                ).count()
                if active_subscriptions > 0:
                    from flask import current_app
                    current_app.logger.info(f"Product '{name}' deactivated with {active_subscriptions} active subscriptions")
            
            flash(f'Product "{name}" updated successfully!', 'success')
            return redirect(url_for('admin_products.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {e}', 'error')
    
    return render_template('admin/product_form.html', product=product)

@admin_products_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    """Delete product"""
    product = Product.query.get_or_404(product_id)
    name = product.name
    
    # Check if product has active subscriptions
    active_subscriptions = Subscription.query.filter_by(product_id=product_id, status='active').count()
    if active_subscriptions > 0:
        flash(f'Cannot delete product "{name}" because it has {active_subscriptions} active subscription(s). Deactivate it instead.', 'error')
        return redirect(url_for('admin_products.products'))
    
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {e}', 'error')
    
    return redirect(url_for('admin_products.products'))
