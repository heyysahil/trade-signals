"""
Admin customer management routes
"""
from flask import render_template, Blueprint, request, redirect, url_for, flash, jsonify
from routes.admin.auth import admin_required, get_current_admin
from models import db
from models.user import User
from models.subscription import Subscription
from utils.validators import validate_email, validate_password
from utils.auth_utils import hash_password

customers_bp = Blueprint('admin_customers', __name__, url_prefix='/admin')

@customers_bp.route('/customers')
@admin_required
def customers():
    """Customer management page"""
    admin = get_current_admin()
    
    # Product-specific admins cannot access customers
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can access customers.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403
    
    # Get filter parameter
    status_filter = request.args.get('status', '')

    # Active customer = at least one subscription with status='approved' AND end_date >= today
    from datetime import datetime
    now = datetime.utcnow()
    active_customer_ids = db.session.query(Subscription.user_id).filter(
        Subscription.status == 'approved',
        Subscription.end_date >= now
    ).distinct().all()
    active_customer_ids = [uid[0] for uid in active_customer_ids]
    
    # Filter customers based on status
    if status_filter == 'active':
        customers_list = User.query.filter(User.id.in_(active_customer_ids)).order_by(User.created_at.desc()).all()
    elif status_filter == 'inactive':
        customers_list = User.query.filter(~User.id.in_(active_customer_ids)).order_by(User.created_at.desc()).all()
    else:
        customers_list = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin/customers.html', 
                         customers=customers_list,
                         status_filter=status_filter,
                         active_customer_ids=active_customer_ids)

@customers_bp.route('/customers/<int:customer_id>')
@admin_required
def view_customer(customer_id):
    """View customer details"""
    customer = User.query.get_or_404(customer_id)
    subscriptions = Subscription.query.filter_by(user_id=customer_id).order_by(Subscription.created_at.desc()).all()
    return render_template('admin/customer_detail.html', customer=customer, subscriptions=subscriptions)

@customers_bp.route('/customers/create', methods=['GET', 'POST'])
@admin_required
def create_customer():
    """Create new customer manually"""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        errors = []
        
        if not full_name:
            errors.append('Full name is required.')
        
        if not mobile or not mobile.isdigit() or not (10 <= len(mobile) <= 15):
            errors.append('Please enter a valid mobile number (10-15 digits).')
        elif User.query.filter_by(mobile=mobile).first():
            errors.append('Mobile number already registered.')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        elif User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        is_password_valid, password_error = validate_password(password)
        if not is_password_valid:
            errors.append(password_error)
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/customer_form.html', form=request.form)
        
        # Create new customer
        new_customer = User(
            full_name=full_name,
            mobile=mobile,
            email=email,
            password_hash=hash_password(password),
            is_active=is_active
        )
        
        try:
            db.session.add(new_customer)
            db.session.commit()
            flash(f'Customer "{full_name}" created successfully!', 'success')
            return redirect(url_for('admin_customers.customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating customer: {e}', 'error')
    
    return render_template('admin/customer_form.html')

@customers_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_customer(customer_id):
    """Edit customer details"""
    customer = User.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        errors = []
        
        if not full_name:
            errors.append('Full name is required.')
        
        if not mobile or not mobile.isdigit() or not (10 <= len(mobile) <= 15):
            errors.append('Please enter a valid mobile number (10-15 digits).')
        elif mobile != customer.mobile and User.query.filter_by(mobile=mobile).first():
            errors.append('Mobile number already registered.')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        elif email != customer.email and User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/customer_form.html', customer=customer, form=request.form)
        
        # Update customer
        customer.full_name = full_name
        customer.mobile = mobile
        customer.email = email
        customer.is_active = is_active
        
        try:
            db.session.commit()
            flash(f'Customer "{full_name}" updated successfully!', 'success')
            return redirect(url_for('admin_customers.customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {e}', 'error')
    
    return render_template('admin/customer_form.html', customer=customer)

@customers_bp.route('/customers/<int:customer_id>/reset-password', methods=['POST'])
@admin_required
def reset_customer_password(customer_id):
    """Reset customer password (admin-provided). Superadmin only. Returns JSON."""
    admin = get_current_admin()
    if not admin or admin.role != 'superadmin':
        return jsonify({'success': False, 'error': 'Access denied.'}), 403

    customer = User.query.get_or_404(customer_id)

    data = request.get_json(silent=True) or {}
    new_password = (data.get('new_password') or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()

    if not new_password:
        return jsonify({'success': False, 'error': 'New password is required.'}), 400
    if len(new_password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters.'}), 400
    if new_password != confirm_password:
        return jsonify({'success': False, 'error': 'Passwords do not match.'}), 400

    is_valid, password_error = validate_password(new_password)
    if not is_valid:
        return jsonify({'success': False, 'error': password_error or 'Invalid password.'}), 400

    customer.password_hash = hash_password(new_password)
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Password has been reset successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update password. Please try again.'}), 500

@customers_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@admin_required
def delete_customer(customer_id):
    """Delete customer (soft delete recommended)"""
    customer = User.query.get_or_404(customer_id)
    
    try:
        # Soft delete - set is_active to False instead of hard delete
        customer.is_active = False
        db.session.commit()
        flash(f'Customer "{customer.full_name}" deactivated successfully!', 'success')
        # TODO: For hard delete, use: db.session.delete(customer)
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {e}', 'error')
    
    return redirect(url_for('admin_customers.customers'))
