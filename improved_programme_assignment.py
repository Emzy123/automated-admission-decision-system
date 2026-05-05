#!/usr/bin/env python3
"""
Improved programme assignment based on UTME scores and subject combinations
This script distributes candidates more realistically across programmes
"""

from app import create_app, db
from app.models import Candidate, Programme
import random

def assign_programme_intelligently(candidate):
    """Assign programme based on candidate's UTME subjects and scores"""
    subjects = set(candidate.utme_subjects.keys()) if candidate.utme_subjects else set()
    utme_score = candidate.utme_score
    
    # Define programme requirements with score ranges and subject combinations
    programme_requirements = {
        # Engineering programmes (high UTME scores required)
        'Software Engineering': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (200, 400),
            'priority': 1
        },
        'Computer Engineering': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (200, 400),
            'priority': 2
        },
        'Electrical Engineering': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (200, 400),
            'priority': 3
        },
        'Mechanical Engineering': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (200, 400),
            'priority': 4
        },
        'Computer Science': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (180, 400),
            'priority': 5
        },
        'Cyber Security': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (180, 400),
            'priority': 6
        },
        'Information Technology': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (180, 400),
            'priority': 7
        },
        
        # Science programmes (moderate UTME scores)
        'Mathematics': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (160, 400),
            'priority': 8
        },
        'Physics': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (160, 400),
            'priority': 9
        },
        'Chemistry': {
            'subjects': {'Chemistry', 'Physics', 'Biology', 'English'},
            'score_range': (160, 400),
            'priority': 10
        },
        'Biochemistry': {
            'subjects': {'Biology', 'Chemistry', 'Physics', 'English'},
            'score_range': (160, 400),
            'priority': 11
        },
        'Microbiology': {
            'subjects': {'Biology', 'Chemistry', 'Physics', 'English'},
            'score_range': (160, 400),
            'priority': 12
        },
        
        # Management programmes (lower UTME scores)
        'Accounting': {
            'subjects': {'Mathematics', 'English', 'Economics', 'Government'},
            'score_range': (140, 400),
            'priority': 13
        },
        'Business Administration': {
            'subjects': {'Mathematics', 'English', 'Economics', 'Government'},
            'score_range': (140, 400),
            'priority': 14
        },
        'Economics': {
            'subjects': {'Mathematics', 'English', 'Economics', 'Government'},
            'score_range': (140, 400),
            'priority': 15
        },
        'Human Resource Management': {
            'subjects': {'Mathematics', 'English', 'Economics', 'Government'},
            'score_range': (140, 400),
            'priority': 16
        },
        
        # Other programmes
        'Architecture': {
            'subjects': {'Mathematics', 'Physics', 'Chemistry', 'English'},
            'score_range': (180, 400),
            'priority': 17
        },
        'Law': {
            'subjects': {'English', 'Literature', 'Government', 'CRK'},
            'score_range': (200, 400),
            'priority': 18
        }
    }
    
    # Find matching programmes
    matching_programmes = []
    
    for programme_name, requirements in programme_requirements.items():
        required_subjects = requirements['subjects']
        score_min, score_max = requirements['score_range']
        
        # Check subject match (at least 3 out of 4 subjects)
        subject_match = len(subjects.intersection(required_subjects)) >= 3
        
        # Check score range
        score_match = score_min <= utme_score <= score_max
        
        if subject_match and score_match:
            matching_programmes.append((programme_name, requirements['priority']))
    
    # Sort by priority (lower number = higher priority)
    matching_programmes.sort(key=lambda x: x[1])
    
    # Add some randomness to avoid everyone getting the same programme
    if matching_programmes:
        # Take top 3 matching programmes and randomly select one
        top_matches = matching_programmes[:3] if len(matching_programmes) >= 3 else matching_programmes
        selected_programme = random.choice(top_matches)[0]
        return selected_programme
    
    return None

def distribute_candidates_realistically():
    """Distribute candidates across programmes realistically"""
    app = create_app()
    with app.app_context():
        # Get all candidates without programme assignments
        candidates = Candidate.query.filter(Candidate.first_choice_programme_id.is_(None)).all()
        
        print(f'Found {len(candidates)} candidates without programme assignments')
        
        # Get all programmes
        programmes = {prog.name: prog for prog in Programme.query.all()}
        
        # Track assignments for distribution
        programme_counts = {}
        assigned_count = 0
        
        # Sort candidates by UTME score (highest first)
        candidates.sort(key=lambda c: c.utme_score, reverse=True)
        
        for candidate in candidates:
            programme_name = assign_programme_intelligently(candidate)
            
            if programme_name and programme_name in programmes:
                programme = programmes[programme_name]
                candidate.first_choice_programme_id = programme.id
                
                # Track distribution
                programme_counts[programme_name] = programme_counts.get(programme_name, 0) + 1
                assigned_count += 1
                
                print(f'Assigned {candidate.full_name} (UTME: {candidate.utme_score}) to {programme_name}')
            else:
                print(f'Could not assign {candidate.full_name} (UTME: {candidate.utme_score}, Subjects: {candidate.utme_subjects})')
        
        # Commit changes
        if assigned_count > 0:
            db.session.commit()
            print(f'\nSuccessfully assigned {assigned_count} candidates to programmes')
            
            print('\nProgramme Distribution:')
            for programme, count in sorted(programme_counts.items(), key=lambda x: x[1], reverse=True):
                print(f'  {programme}: {count} candidates')
        else:
            print('\nNo candidates were assigned to programmes')

if __name__ == "__main__":
    distribute_candidates_realistically()
