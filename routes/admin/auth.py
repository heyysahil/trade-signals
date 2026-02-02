"""
Admin authentication routes
"""
from flask import render_template, request, redirect, url_for, flash, Blueprint, session, current_app
from models import db
from models.admin import Admin
from utils.validators import validate_email
from utils.auth_utils import generate_admin_reset_token, verify_admin_reset_token
from sqlalchemy import func

admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin login and validate admin exists"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access the admin panel.', 'error')
            return redirect(url_for('admin_auth.login'))
        
        # Validate admin still exists and is active
        admin_id = session.get('admin_id')
        admin = Admin.query.get(admin_id)
        
        if not admin:
            session.clear()
            flash('Admin account not found. Please log in again.', 'error')
            return redirect(url_for('admin_auth.login'))
        
        if not admin.is_active:
            session.clear()
            flash('Your admin account is inactive. Please contact support.', 'error')
            return redirect(url_for('admin_auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    """Decorator to require superadmin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access the admin panel.', 'error')
            return redirect(url_for('admin_auth.login'))
        
        admin_id = session.get('admin_id')
        admin = Admin.query.get(admin_id)
        
        if not admin or not admin.is_active:
            session.clear()
            flash('Admin account not found or inactive.', 'error')
            return redirect(url_for('admin_auth.login'))
        
        if admin.role != 'superadmin':
            flash('Access denied. Superadmin privileges required.', 'error')
            return redirect(url_for('admin_dashboard.dashboard')), 403
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_admin():
    """Helper function to get current admin from session"""
    from flask import session
    if 'admin_id' not in session:
        return None
    admin_id = session.get('admin_id')
    return Admin.query.get(admin_id)

@admin_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    # Redirect if already logged in
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard.dashboard'))
    
    if request.method == 'POST':
        login_id = request.form.get('email', '').strip()  # Can be email or username
        password = request.form.get('password', '')
        
        if not login_id or not password:
            flash('Please enter both email/username and password.', 'error')
            return render_template('admin/login.html')
        
        # If input looks like email, validate format
        if '@' in login_id and not validate_email(login_id):
            flash('Please enter a valid email address.', 'error')
            return render_template('admin/login.html')
        
        # Find admin: try email first (case-insensitive), then username (case-insensitive)
        admin = None
        if '@' in login_id:
            admin = Admin.query.filter(func.lower(Admin.email) == login_id.lower()).first()
        if not admin:
            admin = Admin.query.filter(func.lower(Admin.username) == login_id.lower()).first()
        
        if admin and admin.check_password(password):
            if not admin.is_active:
                flash('Your admin account is inactive. Please contact support.', 'error')
                return render_template('admin/login.html')
            
            # Create admin session with timeout
            session['admin_id'] = admin.id
            session['admin_email'] = admin.email
            session['admin_username'] = admin.username
            session['admin_role'] = admin.role
            session.permanent = True  # Enable session timeout
            
            flash(f'Welcome back, {admin.username}!', 'success')
            next_page = request.args.get('next')
            
            # Redirect based on role
            if next_page:
                return redirect(next_page)
            elif admin.role == 'superadmin':
                return redirect(url_for('admin_dashboard.dashboard'))
            else:
                # Product-specific admins go to signals
                return redirect(url_for('admin_signals.signals'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('admin/login.html')

@admin_auth_bp.route("/logout")
def logout():
    """Admin logout"""
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("admin_auth.login"))


@admin_auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Admin forgot password: enter email, send reset link."""
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email or not validate_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("admin/forgot_password.html")

        admin = Admin.query.filter(Admin.email == email).first()
        if admin:
            try:
                from utils.mail import send_admin_password_reset_email
                token = generate_admin_reset_token(admin)
                reset_url = url_for("admin_auth.reset_password", token=token, _external=True)
                send_admin_password_reset_email(admin, reset_url)
            except Exception as e:
                current_app.logger.error("Admin password reset email error: %s", e, exc_info=True)
        flash("If an admin account exists with that email, a password reset link has been sent.", "success")
        return render_template("admin/forgot_password.html")

    return render_template("admin/forgot_password.html")


@admin_auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Admin reset password with token."""
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard.dashboard"))

    admin = verify_admin_reset_token(token)
    if not admin:
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for("admin_auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        retype = request.form.get("retype_password", "")
        if not password or len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("admin/reset_password.html", token=token)
        if password != retype:
            flash("Passwords do not match.", "error")
            return render_template("admin/reset_password.html", token=token)
        try:
            admin.set_password(password)
            db.session.commit()
            flash("Your admin password has been reset. Please log in with your new password.", "success")
            return redirect(url_for("admin_auth.login"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Admin password reset error: %s", e, exc_info=True)
            flash("Failed to reset password. Please try again.", "error")

    return render_template("admin/reset_password.html", token=token)
