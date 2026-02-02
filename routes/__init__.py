"""
Routes package for sendsignals application
"""
# Import routes to register blueprints
from routes import public, auth
from routes.user import dashboard, products, subscriptions, payment, signals
from routes.admin import auth as admin_auth, dashboard, customers, products as admin_products
from routes.admin import subscriptions as admin_subscriptions, transactions, staff, settings, cms

# Export blueprints for registration in app.py
from routes.public import public_bp
from routes.auth import auth_bp
from routes.user.dashboard import dashboard_bp as user_dashboard_bp
from routes.user.products import products_bp as user_products_bp
from routes.user.subscriptions import subscriptions_bp as user_subscriptions_bp
from routes.user.payment import payment_bp as user_payment_bp
from routes.user.signals import signals_bp as user_signals_bp
from routes.admin.auth import admin_auth_bp
from routes.admin.dashboard import admin_dashboard_bp
from routes.admin.customers import customers_bp
from routes.admin.products import admin_products_bp
from routes.admin.subscriptions import admin_subscriptions_bp
from routes.admin.transactions import transactions_bp
from routes.admin.staff import staff_bp
from routes.admin.settings import settings_bp
from routes.admin.cms import cms_bp

__all__ = [
    'public_bp',
    'auth_bp',
    'user_dashboard_bp',
    'user_products_bp',
    'user_subscriptions_bp',
    'user_payment_bp',
    'user_signals_bp',
    'admin_auth_bp',
    'admin_dashboard_bp',
    'customers_bp',
    'admin_products_bp',
    'admin_subscriptions_bp',
    'transactions_bp',
    'staff_bp',
    'settings_bp',
    'cms_bp',
]
