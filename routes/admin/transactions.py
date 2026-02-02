"""
Admin transaction management routes
"""
from flask import render_template, Blueprint, request, redirect, url_for, flash, make_response
from routes.admin.auth import admin_required, get_current_admin
from models import db
from models.transaction import Transaction
from models.user import User
from models.subscription import Subscription
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import csv
import io

transactions_bp = Blueprint('admin_transactions', __name__, url_prefix='/admin')

@transactions_bp.route('/transactions')
@admin_required
def transactions():
    """Transaction management page"""
    admin = get_current_admin()

    # Product-specific admins cannot access transactions
    if admin and admin.role != 'superadmin':
        flash('Access denied. Only superadmin can access transactions.', 'error')
        return redirect(url_for('admin_dashboard.dashboard')), 403

    # Get filter parameters
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    customer_id = request.args.get('customer', type=int)
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')

    # Build query for filtered list (table data)
    query = Transaction.query

    # Timezone-safe date filters: compare date part of created_at (UTC) with selected dates
    if start_date:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')  # validate
            query = query.filter(func.date(Transaction.created_at) >= start_date)
        except ValueError:
            pass

    if end_date:
        try:
            datetime.strptime(end_date, '%Y-%m-%d')  # validate
            query = query.filter(func.date(Transaction.created_at) <= end_date)
        except ValueError:
            pass

    if customer_id:
        query = query.filter_by(user_id=customer_id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        search_conditions = [
            User.full_name.ilike(f'%{search_query}%'),
            User.email.ilike(f'%{search_query}%'),
            Transaction.payment_reference.ilike(f'%{search_query}%'),
        ]
        if search_query.isdigit():
            search_conditions.append(Transaction.id == int(search_query))
        query = query.join(User).filter(or_(*search_conditions))

    # Sort (avoid duplicate join: only join User when needed for sort)
    if sort_by == 'date':
        query = query.order_by(Transaction.created_at.desc())
    elif sort_by == 'amount':
        query = query.order_by(Transaction.amount.desc())
    elif sort_by == 'customer':
        if not search_query:
            query = query.join(User)
        query = query.order_by(User.full_name)

    transactions_list = query.all()

    # Summary statistics: always global (ignore filters), so cards show consistent totals
    total_transactions = Transaction.query.count()

    # Total revenue: sum only successful payments (status = 'completed')
    total_revenue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.status == 'completed'
    ).scalar() or 0

    # Success rate: completed / all (global)
    completed_count = Transaction.query.filter_by(status='completed').count()
    all_count = Transaction.query.count()
    success_rate = (completed_count / all_count * 100) if all_count > 0 else 0

    # Average transaction: average amount of completed transactions only (global)
    avg_transaction = db.session.query(func.avg(Transaction.amount)).filter(
        Transaction.status == 'completed'
    ).scalar() or 0
    
    # Get filter options
    customers_list = User.query.order_by(User.full_name).all()
    
    return render_template('admin/transactions.html',
                         transactions=transactions_list,
                         customers=customers_list,
                         total_transactions=total_transactions,
                         total_revenue=float(total_revenue),
                         success_rate=round(success_rate, 1),
                         average_transaction=float(avg_transaction),
                         filter_start_date=start_date,
                         filter_end_date=end_date,
                         filter_customer_id=customer_id,
                         filter_status=status_filter,
                         search_query=search_query,
                         sort_by=sort_by)

@transactions_bp.route('/transactions/export/csv')
@admin_required
def export_csv():
    """Export transactions to CSV (same filters as main view)"""
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    customer_id = request.args.get('customer', type=int)
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').strip()

    query = Transaction.query

    if start_date:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(func.date(Transaction.created_at) >= start_date)
        except ValueError:
            pass

    if end_date:
        try:
            datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(func.date(Transaction.created_at) <= end_date)
        except ValueError:
            pass

    if customer_id:
        query = query.filter_by(user_id=customer_id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search_query:
        search_conditions = [
            User.full_name.ilike(f'%{search_query}%'),
            User.email.ilike(f'%{search_query}%'),
            Transaction.payment_reference.ilike(f'%{search_query}%'),
        ]
        if search_query.isdigit():
            search_conditions.append(Transaction.id == int(search_query))
        query = query.join(User).filter(or_(*search_conditions))

    transactions = query.order_by(Transaction.created_at.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Transaction ID', 'Date', 'Customer', 'Amount', 
        'Payment Method', 'Reference Number', 'Status', 'Subscription'
    ])
    
    # Write data
    for transaction in transactions:
        customer_name = transaction.user.full_name if transaction.user else 'N/A'
        subscription_name = transaction.subscription.product.name if transaction.subscription and transaction.subscription.product else 'N/A'
        
        writer.writerow([
            transaction.id,
            transaction.created_at.strftime('%d-%m-%Y %H:%M') if transaction.created_at else 'N/A',
            customer_name,
            f"{float(transaction.amount):.2f}",
            transaction.payment_method or 'N/A',
            transaction.payment_reference or 'N/A',
            transaction.status,
            subscription_name
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

@transactions_bp.route('/transactions/export/excel')
@admin_required
def export_excel():
    """Export transactions to Excel (CSV format as fallback)"""
    # For now, redirect to CSV export
    # In production, you can use openpyxl or xlsxwriter for true Excel format
    flash('Excel export uses CSV format. Install openpyxl for true Excel support.', 'info')
    return redirect(url_for('admin_transactions.export_csv', **request.args))
