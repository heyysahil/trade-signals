"""
Payment gateway utility functions (manual/ref logic)
"""
import uuid
from datetime import datetime

def generate_payment_reference():
    """Generate unique payment reference"""
    return f"PAY-{uuid.uuid4().hex[:12].upper()}-{datetime.now().strftime('%Y%m%d')}"

def process_payment(amount, payment_method, user_id, subscription_id=None):
    """
    Process payment manually or via reference
    
    Args:
        amount: Payment amount
        payment_method: Payment method (manual, reference, etc.)
        user_id: User ID
        subscription_id: Optional subscription ID
    
    Returns:
        dict: Payment result with status and reference
    """
    payment_ref = generate_payment_reference()
    
    # TODO: Implement actual payment processing logic
    # This could integrate with payment gateways or handle manual processing
    
    return {
        'status': 'pending',
        'reference': payment_ref,
        'amount': amount,
        'payment_method': payment_method
    }

def verify_payment(reference):
    """Verify payment status by reference"""
    # TODO: Implement payment verification
    pass

def process_refund(transaction_id, amount=None):
    """Process refund for a transaction"""
    # TODO: Implement refund logic
    pass
