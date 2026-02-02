"""
Authentication routes: Login, register, password reset, email verification (OTP + CAPTCHA)
"""
from datetime import datetime, timedelta
import os
import urllib.parse
import urllib.request

from flask import render_template, request, redirect, url_for, flash, Blueprint, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from models.email_verification import EmailVerificationOTP, CaptchaChallenge, OTPSendLog
from utils.auth_utils import hash_password, verify_password
from utils.validators import validate_email, validate_password
from utils.otp_helper import generate_otp, hash_otp, verify_otp, otp_expires_at
from utils.captcha_helper import create_math_captcha, captcha_expires_at
from utils.verification_token import create_registration_verification_token, verify_registration_verification_token

auth_bp = Blueprint('auth', __name__)

# Rate limiting constants
OTP_RESEND_COOLDOWN_SECONDS = 30
OTP_MAX_SENDS_PER_HOUR = 5
GENERIC_ERROR = "Something went wrong. Please try again later."
CAPTCHA_INVALID_MSG = "Verification failed. Please try again."
OTP_SEND_FAIL_MSG = "Unable to send verification code. Please try again later."
OTP_VERIFY_FAIL_MSG = "Invalid or expired code. Please request a new one."
OTP_BLOCKED_MSG = "Too many attempts. Please request a new code."
OTP_RATE_LIMIT_MSG = "Too many requests. Please try again later."
OTP_RESEND_COOLDOWN_MSG = "Please wait before requesting another code."
OTP_SUCCESS_MSG = "Verification code sent. Check your email."
OTP_VERIFY_SUCCESS_MSG = "Email verified successfully."

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login - accepts mobile or email"""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard.dashboard'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        
        if not identifier or not password:
            flash('Please enter both mobile/email and password.', 'error')
            return render_template('login.html')
        
        # Normalize identifier: lowercase for email, digits only for mobile
        identifier_lower = identifier.lower()
        identifier_digits = ''.join(filter(str.isdigit, identifier))
        
        # Try to find user by mobile or email (normalized)
        user = None
        if identifier_digits:
            # Try mobile first (if identifier contains digits)
            user = User.query.filter_by(mobile=identifier_digits).first()
        
        if not user and identifier_lower:
            # Try email (normalized to lowercase)
            user = User.query.filter_by(email=identifier_lower).first()
        
        if user:
            # User found, verify password
            if verify_password(user.password_hash, password):
                if not user.is_active:
                    flash('Your account is inactive. Please contact support.', 'error')
                    return render_template('login.html')
                
                login_user(user, remember=True)  # Enable remember me for session persistence
                flash(f'Welcome back, {user.full_name}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('user_dashboard.dashboard'))
            else:
                # Password incorrect
                flash('Invalid password. Please check your password and try again.', 'error')
        else:
            # User not found
            flash('No account found with this mobile/email. Please check your credentials or register a new account.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard.dashboard'))

    from utils.settings_helper import get_setting
    if get_setting('allow_registration', '1') != '1':
        flash('Registration is currently closed. Please try again later.', 'info')
        return redirect(url_for('public.home'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()  # Will normalize to lowercase later
        password = request.form.get('password', '')
        retype_password = request.form.get('retype_password', '')
        verification_token = request.form.get('verification_token', '').strip()
        
        # If verification_token present, ensure it matches email (proves email was verified)
        email_verified = True  # preserve existing: default True when no token
        if verification_token:
            token_email = verify_registration_verification_token(verification_token)
            email_verified = token_email is not None and token_email == email
        
        # Validation
        errors = []
        
        if not full_name or not full_name.replace(' ', '').isalpha():
            errors.append('Full name is required and must contain only letters and spaces.')
        
        # Normalize mobile (digits only) and email (lowercase)
        mobile_normalized = ''.join(filter(str.isdigit, mobile)) if mobile else ''
        email_normalized = email.lower() if email else ''
        
        # Validate mobile (after normalization)
        if not mobile or not mobile_normalized:
            errors.append('Mobile number is required.')
        elif len(mobile_normalized) < 10 or len(mobile_normalized) > 15:
            errors.append('Mobile number must be between 10 and 15 digits.')
        
        if not validate_email(email_normalized):
            errors.append('Please enter a valid email address.')
        
        is_valid, pwd_error = validate_password(password)
        if not is_valid:
            errors.append(pwd_error)
        
        if password != retype_password:
            errors.append('Passwords do not match.')
        
        # Check if user already exists (using normalized values)
        existing_mobile = User.query.filter_by(mobile=mobile_normalized).first()
        existing_email = User.query.filter_by(email=email_normalized).first()
        
        if existing_mobile:
            errors.append('Mobile number already registered.')
        
        if existing_email:
            errors.append('Email address already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Create new user (email_verified from token when integrated with verify-email step)
        try:
            new_user = User(
                full_name=full_name,
                mobile=mobile_normalized,  # Use normalized mobile
                email=email_normalized,  # Use normalized email
                password_hash=hash_password(password),
                email_verified=email_verified,
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Notify admins of new user registration
            try:
                from utils.mail import send_new_user_notification
                send_new_user_notification(new_user)
            except Exception as e:
                current_app.logger.error(f"Failed to send admin notification for new user: {str(e)}", exc_info=True)
                # Don't fail registration if notification fails
            
            # Create admin notification
            try:
                from utils.notifications import notify_new_user
                notify_new_user(new_user)
            except Exception as e:
                current_app.logger.error(f"Failed to create admin notification for new user: {str(e)}", exc_info=True)
                # Don't fail registration if notification fails
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('public.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request"""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email or not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('forgot_password.html')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Always show success message (security: don't reveal if email exists)
        if user:
            try:
                from utils.auth_utils import generate_reset_token
                from utils.mail import send_password_reset_email
                
                # Generate reset token
                token = generate_reset_token(user)
                
                # Build reset URL
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                
                # Send reset email
                send_password_reset_email(user, reset_url)
                
                flash('If an account exists with that email, a password reset link has been sent.', 'success')
            except Exception as e:
                current_app.logger.error(f"Error sending password reset email: {str(e)}", exc_info=True)
                # Still show success message for security
                flash('If an account exists with that email, a password reset link has been sent.', 'success')
        else:
            # Show success even if user doesn't exist (security best practice)
            flash('If an account exists with that email, a password reset link has been sent.', 'success')
        
        return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard.dashboard'))
    
    from utils.auth_utils import verify_reset_token
    
    # Verify token
    user = verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired password reset link. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        retype_password = request.form.get('retype_password', '')
        
        # Validation
        errors = []
        
        is_valid, pwd_error = validate_password(password)
        if not is_valid:
            errors.append(pwd_error)
        
        if password != retype_password:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('reset_password.html', token=token)
        
        # Update password
        try:
            user.password_hash = hash_password(password)
            db.session.commit()
            flash('Your password has been reset successfully! Please login with your new password.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting password: {str(e)}", exc_info=True)
            flash('Failed to reset password. Please try again.', 'error')
    
    return render_template('reset_password.html', token=token)


# ---------- Email verification (OTP + CAPTCHA) ----------

def _cleanup_expired_verification_data():
    """Remove expired OTP, CAPTCHA and old send-log records."""
    now = datetime.utcnow()
    try:
        EmailVerificationOTP.query.filter(EmailVerificationOTP.otp_expires_at <= now).delete()
        CaptchaChallenge.query.filter(CaptchaChallenge.captcha_expires_at <= now).delete()
        cutoff = now - timedelta(hours=24)
        OTPSendLog.query.filter(OTPSendLog.sent_at <= cutoff).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()


def _validate_captcha_custom(captcha_id, captcha_answer):
    """Validate custom math CAPTCHA. One-time use, expires 2 min."""
    if not captcha_id or not captcha_answer:
        return False
    cap = CaptchaChallenge.query.get(captcha_id)
    if not cap or cap.used or cap.is_expired():
        return False
    ok = str(cap.captcha_answer).strip() == str(captcha_answer).strip()
    if ok:
        cap.used = 1
        db.session.commit()
    return ok


def _validate_recaptcha(token):
    """Verify Google reCAPTCHA v2 token (if RECAPTCHA_SECRET_KEY is set)."""
    secret = os.environ.get("RECAPTCHA_SECRET_KEY") or current_app.config.get("RECAPTCHA_SECRET_KEY")
    if not secret or not token:
        return False
    try:
        import json as _json
        data = urllib.parse.urlencode({"secret": secret, "response": token}).encode()
        req = urllib.request.Request("https://www.google.com/recaptcha/api/siteverify", data=data, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            out = _json.loads(r.read().decode())
        return out.get("success") is True
    except Exception:
        return False


@auth_bp.route('/auth/captcha', methods=['GET'])
def api_captcha():
    """Return a new custom math CAPTCHA. Frontend must solve before sending OTP."""
    try:
        _cleanup_expired_verification_data()
        captcha_id, question, answer = create_math_captcha()
        cap = CaptchaChallenge(
            captcha_id=captcha_id,
            captcha_answer=answer,
            captcha_expires_at=captcha_expires_at(),
        )
        db.session.add(cap)
        db.session.commit()
        return jsonify({"captcha_id": captcha_id, "question": question})
    except Exception as e:
        current_app.logger.error(f"Error generating CAPTCHA: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": "Failed to generate security check. Please try again."}), 500


@auth_bp.route('/auth/send-verification-otp', methods=['POST'])
def api_send_verification_otp():
    """
    Send OTP to email after CAPTCHA validation.
    Input (JSON or form): email, and either (captcha_id + captcha_answer) or captcha_token.
    """
    try:
        _cleanup_expired_verification_data()
        data = request.get_json(silent=True) or request.form
        email = (data.get("email") or "").strip().lower()
        captcha_token = (data.get("captcha_token") or "").strip()
        captcha_id = (data.get("captcha_id") or "").strip()
        captcha_answer = (data.get("captcha_answer") or "").strip()

        if not email or not validate_email(email):
            return jsonify({"success": False, "message": "Please provide a valid email address."}), 400

        # 1) CAPTCHA: require either reCAPTCHA token or custom captcha_id + answer
        captcha_ok = False
        if captcha_token:
            captcha_ok = _validate_recaptcha(captcha_token)
        if not captcha_ok and captcha_id and captcha_answer:
            captcha_ok = _validate_captcha_custom(captcha_id, captcha_answer)
        if not captcha_ok:
            return jsonify({"success": False, "message": CAPTCHA_INVALID_MSG}), 400

        # 2) Rate limit: max OTP sends per hour
        since = datetime.utcnow() - timedelta(hours=1)
        recent_sends = OTPSendLog.query.filter(OTPSendLog.email == email, OTPSendLog.sent_at >= since).count()
        if recent_sends >= OTP_MAX_SENDS_PER_HOUR:
            return jsonify({"success": False, "message": OTP_RATE_LIMIT_MSG}), 429

        # 3) Resend cooldown: same email must wait OTP_RESEND_COOLDOWN_SECONDS
        existing = EmailVerificationOTP.query.get(email)
        if existing and existing.otp_sent_at:
            delta = (datetime.utcnow() - existing.otp_sent_at).total_seconds()
            if delta < OTP_RESEND_COOLDOWN_SECONDS:
                return jsonify({
                    "success": False,
                    "message": OTP_RESEND_COOLDOWN_MSG,
                    "retry_after_seconds": max(1, int(OTP_RESEND_COOLDOWN_SECONDS - delta)),
                }), 429

        # Check if mail is configured BEFORE generating OTP
        if not current_app.config.get('MAIL_SERVER') or not current_app.config.get('MAIL_USERNAME'):
            return jsonify({
                "success": False, 
                "message": "Email service is not configured. Please contact support."
            }), 500

        # 4) Generate OTP, hash, store, send email
        otp = generate_otp()
        otp_hash = hash_otp(otp)
        expires = otp_expires_at()
        now = datetime.utcnow()
        row = EmailVerificationOTP.query.get(email)
        if row:
            row.otp_hash = otp_hash
            row.otp_expires_at = expires
            row.otp_attempts = 0
            row.email_verified = 0
            row.otp_sent_at = now
        else:
            row = EmailVerificationOTP(
                email=email,
                otp_hash=otp_hash,
                otp_expires_at=expires,
                otp_attempts=0,
                email_verified=0,
                otp_sent_at=now,
            )
            db.session.add(row)
        db.session.add(OTPSendLog(email=email, sent_at=now))
        try:
            db.session.commit()
            from utils.mail import send_verification_otp_email
            send_verification_otp_email(email, otp)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to send verification OTP to {email}: {str(e)}", exc_info=True)
            error_msg = OTP_SEND_FAIL_MSG
            # Provide more specific error message in development
            if current_app.config.get('DEBUG'):
                error_msg = f"Failed to send email: {str(e)}"
            return jsonify({"success": False, "message": error_msg}), 500
        return jsonify({"success": True, "message": OTP_SUCCESS_MSG})
    except Exception as e:
        current_app.logger.error(f"Unexpected error in api_send_verification_otp: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": GENERIC_ERROR}), 500


@auth_bp.route('/auth/verify-email-otp', methods=['POST'])
def api_verify_email_otp():
    """Verify OTP and mark email as verified. Input: email, otp (JSON or form)."""
    try:
        _cleanup_expired_verification_data()
        data = request.get_json(silent=True) or request.form
        email = (data.get("email") or "").strip().lower()
        otp = (data.get("otp") or "").strip()

        if not email or not validate_email(email):
            return jsonify({"success": False, "message": "Please provide a valid email address."}), 400
        if not otp or not otp.isdigit() or len(otp) != 6:
            return jsonify({"success": False, "message": OTP_VERIFY_FAIL_MSG}), 400

        row = EmailVerificationOTP.query.get(email)
        if not row:
            return jsonify({"success": False, "message": OTP_VERIFY_FAIL_MSG}), 400
        if row.is_expired():
            return jsonify({"success": False, "message": OTP_VERIFY_FAIL_MSG}), 400
        if row.attempts_exceeded():
            return jsonify({"success": False, "message": OTP_BLOCKED_MSG}), 400

        if not verify_otp(otp, row.otp_hash):
            row.otp_attempts += 1
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({"success": False, "message": OTP_VERIFY_FAIL_MSG}), 400

        # Success: invalidate OTP and set user email_verified if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            user.email_verified = True
        db.session.delete(row)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"success": False, "message": GENERIC_ERROR}), 500
        # Issuing a short-lived token for registration so register can set email_verified=True
        verification_token = create_registration_verification_token(email)
        return jsonify({
            "success": True,
            "message": OTP_VERIFY_SUCCESS_MSG,
            "verification_token": verification_token,
        })
    except Exception as e:
        current_app.logger.error(f"Error verifying OTP: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": GENERIC_ERROR}), 500


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email_page():
    """Verify email page: CAPTCHA + Send OTP + OTP input + timer + resend."""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard.dashboard'))
    return render_template('verify_email.html')
