#!/usr/bin/env python3
"""
Demonstrate the proper JAMB import process that preserves original data
This shows how the system should work when importing external JAMB data
"""

import pandas as pd
from app import create_app, db
from app.models import Candidate, AcademicSession, Programme, University
from app.services.candidate_processor import CandidateProcessor
from datetime import datetime

def demonstrate_proper_import():
    """Demonstrate the correct JAMB import process"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("PROPER JAMB IMPORT PROCESS DEMONSTRATION")
        print("=" * 60)
        
        # Step 1: Show what the system should do
        print("\n1. WHAT THE SYSTEM SHOULD DO:")
        print("   - Read JAMB CSV with FIRST_CHOICE and FIRST_COURSE columns")
        print("   - Map institution/course names to internal database programmes")
        print("   - PRESERVE original candidate choices from uploaded data")
        print("   - NOT use hardcoded assignment rules")
        
        # Step 2: Show the improved mapping working
        print("\n2. TESTING IMPROVED MAPPING:")
        print("-" * 30)
        
        # Create sample JAMB data that represents real uploads
        sample_jamb_data = [
            {
                'JAMB_REG': '2025100001',
                'FULLNAME': 'AHMED BELLO',
                'STATE': 'Kano',
                'LGA': 'Kano Municipal',
                'UTME_SCORE': '265',
                'UTME_ENG': '72',
                'UTME_MATH': '78',
                'UTME_PHY': '65',
                'UTME_CHEM': '50',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Software Engineering',
            },
            {
                'JAMB_REG': '2025100002',
                'FULLNAME': 'MARIAM YUSUF',
                'STATE': 'Lagos',
                'LGA': 'Ikeja',
                'UTME_SCORE': '258',
                'UTME_ENG': '68',
                'UTME_MATH': '75',
                'UTME_PHY': '62',
                'UTME_CHEM': '53',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Computer Science',
            },
            {
                'JAMB_REG': '2025100003',
                'FULLNAME': 'IBRAHIM ABUBAKAR',
                'STATE': 'Abuja',
                'LGA': 'AMAC',
                'UTME_SCORE': '272',
                'UTME_ENG': '75',
                'UTME_MATH': '82',
                'UTME_PHY': '68',
                'UTME_CHEM': '47',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Electrical Engineering',
            }
        ]
        
        # Initialize processor
        processor = CandidateProcessor()
        
        # Test mapping for each sample
        for i, row in enumerate(sample_jamb_data, 1):
            print(f"\nSample {i}: {row['FULLNAME']}")
            print(f"  JAMB Data: {row['FIRST_CHOICE']} - {row['FIRST_COURSE']}")
            
            # Use the improved mapping
            result = processor.parse_first_choice(row)
            
            if result['programme_id']:
                programme = Programme.query.get(result['programme_id'])
                print(f"  ✓ Mapped to: {programme.name}")
            else:
                print(f"  ✗ Mapping failed")
                if processor.warnings:
                    print(f"    Warning: {processor.warnings[-1]}")
                    processor.warnings = []
        
        # Step 3: Show the difference between wrong and right approach
        print("\n3. WRONG vs RIGHT APPROACH:")
        print("-" * 30)
        print("WRONG (what I did earlier):")
        print("  - Use hardcoded assignment rules")
        print("  - Ignore original JAMB choices")
        print("  - Assign everyone based on UTME scores")
        print("  - Result: All candidates in Software Engineering")
        
        print("\nRIGHT (proper import process):")
        print("  - Read FIRST_CHOICE and FIRST_COURSE from CSV")
        print("  - Map names using intelligent matching")
        print("  - Preserve original candidate preferences")
        print("  - Result: Candidates in their chosen programmes")
        
        # Step 4: Import sample data to demonstrate
        print("\n4. IMPORTING SAMPLE DATA:")
        print("-" * 30)
        
        # Get active session
        session = AcademicSession.query.filter_by(is_active=True).first()
        if not session:
            print("No active session found")
            return
        
        imported_count = 0
        
        for row in sample_jamb_data:
            try:
                # Check if already exists
                jamb_reg = str(row['JAMB_REG']).strip()
                existing = Candidate.query.filter_by(jamb_reg_number=jamb_reg).first()
                
                if existing:
                    print(f"  Skipping {jamb_reg} - already exists")
                    continue
                
                # Parse data
                utme_subjects = processor.parse_utme_subjects(row)
                first_choice = processor.parse_first_choice(row)
                
                # Create candidate
                candidate = Candidate(
                    session_id=session.id,
                    jamb_reg_number=jamb_reg,
                    full_name=str(row.get('FULLNAME', '')).strip(),
                    state_of_origin=str(row.get('STATE', '')).strip(),
                    lga_of_origin=str(row.get('LGA', '')).strip(),
                    utme_score=int(float(row['UTME_SCORE'])) if pd.notna(row.get('UTME_SCORE')) else 0,
                    utme_subjects=utme_subjects,
                    first_choice_programme_id=first_choice.get('programme_id'),
                    status='pending',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(candidate)
                imported_count += 1
                
                programme_name = "Unknown"
                if first_choice.get('programme_id'):
                    programme = Programme.query.get(first_choice['programme_id'])
                    programme_name = programme.name if programme else "Unknown"
                
                print(f"  ✓ Imported: {candidate.full_name} → {programme_name}")
                
            except Exception as e:
                print(f"  ✗ Error importing {row['JAMB_REG']}: {e}")
        
        # Commit
        if imported_count > 0:
            db.session.commit()
            print(f"\nSuccessfully imported {imported_count} candidates")
        else:
            print("\nNo candidates imported")
        
        # Step 5: Show final results
        print("\n5. FINAL RESULTS:")
        print("-" * 30)
        
        candidates = Candidate.query.all()
        print(f"Total candidates: {len(candidates)}")
        
        print("\nProgramme Distribution:")
        programmes = db.session.query(
            Programme.name, 
            db.func.count(Candidate.id)
        ).join(
            Candidate, Programme.id == Candidate.first_choice_programme_id
        ).group_by(Programme.name).order_by(db.func.count(Candidate.id).desc()).all()
        
        for programme_name, count in programmes:
            print(f"  {programme_name}: {count} candidates")
        
        print("\n" + "=" * 60)
        print("CONCLUSION:")
        print("The system now correctly preserves JAMB data and maps")
        print("institution/course names to internal programmes using")
        print("intelligent matching instead of hardcoded rules.")
        print("=" * 60)

if __name__ == "__main__":
    demonstrate_proper_import()
