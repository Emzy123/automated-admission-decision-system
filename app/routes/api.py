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


@api_bp.before_request
def require_staff():
    from flask import request
    if request.endpoint == 'api.health_check':
        return None
    from flask_login import current_user
    if not current_user.is_authenticated:
        from flask import redirect, url_for, flash
        flash("Please sign in to continue.", "warning")
        return redirect(url_for('index'))
    if current_user.role not in ["admin", "super_admin", "admission_officer", "faculty_officer"]:
        from flask import abort
        abort(403)


@api_bp.route('/admission/generate/<int:programme_id>', methods=['POST'])
@login_required
def generate_admissions(programme_id):
    """Generate merit list for a specific programme — runs synchronously."""
    try:
        active_session = get_active_session()
        if not active_session:
            return jsonify({'success': False, 'message': 'No active session found'}), 400

        programme = Programme.query.get_or_404(programme_id)
        generator = MeritListGenerator(programme_id, active_session.id)
        result = generator.generate_full_list(persist=True)
        db.session.commit()

        stats = generator.get_statistics(result)
        return jsonify({
            'success': True,
            'sync': True,
            'programme': programme.name,
            'total_admitted': stats.get('filled', 0),
            'message': f'Merit list generated for {programme.name}: {stats.get("filled", 0)} admitted.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admission/generate-all', methods=['POST'])
@login_required
def generate_all_admissions():
    """Generate merit lists for ALL programmes — runs synchronously."""
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
                merit_data = generator.generate_full_list(persist=True)
                db.session.flush()
                stats = generator.get_statistics(merit_data)
                total_admitted += stats.get('filled', 0)
                results.append({'programme': programme.name, 'admitted': stats.get('filled', 0)})
            except Exception as prog_err:
                db.session.rollback()
                results.append({'programme': programme.name, 'error': str(prog_err)})
        db.session.commit()

        return jsonify({
            'success': True,
            'sync': True,
            'total_programmes': len(programmes),
            'total_admitted': total_admitted,
            'results': results,
            'message': f'Merit lists generated for {len(programmes)} programmes: {total_admitted} total admitted.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admission/screen', methods=['POST'])
@login_required
def screen_candidates():
    """AJAX endpoint for batch screening candidates — runs synchronously."""
    import logging
    from datetime import datetime as _dt
    logger = logging.getLogger(__name__)
    try:
        data = request.get_json()
        candidate_ids = data.get('candidate_ids', [])

        if not candidate_ids:
            return jsonify({'success': False, 'message': 'No candidate IDs provided'}), 400

        active_session = get_active_session()
        if not active_session:
            return jsonify({'success': False, 'message': 'No active academic session found'}), 400

        university = University.query.first()
        if not university:
            return jsonify({'success': False, 'message': 'No university configuration found'}), 400

        candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
        if not candidates:
            return jsonify({'success': False, 'message': 'No valid candidates found'}), 400

        # Group by first-choice programme
        programme_groups: dict = {}
        no_programme: list = []
        for c in candidates:
            if c.first_choice_programme_id:
                programme_groups.setdefault(c.first_choice_programme_id, []).append(c)
            else:
                no_programme.append(c.id)

        if not programme_groups:
            return jsonify({
                'success': False,
                'message': 'None of the selected candidates have a first-choice programme assigned.'
            }), 400

        total_admitted = 0
        total_rejected = 0
        first_programme_id = next(iter(programme_groups))

        for programme_id, prog_candidates in programme_groups.items():
            try:
                engine = ScreeningEngine(
                    university_id=university.id,
                    programme_id=programme_id,
                    session_id=active_session.id
                )
                for c in prog_candidates:
                    result = engine.screen_candidate(c)
                    if result.get('status') == 'recommended':
                        total_admitted += 1
                    else:
                        total_rejected += 1
                db.session.flush()
            except Exception as prog_err:
                db.session.rollback()
                logger.exception("Screening failed for programme %s", programme_id)

        # Persist a batch tracking record
        now = _dt.utcnow()
        batch = AdmissionBatch(
            session_id=active_session.id,
            programme_id=first_programme_id,
            batch_name=f"BatchScreen_{now.strftime('%Y%m%d_%H%M%S')}",
            quota_category="all",
            processed_by=current_user.id,
            total_candidates=len(candidates),
            admitted_count=total_admitted,
            rejected_count=total_rejected,
            processed_at=now,
        )
        db.session.add(batch)
        db.session.commit()

        return jsonify({
            'success': True,
            'sync': True,
            'batch_id': batch.id,
            'total': len(candidates),
            'admitted': total_admitted,
            'rejected': total_rejected,
            'skipped': len(no_programme),
            'message': f'Screening complete: {total_admitted} recommended, {total_rejected} not recommended.'
        })

    except Exception as e:
        db.session.rollback()
        logger.exception("screen_candidates API error")
        return jsonify({'success': False, 'message': f'Screening error: {str(e)}'}), 500





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
