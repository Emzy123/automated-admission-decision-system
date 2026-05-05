import pandas as pd
import re
from datetime import datetime
from app.models import db, Candidate, OLevelResult, Programme, University, User

class CandidateProcessor:
    """Processes JAMB-format CSV and standard CSV candidate uploads"""
    
    # JAMB CSV exact column names (internal standard)
    JAMB_COLUMNS = [
        'JAMB_REG', 'FULLNAME', 'STATE', 'LGA', 
        'UTME_SCORE', 'UTME_ENG', 'UTME_MATH', 'UTME_PHY', 'UTME_CHEM',
        'FIRST_CHOICE', 'FIRST_COURSE',
        'WAEC_NO', 'WAEC_YEAR',
        'G1_SUBJECT', 'G1_GRADE', 'G2_SUBJECT', 'G2_GRADE',
        'G3_SUBJECT', 'G3_GRADE', 'G4_SUBJECT', 'G4_GRADE',
        'G5_SUBJECT', 'G5_GRADE'
    ]
    
    JAMB_REQUIRED_COLUMNS = ['JAMB_REG', 'FULLNAME', 'STATE', 'UTME_SCORE']
    
    # Flexible aliases: maps common real-world column names → internal standard
    COLUMN_ALIASES = {
        # JAMB REG
        'JAMB_REG': [
            'JAMB_REG', 'JAMB REG', 'JAMB REG NO', 'JAMB REG NUMBER',
            'REGISTRATION NUMBER', 'REG NO', 'REG NUMBER', 'REG_NO',
            'JAMB_REG_NUMBER', 'JAMBREGNO', 'JAMBNO', 'REGISTRATION NO',
        ],
        # Full name
        'FULLNAME': [
            'FULLNAME', 'FULL NAME', 'CANDIDATE NAME', 'NAME', 'CANDIDATE_NAME',
            'APPLICANT NAME', 'APPLICANT_NAME', 'STUDENT NAME', 'STUDENT_NAME',
        ],
        # State
        'STATE': [
            'STATE', 'STATE OF ORIGIN', 'STATE_OF_ORIGIN', 'HOME STATE',
            'ORIGIN STATE', 'CANDIDATE STATE',
        ],
        # LGA
        'LGA': [
            'LGA', 'L.G.A', 'LOCAL GOVERNMENT', 'LOCAL GOVT', 'LGA OF ORIGIN',
            'LGA_OF_ORIGIN', 'LOCAL GOVERNMENT AREA',
        ],
        # UTME score
        'UTME_SCORE': [
            'UTME_SCORE', 'UTME SCORE', 'TOTAL UTME', 'JAMB SCORE', 'SCORE',
            'TOTAL SCORE', 'TOTAL', 'JAMB_SCORE', 'UTME_TOTAL', 'AGGREGATE UTME',
        ],
        # UTME subjects
        'UTME_ENG': ['UTME_ENG', 'ENGLISH', 'USE OF ENGLISH', 'ENG', 'ENGLISH LANG'],
        'UTME_MATH': ['UTME_MATH', 'MATHEMATICS', 'MATHS', 'MATH', 'MTH'],
        'UTME_PHY': ['UTME_PHY', 'PHYSICS', 'PHY'],
        'UTME_CHEM': ['UTME_CHEM', 'CHEMISTRY', 'CHEM'],
        'UTME_BIO': ['UTME_BIO', 'BIOLOGY', 'BIO'],
        'UTME_ECO': ['UTME_ECO', 'ECONOMICS', 'ECO', 'ECON'],
        'UTME_GEO': ['UTME_GEO', 'GEOGRAPHY', 'GEO'],
        'UTME_GOV': ['UTME_GOV', 'GOVERNMENT', 'GOV', 'GOVT'],
        'UTME_LIT': ['UTME_LIT', 'LITERATURE', 'LIT IN ENGLISH', 'LIT IN ENG'],
        # Choice / course
        'FIRST_CHOICE': [
            'FIRST_CHOICE', 'FIRST CHOICE', 'INSTITUTION', 'FIRST CHOICE INSTITUTION',
            'UNIVERSITY', 'SCHOOL', '1ST CHOICE',
        ],
        'FIRST_COURSE': [
            'FIRST_COURSE', 'FIRST COURSE', 'COURSE', 'PROGRAMME', 'DEPARTMENT',
            'FACULTY', '1ST COURSE', 'COURSE OF STUDY',
        ],
        # O'Level
        'WAEC_NO': ['WAEC_NO', 'WAEC NO', 'EXAM NUMBER', 'EXAM_NO', 'EXAM NO', 'CERT NO'],
        'WAEC_YEAR': ['WAEC_YEAR', 'WAEC YEAR', 'EXAM YEAR', 'YEAR', 'EXAMINATION YEAR'],
        'G1_SUBJECT': ['G1_SUBJECT', 'SUBJECT1', 'SUBJECT 1', 'SUB1'],
        'G1_GRADE':   ['G1_GRADE',   'GRADE1',   'GRADE 1',   'GRD1'],
        'G2_SUBJECT': ['G2_SUBJECT', 'SUBJECT2', 'SUBJECT 2', 'SUB2'],
        'G2_GRADE':   ['G2_GRADE',   'GRADE2',   'GRADE 2',   'GRD2'],
        'G3_SUBJECT': ['G3_SUBJECT', 'SUBJECT3', 'SUBJECT 3', 'SUB3'],
        'G3_GRADE':   ['G3_GRADE',   'GRADE3',   'GRADE 3',   'GRD3'],
        'G4_SUBJECT': ['G4_SUBJECT', 'SUBJECT4', 'SUBJECT 4', 'SUB4'],
        'G4_GRADE':   ['G4_GRADE',   'GRADE4',   'GRADE 4',   'GRD4'],
        'G5_SUBJECT': ['G5_SUBJECT', 'SUBJECT5', 'SUBJECT 5', 'SUB5'],
        'G5_GRADE':   ['G5_GRADE',   'GRADE5',   'GRADE 5',   'GRD5'],
        'G6_SUBJECT': ['G6_SUBJECT', 'SUBJECT6', 'SUBJECT 6', 'SUB6'],
        'G6_GRADE':   ['G6_GRADE',   'GRADE6',   'GRADE 6',   'GRD6'],
        'G7_SUBJECT': ['G7_SUBJECT', 'SUBJECT7', 'SUBJECT 7', 'SUB7'],
        'G7_GRADE':   ['G7_GRADE',   'GRADE7',   'GRADE 7',   'GRD7'],
        'G8_SUBJECT': ['G8_SUBJECT', 'SUBJECT8', 'SUBJECT 8', 'SUB8'],
        'G8_GRADE':   ['G8_GRADE',   'GRADE8',   'GRADE 8',   'GRD8'],
        'G9_SUBJECT': ['G9_SUBJECT', 'SUBJECT9', 'SUBJECT 9', 'SUB9'],
        'G9_GRADE':   ['G9_GRADE',   'GRADE9',   'GRADE 9',   'GRD9'],
    }
    
    # Map JAMB UTME column names to subject names
    UTME_SUBJECT_MAP = {
        'UTME_ENG': 'English',
        'UTME_MATH': 'Mathematics',
        'UTME_PHY': 'Physics',
        'UTME_CHEM': 'Chemistry',
        'UTME_BIO': 'Biology',
        'UTME_ECO': 'Economics',
        'UTME_GOV': 'Government',
        'UTME_LIT': 'Literature in English',
        'UTME_CRS': 'CRS',
        'UTME_GEO': 'Geography',
    }
    
    def __init__(self, validate_duplicates=True, skip_errors=False):
        self.validate_duplicates = validate_duplicates
        self.skip_errors = skip_errors
        self.errors = []
        self.warnings = []
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0

    def validate_jamb_reg(self, jamb_reg):
        """Validate a JAMB registration number string.
        Returns (is_valid: bool, normalized_or_error: str).
        """
        import re as _re
        if not jamb_reg:
            return False, "JAMB registration number is required."
        cleaned = str(jamb_reg).strip().upper()
        if not _re.match(r'^\d{10}$', cleaned):
            return False, f"Invalid JAMB reg format: expected 10 digits, got '{cleaned}'."
        return True, cleaned

    def normalize_columns(self, df):
        """Rename dataframe columns to internal standard names using alias map"""
        # Build a lookup: UPPERCASE_NO_EXTRA_SPACE → standard_name
        alias_lookup = {}
        for standard, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                alias_lookup[alias.upper().strip()] = standard
        
        rename_map = {}
        unmapped = []
        for col in df.columns:
            normalised = col.upper().strip()
            # Remove common punctuation/extra spaces
            normalised_clean = re.sub(r'[\s/\-\.]+', ' ', normalised).strip()
            if normalised_clean in alias_lookup:
                rename_map[col] = alias_lookup[normalised_clean]
            elif normalised in alias_lookup:
                rename_map[col] = alias_lookup[normalised]
            else:
                unmapped.append(col)
        
        if unmapped:
            self.warnings.append(f"Unrecognised columns (kept as-is): {unmapped}")
        
        return df.rename(columns=rename_map)

    def is_jamb_format(self, df):
        """Detect if CSV is in JAMB format (after normalisation)"""
        df = self.normalize_columns(df)
        jamb_indicators = ['JAMB_REG', 'UTME_SCORE', 'STATE']
        columns = df.columns.tolist()
        matches = sum(1 for col in jamb_indicators if col in columns)
        return matches >= 2  # At least 2 JAMB-specific columns found

    
    def validate_jamb_csv(self, df):
        """Validate JAMB CSV structure"""
        errors = []
        
        # Check required columns
        for col in self.JAMB_REQUIRED_COLUMNS:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
        
        if errors:
            raise ValueError(f"Invalid JAMB format: {'; '.join(errors)}")
        
        # Validate JAMB reg format (must be 10 digits)
        invalid_regs = []
        for idx, reg in enumerate(df['JAMB_REG']):
            reg_str = str(reg).strip()
            if not re.match(r'^\d{10}$', reg_str):
                invalid_regs.append(f"Row {idx+2}: {reg_str}")
        
        if invalid_regs:
            self.warnings.append(f"Invalid JAMB reg numbers: {invalid_regs[:5]}...")
        
        return True
    
    def parse_utme_subjects(self, row):
        """Convert JAMB UTME columns to JSON object"""
        subjects = {}
        for col_name, subject_name in self.UTME_SUBJECT_MAP.items():
            if col_name in row.index:
                value = row[col_name]
                if pd.notna(value) and value != '':
                    try:
                        subjects[subject_name] = int(float(value))
                    except (ValueError, TypeError):
                        self.warnings.append(f"Invalid UTME score for {subject_name}: {value}")
        return subjects if subjects else None
    
    def parse_olevel_results(self, row):
        """Convert JAMB O'Level columns to list of result dicts"""
        results = []
        waec_no = str(row.get('WAEC_NO', '')).strip() if pd.notna(row.get('WAEC_NO')) else ''
        waec_year = int(row['WAEC_YEAR']) if pd.notna(row.get('WAEC_YEAR')) else None
        
        # Track subjects to avoid duplicates in the same sitting
        seen_subjects = set()
        
        for i in range(1, 10):  # G1 through G9
            subject_col = f'G{i}_SUBJECT'
            grade_col = f'G{i}_GRADE'
            
            if subject_col in row.index and pd.notna(row[subject_col]):
                subject = str(row[subject_col]).strip()
                if subject and subject not in seen_subjects:
                    grade = str(row[grade_col]).strip() if grade_col in row.index and pd.notna(row[grade_col]) else ''
                    results.append({
                        'exam_body': 'WAEC',
                        'exam_number': waec_no,
                        'exam_year': waec_year,
                        'sitting_number': 1,
                        'subject': subject,
                        'grade': grade
                    })
                    seen_subjects.add(subject)
                elif subject and subject in seen_subjects:
                    self.warnings.append(f"Duplicate subject '{subject}' found for candidate, skipping duplicate")
        
        return results
    
    def parse_first_choice(self, row):
        """Map JAMB institution/course names to database IDs"""
        institution_name = str(row.get('FIRST_CHOICE', '')).strip() if pd.notna(row.get('FIRST_CHOICE')) else ''
        course_name = str(row.get('FIRST_COURSE', '')).strip() if pd.notna(row.get('FIRST_COURSE')) else ''
        
        result = {'university_id': None, 'programme_id': None}
        
        # Enhanced university mapping with common variations
        university = None
        if institution_name:
            # Common university name mappings
            university_mappings = {
                'custech': 'Confluence University of Science and Technology',
                'custech osara': 'Confluence University of Science and Technology',
                'confluence': 'Confluence University of Science and Technology',
                'c.u.s.t.e.c.h': 'Confluence University of Science and Technology',
            }
            
            # Try direct mappings first
            institution_lower = institution_name.lower()
            for key, full_name in university_mappings.items():
                if key in institution_lower:
                    university = University.query.filter(
                        University.name.ilike(f"%{full_name}%")
                    ).first()
                    break
            
            # If no mapping found, try fuzzy matching
            if not university:
                # Try exact match
                university = University.query.filter(
                    University.name.ilike(f"%{institution_name}%")
                ).first()
                
                # Try partial matching with key words
                if not university:
                    key_words = ['university', 'technology', 'science', 'confluence', 'osara', 'custech']
                    for word in key_words:
                        if word in institution_lower:
                            university = University.query.filter(
                                University.name.ilike(f"%{word}%")
                            ).first()
                            if university:
                                break
        
        if not university:
            # Fallback to the first university (CUSTECH) for testing/import purposes
            university = University.query.first()
            
        if university:
            result['university_id'] = university.id
            
            # Enhanced programme mapping
            if course_name:
                programme = None
                
                # Common course name mappings
                course_mappings = {
                    'software eng': 'Software Engineering',
                    'software engineering': 'Software Engineering',
                    'computer science': 'Computer Science',
                    'computer sci': 'Computer Science',
                    'cyber security': 'Cyber Security',
                    'cybersec': 'Cyber Security',
                    'information technology': 'Information Technology',
                    'i.t': 'Information Technology',
                    'electrical engineering': 'Electrical Engineering',
                    'elect eng': 'Electrical Engineering',
                    'mechanical engineering': 'Mechanical Engineering',
                    'mech eng': 'Mechanical Engineering',
                    'computer engineering': 'Computer Engineering',
                    'comp eng': 'Computer Engineering',
                }
                
                # Try course mappings
                course_lower = course_name.lower()
                for key, full_name in course_mappings.items():
                    if key in course_lower:
                        programme = Programme.query.filter(
                            Programme.university_id == university.id,
                            Programme.name.ilike(f"%{full_name}%")
                        ).first()
                        break
                
                # If no mapping found, try fuzzy matching
                if not programme:
                    programme = Programme.query.filter(
                        Programme.university_id == university.id,
                        Programme.name.ilike(f"%{course_name}%")
                    ).first()
                
                if programme:
                    result['programme_id'] = programme.id
                else:
                    self.warnings.append(f"Programme not found: {course_name} at {institution_name}")
            else:
                self.warnings.append(f"University not found: {institution_name}")
        
        return result
    
    def create_applicant_account(self, candidate):
        """Create applicant account for candidate with default password 'password'"""
        try:
            # Generate email if not provided
            email = candidate.email
            if not email:
                # Create email from name and JAMB reg number
                name_parts = candidate.full_name.lower().replace(' ', '.')
                email = f"{name_parts}.{candidate.jamb_reg_number}@applicant.custech.edu.ng"
                candidate.email = email
            
            # Check if user account already exists
            existing_user = User.query.filter_by(username=candidate.jamb_reg_number).first()
            if existing_user:
                # Link existing user to candidate if not already linked
                if not candidate.user_id:
                    candidate.user_id = existing_user.id
                return existing_user
            
            # Create new user account
            user = User(
                username=candidate.jamb_reg_number,
                email=email,
                full_name=candidate.full_name,
                role='candidate',
                is_active=True,
                created_at=datetime.utcnow()
            )
            user.set_password('password')  # Default password for all applicants
            
            db.session.add(user)
            db.session.flush()  # Get user.id
            
            # Link user to candidate
            candidate.user_id = user.id
            
            return user
            
        except Exception as e:
            self.errors.append(f"Failed to create account for {candidate.jamb_reg_number}: {str(e)}")
            return None
    
    def process_jamb_row(self, row, session_id):
        """Process a single JAMB CSV row into database records"""
        jamb_reg = str(row['JAMB_REG']).strip()
        
        # Validate JAMB reg
        if not re.match(r'^\d{10}$', jamb_reg):
            self.errors.append(f"Invalid JAMB reg: {jamb_reg}")
            self.skipped_count += 1
            return None
        
        # Check if candidate already exists
        existing = Candidate.query.filter_by(jamb_reg_number=jamb_reg).first()
        if existing:
            self.skipped_count += 1
            return existing
        
        # Parse data
        utme_subjects = self.parse_utme_subjects(row)
        olevel_results = self.parse_olevel_results(row)
        first_choice = self.parse_first_choice(row)
        
        try:
            import random
            
            # Simulate Post-UTME score for testing purposes if the format doesn't provide it
            # Typically 80-90% of candidates take the post-UTME
            post_utme_present = random.random() < 0.85
            post_utme_score = round(random.uniform(35.0, 95.0), 1) if post_utme_present else None

            # Create candidate
            candidate = Candidate(
            session_id=session_id,
            jamb_reg_number=jamb_reg,
            full_name=str(row.get('FULLNAME', '')).strip(),
            state_of_origin=str(row.get('STATE', '')).strip(),
            lga_of_origin=str(row.get('LGA', '')).strip() if pd.notna(row.get('LGA')) else '',
            utme_score=int(float(row['UTME_SCORE'])) if pd.notna(row.get('UTME_SCORE')) else 0,
            utme_subjects=utme_subjects,
            first_choice_programme_id=first_choice.get('programme_id'),
            post_utme_present=post_utme_present,
            post_utme_score=post_utme_score,
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
            
            # Automatically create applicant account
            self.create_applicant_account(candidate)
            
            self.created_count += 1
            return candidate
            
        except Exception as e:
            # Rollback the current transaction to prevent session corruption
            db.session.rollback()
            self.errors.append(f"Failed to process candidate {jamb_reg}: {str(e)}")
            return None
    
    def process_file(self, file_path, session_id):
        """Main method: Process uploaded CSV file"""
        df = pd.read_csv(file_path)
        
        # Detect format
        if not self.is_jamb_format(df):
            raise ValueError(
                "File is not in JAMB format. Expected columns: JAMB_REG, UTME_ENG, UTME_MATH, G1_SUBJECT, etc."
            )
        
        # Validate
        self.validate_jamb_csv(df)
        
        # Process each row with better error handling
        successful_rows = 0
        for idx, row in df.iterrows():
            try:
                result = self.process_jamb_row(row, session_id)
                if result:
                    successful_rows += 1
            except Exception as e:
                self.errors.append(f"Row {idx+2}: {str(e)}")
                self.skipped_count += 1
                # Continue processing other rows even if one fails
        
        # Only commit if we have successful rows and no critical errors
        if successful_rows > 0:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                self.errors.append(f"Failed to commit changes: {str(e)}")
                # Mark all successful rows as failed due to commit failure
                self.created_count = 0
                self.skipped_count += successful_rows
        
        return self.get_summary()
    
    def get_preview(self, file_path, max_rows=5):
        """Return preview data for display before import"""
        df = pd.read_csv(file_path)
        is_jamb = self.is_jamb_format(df)
        
        preview_rows = []
        for idx, row in df.head(max_rows).iterrows():
            subjects = self.parse_utme_subjects(row) if is_jamb else None
            preview_rows.append({
                'row': idx + 2,
                'jamb_reg': str(row.get('JAMB_REG', '')).strip() if is_jamb else str(row.iloc[0]),
                'name': str(row.get('FULLNAME', '')).strip() if is_jamb else str(row.iloc[1]),
                'state': str(row.get('STATE', '')).strip() if is_jamb else '',
                'utme_score': int(float(row['UTME_SCORE'])) if is_jamb and pd.notna(row.get('UTME_SCORE')) else 0,
                'subjects': subjects
            })
        
        return {
            'is_jamb_format': is_jamb,
            'total_rows': len(df),
            'columns': df.columns.tolist(),
            'preview': preview_rows
        }
    
    def get_summary(self):
        """Return import summary"""
        return {
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'error_details': self.errors[:10],  # First 10 errors
            'warning_details': self.warnings[:10]  # First 10 warnings
        }
