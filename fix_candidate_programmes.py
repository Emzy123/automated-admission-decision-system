#!/usr/bin/env python3
"""
Fix candidate programme assignments based on UTME subjects
This script assigns candidates to programmes based on their UTME subject combinations
"""

from app import create_app, db
from app.models import Candidate, Programme

def assign_programme_by_subjects(candidate):
    """Assign programme based on candidate's UTME subjects"""
    subjects = set(candidate.utme_subjects.keys()) if candidate.utme_subjects else set()
    
    # Define programme requirements (subject combinations)
    programme_requirements = {
        'Software Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Computer Science': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Computer Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Computer Science and Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Cyber Security': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Information Technology': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Electrical Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Mechanical Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Civil and Mining Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Chemical Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Petroleum and Gas Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Marine Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Materials and Metallurgical Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Agricultural Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Mechatronics Engineering': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        
        # Science programmes
        'Biology': {'Biology', 'Chemistry', 'Physics', 'English'},
        'Biochemistry': {'Biology', 'Chemistry', 'Physics', 'English'},
        'Chemistry': {'Chemistry', 'Physics', 'Biology', 'English'},
        'Physics': {'Physics', 'Chemistry', 'Mathematics', 'English'},
        'Mathematics': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Microbiology': {'Biology', 'Chemistry', 'Physics', 'English'},
        'Statistics': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        
        # Education programmes
        'Mathematics Education': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Physics Education': {'Physics', 'Chemistry', 'Mathematics', 'English'},
        'Chemistry Education': {'Chemistry', 'Physics', 'Biology', 'English'},
        'Biology Education': {'Biology', 'Chemistry', 'Physics', 'English'},
        'Computer Education': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        
        # Management programmes
        'Accounting': {'Mathematics', 'English', 'Economics', 'Physics'},
        'Business Administration': {'Mathematics', 'English', 'Economics', 'Physics'},
        'Economics': {'Mathematics', 'English', 'Economics', 'Physics'},
        'Human Resource Management': {'Mathematics', 'English', 'Economics', 'Physics'},
        'Transport and Logistics Management': {'Mathematics', 'English', 'Economics', 'Physics'},
        'Actuarial Science': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        
        # Other programmes
        'Architecture': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Building': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Geography': {'Geography', 'Physics', 'Chemistry', 'English'},
        'Surveying and Geo-information': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Urban and Regional Planning': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Geography Education': {'Geography', 'Physics', 'Chemistry', 'English'},
        'Technology Education': {'Mathematics', 'Physics', 'Chemistry', 'English'},
        'Law': {'English', 'Literature', 'Government', 'Christian Religious Knowledge'},
    }
    
    # Find best matching programme
    best_match = None
    best_score = 0
    
    for programme_name, required_subjects in programme_requirements.items():
        # Calculate match score
        match_score = len(subjects.intersection(required_subjects))
        
        # Require at least 3 matching subjects including English and Mathematics (for most programmes)
        if 'English' not in subjects:
            continue
            
        # For engineering/science programmes, require Mathematics
        if programme_name not in ['Law', 'Geography', 'Geography Education'] and 'Mathematics' not in subjects:
            continue
            
        if match_score > best_score:
            best_score = match_score
            best_match = programme_name
    
    return best_match

def fix_all_candidates():
    """Fix all candidates by assigning them to appropriate programmes"""
    app = create_app()
    with app.app_context():
        # Get all candidates without programme assignments
        candidates = Candidate.query.filter(Candidate.first_choice_programme_id.is_(None)).all()
        
        print(f"Found {len(candidates)} candidates without programme assignments")
        
        # Get all programmes
        programmes = {prog.name: prog for prog in Programme.query.all()}
        
        fixed_count = 0
        for candidate in candidates:
            programme_name = assign_programme_by_subjects(candidate)
            
            if programme_name and programme_name in programmes:
                programme = programmes[programme_name]
                candidate.first_choice_programme_id = programme.id
                print(f"Assigned {candidate.full_name} to {programme_name}")
                fixed_count += 1
            else:
                print(f"Could not assign {candidate.full_name} (subjects: {candidate.utme_subjects})")
        
        # Commit changes
        if fixed_count > 0:
            db.session.commit()
            print(f"\nSuccessfully assigned {fixed_count} candidates to programmes")
        else:
            print("\nNo candidates were assigned to programmes")

if __name__ == "__main__":
    fix_all_candidates()
