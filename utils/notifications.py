"""
Admin notification utility functions
"""
from models import db
from models.admin_notification import AdminNotification
from flask import current_app

def create_notification(notification_type, title, message, related_id=None):
    """
    Create a new admin notification
    
    Args:
        notification_type: 'subscription', 'signal', 'user', or 'system'
        title: Notification title
        message: Notification message
        related_id: Optional ID of related entity (subscription_id, signal_id, user_id)
    
    Returns:
        AdminNotification object or None if creation failed
    """
    try:
        notification = AdminNotification(
            type=notification_type,
            title=title,
            message=message,
            related_id=related_id,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create notification: {str(e)}", exc_info=True)
        return None

def notify_new_user(user):
    """Create notification for new user registration"""
    title = "New User Registered"
    message = f"New user registered: {user.full_name} ({user.email})"
    return create_notification('user', title, message, related_id=user.id)

def notify_new_subscription(subscription, user, product):
    """Create notification for new subscription (pending)"""
    title = "New Subscription Request"
    message = f"User {user.full_name} requested subscription for {product.name} (Status: PENDING)"
    return create_notification('subscription', title, message, related_id=subscription.id)

def notify_payment_submitted(transaction, user, product):
    """Create notification for payment/subscription request"""
    title = "Payment Submitted"
    message = f"User {user.full_name} submitted payment of ₹{transaction.amount} for {product.name}"
    return create_notification('subscription', title, message, related_id=transaction.subscription_id)

def notify_new_signal(signal, product=None):
    """Create notification for new signal creation"""
    product_name = product.name if product else "Unknown Product"
    title = "New Signal Created"
    message = f"New {signal.signal_type} signal for {signal.symbol} in {product_name}"
    return create_notification('signal', title, message, related_id=signal.id)

def notify_signal_approval_required(signal, product=None):
    """Create notification when signal requires approval"""
    product_name = product.name if product else "Unknown Product"
    title = "Signal Requires Approval"
    message = f"{signal.signal_type} signal for {signal.symbol} in {product_name} requires approval"
    return create_notification('signal', title, message, related_id=signal.id)

def notify_approval_action(action_type, entity_type, entity_id, success=True, error_message=None):
    """Create notification for approval/rejection actions (audit)"""
    if success:
        title = f"{action_type.title()} Successful"
        message = f"{entity_type.title()} #{entity_id} was {action_type.lower()}ed successfully"
    else:
        title = f"{action_type.title()} Failed"
        message = f"Failed to {action_type.lower()} {entity_type} #{entity_id}"
        if error_message:
            message += f": {error_message}"
    return create_notification('system', title, message, related_id=entity_id)

def notify_unauthorized_access(admin_id, attempted_action):
    """Create notification for unauthorized access attempt"""
    title = "Unauthorized Access Attempt"
    message = f"Admin #{admin_id} attempted unauthorized action: {attempted_action}"
    return create_notification('system', title, message, related_id=admin_id)
