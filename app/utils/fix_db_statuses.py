import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from run import app
from app import db
from app.models import Candidate, AdmissionRecord

def fix_candidate_statuses():
    """Align Candidate.status with AdmissionRecord.status in the database."""
    print("🚀 Running candidate status database alignment utility...")
    
    with app.app_context():
        # Get all candidates
        candidates = Candidate.query.all()
        print(f"Loaded {len(candidates)} candidates from database.")
        
        fixed_count = 0
        status_counts = {}
        
        for candidate in candidates:
            # Get their admission record
            record = AdmissionRecord.query.filter_by(
                candidate_id=candidate.id,
                session_id=candidate.session_id
            ).first()
            
            old_status = candidate.status
            new_status = 'pending'
            
            if record:
                new_status = record.status
            
            if old_status != new_status:
                candidate.status = new_status
                fixed_count += 1
                status_counts[new_status] = status_counts.get(new_status, 0) + 1
        
        if fixed_count > 0:
            db.session.commit()
            print(f"✅ Successfully updated {fixed_count} candidates:")
            for status, count in status_counts.items():
                print(f"  - {status}: {count} candidates")
        else:
            print("✨ No candidates needed status alignment. Database is already in sync!")

if __name__ == '__main__':
    fix_candidate_statuses()
