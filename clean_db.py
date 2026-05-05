#!/usr/bin/env python3
"""
Database cleanup script to prepare for fresh manual testing
"""

import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import (
    Candidate, User, OLevelResult, AdmissionRecord, 
    AdmissionBatch, MeritListApproval, AuditLog,
    AcademicSession, University, Faculty, Programme, CatchmentState
)

def clean_database():
    """Clean database for fresh manual testing while preserving basic structure"""
    app = create_app()
    
    with app.app_context():
        print("🧹 Cleaning Database for Fresh Manual Testing")
        print("=" * 50)
        
        # Get counts before cleaning
        candidates_before = Candidate.query.count()
        users_before = User.query.count()
        admission_records_before = AdmissionRecord.query.count()
        
        print(f"📊 Before Cleaning:")
        print(f"   Candidates: {candidates_before}")
        print(f"   Users: {users_before}")
        print(f"   Admission Records: {admission_records_before}")
        
        # Clean in order of dependencies to avoid foreign key constraints
        print("\n🗑️  Cleaning data...")
        
        # Clean admission-related tables first
        admission_batches = AdmissionBatch.query.count()
        MeritListApproval.query.delete()
        AdmissionBatch.query.delete()
        AdmissionRecord.query.delete()
        print(f"   ✅ Cleaned {admission_batches} admission batches and related records")
        
        # Clean O'Level results (dependent on candidates)
        olevel_results = OLevelResult.query.count()
        OLevelResult.query.delete()
        print(f"   ✅ Cleaned {olevel_results} O'Level results")
        
        # Clean candidates
        candidates_deleted = Candidate.query.count()
        Candidate.query.delete()
        print(f"   ✅ Cleaned {candidates_deleted} candidates")
        
        # Clean user accounts (except admin)
        admin_users = User.query.filter_by(role='admin').count()
        applicant_users = User.query.filter_by(role='applicant').count()
        User.query.filter(User.role != 'admin').delete()
        print(f"   ✅ Cleaned {applicant_users} applicant accounts (kept {admin_users} admin accounts)")
        
        # Clean audit logs
        audit_logs = AuditLog.query.count()
        AuditLog.query.delete()
        print(f"   ✅ Cleaned {audit_logs} audit logs")
        
        # Commit changes
        db.session.commit()
        
        # Verify cleaning
        candidates_after = Candidate.query.count()
        users_after = User.query.count()
        admission_records_after = AdmissionRecord.query.count()
        
        print(f"\n📊 After Cleaning:")
        print(f"   Candidates: {candidates_after}")
        print(f"   Users: {users_after} (admin accounts only)")
        print(f"   Admission Records: {admission_records_after}")
        
        # Show preserved structure
        print(f"\n🏛️ Preserved Structure:")
        sessions = AcademicSession.query.count()
        universities = University.query.count()
        faculties = Faculty.query.count()
        programmes = Programme.query.count()
        catchment_states = CatchmentState.query.count()
        
        print(f"   Academic Sessions: {sessions}")
        print(f"   Universities: {universities}")
        print(f"   Faculties: {faculties}")
        print(f"   Programmes: {programmes}")
        print(f"   Catchment States: {catchment_states}")
        
        # Show admin accounts
        admin_accounts = User.query.filter_by(role='admin').all()
        print(f"\n👤 Admin Accounts Preserved:")
        for admin in admin_accounts:
            print(f"   {admin.username} ({admin.full_name})")
        
        print(f"\n✅ Database cleaned successfully!")
        print(f"🚀 Ready for fresh manual testing!")
        
        return True

if __name__ == '__main__':
    try:
        success = clean_database()
        if success:
            print("\n🎉 Database Cleanup: SUCCESS")
            sys.exit(0)
        else:
            print("\n❌ Database Cleanup: FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during cleanup: {str(e)}")
        sys.exit(1)
