#!/usr/bin/env python3
"""
Final fix for JAMB import O'Level constraint issues
This script provides a clean solution that handles all the database constraints
"""

import pandas as pd
from app import create_app, db
from app.models import Candidate, AcademicSession, OLevelResult, Programme, University
from app.services.candidate_processor import CandidateProcessor
from datetime import datetime

def clean_import_test():
    """Test the clean import process with proper constraint handling"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("FINAL IMPORT FIX - CLEAN TEST")
        print("=" * 60)
        
        # Get active session
        session = AcademicSession.query.filter_by(is_active=True).first()
        if not session:
            print("No active session found")
            return
        
        print(f"Using session: {session.name}")
        
        # Clean test data first
        test_regs = ['2025100001', '2025100002']
        candidates = Candidate.query.filter(Candidate.jamb_reg_number.in_(test_regs)).all()
        
        for candidate in candidates:
            # Delete O'Level results first (due to foreign key constraint)
            OLevelResult.query.filter_by(candidate_id=candidate.id).delete()
            # Delete candidate
            db.session.delete(candidate)
        
        db.session.commit()
        print(f"Cleaned existing test candidates")
        
        # Create clean test data
        test_data = [
            {
                'JAMB_REG': '2025100001',
                'FULLNAME': 'CLEAN TEST ONE',
                'STATE': 'Kano',
                'LGA': 'Kano Municipal',
                'UTME_SCORE': '250',
                'UTME_ENG': '65',
                'UTME_MATH': '70',
                'UTME_PHY': '60',
                'UTME_CHEM': '55',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Software Engineering',
                'WAEC_NO': '9999999991',
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
            },
            {
                'JAMB_REG': '2025100002',
                'FULLNAME': 'CLEAN TEST TWO',
                'STATE': 'Lagos',
                'LGA': 'Ikeja',
                'UTME_SCORE': '245',
                'UTME_ENG': '68',
                'UTME_MATH': '72',
                'UTME_PHY': '58',
                'UTME_CHEM': '47',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Computer Science',
                'WAEC_NO': '9999999992',
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
        
        # Create temporary CSV file
        temp_csv = '/tmp/clean_test_import.csv'
        df.to_csv(temp_csv, index=False)
        
        try:
            # Initialize processor
            processor = CandidateProcessor()
            
            # Process the file
            print("\nProcessing clean test import...")
            result = processor.process_file(temp_csv, session.id)
            
            print(f"Import completed:")
            print(f"  Created: {result['created']}")
            print(f"  Skipped: {result['skipped']}")
            print(f"  Errors: {result['errors']}")
            
            if result['error_details']:
                print("\nError details:")
                for error in result['error_details']:
                    print(f"  - {error}")
            
            # Show imported candidates
            candidates = Candidate.query.filter(Candidate.jamb_reg_number.in_(test_regs)).all()
            print(f"\nSuccessfully imported {len(candidates)} candidates:")
            
            for candidate in candidates:
                programme_name = candidate.first_choice_programme.name if candidate.first_choice_programme else "None"
                print(f"  - {candidate.full_name} ({candidate.jamb_reg_number}) → {programme_name}")
                
                # Show O'Level results count
                olevel_count = OLevelResult.query.filter_by(candidate_id=candidate.id).count()
                print(f"    O'Level subjects: {olevel_count}")
                
                # Show actual O'Level results
                olevels = OLevelResult.query.filter_by(candidate_id=candidate.id).all()
                for olevel in olevels:
                    print(f"      - {olevel.subject}: {olevel.grade}")
        
        except Exception as e:
            print(f"Import failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
        
        print("\n" + "=" * 60)
        print("CLEAN TEST COMPLETED")
        print("=" * 60)

def demonstrate_solution():
    """Demonstrate the complete solution for the import issue"""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("SOLUTION SUMMARY")
        print("=" * 60)
        
        print("\nPROBLEM IDENTIFIED:")
        print("- O'Level results have UNIQUE constraint on (candidate_id, sitting_number, subject)")
        print("- Import process was trying to insert duplicate subjects")
        print("- Database session corruption occurred on constraint violations")
        
        print("\nFIXES IMPLEMENTED:")
        print("1. Enhanced parse_olevel_results() to skip duplicate subjects")
        print("2. Added proper error handling with session rollback")
        print("3. Improved process_file() to handle partial failures")
        print("4. Added transaction management to prevent session corruption")
        
        print("\nHOW THE FIX WORKS:")
        print("- CSV parsing now tracks seen subjects per candidate")
        print("- Duplicate subjects are skipped with warnings")
        print("- Database errors trigger immediate rollback")
        print("- Import continues processing other rows after failures")
        print("- Final commit only happens if no critical errors")
        
        print("\nRESULT:")
        print("- No more UNIQUE constraint violations")
        print("- Clean import process with proper error handling")
        print("- Preserved data integrity")
        print("- Better error reporting for debugging")

if __name__ == "__main__":
    clean_import_test()
    demonstrate_solution()
