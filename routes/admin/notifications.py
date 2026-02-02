"""
Admin notification routes
"""
from flask import Blueprint, jsonify, request
from routes.admin.auth import admin_required, get_current_admin
from models import db
from models.admin_notification import AdminNotification
from models.subscription import Subscription
from models.signal import Signal
from models.user import User
from models.product import Product
from sqlalchemy import or_

admin_notifications_bp = Blueprint('admin_notifications', __name__, url_prefix='/admin')

def get_notifications_for_admin(admin, limit=50):
    """
    Get notifications for admin based on their role
    - Superadmin: All notifications
    - Product-level admin: Only notifications related to their product
    """
    query = AdminNotification.query
    
    # Filter by admin role
    if admin.role != 'superadmin' and admin.product_category:
        # Product-level admin: only see notifications for their product
        # Get product IDs for this category
        products = Product.query.filter_by(name=admin.product_category, is_active=True).all()
        product_ids = [p.id for p in products]
        
        if not product_ids:
            # No products for this admin, return empty
            return []
        
        # Filter notifications by related entities that belong to this product
        # For subscriptions: check subscription.product_id
        # For signals: check signal.product_id
        # For users: show all (users are not product-specific)
        # For system: show all
        
        subscription_ids = db.session.query(Subscription.id).filter(
            Subscription.product_id.in_(product_ids)
        ).subquery()
        
        signal_ids = db.session.query(Signal.id).filter(
            Signal.product_id.in_(product_ids)
        ).subquery()
        
        # Filter notifications
        query = query.filter(
            or_(
                # Subscriptions for this product
                db.and_(
                    AdminNotification.type == 'subscription',
                    AdminNotification.related_id.in_(db.session.query(subscription_ids.c.id))
                ),
                # Signals for this product
                db.and_(
                    AdminNotification.type == 'signal',
                    AdminNotification.related_id.in_(db.session.query(signal_ids.c.id))
                ),
                # Users (all users)
                AdminNotification.type == 'user',
                # System notifications (all)
                AdminNotification.type == 'system'
            )
        )
    
    # Order by newest first
    query = query.order_by(AdminNotification.created_at.desc())
    
    # Limit results
    if limit:
        query = query.limit(limit)
    
    return query.all()

@admin_notifications_bp.route('/notifications')
@admin_required
def get_notifications():
    """Get notifications for current admin"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 401
    
    limit = request.args.get('limit', 50, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    notifications = get_notifications_for_admin(admin, limit=limit)
    
    if unread_only:
        notifications = [n for n in notifications if not n.is_read]
    
    return jsonify({
        'success': True,
        'notifications': [n.to_dict() for n in notifications]
    })

@admin_notifications_bp.route('/notifications/unread-count')
@admin_required
def get_unread_count():
    """Get unread notification count for current admin"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 401
    
    notifications = get_notifications_for_admin(admin, limit=None)
    unread_count = sum(1 for n in notifications if not n.is_read)
    
    return jsonify({
        'success': True,
        'unread_count': unread_count
    })

@admin_notifications_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@admin_required
def mark_as_read(notification_id):
    """Mark a notification as read"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 401
    
    notification = AdminNotification.query.get_or_404(notification_id)
    
    # Verify admin has access to this notification
    admin_notifications = get_notifications_for_admin(admin, limit=None)
    notification_ids = [n.id for n in admin_notifications]
    
    if notification.id not in notification_ids:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    notification.is_read = True
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notification marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
@admin_required
def mark_all_as_read():
    """Mark all notifications as read for current admin"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 401
    
    notifications = get_notifications_for_admin(admin, limit=None)
    unread_notifications = [n for n in notifications if not n.is_read]
    
    try:
        for notification in unread_notifications:
            notification.is_read = True
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'{len(unread_notifications)} notifications marked as read'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_notifications_bp.route('/notifications/<int:notification_id>/redirect')
@admin_required
def redirect_notification(notification_id):
    """Get redirect URL for a notification"""
    from flask import url_for
    
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 401
    
    notification = AdminNotification.query.get_or_404(notification_id)
    
    # Verify admin has access to this notification
    admin_notifications = get_notifications_for_admin(admin, limit=None)
    notification_ids = [n.id for n in admin_notifications]
    
    if notification.id not in notification_ids:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Mark as read when clicked
    notification.is_read = True
    db.session.commit()
    
    # Determine redirect URL based on notification type
    redirect_url = None
    
    if notification.type == 'subscription' and notification.related_id:
        redirect_url = url_for('admin_subscriptions.view_subscription', subscription_id=notification.related_id)
    elif notification.type == 'signal' and notification.related_id:
        redirect_url = url_for('admin_signals.signals')  # Redirect to signals list
    elif notification.type == 'user' and notification.related_id:
        redirect_url = url_for('admin_customers.customers')  # Redirect to customers list
    else:
        redirect_url = url_for('admin_dashboard.dashboard')
    
    return jsonify({
        'success': True,
        'redirect_url': redirect_url
    })
