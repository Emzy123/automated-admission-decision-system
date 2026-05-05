#!/usr/bin/env python3
"""Initialize database for CUSTECH Admission System"""

from app import create_app, db

def init_database():
    """Create database tables"""
    app = create_app()
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")

if __name__ == "__main__":
    init_database()
