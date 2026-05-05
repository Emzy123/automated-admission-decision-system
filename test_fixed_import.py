#!/usr/bin/env python3
"""
Test the fixed import process to ensure O'Level constraint errors are resolved
"""

import pandas as pd
from app import create_app, db
from app.models import Candidate, AcademicSession
from app.services.candidate_processor import CandidateProcessor

def test_fixed_import():
    """Test the fixed import process"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("TESTING FIXED JAMB IMPORT PROCESS")
        print("=" * 60)
        
        # Create test data with potential duplicate subjects
        test_data = [
            {
                'JAMB_REG': '2025100001',
                'FULLNAME': 'TEST CANDIDATE ONE',
                'STATE': 'Kano',
                'LGA': 'Kano Municipal',
                'UTME_SCORE': '250',
                'UTME_ENG': '65',
                'UTME_MATH': '70',
                'UTME_PHY': '60',
                'UTME_CHEM': '55',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Software Engineering',
                'WAEC_NO': '1234567890',
                'WAEC_YEAR': '2024',
                'G1_SUBJECT': 'English Language',
                'G1_GRADE': 'B3',
                'G2_SUBJECT': 'Mathematics',
                'G2_GRADE': 'A1',
                'G3_SUBJECT': 'Physics',
                'G3_GRADE': 'B2',
                'G4_SUBJECT': 'Chemistry',
                'G4_GRADE': 'B2',
                'G5_SUBJECT': 'Biology',
                'G5_GRADE': 'C4',
                # Test duplicate subject
                'G6_SUBJECT': 'English Language',  # Duplicate!
                'G6_GRADE': 'C5',
            },
            {
                'JAMB_REG': '2025100002',
                'FULLNAME': 'TEST CANDIDATE TWO',
                'STATE': 'Lagos',
                'LGA': 'Ikeja',
                'UTME_SCORE': '245',
                'UTME_ENG': '68',
                'UTME_MATH': '72',
                'UTME_PHY': '58',
                'UTME_CHEM': '47',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Computer Science',
                'WAEC_NO': '1234567891',
                'WAEC_YEAR': '2024',
                'G1_SUBJECT': 'English Language',
                'G1_GRADE': 'B2',
                'G2_SUBJECT': 'Mathematics',
                'G2_GRADE': 'A1',
                'G3_SUBJECT': 'Physics',
                'G3_GRADE': 'B3',
                'G4_SUBJECT': 'Chemistry',
                'G4_GRADE': 'C4',
                'G5_SUBJECT': 'Economics',
                'G5_GRADE': 'B3',
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(test_data)
        
        # Get active session
        session = AcademicSession.query.filter_by(is_active=True).first()
        if not session:
            print("No active session found")
            return
        
        print(f"Using session: {session.name}")
        
        # Initialize processor
        processor = CandidateProcessor()
        
        # Test O'Level parsing first
        print("\n1. TESTING O'LEVEL PARSING:")
        print("-" * 30)
        
        for i, row in df.iterrows():
            print(f"\nRow {i+1}: {row['FULLNAME']}")
            olevel_results = processor.parse_olevel_results(row)
            print(f"  O'Level results: {len(olevel_results)} subjects")
            for result in olevel_results:
                print(f"    - {result['subject']}: {result['grade']}")
            
            if processor.warnings:
                for warning in processor.warnings:
                    print(f"  Warning: {warning}")
                processor.warnings = []
        
        # Test full import
        print("\n2. TESTING FULL IMPORT:")
        print("-" * 30)
        
        # Clear any existing test candidates
        test_regs = [str(row['JAMB_REG']) for row in test_data]
        Candidate.query.filter(Candidate.jamb_reg_number.in_(test_regs)).delete()
        db.session.commit()
        
        # Create temporary CSV file
        temp_csv = '/tmp/test_jamb_import.csv'
        df.to_csv(temp_csv, index=False)
        
        try:
            # Process the file
            result = processor.process_file(temp_csv, session.id)
            
            print(f"Import completed:")
            print(f"  Created: {result['created']}")
            print(f"  Skipped: {result['skipped']}")
            print(f"  Errors: {result['errors']}")
            
            if result['error_details']:
                print("\nError details:")
                for error in result['error_details'][:5]:
                    print(f"  - {error}")
            
            # Show imported candidates
            candidates = Candidate.query.filter(Candidate.jamb_reg_number.in_(test_regs)).all()
            print(f"\nSuccessfully imported {len(candidates)} candidates:")
            
            for candidate in candidates:
                programme_name = candidate.first_choice_programme.name if candidate.first_choice_programme else "None"
                print(f"  - {candidate.full_name} ({candidate.jamb_reg_number}) → {programme_name}")
                
                # Show O'Level results
                olevel_count = len(candidate.olevel_results) if hasattr(candidate, 'olevel_results') else 0
                print(f"    O'Level subjects: {olevel_count}")
        
        except Exception as e:
            print(f"Import failed: {e}")
        
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
        
        print("\n" + "=" * 60)
        print("TEST COMPLETED")
        print("=" * 60)

if __name__ == "__main__":
    test_fixed_import()
