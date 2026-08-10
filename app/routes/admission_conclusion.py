import os
import shutil
import pandas as pd
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AcademicSession, Candidate, AdmissionRecord, Programme
from app.utils.helpers import get_active_session, log_audit

conclusion_bp = Blueprint("conclusion", __name__, url_prefix="/admin/admission-conclusion")

@conclusion_bp.before_request
@login_required
def require_admin():
    if current_user.role not in ["admin", "super_admin"]:
        flash("Unauthorized access. Admin privileges required.", "danger")
        return redirect(url_for("admin.dashboard"))


@conclusion_bp.route("", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "create_session":
            name = request.form.get("name", "").strip()
            start_date_str = request.form.get("start_date", "").strip()
            end_date_str = request.form.get("end_date", "").strip()
            make_active = request.form.get("make_active") == "true"
            
            if not name:
                flash("Academic session name is required.", "danger")
                return redirect(url_for("conclusion.index"))
                
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else datetime.utcnow().date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else datetime.utcnow().date()
                
                # Check for duplicate session name
                dup = AcademicSession.query.filter_by(name=name).first()
                if dup:
                    flash(f"Session with name '{name}' already exists.", "danger")
                    return redirect(url_for("conclusion.index"))
                
                # Create session
                session = AcademicSession(
                    name=name,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=make_active
                )
                db.session.add(session)
                db.session.flush()
                
                if make_active:
                    # Deactivate other sessions
                    AcademicSession.query.filter(AcademicSession.id != session.id).update({"is_active": False})
                    
                db.session.commit()
                log_audit("create_session", "AcademicSession", session.id, {"name": name, "make_active": make_active})
                flash(f"Academic session '{name}' created successfully.", "success")
                
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to create academic session: {str(e)}", "danger")
                
            return redirect(url_for("conclusion.index"))

    sessions = AcademicSession.query.order_by(AcademicSession.start_date.desc()).all()
    active_session = get_active_session()
    
    # Calculate stats for the active session
    stats = {}
    if active_session:
        total = Candidate.query.filter_by(session_id=active_session.id).count()
        admitted = AdmissionRecord.query.filter(
            AdmissionRecord.session_id == active_session.id,
            AdmissionRecord.status.in_(["admitted", "finalized", "accepted"])
        ).count()
        rejected = AdmissionRecord.query.filter_by(
            session_id=active_session.id,
            status="rejected"
        ).count()
        pending = max(total - admitted - rejected, 0)
        stats = {
            "total": total,
            "admitted": admitted,
            "rejected": rejected,
            "pending": pending
        }
        
    return render_template(
        "admin/admission_conclusion.html",
        sessions=sessions,
        active_session=active_session,
        stats=stats
    )


@conclusion_bp.route("/conclude", methods=["POST"])
def conclude():
    """Conclude the active session, deactivate it, and perform cleanup."""
    active_session = get_active_session()
    if not active_session:
        flash("No active session found to conclude.", "warning")
        return redirect(url_for("conclusion.index"))
        
    try:
        # Deactivate session
        active_session.is_active = False
        
        # Clean up temporary uploaded files
        temp_dir = os.path.abspath(os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp'))
        cleanup_count = 0
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        cleanup_count += 1
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        cleanup_count += 1
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
                    
        db.session.commit()
        log_audit("conclude_session", "AcademicSession", active_session.id, {
            "name": active_session.name,
            "cleaned_temp_files": cleanup_count
        })
        flash(f"Session '{active_session.name}' has been successfully concluded and archived. Temporary upload folder cleared.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to conclude session: {str(e)}", "danger")
        
    return redirect(url_for("conclusion.index"))


@conclusion_bp.route("/activate/<int:session_id>", methods=["POST"])
def activate(session_id):
    """Manually activate a session"""
    session = AcademicSession.query.get_or_404(session_id)
    try:
        # Deactivate all sessions
        AcademicSession.query.update({"is_active": False})
        session.is_active = True
        db.session.commit()
        
        log_audit("activate_session", "AcademicSession", session.id, {"name": session.name})
        flash(f"Academic session '{session.name}' is now active.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to activate session: {str(e)}", "danger")
    return redirect(url_for("conclusion.index"))


@conclusion_bp.route("/export/admitted")
def export_admitted():
    """Export report of all admitted candidates in active session."""
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "danger")
        return redirect(url_for("conclusion.index"))
        
    records = AdmissionRecord.query.options(
        db.joinedload(AdmissionRecord.candidate),
        db.joinedload(AdmissionRecord.programme)
    ).filter(
        AdmissionRecord.session_id == active_session.id,
        AdmissionRecord.status.in_(["admitted", "finalized", "accepted"])
    ).all()
    
    rows = []
    for r in records:
        rows.append({
            "JAMB Reg Number": r.candidate.jamb_reg_number if r.candidate else "",
            "Full Name": r.candidate.full_name if r.candidate else "",
            "State of Origin": r.candidate.state_of_origin if r.candidate else "",
            "UTME Score": r.candidate.utme_score if r.candidate else "",
            "Post-UTME Score": r.candidate.post_utme_score if r.candidate and r.candidate.post_utme_score else "",
            "Aggregate Score": r.aggregate_score,
            "Admitted Programme Code": r.programme.code if r.programme else "",
            "Admitted Programme Name": r.programme.name if r.programme else "",
            "Quota Category": r.quota_category or "Merit"
        })
        
    df = pd.DataFrame(rows)
    stream = BytesIO()
    df.to_excel(stream, index=False)
    stream.seek(0)
    
    log_audit("export_admitted_report", "AcademicSession", active_session.id, {"records_count": len(records)})
    
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"admitted_report_{active_session.name.replace('/', '-')}.xlsx"
    )


@conclusion_bp.route("/export/rejected")
def export_rejected():
    """Export report of all rejected candidates in active session for manual check."""
    active_session = get_active_session()
    if not active_session:
        flash("No active academic session found.", "danger")
        return redirect(url_for("conclusion.index"))
        
    records = AdmissionRecord.query.options(
        db.joinedload(AdmissionRecord.candidate),
        db.joinedload(AdmissionRecord.programme)
    ).filter(
        AdmissionRecord.session_id == active_session.id,
        AdmissionRecord.status == "rejected"
    ).all()
    
    rejection_reasons_map = {
        'utme_cutoff': 'UTME Score below cutoff',
        'subject_combination': 'Invalid UTME Subject Combination',
        'olevel_credits': 'Deficient O\'Level Credits (less than 5 credits in core subjects)',
        'olevel_sittings': 'Too many O\'Level sittings (exceeds limit)',
    }
    
    rows = []
    for r in records:
        reason_raw = r.rejection_reason or ""
        reason_human = rejection_reasons_map.get(reason_raw, reason_raw or "Screening rules violation")
        
        # Construct list of passed steps vs failed steps
        failed_steps = []
        if not r.utme_cutoff_passed: failed_steps.append("UTME Cutoff")
        if not r.subject_combination_passed: failed_steps.append("Subject Combination")
        if not r.olevel_credits_passed: failed_steps.append("O'Level Credits")
        if not r.olevel_sittings_passed: failed_steps.append("O'Level Sittings")
        
        rows.append({
            "JAMB Reg Number": r.candidate.jamb_reg_number if r.candidate else "",
            "Full Name": r.candidate.full_name if r.candidate else "",
            "State of Origin": r.candidate.state_of_origin if r.candidate else "",
            "UTME Score": r.candidate.utme_score if r.candidate else "",
            "Post-UTME Score": r.candidate.post_utme_score if r.candidate and r.candidate.post_utme_score else "",
            "Intended Programme Choice": r.programme.name if r.programme else "",
            "Primary Failure Cause": reason_human,
            "All Failed Requirements": ", ".join(failed_steps) if failed_steps else "None"
        })
        
    df = pd.DataFrame(rows)
    stream = BytesIO()
    df.to_excel(stream, index=False)
    stream.seek(0)
    
    log_audit("export_rejected_report", "AcademicSession", active_session.id, {"records_count": len(records)})
    
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"rejected_manual_check_report_{active_session.name.replace('/', '-')}.xlsx"
    )
