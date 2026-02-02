"""
Centralized payment status logic for subscriptions.
Keeps subscription.payment_status in sync with transactions; provides single source for user-facing display.
"""
from models.transaction import Transaction
from models import db


def _has_payment_status_column(subscription):
    """Check if subscription model has payment_status column (e.g. after migration)."""
    return hasattr(subscription, 'payment_status')

def sync_subscription_payment_status(subscription):
    """
    If subscription has a completed transaction, set subscription.payment_status = 'completed'.
    Otherwise set from latest transaction status. Returns effective payment status.
    Caller should commit if subscription was modified.
    Safe when payment_status column does not exist yet (no-op for persist, still returns correct status).
    """
    completed = Transaction.query.filter_by(
        subscription_id=subscription.id,
        status='completed'
    ).first()
    if completed:
        if _has_payment_status_column(subscription):
            subscription.payment_status = 'completed'
        return 'completed'
    latest = Transaction.query.filter_by(subscription_id=subscription.id).order_by(
        Transaction.created_at.desc()
    ).first()
    if latest:
        status = latest.status or 'pending'
        if _has_payment_status_column(subscription) and getattr(subscription, 'payment_status', None) != status:
            subscription.payment_status = status
        return status
    return getattr(subscription, 'payment_status', None) or 'pending'


def get_subscription_payment_status(subscription, sync=True):
    """
    Return payment status for user-facing display.
    - If sync=True and a completed transaction exists but subscription.payment_status is not 'completed',
      sync subscription.payment_status and return 'completed'.
    - Otherwise return subscription.payment_status if set, else derive from latest transaction.
    """
    if sync:
        return sync_subscription_payment_status(subscription)
    if _has_payment_status_column(subscription) and getattr(subscription, 'payment_status', None):
        return subscription.payment_status
    latest = Transaction.query.filter_by(subscription_id=subscription.id).order_by(
        Transaction.created_at.desc()
    ).first()
    return latest.status if latest else 'pending'
