"""
Admin staff management routes
"""
from flask import render_template, Blueprint, request, redirect, url_for, flash, session, jsonify
from routes.admin.auth import admin_required, superadmin_required, get_current_admin
from models import db
from models.admin import Admin
from models.product import Product
from utils.validators import validate_email, validate_password

staff_bp = Blueprint('admin_staff', __name__, url_prefix='/admin')

# Product categories (8 categories)
PRODUCT_CATEGORIES = [
    'Indices Option',
    'Stock Option',
    'Intraday Stocks',
    'Stocks Short Term',
    'Stocks Long Term',
    'Multi Bagger Stocks',
    'Forex Trading',
    'Crypto Trading'
]

@staff_bp.route('/staff')
@admin_required
def staff():
    """Staff management page"""
    admin = get_current_admin()
    # Only superadmin can access staff management
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can access staff management.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403
    
    staff_list = Admin.query.order_by(Admin.created_at.desc()).all()
    return render_template('admin/staff.html', staff=staff_list, product_categories=PRODUCT_CATEGORIES)

@staff_bp.route('/staff/create', methods=['GET', 'POST'])
@admin_required
def create_staff():
    """Create new staff member"""
    admin = get_current_admin()
    # Only superadmin can create staff
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can create staff.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        product_category = request.form.get('product_category', '').strip() or None
        is_active = request.form.get('is_active') == 'on'
        
        errors = []
        
        if not username:
            errors.append('Username is required.')
        elif Admin.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        elif Admin.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        # Validate product category if provided
        if product_category and product_category not in PRODUCT_CATEGORIES:
            errors.append('Invalid product category selected.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template(
                'admin/staff_form.html',
                staff=None,
                form=request.form,
                product_categories=PRODUCT_CATEGORIES
            )
        
        # Determine role: superadmin has no category, others are product-specific admins
        role = 'superadmin' if not product_category else 'admin'
        
        # Create new staff
        new_staff = Admin(
            username=username,
            email=email,
            role=role,
            product_category=product_category,
            is_active=is_active
        )
        new_staff.set_password(password)
        
        try:
            db.session.add(new_staff)
            db.session.commit()
            flash(f'Staff member "{username}" created successfully!', 'success')
            return redirect(url_for('admin_staff.staff'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating staff: {e}', 'error')
    
    return render_template('admin/staff_form.html', staff=None, product_categories=PRODUCT_CATEGORIES)

@staff_bp.route('/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_staff(staff_id):
    """Edit staff member"""
    admin = get_current_admin()
    # Only superadmin can edit staff
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can edit staff.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403
    
    staff = Admin.query.get_or_404(staff_id)
    
    # Prevent editing superadmin role
    if staff.role == 'superadmin' and staff.id != admin.id:
        flash('Cannot edit another superadmin account.', 'error')
        return redirect(url_for('admin_staff.staff'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        product_category = request.form.get('product_category', '').strip() or None
        is_active = request.form.get('is_active') == 'on'
        password = request.form.get('password', '').strip()
        
        errors = []
        
        if not username:
            errors.append('Username is required.')
        elif username != staff.username and Admin.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        elif email != staff.email and Admin.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        # Validate product category if provided
        if product_category and product_category not in PRODUCT_CATEGORIES:
            errors.append('Invalid product category selected.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/staff_form.html', staff=staff, form=request.form, product_categories=PRODUCT_CATEGORIES)
        
        # Update staff
        staff.username = username
        staff.email = email
        staff.is_active = is_active
        
        # Update role and category
        if staff.role == 'superadmin':
            # Superadmin cannot have category
            staff.product_category = None
        else:
            # Product-specific admin
            staff.product_category = product_category
            staff.role = 'admin'  # Ensure role is 'admin' for product-specific admins
        
        if password:
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('admin/staff_form.html', staff=staff, form=request.form, product_categories=PRODUCT_CATEGORIES)
            staff.set_password(password)
        
        try:
            db.session.commit()
            flash(f'Staff member "{username}" updated successfully!', 'success')
            return redirect(url_for('admin_staff.staff'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating staff: {e}', 'error')
    
    return render_template('admin/staff_form.html', staff=staff, product_categories=PRODUCT_CATEGORIES)

@staff_bp.route('/staff/<int:staff_id>/delete', methods=['POST'])
@admin_required
def delete_staff(staff_id):
    """Delete staff member"""
    staff = Admin.query.get_or_404(staff_id)
    
    # Prevent deleting yourself
    if staff.id == session.get('admin_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_staff.staff'))
    
    try:
        db.session.delete(staff)
        db.session.commit()
        flash(f'Staff member "{staff.username}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting staff: {e}', 'error')
    
    return redirect(url_for('admin_staff.staff'))

@staff_bp.route('/staff/<int:staff_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(staff_id):
    """Reset staff password (admin-provided). Superadmin only. Returns JSON."""
    admin = get_current_admin()
    if not admin or admin.role != 'superadmin':
        return jsonify({'success': False, 'error': 'Access denied.'}), 403

    staff = Admin.query.get_or_404(staff_id)

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

    staff.set_password(new_password)
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Password has been reset successfully.'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update password. Please try again.'}), 500
