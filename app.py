"""
Main Flask application entry point for sendsignals
"""
from flask import Flask, jsonify, request, redirect
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User
from utils.mail import mail

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Error handler for API routes to always return JSON
    @app.errorhandler(500)
    def handle_500_error(e):
        """Handle 500 errors and return JSON for API routes"""
        if request.path.startswith('/auth/'):
            return jsonify({"success": False, "message": "Internal server error. Please try again later."}), 500
        # For non-API routes, return the default Flask error page
        return None
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Seed initial products if database is empty
        seed_products()
        # Seed initial admin if database is empty
        seed_admin()
    
    # Register blueprints
    from routes import public_bp, auth_bp
    from routes.user.dashboard import dashboard_bp as user_dashboard_bp
    from routes.user.products import products_bp as user_products_bp
    from routes.user.subscriptions import subscriptions_bp as user_subscriptions_bp
    from routes.user.payment import payment_bp as user_payment_bp
    from routes.user.signals import signals_bp as user_signals_bp
    
    # Register admin blueprints
    from routes.admin.auth import admin_auth_bp
    from routes.admin.dashboard import admin_dashboard_bp
    from routes.admin.customers import customers_bp
    from routes.admin.products import admin_products_bp
    from routes.admin.subscriptions import admin_subscriptions_bp
    from routes.admin.transactions import transactions_bp
    from routes.admin.staff import staff_bp
    from routes.admin.settings import settings_bp
    from routes.admin.cms import cms_bp
    from routes.admin.signals import admin_signals_bp
    from routes.admin.api_keys import api_keys_bp
    from routes.admin.notifications import admin_notifications_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_dashboard_bp)
    app.register_blueprint(user_products_bp)
    app.register_blueprint(user_subscriptions_bp)
    app.register_blueprint(user_payment_bp)
    app.register_blueprint(user_signals_bp)
    
    # Register admin blueprints
    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(admin_products_bp)
    app.register_blueprint(admin_subscriptions_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(cms_bp)
    app.register_blueprint(admin_signals_bp)
    app.register_blueprint(api_keys_bp)
    app.register_blueprint(admin_notifications_bp)

    # Inject app settings into all templates (user-side branding and controls)
    @app.context_processor
    def inject_app_settings():
        from utils.settings_helper import get_setting
        return {
            'app_settings': {
                'website_name': get_setting('website_name', 'Trade Signals'),
                'website_url': get_setting('website_url', 'https://tradesignal.tech'),
                'analyst_name': get_setting('analyst_name', 'Trade Signals Team'),
                'support_email': get_setting('support_email', 'support@tradesignal.tech'),
                'support_phone': get_setting('support_phone', '+91 99999 99999'),
                'privacy_policy_url': get_setting('privacy_policy_url', ''),
                'terms_url': get_setting('terms_url', ''),
                'announcement_banner': get_setting('announcement_banner', '').strip(),
                'allow_registration': get_setting('allow_registration', '1') == '1',
                'contact_form_enabled': get_setting('contact_form_enabled', '1') == '1',
                'show_pricing_on_home': get_setting('show_pricing_on_home', '1') == '1',
            }
        }

    # Maintenance mode: block user-side access (admin and static always allowed)
    @app.before_request
    def check_maintenance():
        from utils.settings_helper import get_setting
        if get_setting('maintenance_mode', '0') != '1':
            return None
        path = request.path
        if path.startswith('/admin') or path.startswith('/static') or path == '/maintenance':
            return None
        return redirect('/maintenance')

    return app

def seed_products():
    """Seed initial products if database is empty"""
    from models.product import Product
    
    # Check if products already exist
    if Product.query.count() > 0:
        return
    
    # Define initial products
    products_data = [
        {
            'name': 'Indices Option',
            'description': 'This is the stocks data',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Stock Option',
            'description': 'This is stock options',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Intraday Stocks',
            'description': 'Intraday stocks help users trade within the same day',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Stocks Short Term',
            'description': 'Invest for the short term in high-momentum stocks and gain quick returns on your investment',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Stocks Long Term',
            'description': 'Stocks suitable for long-term investment',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Multi Bagger Stocks',
            'description': 'Stocks with high growth potential',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Forex Trading',
            'description': 'Forex market trading signals',
            'price': 3000,
            'duration_days': 30
        },
        {
            'name': 'Crypto Trading',
            'description': 'Cryptocurrency trading signals',
            'price': 3000,
            'duration_days': 30
        }
    ]
    
    # Create products
    for product_data in products_data:
        product = Product(**product_data, is_active=True)
        db.session.add(product)
    
    try:
        db.session.commit()
        print("Initial products seeded successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding products: {e}")

def seed_admin():
    """Seed initial superadmin user if database is empty"""
    from models.admin import Admin
    
    # Check if superadmin already exists
    if Admin.query.filter_by(role='superadmin').first():
        return
    
    # Create or update superadmin
    admin = Admin.query.filter_by(email='superadmin@tradesignal.tech').first()
    if not admin:
        admin = Admin(
            username='superadmin',
            email='superadmin@tradesignal.tech',
            role='superadmin',
            is_active=True
        )
        db.session.add(admin)
    else:
        # Update existing admin to superadmin
        admin.username = 'superadmin'
        admin.role = 'superadmin'
        admin.is_active = True
    
    admin.set_password('TradeSignal@2026')  # Default password - change in production!
    
    try:
        db.session.commit()
        print("Superadmin created/updated successfully!")
        print("Email: superadmin@tradesignal.tech")
        print("Password: TradeSignal@2026")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding superadmin: {e}")

# WSGI entry point for cPanel/Passenger (application = Flask app)
app = create_app()
application = app

if __name__ == '__main__':
    app.run(debug=True)
