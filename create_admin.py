"""
Script to create or reset admin user
Run this script to create/reset the default admin user
"""
from app import create_app
from models import db
from models.admin import Admin

def create_admin():
    """Create or reset admin user"""
    app = create_app()
    
    with app.app_context():
        # Check if admin exists
        admin = Admin.query.filter_by(email='admin@simpleincome.in').first()
        
        if admin:
            # Reset existing admin password
            admin.set_password('admin123')
            admin.is_active = True
            admin.role = 'admin'
            db.session.commit()
            print("[SUCCESS] Admin user password reset successfully!")
        else:
            # Create new admin
            admin = Admin(
                username='admin',
                email='admin@simpleincome.in',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("[SUCCESS] Admin user created successfully!")
        
        print("\n" + "="*50)
        print("ADMIN LOGIN CREDENTIALS:")
        print("="*50)
        print("URL: http://127.0.0.1:5000/admin/login")
        print("Email: admin@simpleincome.in")
        print("Password: admin123")
        print("="*50)

if __name__ == '__main__':
    create_admin()
