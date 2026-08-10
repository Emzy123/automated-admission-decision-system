from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models import AdmissionBatch, AdmissionRecord, Candidate, Programme, MeritListApproval
from app.services.merit_list import MeritListGenerator
from app.services.mock_caps import MockCAPSService
from app.services.caps_sync import CAPSSyncService
from app.utils.helpers import get_active_session
from flask import send_file

admission_bp = Blueprint("admission", __name__, url_prefix="/admission")


@admission_bp.before_request
def require_staff():
    from flask import request
    if request.endpoint == 'admission.health_check':
        return None
    from flask_login import current_user
    if not current_user.is_authenticated:
        from flask import redirect, url_for, flash
        flash("Please sign in to continue.", "warning")
        return redirect(url_for('index'))
    if current_user.role not in ["admin", "super_admin", "admission_officer", "faculty_officer"]:
        from flask import abort
        abort(403)


@admission_bp.route("/health")
def health_check():
    return jsonify({"status": "ok", "service": "admission"})


@admission_bp.route("/screening/screen-all-pending", methods=["POST"])
@login_required
def screen_all_pending():
    """Screen every candidate that has a programme but no AdmissionRecord yet — runs synchronously."""
    import logging
    from datetime import datetime as _dt
    logger = logging.getLogger(__name__)

    active_session = get_active_session()
    if not active_session:
        return jsonify({"success": False, "message": "No active session found."}), 400

    from app.models import University
    uni = University.query.first()
    if not uni:
        return jsonify({"success": False, "message": "No university configured."}), 400

    # Find all candidates with a programme but no AdmissionRecord
    screened_ids = db.session.query(AdmissionRecord.candidate_id)\
        .filter_by(session_id=active_session.id).distinct().subquery()

    unscreened = Candidate.query.filter(
        Candidate.session_id == active_session.id,
        Candidate.first_choice_programme_id.isnot(None),
        ~Candidate.id.in_(db.session.query(screened_ids.c.candidate_id))
    ).all()

    if not unscreened:
        return jsonify({"success": False, "message": "All candidates with a programme have already been screened."}), 400

    # Group by first-choice programme
    programme_groups: dict = {}
    for c in unscreened:
        programme_groups.setdefault(c.first_choice_programme_id, []).append(c)

    total_admitted = 0
    total_rejected = 0
    first_programme_id = next(iter(programme_groups))

    for programme_id, prog_candidates in programme_groups.items():
        try:
            from app.services.screening_engine import ScreeningEngine
            engine = ScreeningEngine(
                university_id=uni.id,
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
            logger.exception("screen_all_pending: failed for programme %s", programme_id)

    # Create a batch tracking record
    now = _dt.utcnow()
    batch = AdmissionBatch(
        session_id=active_session.id,
        programme_id=first_programme_id,
        batch_name=f"AllPending_{now.strftime('%Y%m%d_%H%M%S')}",
        quota_category="all",
        processed_by=current_user.id,
        total_candidates=len(unscreened),
        admitted_count=total_admitted,
        rejected_count=total_rejected,
        processed_at=now,
    )
    db.session.add(batch)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("screen_all_pending: batch commit failed")

    return jsonify({
        "success": True,
        "sync": True,
        "batch_id": batch.id if batch.id else None,
        "total": len(unscreened),
        "admitted": total_admitted,
        "rejected": total_rejected,
        "message": f"Screening complete: {total_admitted} recommended, {total_rejected} not recommended."
    })




@admission_bp.route("/screening")
@login_required
def screening_dashboard():
    """Main screening dashboard with unscreened candidates"""
    page = request.args.get("page", type=int, default=1)
    programme_id = request.args.get("programme_id", type=int)
    state_filter = request.args.get("state", type=str, default="").strip()
    utme_min = request.args.get("utme_min", type=int)
    utme_max = request.args.get("utme_max", type=int)
    
    # Get active session, return error if none exists
    active_session = get_active_session()
    if not active_session:
        flash("No active admission session configured. Please contact administrator.", "warning")
        return render_template("errors/404.html", message="No active session"), 404
    
    # Build query for unscreened candidates
    query = Candidate.query.options(
        joinedload(Candidate.first_choice_programme).joinedload(Programme.university),
        joinedload(Candidate.session)
    ).filter(
        ~Candidate.id.in_(
            db.session.query(AdmissionRecord.candidate_id).filter(
                AdmissionRecord.session_id == active_session.id
            )
        )
    )
    
    # Restrict to faculty if user is faculty officer
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        query = query.join(Programme, Candidate.first_choice_programme_id == Programme.id)\
                     .filter(Programme.faculty_id == current_user.faculty_id)
    
    # Apply filters
    if programme_id:
        query = query.filter(Candidate.first_choice_programme_id == programme_id)
    if state_filter:
        query = query.filter(Candidate.state_of_origin.ilike(f"%{state_filter}%"))
    if utme_min:
        query = query.filter(Candidate.utme_score >= utme_min)
    if utme_max:
        query = query.filter(Candidate.utme_score <= utme_max)
    
    # Order and paginate
    query = query.order_by(Candidate.utme_score.desc(), Candidate.full_name.asc())
    pagination = query.paginate(page=page, per_page=50, error_out=False)
    
    # Get filter options
    programmes_query = Programme.query.options(joinedload(Programme.university)).order_by(Programme.name.asc())
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        programmes_query = programmes_query.filter_by(faculty_id=current_user.faculty_id)
    programmes = programmes_query.all()
    states = db.session.query(Candidate.state_of_origin).distinct().order_by(Candidate.state_of_origin).all()
    states = [state[0] for state in states if state[0]]
    
    return render_template(
        "admin/screening_dashboard.html",
        candidates=pagination.items,
        pagination=pagination,
        programmes=programmes,
        states=states,
        selected_programme_id=programme_id,
        selected_state=state_filter,
        selected_utme_min=utme_min,
        selected_utme_max=utme_max
    )


@admission_bp.route("/screening/status/<int:batch_id>")
@login_required
def screening_status(batch_id):
    """Return JSON with batch screening progress"""
    batch = AdmissionBatch.query.get_or_404(batch_id)
    
    # Calculate progress based on processed candidates
    total_processed = batch.admitted_count + batch.rejected_count
    progress_percent = (total_processed / batch.total_candidates * 100) if batch.total_candidates > 0 else 0
    
    return jsonify({
        "batch_id": batch_id,
        "total_candidates": batch.total_candidates,
        "processed": total_processed,
        "admitted": batch.admitted_count,
        "rejected": batch.rejected_count,
        "progress_percent": round(progress_percent, 1),
        "status": "completed" if progress_percent >= 100 else "processing",
        "message": f"Processed {total_processed} of {batch.total_candidates} candidates"
    })


@admission_bp.route("/screening/results/<int:batch_id>")
@login_required
def screening_results(batch_id):
    """View detailed batch screening results & analytics report"""
    batch = AdmissionBatch.query.options(
        joinedload(AdmissionBatch.programme).joinedload(Programme.university),
        joinedload(AdmissionBatch.session)
    ).get_or_404(batch_id)
    
    # Get admission records for this batch
    records = AdmissionRecord.query.options(
        joinedload(AdmissionRecord.candidate),
        joinedload(AdmissionRecord.programme)
    ).filter(
        AdmissionRecord.session_id == batch.session_id,
        AdmissionRecord.programme_id == batch.programme_id
    ).order_by(AdmissionRecord.aggregate_score.desc()).all()
    
    # Compute Analytics Metrics
    total_records = len(records)
    admitted_count = sum(1 for r in records if r.status in ['recommended', 'admitted'])
    rejected_count = total_records - admitted_count
    
    aggregate_scores = [r.aggregate_score for r in records if r.aggregate_score is not None]
    avg_score = round(sum(aggregate_scores) / len(aggregate_scores), 2) if aggregate_scores else 0
    highest_score = round(max(aggregate_scores), 2) if aggregate_scores else 0
    lowest_score = round(min(aggregate_scores), 2) if aggregate_scores else 0
    
    # Quota breakdown for recommended candidates
    quota_counts = {"merit": 0, "catchment": 0, "elds": 0, "none": 0}
    state_counts = {}
    
    # Score distribution bands
    score_bands = {"80-100": 0, "70-79": 0, "60-69": 0, "50-59": 0, "<50": 0}
    
    for r in records:
        if r.status in ['recommended', 'admitted']:
            cat = (r.quota_category or 'none').lower()
            if cat in quota_counts:
                quota_counts[cat] += 1
            else:
                quota_counts['none'] += 1
                
        # State distribution
        if r.candidate and r.candidate.state_of_origin:
            st = r.candidate.state_of_origin.strip().title()
            state_counts[st] = state_counts.get(st, 0) + 1

        # Score distribution
        score = r.aggregate_score or 0
        if score >= 80:
            score_bands["80-100"] += 1
        elif score >= 70:
            score_bands["70-79"] += 1
        elif score >= 60:
            score_bands["60-69"] += 1
        elif score >= 50:
            score_bands["50-59"] += 1
        else:
            score_bands["<50"] += 1
            
    # Sort top 10 states
    top_states = dict(sorted(state_counts.items(), key=lambda item: item[1], reverse=True)[:10])

    analytics = {
        "avg_score": avg_score,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "quota_counts": quota_counts,
        "score_bands": score_bands,
        "top_states": top_states,
        "admission_rate": round((admitted_count / total_records * 100), 1) if total_records > 0 else 0
    }
    
    return render_template(
        "admin/screening_results.html",
        batch=batch,
        programme=batch.programme,
        session=batch.session,
        records=records,
        analytics=analytics,
        results={
            "total": total_records,
            "admitted": admitted_count,
            "rejected": rejected_count,
            "results": [
                {
                    "candidate_id": record.candidate_id,
                    "candidate_name": record.candidate.full_name if record.candidate else None,
                    "jamb_reg": record.candidate.jamb_reg_number if record.candidate else None,
                    "state_of_origin": record.candidate.state_of_origin if record.candidate else None,
                    "utme_score": record.candidate.utme_score if record.candidate else None,
                    "post_utme_score": record.candidate.post_utme_score if record.candidate else None,
                    "programme_name": record.programme.name if record.programme else None,
                    "programme_code": record.programme.code if record.programme else None,
                    "session_name": batch.session.name if batch.session else None,
                    "status": record.status,
                    "quota_category": record.quota_category,
                    "aggregate_score": record.aggregate_score,
                    "rejection_reason": record.rejection_reason,
                    "evaluation_log": record.evaluation_log
                }
                for record in records
            ]
        }
    )



@admission_bp.route("/screening/result/<int:record_id>")
@login_required
def screening_result_detail(record_id):
    """View detailed screening result for a single candidate"""
    record = AdmissionRecord.query.options(
        joinedload(AdmissionRecord.candidate).joinedload(Candidate.olevel_results),
        joinedload(AdmissionRecord.programme),
        joinedload(AdmissionRecord.session)
    ).get_or_404(record_id)
    
    return render_template("admin/screening_result_detail.html", record=record)


@admission_bp.route("/screening/override/<int:record_id>", methods=["POST"])
@login_required
def override_screening_result(record_id):
    """Override screening decision (admin only)"""
    record = AdmissionRecord.query.get_or_404(record_id)
    new_status = request.form.get("new_status")
    reason = request.form.get("reason", "").strip()
    
    if not new_status or new_status not in ["admitted", "recommended", "rejected"]:
        flash("Invalid status specified.", "danger")
        return redirect(request.referrer)
    
    if not reason:
        flash("Reason for override is required.", "danger")
        return redirect(request.referrer)
    
    # Update record
    old_status = record.status
    record.status = new_status
    if new_status in ["admitted", "recommended"]:
        record.rejection_reason = None  # Clear reason on override
    if record.candidate:
        record.candidate.status = new_status
    
    # Add override to evaluation log
    if not record.evaluation_log:
        record.evaluation_log = []
    
    record.evaluation_log.append({
        "step": "admin_override",
        "timestamp": datetime.utcnow().isoformat(),
        "old_status": old_status,
        "new_status": new_status,
        "reason": reason,
        "admin_id": current_user.id,
        "admin_name": current_user.full_name
    })
    
    # Log audit
    from app.utils.helpers import log_audit
    log_audit(
        action="override_screening",
        entity_type="Candidate",
        entity_id=record.candidate_id,
        details={
            "record_id": record.id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason
        }
    )
    
    db.session.commit()
    
    flash(f"Screening result overridden from {old_status} to {new_status}.", "success")
    return redirect(request.referrer or url_for("admission.screening_dashboard"))


@admission_bp.route("/run-screening")
@login_required
def run_screening():
    """Legacy endpoint - redirects to new screening dashboard"""
    return redirect(url_for("admission.screening_dashboard"))


@admission_bp.route("/merit-list")
@login_required
def merit_list_dashboard():
    """Main merit list dashboard showing all programmes"""
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    # Get all programmes with their statistics
    programmes_query = Programme.query.options(
        joinedload(Programme.university),
        joinedload(Programme.faculty)
    ).order_by(Programme.name.asc())
    
    # Restrict to faculty if user is faculty officer
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        programmes_query = programmes_query.filter_by(faculty_id=current_user.faculty_id)
        
    programmes = programmes_query.all()
    
    programme_stats = []
    for programme in programmes:
        try:
            generator = MeritListGenerator(programme.id, active_session.id)
            stats = generator.get_statistics()
            programme_stats.append({
                'programme': programme,
                'stats': stats
            })
        except Exception as e:
            # Skip programmes with errors
            programme_stats.append({
                'programme': programme,
                'stats': None,
                'error': str(e)
            })
    
    return render_template(
        "admin/merit_list_dashboard.html",
        programmes=programme_stats,
        session=active_session
    )


@admission_bp.route("/merit-list/<int:programme_id>")
@login_required
def merit_list_detail(programme_id):
    """View detailed merit list for a specific programme"""
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    programme = Programme.query.options(
        joinedload(Programme.university),
        joinedload(Programme.faculty)
    ).get_or_404(programme_id)
    
    try:
        generator = MeritListGenerator(programme_id, active_session.id)
        merit_data = generator.generate_full_list(persist=False)
        statistics = generator.get_statistics(merit_data)
        approval_status = generator.get_approval_status()
        
        return render_template(
            "admin/merit_list_detail.html",
            programme=programme,
            merit_data=merit_data,
            statistics=statistics,
            approval_status=approval_status,
            session=active_session
        )
        
    except Exception as e:
        flash(f"Error generating merit list: {e}", "danger")
        return redirect(url_for("admission.merit_list_dashboard"))


@admission_bp.route("/merit-list/<int:programme_id>/finalize", methods=["POST"])
@login_required
def finalize_merit_list(programme_id):
    """Finalize the merit list and prevent further changes"""
    if current_user.role not in ["admin", "admission_officer"]:
        flash("You don't have permission to finalize merit lists.", "danger")
        return redirect(request.referrer)
    
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    programme = Programme.query.get_or_404(programme_id)
    
    if not request.form.get("confirm"):
        flash("Please confirm the finalization action.", "warning")
        return redirect(url_for("admission.merit_list_detail", programme_id=programme_id))
    
    try:
        generator = MeritListGenerator(programme_id, active_session.id)
        
        if generator.finalize_list():
            flash(f"Merit list for {programme.name} has been finalized.", "success")
        else:
            flash("Failed to finalize merit list.", "danger")
            
    except Exception as e:
        flash(f"Error finalizing merit list: {e}", "danger")
    
    return redirect(url_for("admission.merit_list_detail", programme_id=programme_id))


@admission_bp.route("/merit-list/<int:programme_id>/export")
@login_required
def export_merit_list(programme_id):
    """Export merit list to Excel"""
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    programme = Programme.query.get_or_404(programme_id)
    quota_category = request.args.get("quota")
    
    try:
        generator = MeritListGenerator(programme_id, active_session.id)
        excel_file = generator.export_to_excel(quota_category)
        
        filename = f"{programme.code}_{'full' if not quota_category else quota_category}_merit_list.xlsx"
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f"Error exporting merit list: {e}", "danger")
        return redirect(url_for("admission.merit_list_detail", programme_id=programme_id))


@admission_bp.route("/merit-list/<int:programme_id>/approve/<level>", methods=["POST"])
@login_required
def approve_merit_list(programme_id, level):
    """Approve list at department, faculty, or senate level"""
    if current_user.role not in ["admin", "admission_officer", "faculty_officer"]:
        flash("You don't have permission to approve merit lists.", "danger")
        return redirect(request.referrer)
    
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    Programme.query.get_or_404(programme_id)
    
    # Check user permissions for different approval levels
    if level == "department" and current_user.role not in ["admin", "admission_officer"]:
        flash("You don't have permission to approve at department level.", "danger")
        return redirect(request.referrer)
    
    if level == "faculty" and current_user.role not in ["admin", "admission_officer", "faculty_officer"]:
        flash("You don't have permission to approve at faculty level.", "danger")
        return redirect(request.referrer)
    
    if level == "senate" and current_user.role != "admin":
        flash("You don't have permission to approve at senate level.", "danger")
        return redirect(request.referrer)
    
    try:
        # Get or create approval record
        approval = MeritListApproval.query.filter_by(
            programme_id=programme_id,
            session_id=active_session.id
        ).first()
        
        if not approval:
            approval = MeritListApproval(
                programme_id=programme_id,
                session_id=active_session.id
            )
            db.session.add(approval)
        
        # Update approval status on MeritListApproval
        if level == "department":
            approval.department_approved = True
            approval.department_approved_by = current_user.id
            approval.department_approved_at = datetime.utcnow()
            # Sync to individual records
            AdmissionRecord.query.filter_by(programme_id=programme_id, session_id=active_session.id, status='admitted').update({
                'dept_approved': True,
                'dept_approved_by': current_user.id,
                'dept_approved_at': datetime.utcnow()
            }, synchronize_session=False)
        elif level == "faculty":
            approval.faculty_approved = True
            approval.faculty_approved_by = current_user.id
            approval.faculty_approved_at = datetime.utcnow()
            # Sync to individual records
            AdmissionRecord.query.filter_by(programme_id=programme_id, session_id=active_session.id, status='admitted').update({
                'faculty_approved': True,
                'faculty_approved_by': current_user.id,
                'faculty_approved_at': datetime.utcnow()
            }, synchronize_session=False)
        elif level == "senate":
            approval.senate_approved = True
            approval.senate_approved_by = current_user.id
            approval.senate_approved_at = datetime.utcnow()
            approval.finalized = True
            # Sync to individual records
            AdmissionRecord.query.filter_by(programme_id=programme_id, session_id=active_session.id, status='admitted').update({
                'senate_approved': True,
                'senate_approved_by': current_user.id,
                'senate_approved_at': datetime.utcnow()
            }, synchronize_session=False)
        
        db.session.commit()
        
        flash(f"Merit list approved at {level} level.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error approving merit list: {e}", "danger")
    
    return redirect(url_for("admission.merit_list_detail", programme_id=programme_id))


# CAPS Integration Routes
@admission_bp.route("/caps/dashboard")
@login_required
def caps_dashboard():
    """CAPS integration dashboard"""
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "warning")
        return redirect(url_for("admin.dashboard"))
    
    # Get CAPS statistics
    caps_stats = MockCAPSService.get_caps_statistics()
    verification_stats = CAPSSyncService.get_verification_statistics()
    upload_stats = CAPSSyncService.get_upload_statistics()
    
    # Get pending verifications
    pending_verifications = CAPSSyncService.get_pending_verifications()
    
    # Get recent uploads
    recent_uploads = []
    if hasattr(MockCAPSService, '_uploads'):
        recent_uploads = list(MockCAPSService._uploads.values())[-5:]  # Last 5 uploads
        recent_uploads.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
    
    # Get all programmes for name lookup
    programmes = Programme.query.all()
    programme_map = {prog.code: prog.name for prog in programmes}
    
    return render_template(
        "admin/caps_dashboard.html",
        session=active_session,
        caps_stats=caps_stats,
        verification_stats=verification_stats,
        upload_stats=upload_stats,
        pending_verifications=pending_verifications,
        recent_uploads=recent_uploads,
        programme_map=programme_map
    )


@admission_bp.route("/caps/verify/<int:candidate_id>", methods=["POST"])
@login_required
def caps_verify_candidate(candidate_id):
    """Verify single candidate against CAPS"""
    candidate = Candidate.query.get_or_404(candidate_id)
    
    try:
        # Sync candidate to CAPS first
        MockCAPSService.seed_from_candidates([candidate])
        
        # Perform verification
        verification = MockCAPSService.verify_candidate(candidate.jamb_reg_number)
        
        # Update candidate record
        candidate.caps_verified = verification['verified']
        candidate.caps_verification_date = datetime.now() if verification['verified'] else None
        candidate.caps_verification_issues = verification.get('issues', [])
        candidate.caps_status = verification['status']
        candidate.data_verified_by = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'verification': verification,
            'message': f'Verification completed for {candidate.full_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Verification failed: {str(e)}'
        }), 500


@admission_bp.route("/caps/bulk-verify", methods=["POST"])
@login_required
def caps_bulk_verify():
    """Bulk CAPS verification — runs synchronously."""
    data = request.get_json()
    candidate_ids = data.get('candidate_ids', [])

    if not candidate_ids:
        return jsonify({'success': False, 'message': 'No candidate IDs provided'}), 400

    try:
        candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
        MockCAPSService.seed_from_candidates(candidates)

        verified_count = 0
        failed_count = 0
        for candidate in candidates:
            result = MockCAPSService.verify_candidate(candidate.jamb_reg_number)
            candidate.caps_verified = result['verified']
            candidate.caps_verification_date = datetime.utcnow() if result['verified'] else None
            candidate.caps_verification_issues = result.get('issues', [])
            candidate.caps_status = result['status']
            if result['verified']:
                verified_count += 1
            else:
                failed_count += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'sync': True,
            'verified': verified_count,
            'failed': failed_count,
            'message': f'Verification complete: {verified_count} verified, {failed_count} failed.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Verification failed: {str(e)}'}), 500


@admission_bp.route("/caps/upload/<int:programme_id>", methods=["POST"])
@login_required
def caps_upload_admission_list(programme_id):
    """Dispatch CAPS admission list upload as a background task."""
    if current_user.role not in ["admin", "admission_officer"]:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    Programme.query.get_or_404(programme_id)
    active_session = get_active_session()
    if not active_session:
        return jsonify({'success': False, 'message': 'No active academic session found'}), 400

    try:
        from app.tasks import upload_admission_list_task
        task = upload_admission_list_task.delay(programme_id, active_session.id, current_user.id)
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': f'Upload queued. Poll /admission/caps/task-status/{task.id} for progress.',
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to queue upload: {str(e)}'}), 500


@admission_bp.route("/caps/status/<upload_id>")
@login_required
def caps_check_upload_status(upload_id):
    """Check CAPS upload status (legacy – kept for backwards compat)"""
    try:
        status = CAPSSyncService.check_upload_status(upload_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to check status: {str(e)}'}), 500


@admission_bp.route("/caps/task-status/<task_id>")
@login_required
def caps_task_status(task_id):
    """
    Poll this endpoint to check the progress of any background Celery task.
    Returns JSON with state, progress, and result.
    """
    try:
        from celery.result import AsyncResult
        task = AsyncResult(task_id)

        if task.state == "PENDING":
            response = {"state": "PENDING", "status": "Task queued, waiting for worker...", "current": 0, "total": 1}
        elif task.state == "PROGRESS":
            meta = task.info or {}
            response = {
                "state": "PROGRESS",
                "current": meta.get("current", 0),
                "total": meta.get("total", 1),
                "status": meta.get("status", ""),
                "verified": meta.get("verified", 0),
                "failed": meta.get("failed", 0),
            }
        elif task.state == "SUCCESS":
            response = {"state": "SUCCESS", "result": task.result}
        elif task.state == "FAILURE":
            response = {"state": "FAILURE", "status": str(task.info)}
        else:
            response = {"state": task.state, "status": str(task.info)}

        return jsonify(response)

    except Exception as e:
        return jsonify({"state": "ERROR", "status": str(e)}), 500


@admission_bp.route("/merit-list/<int:programme_id>/generate-async", methods=["POST"])
@login_required
def generate_merit_list_async(programme_id):
    """Trigger merit list generation for a programme — runs synchronously."""
    if current_user.role not in ["admin", "admission_officer"]:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    active_session = get_active_session()
    if not active_session:
        return jsonify({'success': False, 'message': 'No active session'}), 400

    try:
        generator = MeritListGenerator(programme_id, active_session.id)
        result = generator.generate_full_list(persist=True)
        db.session.commit()
        stats = generator.get_statistics(result)
        return jsonify({
            'success': True,
            'sync': True,
            'total_admitted': stats.get('filled', 0),
            'message': f'Merit list generated: {stats.get("filled", 0)} admitted.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Generation failed: {str(e)}'}), 500


@admission_bp.route("/caps/acceptance/<string:jamb_reg>", methods=["POST"])
@login_required
def caps_simulate_acceptance(jamb_reg):
    """Simulate candidate accepting admission offer"""
    try:
        acceptance = CAPSSyncService.simulate_candidate_acceptance(jamb_reg)
        return jsonify(acceptance)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to simulate acceptance: {str(e)}'}), 500


@admission_bp.route("/caps/verification-details/<int:candidate_id>")
@login_required
def caps_verification_details(candidate_id):
    """View CAPS verification details for a candidate"""
    candidate = Candidate.query.get_or_404(candidate_id)

    comparison_data = CAPSSyncService.get_candidate_caps_comparison(candidate_id)
    comparison = comparison_data.get('comparison', {})
    overall_match = comparison_data.get('overall_match', False)

    return render_template(
        "admin/caps_verification.html",
        candidate=candidate,
        comparison=comparison,
        overall_match=overall_match,
    )


@admission_bp.route("/caps/override/<int:candidate_id>", methods=["POST"])
@login_required
def caps_override(candidate_id):
    """Override CAPS verification (Admin only)"""
    if current_user.role != 'admin':
        flash('Unauthorized to override CAPS verification.', 'danger')
        return redirect(url_for('admission.caps_dashboard'))

    candidate = Candidate.query.get_or_404(candidate_id)
    reason = request.form.get('reason')
    confirm = request.form.get('confirm')

    if reason and confirm:
        candidate.caps_verified = True
        candidate.caps_verification_date = datetime.now()
        candidate.caps_status = "verified_override"
        db.session.commit()
        flash('CAPS verification successfully overridden.', 'success')
    else:
        flash('Reason and confirmation are required to override.', 'warning')

    return redirect(url_for('admission.caps_verification_details', candidate_id=candidate.id))


@admission_bp.route("/screening/screened")
@login_required
def screening_screened():
    """List of all successfully screened/recommended candidates"""
    page = request.args.get("page", type=int, default=1)
    programme_id = request.args.get("programme_id", type=int)
    
    active_session = get_active_session()
    if not active_session:
        flash("No active session found.", "danger")
        return redirect(url_for("admin.dashboard"))
        
    query = Candidate.query.options(
        joinedload(Candidate.first_choice_programme).joinedload(Programme.university),
        joinedload(Candidate.session)
    ).filter(
        Candidate.session_id == active_session.id,
        Candidate.status.in_(["recommended", "admitted", "finalized", "accepted", "waiting_list"])
    )
    
    # Restrict to faculty if user is faculty officer
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        query = query.join(Programme, Candidate.first_choice_programme_id == Programme.id)\
                     .filter(Programme.faculty_id == current_user.faculty_id)
                     
    if programme_id:
        query = query.filter(Candidate.first_choice_programme_id == programme_id)
        
    query = query.order_by(Candidate.utme_score.desc())
    pagination = query.paginate(page=page, per_page=50, error_out=False)
    
    # Get programmes for filter dropdown
    programmes_query = Programme.query.order_by(Programme.name.asc())
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        programmes_query = programmes_query.filter_by(faculty_id=current_user.faculty_id)
    programmes = programmes_query.all()
    
    return render_template(
        "admin/screening_screened.html",
        candidates=pagination.items,
        pagination=pagination,
        programmes=programmes,
        selected_programme_id=programme_id,
        session=active_session
    )


@admission_bp.route("/screening/rejected")
@login_required
def screening_rejected():
    """List of all candidates who failed screening"""
    page = request.args.get("page", type=int, default=1)
    programme_id = request.args.get("programme_id", type=int)
    
    active_session = get_active_session()
    if not active_session:
        flash("No active session found.", "danger")
        return redirect(url_for("admin.dashboard"))
        
    query = Candidate.query.options(
        joinedload(Candidate.first_choice_programme).joinedload(Programme.university),
        joinedload(Candidate.session),
        joinedload(Candidate.admission_records)
    ).filter(
        Candidate.session_id == active_session.id,
        Candidate.status == "rejected"
    )
    
    # Restrict to faculty if user is faculty officer
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        query = query.join(Programme, Candidate.first_choice_programme_id == Programme.id)\
                     .filter(Programme.faculty_id == current_user.faculty_id)
                     
    if programme_id:
        query = query.filter(Candidate.first_choice_programme_id == programme_id)
        
    query = query.order_by(Candidate.utme_score.desc())
    pagination = query.paginate(page=page, per_page=50, error_out=False)
    
    # Get programmes for filter dropdown
    programmes_query = Programme.query.order_by(Programme.name.asc())
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        programmes_query = programmes_query.filter_by(faculty_id=current_user.faculty_id)
    programmes = programmes_query.all()
    
    return render_template(
        "admin/screening_rejected.html",
        candidates=pagination.items,
        pagination=pagination,
        programmes=programmes,
        selected_programme_id=programme_id,
        session=active_session
    )
