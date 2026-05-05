#!/usr/bin/env python3
"""
Test script to verify JAMB import functionality with automatic account creation
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import AcademicSession, University, Faculty, Programme, Candidate, User
from app.services.candidate_processor import CandidateProcessor

def create_test_data():
    """Create test data for JAMB import testing"""
    app = create_app()
    
    with app.app_context():
        # Create university
        university = University.query.filter_by(short_code='CUSTECH').first()
        if not university:
            university = University(
                name='Confluence University of Science and Technology',
                short_code='CUSTECH',
                formula_type='STANDARD'
            )
            db.session.add(university)
            db.session.flush()
        
        # Create faculty
        faculty = Faculty.query.filter_by(code='ENG').first()
        if not faculty:
            faculty = Faculty(
                university_id=university.id,
                name='Faculty of Engineering',
                code='ENG'
            )
            db.session.add(faculty)
            db.session.flush()
        
        # Create programme
        programme = Programme.query.filter_by(code='CSE').first()
        if not programme:
            programme = Programme(
                university_id=university.id,
                faculty_id=faculty.id,
                name='Computer Science and Engineering',
                code='CSE',
                duration_years=4,
                total_slots=100
            )
            db.session.add(programme)
            db.session.flush()
        
        # Create academic session
        session = AcademicSession.query.filter_by(name='2024/2025').first()
        if not session:
            session = AcademicSession(
                name='2024/2025',
                start_date=datetime(2024, 10, 1).date(),
                end_date=datetime(2025, 9, 30).date(),
                is_active=True
            )
            db.session.add(session)
            db.session.flush()
        
        db.session.commit()
        # Re-query to get bound instances
        session = AcademicSession.query.filter_by(name='2024/2025').first()
        programme = Programme.query.filter_by(code='CSE').first()
        return session, programme

def create_test_jamb_csv():
    """Create a test JAMB CSV file"""
    test_data = [
        {
            'JAMB_REG': '1234567890',
            'FULLNAME': 'John Doe Smith',
            'STATE': 'Kano',
            'LGA': 'Kano Municipal',
            'UTME_SCORE': '250',
            'UTME_ENG': '75',
            'UTME_MATH': '80',
            'UTME_PHY': '70',
            'UTME_CHEM': '65',
            'FIRST_CHOICE': 'Confluence University of Science and Technology',
            'FIRST_COURSE': 'Computer Science and Engineering',
            'WAEC_NO': 'WAEC123456',
            'WAEC_YEAR': '2023',
            'G1_SUBJECT': 'English',
            'G1_GRADE': 'B3',
            'G2_SUBJECT': 'Mathematics',
            'G2_GRADE': 'A1',
            'G3_SUBJECT': 'Physics',
            'G3_GRADE': 'B2',
            'G4_SUBJECT': 'Chemistry',
            'G4_GRADE': 'B2',
            'G5_SUBJECT': 'Biology',
            'G5_GRADE': 'C4'
        },
        {
            'JAMB_REG': '9876543210',
            'FULLNAME': 'Jane Mary Johnson',
            'STATE': 'Lagos',
            'LGA': 'Ikeja',
            'UTME_SCORE': '265',
            'UTME_ENG': '78',
            'UTME_MATH': '85',
            'UTME_PHY': '72',
            'UTME_CHEM': '68',
            'FIRST_CHOICE': 'Confluence University of Science and Technology',
            'FIRST_COURSE': 'Computer Science and Engineering',
            'WAEC_NO': 'WAEC654321',
            'WAEC_YEAR': '2023',
            'G1_SUBJECT': 'English',
            'G1_GRADE': 'B2',
            'G2_SUBJECT': 'Mathematics',
            'G2_GRADE': 'A1',
            'G3_SUBJECT': 'Physics',
            'G3_GRADE': 'B3',
            'G4_SUBJECT': 'Chemistry',
            'G4_GRADE': 'B2',
            'G5_SUBJECT': 'Biology',
            'G5_GRADE': 'C5'
        }
    ]
    
    df = pd.DataFrame(test_data)
    csv_path = os.path.join(os.path.dirname(__file__), 'test_jamb_data.csv')
    df.to_csv(csv_path, index=False)
    return csv_path

def test_jamb_import():
    """Test the JAMB import functionality"""
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing JAMB Import with Automatic Account Creation")
        print("=" * 60)
        
        # Create test data
        session, programme = create_test_data()
        print(f"✅ Created test data: Session {session.name}, Programme {programme.name}")
        
        # Create test CSV
        csv_path = create_test_jamb_csv()
        print(f"✅ Created test CSV: {csv_path}")
        
        # Test the import
        processor = CandidateProcessor()
        result = processor.process_file(csv_path, session.id)
        
        print(f"\n📊 Import Results:")
        print(f"   Created: {result['created']}")
        print(f"   Updated: {result['updated']}")
        print(f"   Skipped: {result['skipped']}")
        print(f"   Errors: {result['errors']}")
        print(f"   Warnings: {result['warnings']}")
        
        # Verify candidates were created
        candidates = Candidate.query.all()
        print(f"\n👥 Candidates in database: {len(candidates)}")
        
        # Verify user accounts were created
        users = User.query.filter_by(role='applicant').all()
        print(f"🔐 Applicant accounts created: {len(users)}")
        
        # Test each candidate has a user account
        print(f"\n🔍 Verifying candidate-user relationships:")
        for candidate in candidates:
            user = User.query.filter_by(username=candidate.jamb_reg_number).first()
            if user:
                print(f"   ✅ {candidate.jamb_reg_number} -> {user.username} ({user.email})")
                # Test password
                if user.check_password('password'):
                    print(f"      🔑 Password verification: SUCCESS")
                else:
                    print(f"      🔑 Password verification: FAILED")
            else:
                print(f"   ❌ {candidate.jamb_reg_number} -> No user account found")
        
        # Clean up
        if os.path.exists(csv_path):
            os.remove(csv_path)
            print(f"\n🧹 Cleaned up test file: {csv_path}")
        
        return result['created'] > 0 and len(users) > 0

if __name__ == '__main__':
    success = test_jamb_import()
    if success:
        print("\n🎉 JAMB Import Test: PASSED")
        sys.exit(0)
    else:
        print("\n❌ JAMB Import Test: FAILED")
        sys.exit(1)
