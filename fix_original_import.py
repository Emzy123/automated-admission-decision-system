#!/usr/bin/env python3
"""
Fix the original JAMB import data by using the improved mapping logic
This script updates existing candidates with proper programme assignments
"""

import pandas as pd
from app import create_app, db
from app.models import Candidate, Programme
from app.services.candidate_processor import CandidateProcessor

def fix_original_import():
    """Fix existing candidates with improved programme mapping"""
    app = create_app()
    with app.app_context():
        # Read the JAMB template to get original data
        template_path = '/home/ocheme/Desktop/Admission-portal/admission_system/app/static/templates/jamb_template.csv'
        
        try:
            df = pd.read_csv(template_path)
            print(f"Loaded JAMB template with {len(df)} records")
        except Exception as e:
            print(f"Error reading template: {e}")
            return
        
        # Initialize processor
        processor = CandidateProcessor()
        
        # Get all programmes for mapping
        programmes = {prog.name: prog for prog in Programme.query.all()}
        
        updated_count = 0
        not_found_count = 0
        
        print("\nUpdating candidates with original JAMB choices:")
        print("=" * 50)
        
        for index, row in df.iterrows():
            jamb_reg = str(row['JAMB_REG']).strip()
            first_choice = str(row.get('FIRST_CHOICE', '')).strip()
            first_course = str(row.get('FIRST_COURSE', '')).strip()
            
            # Find candidate
            candidate = Candidate.query.filter_by(jamb_reg_number=jamb_reg).first()
            
            if candidate:
                # Use improved mapping
                result = processor.parse_first_choice(row)
                programme_id = result.get('programme_id')
                
                if programme_id:
                    # Get programme name for display
                    programme = Programme.query.get(programme_id)
                    programme_name = programme.name if programme else "Unknown"
                    
                    # Update candidate
                    old_programme_name = candidate.first_choice_programme.name if candidate.first_choice_programme else "None"
                    candidate.first_choice_programme_id = programme_id
                    
                    print(f"Updated {candidate.full_name} ({jamb_reg})")
                    print(f"  From: {old_programme_name}")
                    print(f"  To: {programme_name} (from: {first_choice} - {first_course})")
                    print()
                    
                    updated_count += 1
                else:
                    print(f"Could not map programme for {candidate.full_name} ({jamb_reg})")
                    print(f"  JAMB data: {first_choice} - {first_course}")
                    
                    # Show warnings
                    if processor.warnings:
                        print(f"  Warning: {processor.warnings[-1]}")
                        processor.warnings = []
                    
                    not_found_count += 1
                    print()
            else:
                print(f"Candidate not found: {jamb_reg}")
                not_found_count += 1
        
        # Commit changes
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"Successfully updated {updated_count} candidates")
            except Exception as e:
                print(f"Error committing changes: {e}")
                db.session.rollback()
        else:
            print("No candidates were updated")
        
        print(f"\nSummary:")
        print(f"  Updated: {updated_count}")
        print(f"  Not found/mapped: {not_found_count}")
        
        # Show final distribution
        print("\nFinal Programme Distribution:")
        programmes = db.session.query(
            Programme.name, 
            db.func.count(Candidate.id)
        ).join(
            Candidate, Programme.id == Candidate.first_choice_programme_id
        ).group_by(Programme.name).order_by(db.func.count(Candidate.id).desc()).all()
        
        for programme_name, count in programmes:
            print(f"  {programme_name}: {count} candidates")

if __name__ == "__main__":
    fix_original_import()
