#!/usr/bin/env python3
"""
Restore original JAMB data using the improved mapping logic
This will re-import the JAMB template data with proper programme assignments
"""

import pandas as pd
from app import create_app, db
from app.models import Candidate, AcademicSession, OLevelResult
from app.services.candidate_processor import CandidateProcessor
from datetime import datetime

def restore_jamb_data():
    """Restore JAMB data using the improved mapping"""
    app = create_app()
    with app.app_context():
        # Read the JAMB template
        template_path = '/home/ocheme/Desktop/Admission-portal/admission_system/app/static/templates/jamb_template.csv'
        
        try:
            df = pd.read_csv(template_path)
            print(f"Loaded JAMB template with {len(df)} records")
        except Exception as e:
            print(f"Error reading template: {e}")
            return
        
        # Get active session
        session = AcademicSession.query.filter_by(is_active=True).first()
        if not session:
            print("No active session found")
            return
        
        print(f"Using session: {session.name}")
        
        # Initialize processor
        processor = CandidateProcessor()
        
        # Clear existing candidates (optional - comment out if you want to keep them)
        print("Clearing existing candidate data...")
        Candidate.query.delete()
        db.session.commit()
        
        # Process each row
        processed_count = 0
        skipped_count = 0
        
        for index, row in df.iterrows():
            try:
                # Check if candidate already exists
                jamb_reg = str(row['JAMB_REG']).strip()
                existing = Candidate.query.filter_by(jamb_reg_number=jamb_reg).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Parse data using improved processor
                utme_subjects = processor.parse_utme_subjects(row)
                olevel_results = processor.parse_olevel_results(row)
                first_choice = processor.parse_first_choice(row)
                
                # Create candidate
                candidate = Candidate(
                    session_id=session.id,
                    jamb_reg_number=jamb_reg,
                    full_name=str(row.get('FULLNAME', '')).strip(),
                    state_of_origin=str(row.get('STATE', '')).strip(),
                    lga_of_origin=str(row.get('LGA', '')).strip() if pd.notna(row.get('LGA')) else '',
                    utme_score=int(float(row['UTME_SCORE'])) if pd.notna(row.get('UTME_SCORE')) else 0,
                    utme_subjects=utme_subjects,
                    first_choice_programme_id=first_choice.get('programme_id'),
                    status='pending',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(candidate)
                db.session.flush()  # Get candidate.id
                
                # Create O'Level results
                for result_data in olevel_results:
                    olevel = OLevelResult(
                        candidate_id=candidate.id,
                        **result_data
                    )
                    db.session.add(olevel)
                
                # Create applicant account
                processor.create_applicant_account(candidate)
                
                processed_count += 1
                
                # Show progress
                if processed_count % 10 == 0:
                    print(f"Processed {processed_count} candidates...")
                    
            except Exception as e:
                print(f"Error processing row {index}: {e}")
                skipped_count += 1
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\nSuccessfully processed {processed_count} candidates")
            print(f"Skipped {skipped_count} candidates")
            
            # Show programme distribution
            print("\nProgramme Distribution:")
            from app.models import Programme
            programmes = db.session.query(
                Programme.name, 
                db.func.count(Candidate.id)
            ).join(
                Candidate, Programme.id == Candidate.first_choice_programme_id
            ).group_by(Programme.name).order_by(db.func.count(Candidate.id).desc()).all()
            
            for programme_name, count in programmes:
                print(f"  {programme_name}: {count} candidates")
                
        except Exception as e:
            print(f"Error committing changes: {e}")
            db.session.rollback()
        
        # Show any warnings from the processor
        if processor.warnings:
            print(f"\nProcessor warnings ({len(processor.warnings)}):")
            for warning in processor.warnings[:10]:  # Show first 10
                print(f"  - {warning}")
            if len(processor.warnings) > 10:
                print(f"  ... and {len(processor.warnings) - 10} more warnings")

if __name__ == "__main__":
    restore_jamb_data()
