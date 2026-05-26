"""
CAPS Synchronization Service
Handles synchronization between local system and Mock CAPS.
"""

from datetime import datetime

from app import db
from app.models import Candidate, AdmissionRecord, Programme
from app.services.mock_caps import MockCAPSService


class CAPSSyncService:
    """
    Handles synchronization between local system and Mock CAPS.
    """
    
    @staticmethod
    def sync_candidate_to_caps(candidate):
        """Sync a single candidate's data to mock CAPS"""
        try:
            MockCAPSService.seed_from_candidates([candidate])
            return {
                'success': True,
                'message': f'Candidate {candidate.jamb_reg_number} synced to CAPS',
                'candidate_id': candidate.id
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to sync candidate: {str(e)}',
                'candidate_id': candidate.id
            }
    
    @staticmethod
    def bulk_verify_candidates(candidate_ids):
        """Verify multiple candidates against CAPS"""
        results = []
        successful_verifications = 0
        
        for cid in candidate_ids:
            candidate = Candidate.query.get(cid)
            if not candidate:
                results.append({
                    'candidate_id': cid,
                    'success': False,
                    'message': 'Candidate not found'
                })
                continue
            
            try:
                # Ensure candidate is synced to CAPS first
                MockCAPSService.seed_from_candidates([candidate])
                
                # Perform verification
                verification = MockCAPSService.verify_candidate(candidate.jamb_reg_number)
                
                # Update candidate CAPS status
                candidate.caps_verified = verification['verified']
                candidate.caps_verification_date = datetime.now() if verification['verified'] else None
                candidate.caps_verification_issues = verification.get('issues', [])
                candidate.caps_status = verification['status']
                
                if verification['verified']:
                    successful_verifications += 1
                
                results.append({
                    'candidate_id': cid,
                    'jamb_reg': candidate.jamb_reg_number,
                    'success': True,
                    'verified': verification['verified'],
                    'status': verification['status'],
                    'message': verification['message'],
                    'issues': verification.get('issues', []),
                    'caps_data': verification.get('caps_data', {})
                })
                
            except Exception as e:
                results.append({
                    'candidate_id': cid,
                    'jamb_reg': candidate.jamb_reg_number if candidate else 'Unknown',
                    'success': False,
                    'message': f'Verification failed: {str(e)}'
                })
        
        # Commit all changes
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Mark all results as failed
            for result in results:
                result['success'] = False
                result['message'] = f'Database error: {str(e)}'
        
        return {
            'total_processed': len(candidate_ids),
            'successful_verifications': successful_verifications,
            'results': results
        }
    
    @staticmethod
    def submit_admission_list_to_caps(programme_id, admitted_records, user_id):
        """Submit final admission list to mock CAPS"""
        try:
            programme = Programme.query.get(programme_id)
            if not programme:
                return {
                    'success': False,
                    'message': 'Programme not found'
                }
            
            # Prepare candidates data for CAPS upload
            candidates_data = []
            for record in admitted_records:
                candidate = record.candidate
                candidates_data.append({
                    'jamb_reg': candidate.jamb_reg_number,
                    'name': candidate.full_name,
                    'aggregate': record.aggregate_score,
                    'quota': record.quota_category,
                    'programme_code': programme.code
                })
            
            # Upload to CAPS
            upload_result = MockCAPSService.upload_admission_list(
                programme_code=programme.code,
                candidates=candidates_data,
                uploaded_by=user_id
            )
            
            if upload_result['success']:
                # Update records with CAPS upload info
                for record in admitted_records:
                    record.caps_status = 'uploaded'
                    record.caps_upload_id = upload_result['upload_id']
                    record.caps_uploaded_at = datetime.now()
                
                # Commit changes
                db.session.commit()
            
            return upload_result
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Failed to submit to CAPS: {str(e)}'
            }
    
    @staticmethod
    def check_upload_status(upload_id):
        """Check the status of a CAPS upload"""
        try:
            status = MockCAPSService.check_upload_status(upload_id)
            
            if 'error' in status:
                return {
                    'success': False,
                    'message': status['error']
                }
            
            return {
                'success': True,
                'status': status
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to check status: {str(e)}'
            }
    
    @staticmethod
    def simulate_candidate_acceptance(jamb_reg):
        """Simulate candidate accepting admission offer on CAPS"""
        try:
            acceptance = MockCAPSService.simulate_candidate_acceptance(jamb_reg)
            
            # Update local candidate record
            candidate = Candidate.query.filter_by(jamb_reg_number=jamb_reg).first()
            if candidate:
                candidate.caps_acceptance_status = acceptance['action']
                candidate.caps_acceptance_date = datetime.fromisoformat(acceptance['response_date'])
                db.session.commit()
            
            return {
                'success': True,
                'acceptance': acceptance
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Failed to simulate acceptance: {str(e)}'
            }
    
    @staticmethod
    def get_pending_verifications():
        """Get candidates pending CAPS verification"""
        candidates = Candidate.query.filter(
            Candidate.caps_verified == False,
            Candidate.status.in_(['pending', 'verified', 'recommended', 'admitted', 'finalized', 'waiting_list', 'accepted'])
        ).all()
        
        return [
            {
                'id': c.id,
                'jamb_reg': c.jamb_reg_number,
                'name': c.full_name,
                'state': c.state_of_origin,
                'utme_score': c.utme_score,
                'status': c.status
            }
            for c in candidates
        ]
    
    @staticmethod
    def get_verification_statistics():
        """Get CAPS verification statistics"""
        total_candidates = Candidate.query.count()
        verified_candidates = Candidate.query.filter(Candidate.caps_verified == True).count()
        pending_candidates = total_candidates - verified_candidates
        
        return {
            'total_candidates': total_candidates,
            'verified_candidates': verified_candidates,
            'pending_candidates': pending_candidates,
            'verification_rate': (verified_candidates / total_candidates * 100) if total_candidates > 0 else 0
        }
    
    @staticmethod
    def get_upload_statistics():
        """Get CAPS upload statistics"""
        uploaded_records = AdmissionRecord.query.filter(
            AdmissionRecord.caps_status == 'uploaded'
        ).count()
        
        # Get unique upload IDs
        upload_ids = db.session.query(AdmissionRecord.caps_upload_id).filter(
            AdmissionRecord.caps_upload_id.isnot(None)
        ).distinct().all()
        
        total_uploads = len([uid[0] for uid in upload_ids])
        
        return {
            'total_uploaded': uploaded_records,
            'total_uploads': total_uploads,
            'last_updated': datetime.now().isoformat()
        }
    
    @staticmethod
    def sync_all_candidates_to_caps():
        """Sync all candidates to CAPS (for initialization)"""
        try:
            candidates = Candidate.query.all()
            MockCAPSService.seed_from_candidates(candidates)
            
            return {
                'success': True,
                'message': f'Synced {len(candidates)} candidates to CAPS',
                'count': len(candidates)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to sync candidates: {str(e)}'
            }
    
    @staticmethod
    def get_candidate_caps_comparison(candidate_id):
        """Compare local candidate data with CAPS data"""
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return {
                'success': False,
                'message': 'Candidate not found'
            }
        
        # Get CAPS data
        caps_data = MockCAPSService.get_candidate_caps_data(candidate.jamb_reg_number)
        if not caps_data:
            return {
                'success': False,
                'message': 'Candidate not found in CAPS'
            }
        
        # Compare data
        comparison = {
            'jamb_reg': {
                'local': candidate.jamb_reg_number,
                'caps': caps_data.get('jamb_reg'),
                'match': candidate.jamb_reg_number == caps_data.get('jamb_reg')
            },
            'full_name': {
                'local': candidate.full_name,
                'caps': caps_data.get('full_name'),
                'match': candidate.full_name == caps_data.get('full_name')
            },
            'utme_score': {
                'local': candidate.utme_score,
                'caps': caps_data.get('utme_score'),
                'match': candidate.utme_score == caps_data.get('utme_score')
            },
            'state_of_origin': {
                'local': candidate.state_of_origin,
                'caps': caps_data.get('state_of_origin'),
                'match': candidate.state_of_origin == caps_data.get('state_of_origin')
            }
        }
        
        # Check O'Level results
        local_olevel = [
            {
                'subject': r.subject,
                'grade': r.grade,
                'exam_body': r.exam_body,
                'exam_year': r.exam_year
            }
            for r in candidate.olevel_results
        ]
        
        caps_olevel = caps_data.get('olevel_results', [])
        
        comparison['olevel_results'] = {
            'local_count': len(local_olevel),
            'caps_count': len(caps_olevel),
            'match': len(local_olevel) == len(caps_olevel)
        }
        
        return {
            'success': True,
            'candidate_id': candidate_id,
            'comparison': comparison,
            'overall_match': all(
                comparison[field]['match'] 
                for field in ['jamb_reg', 'full_name', 'utme_score', 'state_of_origin']
            )
        }
    
    @staticmethod
    def generate_admission_letters(programme_id):
        """Generate admission letters for all admitted candidates in a programme"""
        try:
            programme = Programme.query.get(programme_id)
            if not programme:
                return {
                    'success': False,
                    'message': 'Programme not found'
                }
            
            # Get admitted candidates
            admitted_records = AdmissionRecord.query.filter_by(
                programme_id=programme_id,
                status='admitted'
            ).all()
            
            letters = []
            for record in admitted_records:
                candidate = record.candidate
                reference = MockCAPSService.generate_admission_letter_reference(
                    candidate.jamb_reg_number,
                    programme.code
                )
                
                letters.append({
                    'candidate_id': candidate.id,
                    'jamb_reg': candidate.jamb_reg_number,
                    'name': candidate.full_name,
                    'programme': programme.name,
                    'reference': reference,
                    'quota': record.quota_category,
                    'aggregate': record.aggregate_score
                })
            
            return {
                'success': True,
                'programme': programme.name,
                'letters_generated': len(letters),
                'letters': letters
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to generate letters: {str(e)}'
            }
