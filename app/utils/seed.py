"""
Database Seeding Utilities
Comprehensive seed data generation for admission system
"""

from datetime import date

from app import db
from app.models import (
    AcademicSession, CatchmentState, ELDSState, Faculty, Programme,
    University, Candidate, OLevelResult, User
)


def seed_programmes():
    """Seed CUSTECH faculties and programmes with realistic admission configuration."""
    print("🌱 Seeding CUSTECH faculties and programmes...")
    
    # Ensure university exists
    university = University.query.filter_by(short_code="CUSTECH").first()
    if not university:
        print("❌ CUSTECH university not found. Please run 'flask seed-config' first.")
        return
    
    # Faculty data
    faculties_data = [
        {"name": "Computing and Informatics", "code": "FCI"},
        {"name": "Engineering", "code": "ENG"},
        {"name": "Science", "code": "SCI"},
        {"name": "Environmental Sciences", "code": "ENV"},
        {"name": "Science and Technology Education", "code": "STE"},
        {"name": "Management and Social Sciences", "code": "MSS"},
        {"name": "Law", "code": "LAW"}
    ]
    
    faculties_created = 0
    faculties_skipped = 0
    programmes_created = 0
    programmes_skipped = 0
    
    # Create faculty mapping for lookup
    faculty_map = {}
    
    try:
        # Create faculties with proper error handling
        for faculty_data in faculties_data:
            existing_faculty = Faculty.query.filter_by(
                university_id=university.id,
                name=faculty_data["name"]
            ).first()
            
            if existing_faculty:
                print(f"⏭️ Faculty already exists: {faculty_data['name']}")
                faculty_map[faculty_data["code"]] = existing_faculty
                faculties_skipped += 1
            else:
                faculty = Faculty(
                    university_id=university.id,
                    name=faculty_data["name"],
                    code=faculty_data["code"]
                )
                db.session.add(faculty)
                db.session.flush()  # Get the ID without committing
                faculty_map[faculty_data["code"]] = faculty
                print(f"✅ Created faculty: {faculty_data['name']}")
                faculties_created += 1
        
        # Commit faculties before creating programmes
        db.session.commit()
        print(f"✅ Faculties ready: {len(faculty_map)} faculties available")
        
        # Programme data with explicit faculty codes
        programmes_data = [
            # Computing and Informatics (FCI)
            {"name": "Software Engineering", "code": "SE", "faculty_code": "FCI", "min_utme_score": 180, "total_slots": 100, "merit_slots": 45, "catchment_slots": 35, "elds_slots": 20, "merit_cutoff": 50.0, "catchment_cutoff": 40.0, "elds_cutoff": 35.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Computer Science", "code": "CSC", "faculty_code": "FCI", "min_utme_score": 180, "total_slots": 100, "merit_slots": 45, "catchment_slots": 35, "elds_slots": 20, "merit_cutoff": 50.0, "catchment_cutoff": 40.0, "elds_cutoff": 35.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Cyber Security", "code": "CYS", "faculty_code": "FCI", "min_utme_score": 200, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 50.0, "catchment_cutoff": 40.0, "elds_cutoff": 35.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Information Technology", "code": "IT", "faculty_code": "FCI", "min_utme_score": 160, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 48.0, "catchment_cutoff": 38.0, "elds_cutoff": 33.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry/Economics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            
            # Engineering (ENG)
            {"name": "Agricultural Engineering", "code": "AGE", "faculty_code": "ENG", "min_utme_score": 180, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Chemical Engineering", "code": "CHE", "faculty_code": "ENG", "min_utme_score": 200, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Civil and Mining Engineering", "code": "CME", "faculty_code": "ENG", "min_utme_score": 190, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 48.0, "catchment_cutoff": 40.0, "elds_cutoff": 34.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Computer Engineering", "code": "CEN", "faculty_code": "ENG", "min_utme_score": 200, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Electrical Engineering", "code": "ELE", "faculty_code": "ENG", "min_utme_score": 200, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Marine Engineering", "code": "MAR", "faculty_code": "ENG", "min_utme_score": 180, "total_slots": 50, "merit_slots": 23, "catchment_slots": 17, "elds_slots": 10, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Materials and Metallurgical Engineering", "code": "MME", "faculty_code": "ENG", "min_utme_score": 180, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Mechanical Engineering", "code": "MEE", "faculty_code": "ENG", "min_utme_score": 200, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Mechatronics Engineering", "code": "MTE", "faculty_code": "ENG", "min_utme_score": 200, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            {"name": "Petroleum and Gas Engineering", "code": "PGE", "faculty_code": "ENG", "min_utme_score": 200, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics", "Chemistry"]},
            
            # Science (SCI)
            {"name": "Biology", "code": "BIO", "faculty_code": "SCI", "min_utme_score": 170, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Biology", "Chemistry", "Physics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Biology", "Chemistry"]},
            {"name": "Biochemistry", "code": "BCH", "faculty_code": "SCI", "min_utme_score": 190, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 48.0, "catchment_cutoff": 40.0, "elds_cutoff": 34.0, "required_utme_subjects": ["English", "Biology", "Chemistry", "Physics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Biology", "Chemistry"]},
            {"name": "Chemistry", "code": "CHM", "faculty_code": "SCI", "min_utme_score": 160, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Chemistry", "Physics", "Biology/Mathematics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Chemistry", "Physics"]},
            {"name": "Mathematics", "code": "MTH", "faculty_code": "SCI", "min_utme_score": 150, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry/Economics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            {"name": "Microbiology", "code": "MCB", "faculty_code": "SCI", "min_utme_score": 190, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 48.0, "catchment_cutoff": 40.0, "elds_cutoff": 34.0, "required_utme_subjects": ["English", "Biology", "Chemistry", "Physics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Biology", "Chemistry"]},
            {"name": "Physics", "code": "PHY", "faculty_code": "SCI", "min_utme_score": 150, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Physics", "Mathematics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            {"name": "Statistics", "code": "STA", "faculty_code": "SCI", "min_utme_score": 150, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Economics"], "mandatory_olevel_subjects": ["English Language", "Mathematics"]},
            
            # Environmental Sciences (ENV)
            {"name": "Architecture", "code": "ARC", "faculty_code": "ENV", "min_utme_score": 200, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 50.0, "catchment_cutoff": 42.0, "elds_cutoff": 36.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry/Geography"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            {"name": "Building", "code": "BLD", "faculty_code": "ENV", "min_utme_score": 170, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Chemistry"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            {"name": "Geography", "code": "GEO", "faculty_code": "ENV", "min_utme_score": 150, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Geography", "Mathematics", "Economics/Government"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Geography"]},
            {"name": "Surveying and Geo-information", "code": "SVG", "faculty_code": "ENV", "min_utme_score": 170, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Geography"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            {"name": "Urban and Regional Planning", "code": "URP", "faculty_code": "ENV", "min_utme_score": 170, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Mathematics", "Geography", "Economics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Geography"]},
            
            # Science and Technology Education (STE)
            {"name": "Biology Education", "code": "BED", "faculty_code": "STE", "min_utme_score": 150, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 40.0, "catchment_cutoff": 34.0, "elds_cutoff": 28.0, "required_utme_subjects": ["English", "Biology", "Chemistry", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Biology"]},
            {"name": "Chemistry Education", "code": "CED", "faculty_code": "STE", "min_utme_score": 150, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 40.0, "catchment_cutoff": 34.0, "elds_cutoff": 28.0, "required_utme_subjects": ["English", "Chemistry", "Physics", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Chemistry"]},
            {"name": "Mathematics Education", "code": "MED", "faculty_code": "STE", "min_utme_score": 150, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 40.0, "catchment_cutoff": 34.0, "elds_cutoff": 28.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics"]},
            {"name": "Physics Education", "code": "PED", "faculty_code": "STE", "min_utme_score": 150, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 40.0, "catchment_cutoff": 34.0, "elds_cutoff": 28.0, "required_utme_subjects": ["English", "Physics", "Mathematics", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            {"name": "Computer Education", "code": "COE", "faculty_code": "STE", "min_utme_score": 160, "total_slots": 70, "merit_slots": 32, "catchment_slots": 24, "elds_slots": 14, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics"]},
            {"name": "Geography Education", "code": "GED", "faculty_code": "STE", "min_utme_score": 150, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 40.0, "catchment_cutoff": 34.0, "elds_cutoff": 28.0, "required_utme_subjects": ["English", "Geography", "Mathematics", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Geography"]},
            {"name": "Technology Education", "code": "TED", "faculty_code": "STE", "min_utme_score": 150, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 40.0, "catchment_cutoff": 34.0, "elds_cutoff": 28.0, "required_utme_subjects": ["English", "Mathematics", "Physics", "Education"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Physics"]},
            
            # Management and Social Sciences (MSS)
            {"name": "Accounting", "code": "ACC", "faculty_code": "MSS", "min_utme_score": 180, "total_slots": 100, "merit_slots": 45, "catchment_slots": 35, "elds_slots": 20, "merit_cutoff": 48.0, "catchment_cutoff": 40.0, "elds_cutoff": 34.0, "required_utme_subjects": ["English", "Mathematics", "Economics", "Government/Commerce"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Economics"]},
            {"name": "Actuarial Science", "code": "ASC", "faculty_code": "MSS", "min_utme_score": 180, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 48.0, "catchment_cutoff": 40.0, "elds_cutoff": 34.0, "required_utme_subjects": ["English", "Mathematics", "Economics", "Physics"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Economics"]},
            {"name": "Business Administration", "code": "BUA", "faculty_code": "MSS", "min_utme_score": 170, "total_slots": 100, "merit_slots": 45, "catchment_slots": 35, "elds_slots": 20, "merit_cutoff": 45.0, "catchment_cutoff": 38.0, "elds_cutoff": 32.0, "required_utme_subjects": ["English", "Mathematics", "Economics", "Government/Commerce"], "mandatory_olevel_subjects": ["English Language", "Mathematics"]},
            {"name": "Economics", "code": "ECO", "faculty_code": "MSS", "min_utme_score": 180, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 48.0, "catchment_cutoff": 40.0, "elds_cutoff": 34.0, "required_utme_subjects": ["English", "Mathematics", "Economics", "Government/Geography"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Economics"]},
            {"name": "Human Resource Management", "code": "HRM", "faculty_code": "MSS", "min_utme_score": 160, "total_slots": 80, "merit_slots": 36, "catchment_slots": 28, "elds_slots": 16, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Mathematics", "Economics", "Government"], "mandatory_olevel_subjects": ["English Language", "Mathematics"]},
            {"name": "Transport and Logistics Management", "code": "TLM", "faculty_code": "MSS", "min_utme_score": 160, "total_slots": 60, "merit_slots": 27, "catchment_slots": 21, "elds_slots": 12, "merit_cutoff": 42.0, "catchment_cutoff": 36.0, "elds_cutoff": 30.0, "required_utme_subjects": ["English", "Mathematics", "Economics", "Geography"], "mandatory_olevel_subjects": ["English Language", "Mathematics"]},
            
            # Law (LAW)
            {"name": "Law", "code": "LAW", "faculty_code": "LAW", "min_utme_score": 200, "total_slots": 120, "merit_slots": 54, "catchment_slots": 42, "elds_slots": 24, "merit_cutoff": 55.0, "catchment_cutoff": 48.0, "elds_cutoff": 42.0, "required_utme_subjects": ["English", "Literature in English", "Government", "Economics/CRS"], "mandatory_olevel_subjects": ["English Language", "Mathematics", "Literature in English", "Government"]}
        ]
        
        faculties_created = 0
        faculties_skipped = 0
        programmes_created = 0
        programmes_skipped = 0
        
        print(f"\n📝 Creating {len(programmes_data)} programmes...")
        
        # Create programmes
        for prog_data in programmes_data:
            faculty_code = prog_data["faculty_code"]
            faculty = faculty_map.get(faculty_code)
            
            if not faculty:
                print(f"❌ Faculty not found for {prog_data['name']}: {faculty_code}")
                continue
            
            existing_programme = Programme.query.filter_by(
                university_id=university.id,
                faculty_id=faculty.id,
                code=prog_data["code"]
            ).first()
            
            if existing_programme:
                print(f"⏭️ Programme already exists: {prog_data['name']} ({faculty_code})")
                programmes_skipped += 1
            else:
                programme = Programme(
                    university_id=university.id,
                    faculty_id=faculty.id,
                    name=prog_data["name"],
                    code=prog_data["code"],
                    duration_years=4,  # Default duration
                    min_utme_score=prog_data["min_utme_score"],
                    total_slots=prog_data["total_slots"],
                    merit_slots=prog_data["merit_slots"],
                    catchment_slots=prog_data["catchment_slots"],
                    elds_slots=prog_data["elds_slots"],
                    merit_cutoff=prog_data["merit_cutoff"],
                    catchment_cutoff=prog_data["catchment_cutoff"],
                    elds_cutoff=prog_data["elds_cutoff"],
                    required_utme_subjects=prog_data["required_utme_subjects"],
                    mandatory_olevel_subjects=prog_data["mandatory_olevel_subjects"]
                )
                db.session.add(programme)
                print(f"✅ Created programme: {prog_data['name']} ({faculty_code})")
                programmes_created += 1
        
        # Commit all changes
        db.session.commit()
        
        print("\n--- Seed Complete ---")
        print(f"Faculties created: {faculties_created} new, {faculties_skipped} skipped (already exist)")
        print(f"Programmes created: {programmes_created} new, {programmes_skipped} skipped (already exist)")
        print("🎉 Successfully seeded CUSTECH faculties and programmes!")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error during seeding: {str(e)}")
        raise


def seed_university_config():
    """Seed university configuration if not exists."""
    print("🏛️ Seeding university configuration...")
    
    existing_university = University.query.filter_by(short_code="CUSTECH").first()
    if existing_university:
        print("⏭️ University configuration already exists")
        return
    
    # Create academic session
    session = AcademicSession(
        name="2025/2026",
        is_active=True,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31)
    )
    db.session.add(session)
    
    # Create university
    university = University(
        name="Confluence University of Science and Technology, Osara",
        short_code="CUSTECH",
        formula_type="CUSTECH",
        jamb_divisor=8.0,
        post_utme_divisor=4.0,
        merit_quota_percent=45,
        catchment_quota_percent=35,
        elds_quota_percent=20,
        min_olevel_credits=5,
        max_olevel_sittings=2,
        min_utme_score=140,
        grade_points={
            'A1': 8, 'B2': 7, 'B3': 6, 'C4': 5, 
            'C5': 4, 'C6': 3, 'D7': 0, 'E8': 0, 'F9': 0
        }
    )
    db.session.add(university)
    
    # Add catchment state
    catchment = CatchmentState(university_id=1, state_name="Kogi")
    db.session.add(catchment)
    
    # Add ELDS states
    elds_states = [
        "Adamawa", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River",
        "Ebonyi", "Gombe", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi",
        "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "Rivers", "Sokoto",
        "Taraba", "Yobe", "Zamfara"
    ]
    for state in elds_states:
        db.session.add(ELDSState(state_name=state))
    
    db.session.commit()
    print("✅ University configuration seeded successfully!")


def seed_all():
    """Seed database with realistic test data"""
    # 1. Create Academic Session
    session = AcademicSession(
        name="2025/2026",
        is_active=True,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 8, 31)
    )
    db.session.add(session)
    
    # 2. Create University (CUSTECH)
    university = University(
        name="Confluence University of Science and Technology, Osara",
        short_code="CUSTECH",
        formula_type="CUSTECH",
        jamb_divisor=8.0,
        post_utme_divisor=4.0,
        merit_quota_percent=45,
        catchment_quota_percent=35,
        elds_quota_percent=20,
        min_olevel_credits=5,
        max_olevel_sittings=2,
        min_utme_score=140,
        grade_points={
            'A1': 8, 'B2': 7, 'B3': 6, 'C4': 5, 
            'C5': 4, 'C6': 3, 'D7': 0, 'E8': 0, 'F9': 0
        }
    )
    db.session.add(university)
    
    # 3. Add Catchment State (Kogi)
    catchment = CatchmentState(university_id=1, state_name="Kogi")
    db.session.add(catchment)
    
    # 4. Pre-populate ELDS States
    elds_states = [
        "Adamawa", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River",
        "Ebonyi", "Gombe", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi",
        "Kogi", "Kwara", "Nasarawa", "Niger", "Plateau", "Rivers", "Sokoto",
        "Taraba", "Yobe", "Zamfara"
    ]
    for state in elds_states:
        db.session.add(ELDSState(state_name=state))
    
    # 5. Create Faculties
    faculties = [
        Faculty(university_id=1, name="Computing and Informatics", code="FCI"),
        Faculty(university_id=1, name="Engineering", code="ENG"),
        Faculty(university_id=1, name="Science", code="SCI"),
    ]
    for faculty in faculties:
        db.session.add(faculty)
    
    db.session.commit()
    
    # 6. Create Programmes
    programmes = [
        Programme(
            university_id=1,
            faculty_id=1,
            name="Software Engineering",
            code="SE",
            duration_years=4,
            min_utme_score=180,
            total_slots=100,
            merit_slots=45,
            catchment_slots=35,
            elds_slots=20,
            merit_cutoff=50.0,
            catchment_cutoff=40.0,
            elds_cutoff=35.0,
            required_utme_subjects=["English", "Mathematics", "Physics", "Chemistry"],
            mandatory_olevel_subjects=["English Language", "Mathematics", "Physics", "Chemistry"]
        ),
        Programme(
            university_id=1,
            faculty_id=1,
            name="Computer Science",
            code="CSC",
            duration_years=4,
            min_utme_score=170,
            total_slots=80,
            merit_slots=36,
            catchment_slots=28,
            elds_slots=16,
            merit_cutoff=48.0,
            catchment_cutoff=38.0,
            elds_cutoff=33.0,
            required_utme_subjects=["English", "Mathematics", "Physics", "Chemistry"],
            mandatory_olevel_subjects=["English Language", "Mathematics", "Physics"]
        )
    ]
    for prog in programmes:
        db.session.add(prog)
    
    db.session.commit()
    
    # 7. Create Admin User
    admin = User(
        username="admin",
        email="admin@custech.edu.ng",
        full_name="System Administrator",
        role="super_admin",
        is_active=True
    )
    admin.set_password("admin123")  # Change in production!
    db.session.add(admin)
    
    db.session.commit()
    
    print("Database seeded successfully!")


def generate_test_candidates(count=100):
    """Generate realistic test candidates for demonstration.

    Every candidate is generated with all mandatory O'Level subjects at credit
    level (C6 or better) so that the screening engine can actually produce a
    mix of recommended / rejected outcomes based on UTME score and aggregate
    thresholds rather than universally failing the O'Level check.
    """
    import random
    from faker import Faker

    fake = Faker('en')

    session = AcademicSession.query.filter_by(is_active=True).first()
    if not session:
        print('❌ No active academic session found. Run flask seed-config first.')
        return

    programmes = Programme.query.all()
    if not programmes:
        print('❌ No programmes found. Run flask seed-programmes first.')
        return

    nigerian_states = [
        'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
        'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'Gombe',
        'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara',
        'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau',
        'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara', 'FCT',
    ]

    # Credit-level grades only (C6 and above)
    credit_grades = ['A1', 'B2', 'B3', 'C4', 'C5', 'C6']
    credit_weights = [0.10, 0.18, 0.22, 0.20, 0.18, 0.12]

    # Additional O'Level subjects to pad to >=5 total
    extra_subjects_pool = [
        'Agricultural Science', 'Commerce', 'CRS', 'Further Mathematics',
        'Technical Drawing', 'Home Economics', 'French', 'Yoruba', 'Igbo', 'Hausa',
    ]
    all_grades = ['A1', 'B2', 'B3', 'C4', 'C5', 'C6', 'D7', 'E8']
    all_grade_weights = [0.05, 0.10, 0.15, 0.20, 0.20, 0.15, 0.10, 0.05]

    # Map programme mandatory subjects -> appropriate UTME subject combo
    # We also want ~30% of candidates to have post_utme_score so we can demo aggregate

    created = 0
    per_programme = max(1, count // len(programmes))

    for programme in programmes:
        mandatory_olevel = programme.mandatory_olevel_subjects or ['English Language', 'Mathematics']
        required_utme = programme.required_utme_subjects or ['English', 'Mathematics', 'Physics', 'Chemistry']
        min_utme = programme.min_utme_score or 140

        for _ in range(per_programme):
            state = random.choice(nigerian_states)

            # Realistic UTME score distribution:
            # 20% top scorers (300-400) — can reach merit cutoff
            # 40% competitive (min_utme to 300) — catchment/ELDS range
            # 40% below cutoff (rejected at step 1)
            rand = random.random()
            if rand < 0.20:
                utme_score = random.randint(300, 400)
            elif rand < 0.60:
                utme_score = random.randint(min_utme, 300)
            else:
                utme_score = random.randint(max(100, min_utme - 60), min_utme - 1)

            # Build UTME subjects dict from programme's required subjects
            utme_subjects = {}
            for subj in required_utme:
                # Handle compound subjects like 'Chemistry/Economics'
                chosen = subj.split('/')[0].strip()
                utme_subjects[chosen] = random.randint(35, 95)

            # Ensure 'English' is always present (JAMB requirement)
            if 'English' not in utme_subjects:
                utme_subjects['English'] = random.randint(35, 90)

            # ~85% have sat Post-UTME (merit list screening happens after Post-UTME)
            post_utme_present = random.random() < 0.85
            post_utme_score = round(random.uniform(35.0, 95.0), 1) if post_utme_present else None

            # Generate a unique 10-digit JAMB reg
            jamb_reg = str(random.randint(2025100000, 2025999999))
            while Candidate.query.filter_by(jamb_reg_number=jamb_reg).first():
                jamb_reg = str(random.randint(2025100000, 2025999999))

            candidate = Candidate(
                session_id=session.id,
                jamb_reg_number=jamb_reg,
                full_name=fake.name(),
                email=fake.email(),
                phone=fake.phone_number()[:20],
                gender=random.choice(['Male', 'Female']),
                state_of_origin=state,
                lga_of_origin=fake.city()[:64],
                first_choice_programme_id=programme.id,
                utme_score=utme_score,
                utme_subjects=utme_subjects,
                post_utme_score=post_utme_score,
                post_utme_present=post_utme_present,
                status='pending',
            )
            db.session.add(candidate)
            db.session.flush()  # get candidate.id

            # --- O'Level results ---
            # 1. Always include ALL mandatory subjects at credit level
            seen_subjects = set()
            for subject in mandatory_olevel:
                grade = random.choices(credit_grades, weights=credit_weights)[0]
                db.session.add(OLevelResult(
                    candidate_id=candidate.id,
                    exam_body=random.choice(['WAEC', 'NECO']),
                    exam_number=f'{random.randint(40000000, 49999999)}',
                    exam_year=random.choice([2023, 2024]),
                    sitting_number=1,
                    subject=subject,
                    grade=grade,
                ))
                seen_subjects.add(subject.lower())

            # 2. Pad to at least 5 subjects with random extras
            extras_needed = max(0, 5 - len(seen_subjects))
            available_extras = [s for s in extra_subjects_pool if s.lower() not in seen_subjects]
            random.shuffle(available_extras)
            for subject in available_extras[:extras_needed]:
                grade = random.choices(all_grades, weights=all_grade_weights)[0]
                db.session.add(OLevelResult(
                    candidate_id=candidate.id,
                    exam_body=random.choice(['WAEC', 'NECO']),
                    exam_number=f'{random.randint(40000000, 49999999)}',
                    exam_year=random.choice([2023, 2024]),
                    sitting_number=1,
                    subject=subject,
                    grade=grade,
                ))

            created += 1

    db.session.commit()
    print(f'✅ Generated {created} test candidates across {len(programmes)} programmes')


def create_admin_user():
    """Create admin user if not exists"""
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@custech.edu.ng",
            full_name="System Administrator",
            role="super_admin",
            is_active=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created!")


def reset_database():
    """Reset database for fresh seeding"""
    print("🗑️ Reseting database...")
    
    # Drop all tables
    db.drop_all()
    print("   - Dropped all tables")
    
    # Create all tables
    db.create_all()
    print("   - Created all tables")
    
    # Seed fresh data
    seed_all()
    print("✅ Database reset and reseeded!")


def get_database_stats():
    """Get current database statistics"""
    stats = {
        'academic_sessions': AcademicSession.query.count(),
        'universities': University.query.count(),
        'faculties': Faculty.query.count(),
        'programmes': Programme.query.count(),
        'candidates': Candidate.query.count(),
        'olevel_results': OLevelResult.query.count(),
        'users': User.query.count(),
        'catchment_states': CatchmentState.query.count(),
        'elds_states': ELDSState.query.count()
    }
    
    print("Database Statistics:")
    for key, value in stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    return stats


# CLI Commands
def register_cli_commands(app):
    """Register CLI commands with Flask app"""
    import click
    
    @app.cli.command("seed")
    def seed_command():
        """Seed the database with basic data."""
        seed_all()
    
    @app.cli.command("seed-programmes")
    def seed_programmes_command():
        """Seed CUSTECH faculties and programmes into the database."""
        seed_programmes()
    
    @app.cli.command("seed-config")
    def seed_config_command():
        """Seed university configuration."""
        seed_university_config()
    
    @app.cli.command("seed-all")
    def seed_all_command():
        """Run all seed operations in order."""
        print("🌱 Running all seed operations...")
        try:
            seed_university_config()
            seed_programmes()
            create_admin_user()
            print("✅ All seed operations complete!")
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            raise
    
    @app.cli.command("generate-candidates")
    @click.argument('count', type=int)
    def generate_candidates_command(count):
        """Generate test candidates."""
        generate_test_candidates(count)
    
    @app.cli.command("create-admin")
    def create_admin_command():
        """Create admin user interactively."""
        create_admin_user()
    
    @app.cli.command('reset-db')
    def reset_db():
        """Drop all tables and recreate."""
        print('🗑️ Resetting database...')
        db.drop_all()
        db.create_all()
        print('✅ Database reset complete. Run \'flask seed-all\' to populate.')

    @app.cli.command('screen-all')
    def screen_all_command():
        """Screen every candidate that has a first-choice programme but no AdmissionRecord."""
        from collections import defaultdict
        from app.models import (
            University, Programme, AcademicSession, Candidate, AdmissionRecord
        )
        from app.services.screening_engine import ScreeningEngine

        uni = University.query.first()
        if not uni:
            print('❌ No university configured.')
            return

        session = AcademicSession.query.filter_by(is_active=True).first()
        if not session:
            print('❌ No active academic session.')
            return

        # Find all candidates with a programme but no AdmissionRecord
        screened_ids = db.session.query(AdmissionRecord.candidate_id)\
            .filter_by(session_id=session.id).distinct().subquery()

        unscreened = Candidate.query.filter(
            Candidate.session_id == session.id,
            Candidate.first_choice_programme_id.isnot(None),
            ~Candidate.id.in_(db.session.query(screened_ids.c.candidate_id))
        ).all()

        if not unscreened:
            print('✅ No unscreened candidates found — all done!')
            return

        print(f'⚙️  Screening {len(unscreened)} candidates...')

        groups = defaultdict(list)
        for c in unscreened:
            groups[c.first_choice_programme_id].append(c.id)

        total_recommended = 0
        total_rejected = 0

        for prog_id, cand_ids in groups.items():
            prog = Programme.query.get(prog_id)
            try:
                engine = ScreeningEngine(uni.id, prog_id, session.id)
                results = engine.screen_batch(cand_ids)
                db.session.commit()
                total_recommended += results['admitted']
                total_rejected += results['rejected']
                print(f'  {prog.code if prog else prog_id}: '
                      f'{results["total"]} screened, '
                      f'{results["admitted"]} recommended, '
                      f'{results["rejected"]} rejected')
            except Exception as exc:
                db.session.rollback()
                print(f'  ❌ {prog.code if prog else prog_id}: {exc}')

        print()
        print(f'✅ Bulk screening complete: {total_recommended} recommended, {total_rejected} rejected')
    
    @app.cli.command("test-upload")
    def test_upload():
        """Test JAMB CSV upload with sample data"""
        from app.services.candidate_processor import CandidateProcessor
        from app.utils.helpers import get_active_session
        
        processor = CandidateProcessor()
        session = get_active_session()
        
        test_file = 'app/static/templates/jamb_template.csv'
        
        # Test preview
        preview = processor.get_preview(test_file)
        print(f"Format detected as JAMB: {preview['is_jamb_format']}")
        print(f"Preview rows: {len(preview['preview'])}")
        
        # Test import
        result = processor.process_file(test_file, session.id)
        print("\nImport Summary:")
        print(f"  Created: {result['created']}")
        print(f"  Skipped: {result['skipped']}")
        print(f"  Errors: {result['errors']}")
        
        if result['error_details']:
            print("\nErrors:")
            for error in result['error_details']:
                print(f"  - {error}")
