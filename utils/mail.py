"""
Email utility functions
"""
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def send_email(subject, recipients, body, html=None):
    """
    Send an email
    
    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        body: Plain text body
        html: HTML body (optional)
    """
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body,
        html=html
    )
    mail.send(msg)

def send_password_reset_email(user, reset_url):
    """
    Send password reset email to user with reset link.
    
    Args:
        user: User object
        reset_url: Full URL to password reset page with token
    """
    # Check if mail is properly initialized
    if not mail.app:
        raise RuntimeError("Mail extension not initialized. Check app configuration.")
    
    # Check if mail server is configured
    if not current_app.config.get('MAIL_SERVER'):
        raise RuntimeError("MAIL_SERVER not configured. Please set MAIL_SERVER environment variable.")
    
    if not current_app.config.get('MAIL_USERNAME'):
        raise RuntimeError("MAIL_USERNAME not configured. Please set MAIL_USERNAME environment variable.")
    
    subject = "Reset Your Password - SendSignals"
    body = f"""
Hello {user.full_name},

You requested to reset your password for your SendSignals account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email. Your password will remain unchanged.

Best regards,
SendSignals Team
"""
    html = _password_reset_email_html(user.full_name, reset_url)
    msg = Message(
        subject=subject,
        recipients=[user.email],
        body=body,
        html=html,
    )
    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"SMTP error sending password reset email to {user.email}: {str(e)}", exc_info=True)
        raise


def _password_reset_email_html(name: str, reset_url: str) -> str:
    """Clean HTML template for password reset email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Reset Your Password</title></head>
    <body style="font-family: system-ui, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">Reset Your Password</h2>
        <p>Hello {name},</p>
        <p>You requested to reset your password for your SendSignals account.</p>
        <p style="margin: 24px 0;">
            <a href="{reset_url}" 
               style="display: inline-block; padding: 12px 24px; background-color: #16213e; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
                Reset Password
            </a>
        </p>
        <p style="color: #666;">Or copy and paste this link into your browser:</p>
        <p style="color: #999; font-size: 12px; word-break: break-all;">{reset_url}</p>
        <p style="color: #666;">This link will expire in 1 hour.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="font-size: 12px; color: #999;">If you did not request this password reset, please ignore this email. Your password will remain unchanged.</p>
    </body>
    </html>
    """

def send_welcome_email(user):
    """Send welcome email to new user"""
    # TODO: Implement welcome email
    pass

def get_admin_emails():
    """Get list of active admin email addresses for notifications"""
    try:
        from models.admin import Admin
        admins = Admin.query.filter_by(is_active=True).all()
        return [admin.email for admin in admins]
    except Exception:
        return []

def send_admin_notification(subject, body, html=None):
    """
    Send notification email to all active admins.
    Silently fails if mail is not configured.
    """
    if not mail.app:
        return
    
    if not current_app.config.get('MAIL_SERVER'):
        return
    
    admin_emails = get_admin_emails()
    if not admin_emails:
        return
    
    try:
        msg = Message(
            subject=subject,
            recipients=admin_emails,
            body=body,
            html=html
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Error sending admin notification: {str(e)}", exc_info=True)
        # Don't raise - admin notifications are non-critical

def send_new_user_notification(user):
    """Notify admins of new user registration"""
    subject = f"New User Registration - {user.full_name}"
    body = f"""
A new user has registered on SendSignals:

Name: {user.full_name}
Email: {user.email}
Mobile: {user.mobile}
Registered: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}

View user details in admin panel.
"""
    html = _new_user_notification_html(user)
    send_admin_notification(subject, body, html)

def send_new_subscription_notification(subscription, user, product):
    """Notify admins of new subscription request"""
    subject = f"New Subscription Request - {user.full_name}"
    body = f"""
A new subscription has been requested:

User: {user.full_name} ({user.email})
Product: {product.name}
Status: {subscription.status}
Start Date: {subscription.start_date.strftime('%Y-%m-%d') if subscription.start_date else 'N/A'}
End Date: {subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else 'N/A'}

View subscription in admin panel.
"""
    html = _new_subscription_notification_html(subscription, user, product)
    send_admin_notification(subject, body, html)

def send_payment_notification(transaction, user, product):
    """Notify admins of new payment"""
    subject = f"New Payment Received - ₹{float(transaction.amount):.2f}"
    body = f"""
A new payment has been received:

User: {user.full_name} ({user.email})
Amount: ₹{float(transaction.amount):.2f}
Payment Method: {transaction.payment_method or 'N/A'}
Reference: {transaction.payment_reference or 'N/A'}
Status: {transaction.status}
Product: {product.name if product else 'N/A'}

View transaction in admin panel.
"""
    html = _payment_notification_html(transaction, user, product)
    send_admin_notification(subject, body, html)

def _new_user_notification_html(user) -> str:
    """HTML template for new user notification"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>New User Registration</title></head>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">New User Registration</h2>
        <p>A new user has registered on SendSignals:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Name:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{user.full_name}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Email:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{user.email}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Mobile:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{user.mobile}</td></tr>
            <tr><td style="padding: 8px;"><strong>Registered:</strong></td><td style="padding: 8px;">{user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}</td></tr>
        </table>
    </body>
    </html>
    """

def _new_subscription_notification_html(subscription, user, product) -> str:
    """HTML template for new subscription notification"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>New Subscription Request</title></head>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">New Subscription Request</h2>
        <p>A new subscription has been requested:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>User:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{user.full_name} ({user.email})</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Product:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{product.name}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Status:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{subscription.status}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Start Date:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{subscription.start_date.strftime('%Y-%m-%d') if subscription.start_date else 'N/A'}</td></tr>
            <tr><td style="padding: 8px;"><strong>End Date:</strong></td><td style="padding: 8px;">{subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else 'N/A'}</td></tr>
        </table>
    </body>
    </html>
    """

def _payment_notification_html(transaction, user, product) -> str:
    """HTML template for payment notification"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>New Payment Received</title></head>
    <body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">New Payment Received</h2>
        <p>A new payment has been received:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>User:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{user.full_name} ({user.email})</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Amount:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">₹{float(transaction.amount):.2f}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Payment Method:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{transaction.payment_method or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Reference:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{transaction.payment_reference or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Status:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{transaction.status}</td></tr>
            <tr><td style="padding: 8px;"><strong>Product:</strong></td><td style="padding: 8px;">{product.name if product else 'N/A'}</td></tr>
        </table>
    </body>
    </html>
    """


def send_verification_otp_email(email: str, otp: str) -> None:
    """
    Send OTP verification email. Subject: "Verify Your Email Address".
    Uses clean HTML template; fallback plain body.
    """
    # Check if mail is properly initialized
    if not mail.app:
        raise RuntimeError("Mail extension not initialized. Check app configuration.")
    
    # Check if mail server is configured
    if not current_app.config.get('MAIL_SERVER'):
        raise RuntimeError("MAIL_SERVER not configured. Please set MAIL_SERVER environment variable.")
    
    if not current_app.config.get('MAIL_USERNAME'):
        raise RuntimeError("MAIL_USERNAME not configured. Please set MAIL_USERNAME environment variable.")
    
    subject = "Verify Your Email Address"
    body = f"Your verification code is: {otp}. It expires in 5 minutes. Do not share this code."
    html = _otp_email_html(otp)
    msg = Message(
        subject=subject,
        recipients=[email],
        body=body,
        html=html,
    )
    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"SMTP error sending email to {email}: {str(e)}", exc_info=True)
        raise


def _otp_email_html(otp: str) -> str:
    """Clean HTML template for OTP email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Verify Your Email</title></head>
    <body style="font-family: system-ui, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">Verify Your Email Address</h2>
        <p>Use the code below to verify your email:</p>
        <p style="font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #16213e;">{otp}</p>
        <p style="color: #666;">This code expires in 5 minutes. Do not share it with anyone.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="font-size: 12px; color: #999;">If you did not request this, you can ignore this email.</p>
    </body>
    </html>
    """
