#!/usr/bin/env python3
"""
Create admin account for testing
"""

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import User

def create_admin_account():
    """Create admin account for testing"""
    app = create_app()
    
    with app.app_context():
        print("👤 Creating Admin Account for Testing")
        print("=" * 40)
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print(f"❌ Admin account 'admin' already exists")
            return False
        
        # Create admin account
        admin = User(
            username='admin',
            email='admin@custech.edu.ng',
            full_name='System Administrator',
            role='admin',
            is_active=True
        )
        admin.set_password('admin')  # Simple password for testing
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"✅ Admin account created successfully!")
        print(f"   Username: admin")
        print(f"   Password: admin")
        print(f"   Email: admin@custech.edu.ng")
        print(f"   Role: admin")
        
        return True

if __name__ == '__main__':
    try:
        success = create_admin_account()
        if success:
            print("\n🎉 Admin Account Creation: SUCCESS")
            sys.exit(0)
        else:
            print("\n❌ Admin Account Creation: FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error creating admin: {str(e)}")
        sys.exit(1)
