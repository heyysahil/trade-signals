"""
Seed all 9 admins: 1 superadmin + 8 staff (one per product category).
Run: python seed_all_admins.py
"""
import os
from app import create_app
from models import db
from models.admin import Admin

# Same 8 product categories as in routes/admin/staff.py
PRODUCT_CATEGORIES = [
    'Indices Option',
    'Stock Option',
    'Intraday Stocks',
    'Stocks Short Term',
    'Stocks Long Term',
    'Multi Bagger Stocks',
    'Forex Trading',
    'Crypto Trading',
]

def _get_admins():
    """Build admin list; superadmin uses env vars if set (e.g. on Railway)."""
    seed_email = os.environ.get('SEED_ADMIN_EMAIL', 'superadmin@tradesignal.tech').strip().lower()
    seed_password = os.environ.get('SEED_ADMIN_PASSWORD', 'Admin@2026')
    seed_username = (os.environ.get('SEED_ADMIN_USERNAME') or (seed_email.split('@')[0] if '@' in seed_email else 'superadmin')).strip()
    return [
        # Superadmin (env overrides for Railway)
        {'username': seed_username, 'email': seed_email, 'role': 'superadmin', 'product_category': None, 'password': seed_password},
        # Staff: one per product category
        {'username': 'admin_indices', 'email': 'admin_indices@tradesignal.tech', 'role': 'admin', 'product_category': 'Indices Option', 'password': 'Admin@Indices1'},
        {'username': 'admin_stock', 'email': 'admin_stock@tradesignal.tech', 'role': 'admin', 'product_category': 'Stock Option', 'password': 'Admin@Stock1'},
        {'username': 'admin_intraday', 'email': 'admin_intraday@tradesignal.tech', 'role': 'admin', 'product_category': 'Intraday Stocks', 'password': 'Admin@Intraday1'},
        {'username': 'admin_short_term', 'email': 'admin_shortterm@tradesignal.tech', 'role': 'admin', 'product_category': 'Stocks Short Term', 'password': 'Admin@Short1'},
        {'username': 'admin_long_term', 'email': 'admin_longterm@tradesignal.tech', 'role': 'admin', 'product_category': 'Stocks Long Term', 'password': 'Admin@Long1'},
        {'username': 'admin_multi_bagger', 'email': 'admin_multibagger@tradesignal.tech', 'role': 'admin', 'product_category': 'Multi Bagger Stocks', 'password': 'Admin@Multi1'},
        {'username': 'admin_forex', 'email': 'admin_forex@tradesignal.tech', 'role': 'admin', 'product_category': 'Forex Trading', 'password': 'Admin@Forex1'},
        {'username': 'admin_crypto', 'email': 'admin_crypto@tradesignal.tech', 'role': 'admin', 'product_category': 'Crypto Trading', 'password': 'Admin@Crypto1'},
    ]


def seed_all_admins():
    app = create_app()
    admins = _get_admins()
    with app.app_context():
        print("Seeding 9 admins (1 superadmin + 8 staff)...")
        created = 0
        updated = 0
        for data in admins:
            admin = Admin.query.filter(Admin.email.ilike(data['email'])).first()
            if not admin:
                admin = Admin(
                    username=data['username'],
                    email=data['email'],
                    role=data['role'],
                    product_category=data['product_category'],
                    is_active=True,
                )
                db.session.add(admin)
                created += 1
            else:
                admin.username = data['username']
                admin.role = data['role']
                admin.product_category = data['product_category']
                admin.is_active = True
                updated += 1
            admin.set_password(data['password'])

        try:
            db.session.commit()
            print(f"Done. Created: {created}, Updated: {updated}")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            return

        print("\n" + "=" * 60)
        print("ADMIN LOGIN CREDENTIALS (9 admins)")
        print("=" * 60)
        for data in admins:
            cat = data['product_category'] or 'Superadmin'
            print(f"  {data['username']:20} {data['email']:40} {data['password']:18} ({cat})")
        print("=" * 60)
        print("Admin panel: /admin/login")
        print("=" * 60)


if __name__ == '__main__':
    seed_all_admins()
