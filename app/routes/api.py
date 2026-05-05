from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from sqlalchemy.orm import joinedload
from app.models import AdmissionBatch, Candidate, Programme, University
from app.services.screening_engine import ScreeningEngine
from app.services.merit_list import MeritListGenerator
from app.utils.helpers import get_active_session

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/admission/generate/<int:programme_id>', methods=['POST'])
@login_required
def generate_admissions(programme_id):
    """Generate admission decisions for a specific programme"""
    try:
        active_session = get_active_session()
        if not active_session:
            return jsonify({'success': False, 'message': 'No active session found'}), 400

        programme = Programme.query.get_or_404(programme_id)
        generator = MeritListGenerator(programme_id, active_session.id)
        generator.generate_full_list()
        db.session.commit()

        stats = generator.get_statistics()
        return jsonify({
            'success': True,
            'message': f'Admissions generated for {programme.name}',
            'programme': programme.name,
            'stats': {
                'total_slots': stats['total_slots'],
                'filled': stats['filled'],
                'merit_admitted': stats['merit']['filled'],
                'catchment_admitted': stats['catchment']['filled'],
                'elds_admitted': stats['elds']['filled'],
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admission/generate-all', methods=['POST'])
@login_required
def generate_all_admissions():
    """Generate admission decisions for ALL programmes"""
    try:
        active_session = get_active_session()
        if not active_session:
            return jsonify({'success': False, 'message': 'No active session found'}), 400

        programmes = Programme.query.all()
        total_admitted = 0
        results = []

        for programme in programmes:
            try:
                generator = MeritListGenerator(programme.id, active_session.id)
                generator.generate_full_list()
                stats = generator.get_statistics()
                total_admitted += stats['filled']
                results.append({
                    'programme': programme.name,
                    'code': programme.code,
                    'admitted': stats['filled'],
                    'slots': stats['total_slots']
                })
            except Exception as prog_err:
                results.append({
                    'programme': programme.name,
                    'code': programme.code,
                    'error': str(prog_err)
                })

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Admissions generated for {len(programmes)} programmes. {total_admitted} candidates admitted.',
            'total_admitted': total_admitted,
            'results': results
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admission/screen', methods=['POST'])
@login_required
def screen_candidates():
    """AJAX endpoint for batch screening candidates"""
    try:
        data = request.get_json()
        candidate_ids = data.get('candidate_ids', [])

        if not candidate_ids:
            return jsonify({
                'success': False,
                'message': 'No candidate IDs provided'
            }), 400

        # Get active session and university
        active_session = get_active_session()
        if not active_session:
            return jsonify({
                'success': False,
                'message': 'No active academic session found'
            }), 400

        university = University.query.first()
        if not university:
            return jsonify({
                'success': False,
                'message': 'No university configuration found'
            }), 400

        # Load all requested candidates
        candidates = Candidate.query.filter(
            Candidate.id.in_(candidate_ids)
        ).all()

        if not candidates:
            return jsonify({
                'success': False,
                'message': 'No valid candidates found'
            }), 400

        # --- GROUP by programme so each candidate is screened against
        # their own programme's rules, cutoffs, and subject requirements ---
        programme_groups: dict[int, list] = {}
        skipped_no_programme = []
        for candidate in candidates:
            if not candidate.first_choice_programme_id:
                skipped_no_programme.append(candidate.id)
                continue
            pid = candidate.first_choice_programme_id
            programme_groups.setdefault(pid, []).append(candidate)

        if not programme_groups:
            return jsonify({
                'success': False,
                'message': 'None of the selected candidates have a first choice programme set.'
            }), 400

        # Create one batch record to track overall progress
        batch = AdmissionBatch(
            session_id=active_session.id,
            programme_id=next(iter(programme_groups)),   # representative programme
            batch_name=f"Batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            quota_category="all",
            processed_by=current_user.id,
            total_candidates=len(candidates) - len(skipped_no_programme),
            admitted_count=0,
            rejected_count=0
        )
        db.session.add(batch)
        db.session.flush()

        total_admitted = 0
        total_rejected = 0
        all_results = []
        programme_errors = []

        # Screen each group with the correct engine for that programme
        for programme_id, prog_candidates in programme_groups.items():
            try:
                engine = ScreeningEngine(
                    university_id=university.id,
                    programme_id=programme_id,
                    session_id=active_session.id
                )
                ids = [c.id for c in prog_candidates]
                results = engine.screen_batch(ids)
                total_admitted += results['admitted']
                total_rejected += results['rejected']
                all_results.extend(results['results'])
            except Exception as prog_err:
                programme = Programme.query.get(programme_id)
                prog_name = programme.name if programme else f"Programme #{programme_id}"
                programme_errors.append(f"{prog_name}: {str(prog_err)}")

        # Update batch totals
        batch.admitted_count = total_admitted
        batch.rejected_count = total_rejected
        batch.processed_at = datetime.utcnow()
        db.session.commit()

        response_payload = {
            'success': True,
            'batch_id': batch.id,
            'summary': {
                'total': total_admitted + total_rejected,
                'admitted': total_admitted,
                'rejected': total_rejected,
                'results': all_results
            },
            'message': f'Screening completed for {total_admitted + total_rejected} candidates across {len(programme_groups)} programme(s)'
        }
        if skipped_no_programme:
            response_payload['skipped'] = skipped_no_programme
            response_payload['skip_reason'] = 'No first choice programme set'
        if programme_errors:
            response_payload['programme_errors'] = programme_errors

        return jsonify(response_payload)

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'API error: {str(e)}'
        }), 500



@api_bp.route('/admission/logs/<int:batch_id>')
@login_required
def get_batch_logs(batch_id):
    """Get screening logs for a batch"""
    try:
        batch = AdmissionBatch.query.get_or_404(batch_id)
        
        # For now, return basic log info
        # In production, you might want to store detailed logs in a separate table
        logs = [
            {
                'timestamp': batch.processed_at.isoformat() if batch.processed_at else datetime.utcnow().isoformat(),
                'level': 'info',
                'message': f'Screening batch {batch.batch_name} started'
            },
            {
                'timestamp': batch.processed_at.isoformat() if batch.processed_at else datetime.utcnow().isoformat(),
                'level': 'info',
                'message': f'Processing {batch.total_candidates} candidates'
            }
        ]
        
        if batch.processed_at:
            logs.append({
                'timestamp': batch.processed_at.isoformat(),
                'level': 'success',
                'message': f'Screening completed: {batch.admitted_count} admitted, {batch.rejected_count} rejected'
            })
        
        return jsonify({
            'success': True,
            'logs': logs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching logs: {str(e)}'
        }), 500


@api_bp.route('/admission/status/<int:batch_id>')
@login_required
def get_batch_status(batch_id):
    """Get screening status for a batch"""
    try:
        batch = AdmissionBatch.query.get_or_404(batch_id)
        
        total_processed = batch.admitted_count + batch.rejected_count
        progress_percent = (total_processed / batch.total_candidates * 100) if batch.total_candidates > 0 else 100
        
        status = 'completed' if batch.processed_at else 'processing'
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'total_candidates': batch.total_candidates,
            'processed': total_processed,
            'admitted': batch.admitted_count,
            'rejected': batch.rejected_count,
            'progress_percent': round(progress_percent, 1),
            'status': status,
            'message': f'Processed {total_processed} of {batch.total_candidates} candidates'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching status: {str(e)}'
        }), 500


@api_bp.route('/candidates/validate-jamb')
@login_required
def validate_jamb_reg():
    """Validate JAMB registration number via AJAX"""
    jamb_reg = request.args.get('jamb_reg_number', type=str, default='').strip().upper()
    
    if not jamb_reg:
        return jsonify({
            'valid': False,
            'message': 'JAMB registration number is required.'
        }), 400
    
    try:
        from app.services.candidate_processor import CandidateProcessor
        processor = CandidateProcessor(validate_duplicates=False, skip_errors=True)
        valid, result = processor.validate_jamb_reg(jamb_reg)
        
        if not valid:
            return jsonify({
                'valid': False,
                'message': result
            })
        
        from app.models import Candidate
        exists = Candidate.query.filter_by(jamb_reg_number=result).first() is not None
        
        return jsonify({
            'valid': not exists,
            'exists': exists,
            'normalized': result,
            'message': 'JAMB number already exists.' if exists else 'JAMB number is available.'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': f'Validation error: {str(e)}'
        }), 500


@api_bp.route('/programmes/<int:programme_id>/details')
@login_required
def get_programme_details(programme_id):
    """Get programme details for AJAX requests"""
    try:
        programme = Programme.query.options(
            joinedload(Programme.university),
            joinedload(Programme.faculty)
        ).get_or_404(programme_id)
        
        return jsonify({
            'success': True,
            'programme': {
                'id': programme.id,
                'name': programme.name,
                'code': programme.code,
                'university': programme.university.name,
                'faculty': programme.faculty.name,
                'min_utme_score': programme.min_utme_score,
                'total_slots': programme.total_slots,
                'merit_cutoff': programme.merit_cutoff,
                'catchment_cutoff': programme.catchment_cutoff,
                'elds_cutoff': programme.elds_cutoff,
                'required_utme_subjects': programme.required_utme_subjects,
                'mandatory_olevel_subjects': programme.mandatory_olevel_subjects
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching programme details: {str(e)}'
        }), 500


@api_bp.route('/candidates/search')
@login_required
def search_candidates():
    """Search candidates via AJAX"""
    try:
        query = request.args.get('q', type=str, default='').strip()
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=20)
        
        if not query or len(query) < 2:
            return jsonify({
                'success': False,
                'message': 'Search query must be at least 2 characters'
            }), 400
        
        # Search candidates
        candidates = Candidate.query.filter(
            Candidate.jamb_reg_number.ilike(f'%{query}%') |
            Candidate.full_name.ilike(f'%{query}%')
        ).limit(per_page).offset((page - 1) * per_page).all()
        
        results = []
        for candidate in candidates:
            results.append({
                'id': candidate.id,
                'jamb_reg_number': candidate.jamb_reg_number,
                'full_name': candidate.full_name,
                'state_of_origin': candidate.state_of_origin,
                'utme_score': candidate.utme_score,
                'programme': candidate.first_choice_programme.name if candidate.first_choice_programme else None
            })
        
        return jsonify({
            'success': True,
            'candidates': results,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Search error: {str(e)}'
        }), 500


@api_bp.route('/health')
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'api',
        'timestamp': datetime.utcnow().isoformat()
    })
