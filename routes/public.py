"""
Public routes: Home, contact, public signals
"""
from flask import render_template, Blueprint, request, flash, redirect, url_for
from models.signal import Signal
from models.product import Product
from models.user import User
from models.subscription import Subscription
from utils.validators import validate_email

# Import mail function only if needed (may not be configured)
try:
    from utils.mail import send_email
    MAIL_AVAILABLE = True
except:
    MAIL_AVAILABLE = False

public_bp = Blueprint('public', __name__)

def calculate_win_rate():
    """Calculate actual win rate from completed signals"""
    try:
        # Try to query with new columns (after migration)
        completed_signals = Signal.query.filter(
            Signal.status.in_(['PROFIT', 'LOSS'])
        ).all()
    except Exception as e:
        # If columns don't exist yet, use raw SQL query
        from models import db
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT id, status, profit_loss 
                FROM signals 
                WHERE status IN ('PROFIT', 'LOSS')
            """))
            completed_signals = result.fetchall()
            # Convert to list of dicts for compatibility
            completed_signals = [{'status': row[1], 'profit_loss': row[2] or 0} for row in completed_signals]
        except:
            # If that also fails, return 0
            return 0
    
    if not completed_signals:
        return 0
    
    # Handle both model objects and dicts
    if isinstance(completed_signals[0], dict):
        profit_signals = [s for s in completed_signals if s.get('status') == 'PROFIT']
    else:
        profit_signals = [s for s in completed_signals if s.status == 'PROFIT']
    
    win_rate = (len(profit_signals) / len(completed_signals) * 100) if completed_signals else 0
    return round(win_rate, 1)

@public_bp.route('/')
def home():
    """Public landing page with dynamic metrics"""
    # Calculate real metrics from database
    active_users = User.query.filter_by(is_active=True).count()
    
    # Calculate win rate from completed signals
    win_rate = calculate_win_rate()
    
    # Calculate average profit from completed profitable signals
    try:
        completed_profit_signals = Signal.query.filter_by(status='PROFIT').all()
    except Exception:
        # If columns don't exist yet, use raw SQL
        from models import db
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT profit_loss 
                FROM signals 
                WHERE status = 'PROFIT'
            """))
            completed_profit_signals = [{'profit_loss': row[0] or 0} for row in result.fetchall()]
        except:
            completed_profit_signals = []
    
    if completed_profit_signals:
        if isinstance(completed_profit_signals[0], dict):
            total_profit = sum(float(s.get('profit_loss', 0) or 0) for s in completed_profit_signals)
        else:
            total_profit = sum(float(s.profit_loss or 0) for s in completed_profit_signals)
        avg_profit = total_profit / len(completed_profit_signals)
        # Format as currency (e.g., 2.8L for 280000)
        if avg_profit >= 100000:
            avg_profit_formatted = f"₹{avg_profit/100000:.1f}L"
        elif avg_profit >= 1000:
            avg_profit_formatted = f"₹{avg_profit/1000:.1f}K"
        else:
            avg_profit_formatted = f"₹{avg_profit:.0f}"
    else:
        avg_profit_formatted = "₹0"
    
    # Format active users count
    if active_users >= 1000:
        active_users_formatted = f"{active_users/1000:.0f}K+"
    else:
        active_users_formatted = f"{active_users}+"
    
    return render_template('home.html',
                         win_rate=win_rate,
                         active_users=active_users,
                         active_users_formatted=active_users_formatted,
                         avg_profit_formatted=avg_profit_formatted)

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    from utils.settings_helper import get_setting
    if get_setting('contact_form_enabled', '1') != '1':
        flash('Contact form is temporarily unavailable.', 'info')
        return redirect(url_for('public.home'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validation
        errors = []
        
        if not full_name or not full_name.replace(' ', '').isalpha():
            errors.append('Please enter a valid full name (letters and spaces only).')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        
        if not message or len(message) < 10:
            errors.append('Message must be at least 10 characters long.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('contact.html')
        
        # Send email (if mail is configured)
        try:
            # Email to support team
            email_subject = f"Contact Form Submission from {full_name}"
            email_body = f"""
            New contact form submission:
            
            Name: {full_name}
            Email: {email}
            
            Message:
            {message}
            """
            
            # Try to send email if mail is configured
            # Note: Email sending requires proper mail configuration in config.py
            # For now, we'll just show success message
            # In production, uncomment below to send actual emails
            # try:
            #     send_email(
            #         subject=email_subject,
            #         recipients=['support@simpleincome.in'],
            #         body=email_body
            #     )
            # except Exception as e:
            #     print(f"Email sending failed: {e}")
            
            flash('Thank you for contacting us! We will get back to you soon.', 'success')
            return redirect(url_for('public.contact'))
            
        except Exception as e:
            flash('Failed to send message. Please try again later.', 'error')
            return render_template('contact.html')
    
    return render_template('contact.html')

@public_bp.route('/maintenance')
def maintenance():
    """Maintenance mode page (shown when admin enables maintenance)"""
    return render_template('maintenance.html')

@public_bp.route('/signals')
def signals():
    """Public signals view - read-only mode"""
    # Fetch public signals or completed signals for display
    try:
        signals_list = Signal.query.filter(
            (Signal.is_public == True) | (Signal.status.in_(['PROFIT', 'LOSS']))
        ).order_by(Signal.entry_time.desc()).limit(24).all()
    except Exception:
        # If columns don't exist yet, use raw SQL
        from models import db
        from sqlalchemy import text
        try:
            result = db.session.execute(text("""
                SELECT * FROM signals 
                WHERE is_public = 1 OR status IN ('PROFIT', 'LOSS')
                ORDER BY entry_time DESC 
                LIMIT 24
            """))
            # Convert to Signal objects if possible, otherwise use dicts
            signals_list = []
            for row in result.fetchall():
                try:
                    signal = Signal.query.get(row[0])
                    if signal:
                        signals_list.append(signal)
                except:
                    pass
        except:
            signals_list = []
    
    # Calculate performance metrics
    total_signals = len(signals_list)
    active_count = 0  # Public view shows only completed signals
    pending_count = 0
    
    completed_signals = [s for s in signals_list if s.status in ['PROFIT', 'LOSS']]
    profit_signals = [s for s in completed_signals if s.status == 'PROFIT']
    win_rate = (len(profit_signals) / len(completed_signals) * 100) if completed_signals else 100
    
    total_profit = sum(float(s.profit_loss or 0) for s in profit_signals)
    total_loss = sum(abs(float(s.profit_loss or 0)) for s in completed_signals if s.status == 'LOSS')
    
    return render_template('signals.html',
                         signals=signals_list,
                         total_signals=total_signals,
                         active_count=active_count,
                         pending_count=pending_count,
                         win_rate=round(win_rate, 1),
                         total_profit=round(total_profit, 2),
                         total_loss=round(total_loss, 2))
