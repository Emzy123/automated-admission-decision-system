#!/usr/bin/env python3
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def init_database():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created.")
        
        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # Create default admin user
            admin_user = User(
                username='admin',
                full_name='System Administrator',
                email='admin@custech.edu.ng',
                role='admin',
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created:")
            print("  Username: admin")
            print("  Password: admin123")
        else:
            print("Admin user already exists.")
        
        # Show all users
        users = User.query.all()
        print(f"\nTotal users in database: {len(users)}")
        for user in users:
            print(f"  - {user.username} ({user.role})")

if __name__ == '__main__':
    init_database()
