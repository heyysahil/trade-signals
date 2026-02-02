"""
Reset superadmin password when forgotten.
Run: python reset_superadmin_password.py
     or: python reset_superadmin_password.py "YourNewPassword"
"""
import sys
import getpass

def main():
    from app import create_app
    from models import db
    from models.admin import Admin

    app = create_app()
    with app.app_context():
        # Find superadmin (default email from seed)
        admin = Admin.query.filter_by(email='superadmin@tradesignal.tech').first()
        if not admin:
            admin = Admin.query.filter_by(role='superadmin').first()
        if not admin:
            print("No superadmin found. Check your database.")
            return

        if len(sys.argv) >= 2:
            new_password = sys.argv[1]
        else:
            new_password = getpass.getpass("Enter new password for superadmin: ")
            confirm = getpass.getpass("Confirm new password: ")
            if new_password != confirm:
                print("Passwords do not match. Aborted.")
                return
            if len(new_password) < 6:
                print("Password must be at least 6 characters. Aborted.")
                return

        admin.set_password(new_password)
        try:
            db.session.commit()
            print("[SUCCESS] Superadmin password has been reset.")
            print("  Email:    ", admin.email)
            print("  Username:", admin.username)
            print("You can now log in with the new password.")
        except Exception as e:
            db.session.rollback()
            print("[ERROR]", e)

if __name__ == '__main__':
    main()
