"""
Mock CAPS (JAMB Central Admissions Processing System) Service
Simulates real-world JAMB verification and approval workflow for demonstration purposes.
"""

import random
import uuid
import hashlib
from datetime import datetime, timedelta


class MockCAPSService:
    """
    Simulates JAMB CAPS integration for demonstration purposes.
    Per project scope, this is a mock implementation with realistic behavior.
    """
    
    # Simulated CAPS database (in-memory, resets on server restart)
    _caps_database = {}  # jamb_reg -> candidate CAPS data
    _uploads = {}  # upload_id -> upload record
    
    @classmethod
    def seed_from_candidates(cls, candidates):
        """Populate mock CAPS with candidate data from our system"""
        for candidate in candidates:
            cls._caps_database[candidate.jamb_reg_number] = {
                'jamb_reg': candidate.jamb_reg_number,
                'full_name': candidate.full_name,
                'utme_score': candidate.utme_score,
                'utme_subjects': candidate.utme_subjects or [],
                'olevel_results': [
                    {
                        'exam_body': r.exam_body,
                        'exam_year': r.exam_year,
                        'subject': r.subject,
                        'grade': r.grade
                    }
                    for r in candidate.olevel_results or []
                ],
                'state_of_origin': candidate.state_of_origin,
                'caps_verified': False,
                'verification_issues': []
            }
    
    @classmethod
    def verify_candidate(cls, jamb_reg):
        """
        Simulate JAMB O'Level verification.
        Returns verification result with any mismatches.
        """
        caps_data = cls._caps_database.get(jamb_reg)
        
        if not caps_data:
            return {
                'verified': False,
                'status': 'not_found',
                'message': 'Candidate not found in JAMB CAPS database',
                'issues': ['JAMB registration number not recognized']
            }
        
        # Simulate random verification issues (for realism)
        # In real demo, you can control this via admin settings
        issues = []
        
        # Randomly flag some candidates for demo purposes
        if random.random() < 0.05:  # 5% chance of verification issue
            issues.append('O\'Level result mismatch - Please re-upload')
        
        # Check for missing O'Level results
        if len(caps_data.get('olevel_results', [])) < 5:
            issues.append('Insufficient O\'Level results - Minimum 5 subjects required')
        
        # Check for missing core subjects
        subjects = [r['subject'] for r in caps_data.get('olevel_results', [])]
        core_subjects = ['English Language', 'Mathematics']
        missing_core = [s for s in core_subjects if s not in subjects]
        if missing_core:
            issues.append(f'Missing core subjects: {", ".join(missing_core)}')
        
        verified = len(issues) == 0
        caps_data['caps_verified'] = verified
        caps_data['verification_issues'] = issues
        
        return {
            'verified': verified,
            'status': 'verified' if verified else 'queried',
            'message': 'Verification successful' if verified else 'Verification failed',
            'issues': issues,
            'caps_data': {
                'name': caps_data['full_name'],
                'utme_score': caps_data['utme_score'],
                'state': caps_data['state_of_origin'],
                'subjects_count': len(caps_data.get('olevel_results', [])),
                'verification_date': datetime.now().isoformat()
            }
        }
    
    @classmethod
    def upload_admission_list(cls, programme_code, candidates, uploaded_by):
        """
        Simulate uploading admission list to JAMB CAPS.
        Returns upload receipt with tracking ID.
        """
        upload_id = f"CAPS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        upload_record = {
            'upload_id': upload_id,
            'programme_code': programme_code,
            'candidate_count': len(candidates),
            'candidates': [c['jamb_reg'] for c in candidates],
            'uploaded_by': uploaded_by,
            'uploaded_at': datetime.now().isoformat(),
            'status': 'received',
            'status_checks': 0,
            'approval_status': None,
            'approved_count': 0,
            'queried_count': 0,
            'rejected_count': 0,
            'processing_notes': []
        }
        
        # Store upload record
        cls._uploads[upload_id] = upload_record
        
        return {
            'success': True,
            'upload_id': upload_id,
            'message': f'Successfully uploaded {len(candidates)} candidates to CAPS',
            'estimated_processing': '24-48 hours',
            'tracking_url': f'https://caps.jamb.gov.ng/tracking/{upload_id}'
        }
    
    @classmethod
    def check_upload_status(cls, upload_id):
        """
        Simulate checking CAPS upload processing status.
        Returns current status and any updates.
        """
        upload = cls._uploads.get(upload_id)
        
        if not upload:
            return {'error': 'Upload ID not found', 'message': 'Invalid upload tracking ID'}
        
        # Simulate processing progression
        statuses = ['received', 'processing', 'processing', 'processing', 'completed']
        current_idx = min(upload.get('status_checks', 0), len(statuses) - 1)
        upload['status'] = statuses[current_idx]
        upload['status_checks'] = current_idx + 1
        
        if upload['status'] == 'completed':
            # Simulate approval decisions
            total = upload['candidate_count']
            
            # Realistic approval rates
            approved = int(total * random.uniform(0.85, 0.98))
            queried = total - approved
            
            upload['approval_status'] = 'partial' if queried > 0 else 'full'
            upload['approved_count'] = approved
            upload['queried_count'] = queried
            upload['rejected_count'] = 0  # Usually no rejections in first round
            
            # Add processing notes
            if queried > 0:
                upload['processing_notes'].append(
                    f'{queried} candidates queried for additional documentation'
                )
            else:
                upload['processing_notes'].append('All candidates approved without queries')
        
        return {
            'upload_id': upload_id,
            'status': upload['status'],
            'approval_status': upload.get('approval_status'),
            'approved_count': upload.get('approved_count', 0),
            'queried_count': upload.get('queried_count', 0),
            'rejected_count': upload.get('rejected_count', 0),
            'processing_notes': upload.get('processing_notes', []),
            'message': cls._get_status_message(upload),
            'last_updated': datetime.now().isoformat()
        }
    
    @classmethod
    def _get_status_message(cls, upload):
        """Generate human-readable status message"""
        if upload['status'] == 'received':
            return 'Upload received by CAPS. Awaiting processing.'
        elif upload['status'] == 'processing':
            return 'CAPS is verifying candidate credentials and O\'Level results...'
        elif upload['status'] == 'completed':
            if upload.get('approval_status') == 'full':
                return 'All candidates approved by JAMB! Admission letters can be generated.'
            elif upload.get('approval_status') == 'partial':
                return f"{upload['approved_count']} approved, {upload['queried_count']} queried. Please address queries."
        return 'Unknown status'
    
    @classmethod
    def simulate_candidate_acceptance(cls, jamb_reg):
        """
        Simulate candidate accepting admission offer on CAPS portal.
        """
        # Simulate realistic acceptance patterns
        actions = ['accepted', 'accepted', 'accepted', 'pending', 'rejected']
        weights = [0.70, 0.15, 0.10, 0.04, 0.01]  # Most accept quickly
        
        action = random.choices(actions, weights=weights)[0]
        
        # Simulate different response times
        if action == 'accepted':
            response_time = random.choice([1, 2, 3, 7, 14])  # Most accept within 3 days
        elif action == 'pending':
            response_time = random.choice([3, 7, 14, 21])  # Some take longer
        else:  # rejected
            response_time = random.choice([5, 10, 15])  # Rejections usually take time
        
        response_date = datetime.now() + timedelta(days=response_time)
        
        return {
            'jamb_reg': jamb_reg,
            'action': action,
            'response_time_days': response_time,
            'response_date': response_date.isoformat(),
            'message': cls._get_acceptance_message(action),
            'caps_reference': cls._generate_caps_reference(jamb_reg)
        }
    
    @classmethod
    def _get_acceptance_message(cls, action):
        messages = {
            'accepted': 'Candidate has accepted admission offer.',
            'pending': 'Candidate has not yet responded to admission offer.',
            'rejected': 'Candidate has declined the admission offer.'
        }
        return messages.get(action, 'Unknown status')
    
    @classmethod
    def _generate_caps_reference(cls, jamb_reg):
        """Generate a simulated CAPS reference number"""
        data = f"{jamb_reg}{datetime.now().strftime('%Y%m%d')}"
        hash_val = hashlib.md5(data.encode()).hexdigest()[:8].upper()
        return f"CAPS/{datetime.now().year}/{hash_val}"
    
    @classmethod
    def generate_admission_letter_reference(cls, jamb_reg, programme_code):
        """
        Generate a simulated JAMB admission letter reference number.
        """
        data = f"{jamb_reg}{programme_code}{datetime.now().year}"
        hash_val = hashlib.md5(data.encode()).hexdigest()[:10].upper()
        
        return f"JAMB/ADM/{datetime.now().year}/{hash_val}"
    
    @classmethod
    def get_caps_statistics(cls):
        """Get overall CAPS statistics for dashboard"""
        total_candidates = len(cls._caps_database)
        verified_candidates = len([c for c in cls._caps_database.values() if c.get('caps_verified')])
        pending_candidates = total_candidates - verified_candidates
        
        total_uploads = len(cls._uploads)
        completed_uploads = len([u for u in cls._uploads.values() if u.get('status') == 'completed'])
        
        # Calculate upload statistics
        total_uploaded_candidates = sum(u.get('candidate_count', 0) for u in cls._uploads.values())
        total_approved = sum(u.get('approved_count', 0) for u in cls._uploads.values())
        total_queried = sum(u.get('queried_count', 0) for u in cls._uploads.values())
        
        return {
            'total_candidates': total_candidates,
            'verified_candidates': verified_candidates,
            'pending_candidates': pending_candidates,
            'verification_rate': (verified_candidates / total_candidates * 100) if total_candidates > 0 else 0,
            'total_uploads': total_uploads,
            'completed_uploads': completed_uploads,
            'pending_uploads': total_uploads - completed_uploads,
            'total_uploaded_candidates': total_uploaded_candidates,
            'total_approved': total_approved,
            'total_queried': total_queried,
            'approval_rate': (total_approved / total_uploaded_candidates * 100) if total_uploaded_candidates > 0 else 0,
            'last_updated': datetime.now().isoformat()
        }
    
    @classmethod
    def get_upload_details(cls, upload_id):
        """Get detailed information about a specific upload"""
        return cls._uploads.get(upload_id)
    
    @classmethod
    def get_candidate_caps_data(cls, jamb_reg):
        """Get complete CAPS data for a candidate"""
        return cls._caps_database.get(jamb_reg)
    
    @classmethod
    def reset_database(cls):
        """Reset the mock CAPS database (for testing)"""
        cls._caps_database.clear()
        cls._uploads.clear()
        return {'message': 'CAPS mock database reset successfully'}


def push_to_mock_caps(decision_payload):
    """
    Legacy function for backward compatibility.
    """
    return {
        "message": "Use MockCAPSService class instead.",
        "payload_ready": bool(decision_payload),
    }
