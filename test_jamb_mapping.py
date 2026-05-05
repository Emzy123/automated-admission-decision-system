#!/usr/bin/env python3
"""
Test the improved JAMB mapping functionality
"""

import pandas as pd
from app import create_app, db
from app.services.candidate_processor import CandidateProcessor

def test_jamb_mapping():
    """Test the improved mapping with sample JAMB data"""
    app = create_app()
    with app.app_context():
        # Create sample JAMB data (similar to the template)
        sample_data = [
            {
                'JAMB_REG': '2025001001',
                'FULLNAME': 'AMINA BELLO',
                'STATE': 'Kano',
                'LGA': 'Kano Municipal',
                'UTME_SCORE': '245',
                'UTME_ENG': '68',
                'UTME_MATH': '72',
                'UTME_PHY': '55',
                'UTME_CHEM': '50',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Software Engineering',
                'WAEC_NO': '4250198001',
                'WAEC_YEAR': '2024',
                'G1_SUBJECT': 'English Language',
                'G1_GRADE': 'B2',
                'G2_SUBJECT': 'Mathematics',
                'G2_GRADE': 'A1',
                'G3_SUBJECT': 'Physics',
                'G3_GRADE': 'B3',
                'G4_SUBJECT': 'Chemistry',
                'G4_GRADE': 'C4',
                'G5_SUBJECT': 'Biology',
                'G5_GRADE': 'C5'
            },
            {
                'JAMB_REG': '2025001002',
                'FULLNAME': 'IBRAHIM YUSUF',
                'STATE': 'Lagos',
                'LGA': 'Ikeja',
                'UTME_SCORE': '238',
                'UTME_ENG': '65',
                'UTME_MATH': '70',
                'UTME_PHY': '58',
                'UTME_CHEM': '45',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Computer Science',
                'WAEC_NO': '4250198002',
                'WAEC_YEAR': '2024',
                'G1_SUBJECT': 'English Language',
                'G1_GRADE': 'B3',
                'G2_SUBJECT': 'Mathematics',
                'G2_GRADE': 'A1',
                'G3_SUBJECT': 'Physics',
                'G3_GRADE': 'B2',
                'G4_SUBJECT': 'Chemistry',
                'G4_GRADE': 'C4',
                'G5_SUBJECT': 'Economics',
                'G5_GRADE': 'B3'
            },
            {
                'JAMB_REG': '2025001003',
                'FULLNAME': 'FATIMA ABUBAKAR',
                'STATE': 'Abuja',
                'LGA': 'AMAC',
                'UTME_SCORE': '252',
                'UTME_ENG': '70',
                'UTME_MATH': '75',
                'UTME_PHY': '62',
                'UTME_CHEM': '48',
                'FIRST_CHOICE': 'CUSTECH Osara',
                'FIRST_COURSE': 'Cyber Security',
                'WAEC_NO': '4250198003',
                'WAEC_YEAR': '2024',
                'G1_SUBJECT': 'English Language',
                'G1_GRADE': 'A1',
                'G2_SUBJECT': 'Mathematics',
                'G2_GRADE': 'B2',
                'G3_SUBJECT': 'Physics',
                'G3_GRADE': 'B3',
                'G4_SUBJECT': 'Chemistry',
                'G4_GRADE': 'B3',
                'G5_SUBJECT': 'Biology',
                'G5_GRADE': 'C4'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        
        # Initialize processor
        processor = CandidateProcessor()
        
        print("Testing JAMB Mapping with Sample Data:")
        print("=" * 50)
        
        # Test each row
        for i, row in df.iterrows():
            print(f"\nRow {i+1}: {row['FULLNAME']}")
            print(f"  JAMB Reg: {row['JAMB_REG']}")
            print(f"  First Choice: {row['FIRST_CHOICE']}")
            print(f"  First Course: {row['FIRST_COURSE']}")
            
            # Test the mapping
            result = processor.parse_first_choice(row)
            print(f"  Mapped University ID: {result['university_id']}")
            print(f"  Mapped Programme ID: {result['programme_id']}")
            
            # Show warnings if any
            if processor.warnings:
                print(f"  Warnings: {processor.warnings[-1]}")
                processor.warnings = []  # Clear for next iteration
        
        print(f"\nTotal processor warnings: {len(processor.warnings)}")
        for warning in processor.warnings:
            print(f"  - {warning}")

if __name__ == "__main__":
    test_jamb_mapping()
