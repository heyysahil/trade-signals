"""
Admin signals management routes
"""
from flask import render_template, Blueprint, request, redirect, url_for, flash, session
from routes.admin.auth import admin_required, get_current_admin
from models import db
from models.signal import Signal
from models.product import Product
from models.subscription import Subscription
from sqlalchemy import func, case
from datetime import datetime
from decimal import Decimal

admin_signals_bp = Blueprint('admin_signals', __name__, url_prefix='/admin')

@admin_signals_bp.route('/signals')
@admin_required
def signals():
    """Signal management page"""
    admin = get_current_admin()
    
    # Get filter parameters
    product_id = request.args.get('product_id', type=int)
    
    # Build query
    query = Signal.query
    
    # Product-specific admin: filter by their assigned category
    if admin and admin.role != 'superadmin' and admin.product_category:
        # Filter products by category, then filter signals by those products
        products_in_category = Product.query.filter_by(name=admin.product_category, is_active=True).all()
        product_ids_in_category = [p.id for p in products_in_category]
        if product_ids_in_category:
            query = query.filter(Signal.product_id.in_(product_ids_in_category))
        else:
            # No products in their category, return empty
            query = query.filter_by(id=-1)  # Impossible filter
    
    if product_id:
        # Additional filter: if product-specific admin, ensure product matches their category
        if admin and admin.role != 'superadmin' and admin.product_category:
            product = Product.query.get(product_id)
            if not product or product.name != admin.product_category:
                flash('Access denied. You can only view signals for your assigned product category.', 'error')
                return redirect(url_for('admin_signals.signals'))
        query = query.filter_by(product_id=product_id)
    
    signals_list = query.order_by(Signal.entry_time.desc()).all()
    
    # Filter products list based on admin role
    if admin and admin.role != 'superadmin' and admin.product_category:
        products_list = Product.query.filter_by(name=admin.product_category, is_active=True).order_by(Product.name).all()
    else:
        products_list = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    
    # Calculate summary statistics
    total_signals = len(signals_list)
    
    # Calculate subscriber count for the filtered product(s) - Only APPROVED subscriptions
    if product_id:
        # Specific product selected
        subscribers_count = Subscription.query.filter_by(
            product_id=product_id,
            status='approved'
        ).count()
    elif admin and admin.role != 'superadmin' and admin.product_category:
        # Product-specific admin: count subscribers for their category
        category_products = Product.query.filter_by(name=admin.product_category).all()
        category_product_ids = [p.id for p in category_products]
        subscribers_count = Subscription.query.filter(
            Subscription.product_id.in_(category_product_ids),
            Subscription.status == 'approved'
        ).count() if category_product_ids else 0
    else:
        # Superadmin viewing all: count total approved subscribers
        subscribers_count = Subscription.query.filter_by(status='approved').count()
    
    # Count pending signals for approval (using same filters as main query)
    pending_query = Signal.query
    if admin and admin.role != 'superadmin' and admin.product_category:
        products_in_category = Product.query.filter_by(name=admin.product_category, is_active=True).all()
        product_ids_in_category = [p.id for p in products_in_category]
        if product_ids_in_category:
            pending_query = pending_query.filter(Signal.product_id.in_(product_ids_in_category))
        else:
            pending_query = pending_query.filter_by(id=-1)
    if product_id:
        pending_query = pending_query.filter_by(product_id=product_id)
    pending_signals_count = pending_query.filter(Signal.approval_status == 'PENDING').count()
    
    # Get product category name for non-superadmin admins
    product_category_name = None
    if admin and admin.role != 'superadmin' and admin.product_category:
        product_category_name = admin.product_category
    
    return render_template('admin/signals.html',
                         signals=signals_list,
                         products=products_list,
                         filter_product_id=product_id,
                         total_signals=total_signals,
                         subscribers_count=subscribers_count,
                         product_category_name=product_category_name,
                         pending_signals_count=pending_signals_count)

@admin_signals_bp.route('/signals/create', methods=['GET', 'POST'])
@admin_required
def create_signal():
    """Create new trading signal"""
    admin = get_current_admin()
    
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        symbol = request.form.get('symbol', '').strip().upper()
        exchange = request.form.get('exchange', '').strip()
        signal_type = request.form.get('signal_type', '').strip()
        entry_price = request.form.get('entry_price', type=float)
        target_price = request.form.get('target_price', type=float)
        stop_loss = request.form.get('stop_loss', type=float)
        live_price = request.form.get('live_price', type=float)
        is_public = request.form.get('is_public') == 'on'
        
        errors = []
        
        # For product-specific admins, validate they're creating signal for their category
        if admin and admin.role != 'superadmin' and admin.product_category:
            if product_id:
                product = Product.query.get(product_id)
                if not product or product.name != admin.product_category:
                    errors.append('You can only create signals for your assigned product category.')
            else:
                errors.append('Product selection is required.')
        
        if not symbol:
            errors.append('Symbol is required.')
        if not signal_type or signal_type not in ['BUY', 'SELL']:
            errors.append('Signal type must be BUY or SELL.')
        if not entry_price or entry_price <= 0:
            errors.append('Valid entry price is required.')
        if product_id and not Product.query.get(product_id):
            errors.append('Invalid product selected.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            # Filter products based on admin role
            if admin and admin.role != 'superadmin' and admin.product_category:
                products = Product.query.filter_by(name=admin.product_category, is_active=True).all()
            else:
                products = Product.query.filter_by(is_active=True).all()
            return render_template('admin/signal_form.html', products=products, form=request.form)
        
        # Create new signal - starts as PENDING for approval
        new_signal = Signal(
            product_id=product_id,
            symbol=symbol,
            exchange=exchange,
            signal_type=signal_type,
            entry_price=Decimal(str(entry_price)),
            target_price=Decimal(str(target_price)) if target_price else None,
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            live_price=Decimal(str(live_price)) if live_price else None,
            status='ACTIVE',  # Trading status
            approval_status='PENDING',  # Admin approval status
            is_public=is_public,
            entry_time=datetime.utcnow()
        )
        
        try:
            db.session.add(new_signal)
            db.session.commit()
            
            # Create admin notification for new signal
            try:
                from utils.notifications import notify_new_signal
                product = Product.query.get(product_id) if product_id else None
                notify_new_signal(new_signal, product)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to create admin notification for new signal: {str(e)}", exc_info=True)
                # Don't fail signal creation if notification fails
            
            flash(f'Signal for {symbol} ({signal_type}) created successfully! It will be visible to subscribers of this package.', 'success')
            return redirect(url_for('admin_signals.signals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating signal: {e}', 'error')
    
    # Filter products based on admin role
    if admin and admin.role != 'superadmin' and admin.product_category:
        products = Product.query.filter_by(name=admin.product_category, is_active=True).all()
    else:
        products = Product.query.filter_by(is_active=True).all()
    
    return render_template('admin/signal_form.html', products=products)

@admin_signals_bp.route('/signals/<int:signal_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_signal(signal_id):
    """Edit trading signal - Superadmin only"""
    admin = get_current_admin()
    signal = Signal.query.get_or_404(signal_id)
    
    # Only superadmin can edit signals
    if not admin or admin.role != 'superadmin':
        flash('Access denied. Only superadmin can edit signals.', 'error')
        return redirect(url_for('admin_signals.signals'))
    
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        symbol = request.form.get('symbol', '').strip().upper()
        exchange = request.form.get('exchange', '').strip()
        signal_type = request.form.get('signal_type', '').strip()
        entry_price = request.form.get('entry_price', type=float)
        target_price = request.form.get('target_price', type=float)
        stop_loss = request.form.get('stop_loss', type=float)
        live_price = request.form.get('live_price', type=float)
        is_public = request.form.get('is_public') == 'on'
        
        errors = []
        
        if not symbol:
            errors.append('Symbol is required.')
        if not signal_type or signal_type not in ['BUY', 'SELL']:
            errors.append('Signal type must be BUY or SELL.')
        if not entry_price or entry_price <= 0:
            errors.append('Valid entry price is required.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            # Filter products based on admin role
            if admin and admin.role != 'superadmin' and admin.product_category:
                products = Product.query.filter_by(name=admin.product_category, is_active=True).all()
            else:
                products = Product.query.filter_by(is_active=True).all()
            return render_template('admin/signal_form.html', signal=signal, products=products, form=request.form)
        
        # Update signal
        signal.product_id = product_id
        signal.symbol = symbol
        signal.exchange = exchange
        signal.signal_type = signal_type
        signal.entry_price = Decimal(str(entry_price))
        signal.target_price = Decimal(str(target_price)) if target_price else None
        signal.stop_loss = Decimal(str(stop_loss)) if stop_loss else None
        signal.live_price = Decimal(str(live_price)) if live_price else None
        signal.is_public = is_public
        signal.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash(f'Signal for {symbol} updated successfully!', 'success')
            return redirect(url_for('admin_signals.signals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating signal: {e}', 'error')
    
    # Filter products based on admin role
    if admin and admin.role != 'superadmin' and admin.product_category:
        products = Product.query.filter_by(name=admin.product_category, is_active=True).all()
    else:
        products = Product.query.filter_by(is_active=True).all()
    
    return render_template('admin/signal_form.html', signal=signal, products=products)

@admin_signals_bp.route('/signals/<int:signal_id>/close', methods=['POST'])
@admin_required
def close_signal(signal_id):
    """Close trading signal and calculate P&L"""
    admin = get_current_admin()
    signal = Signal.query.get_or_404(signal_id)
    
    # Product-specific admins can only close signals in their category
    if admin and admin.role != 'superadmin' and admin.product_category:
        if signal.product:
            if signal.product.name != admin.product_category:
                flash('Access denied. You can only close signals for your assigned product category.', 'error')
                return redirect(url_for('admin_signals.signals'))
    
    if signal.status != 'ACTIVE':
        flash('Only active signals can be closed.', 'error')
        return redirect(url_for('admin_signals.signals'))
    
    exit_price = request.form.get('exit_price', type=float)
    
    if not exit_price or exit_price <= 0:
        flash('Valid exit price is required.', 'error')
        return redirect(url_for('admin_signals.signals'))
    
    # Calculate profit/loss
    signal.exit_price = Decimal(str(exit_price))
    signal.exit_time = datetime.utcnow()
    signal.live_price = Decimal(str(exit_price))
    
    # Calculate P&L
    if signal.signal_type == 'BUY':
        pnl = float(exit_price) - float(signal.entry_price)
    else:  # SELL
        pnl = float(signal.entry_price) - float(exit_price)
    
    signal.profit_loss = Decimal(str(round(pnl, 2)))
    
    # Update status
    if pnl > 0:
        signal.status = 'PROFIT'
    elif pnl < 0:
        signal.status = 'LOSS'
    else:
        signal.status = 'ACTIVE'  # Break even
    
    signal.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        status_text = 'PROFIT' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAK EVEN'
        flash(f'Signal closed with {status_text}. P&L: Rs {abs(pnl):.2f}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error closing signal: {e}', 'error')
    
    return redirect(url_for('admin_signals.signals'))

@admin_signals_bp.route('/signals/<int:signal_id>/approve', methods=['POST'])
@admin_required
def approve_signal(signal_id):
    """Approve signal - Admin only"""
    admin = get_current_admin()
    signal = Signal.query.get_or_404(signal_id)
    
    # Product-specific admins can only approve signals in their category
    if admin and admin.role != 'superadmin' and admin.product_category:
        if signal.product:
            if signal.product.name != admin.product_category:
                flash('Access denied. You can only approve signals for your assigned product category.', 'error')
                return redirect(url_for('admin_signals.signals'))
    
    # Approve signal
    signal.approval_status = 'APPROVED'
    signal.approved_by = admin.id if admin else None
    signal.approved_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Signal for {signal.symbol} approved successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving signal: {e}', 'error')
    
    return redirect(url_for('admin_signals.signals'))

@admin_signals_bp.route('/signals/<int:signal_id>/reject', methods=['POST'])
@admin_required
def reject_signal(signal_id):
    """Reject signal - Admin only"""
    admin = get_current_admin()
    signal = Signal.query.get_or_404(signal_id)
    
    # Product-specific admins can only reject signals in their category
    if admin and admin.role != 'superadmin' and admin.product_category:
        if signal.product:
            if signal.product.name != admin.product_category:
                flash('Access denied. You can only reject signals for your assigned product category.', 'error')
                return redirect(url_for('admin_signals.signals'))
    
    # Reject signal
    signal.approval_status = 'REJECTED'
    signal.approved_by = None
    signal.approved_at = None
    
    try:
        db.session.commit()
        flash(f'Signal for {signal.symbol} rejected.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting signal: {e}', 'error')
    
    return redirect(url_for('admin_signals.signals'))

@admin_signals_bp.route('/signals/<int:signal_id>/delete', methods=['POST'])
@admin_required
def delete_signal(signal_id):
    """Delete trading signal"""
    admin = get_current_admin()
    signal = Signal.query.get_or_404(signal_id)
    
    # Product-specific admins can only delete signals in their category
    if admin and admin.role != 'superadmin' and admin.product_category:
        if signal.product:
            if signal.product.name != admin.product_category:
                flash('Access denied. You can only delete signals for your assigned product category.', 'error')
                return redirect(url_for('admin_signals.signals'))
    
    symbol = signal.symbol
    
    try:
        db.session.delete(signal)
        db.session.commit()
        flash(f'Signal for {symbol} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting signal: {e}', 'error')
    
    return redirect(url_for('admin_signals.signals'))
