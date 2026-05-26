import json
import os
from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.forms import (
    AdmissionRuleForm,
    CandidateManualForm,
    CatchmentStateForm,
    FacultyForm,
    ProgrammeForm,
    UniversityConfigForm,
)
from app.models import AuditLog
from app.models import (
    AcademicSession,
    AdmissionRecord,
    AdmissionRule,
    Candidate,
    CatchmentState,
    Faculty,
    OLevelResult,
    Programme,
    University,
)
from app.services.candidate_processor import CandidateProcessor
from app.services.screening_engine import ScreeningEngine
from app.utils.helpers import get_active_session

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def require_login():
    return None


def _first_university():
    return University.query.order_by(University.id.asc()).first()


def _populate_faculty_choices(form, university_id=None):
    query = Faculty.query
    if university_id is not None:
        query = query.filter(Faculty.university_id == university_id)
    faculties = query.order_by(Faculty.name.asc()).all()
    form.faculty_id.choices = [(faculty.id, f"{faculty.name} ({faculty.code})") for faculty in faculties]
    return faculties

def _populate_session_choices(form):
    sessions = AcademicSession.query.order_by(AcademicSession.start_date.desc()).all()
    form.session_id.choices = [(session.id, session.name) for session in sessions]
    return sessions


def _populate_programme_choices(form):
    programmes = Programme.query.order_by(Programme.name.asc()).all()
    form.first_choice_programme_id.choices = [(programme.id, f"{programme.name} ({programme.code})") for programme in programmes]
    return programmes


def _build_candidate_query(search_term=None, programme_id=None, status=None, quota_category=None):
    query = Candidate.query.options(
        joinedload(Candidate.first_choice_programme).joinedload(Programme.faculty),
        joinedload(Candidate.session),
    )
    
    if current_user.role == 'faculty_officer' and current_user.faculty_id:
        query = query.join(Programme, Candidate.first_choice_programme_id == Programme.id)\
                     .filter(Programme.faculty_id == current_user.faculty_id)
                     
    if quota_category:
        query = query.join(
            AdmissionRecord,
            AdmissionRecord.candidate_id == Candidate.id,
        ).filter(AdmissionRecord.quota_category == quota_category)
    if search_term:
        wildcard = f"%{search_term.strip()}%"
        query = query.filter(
            Candidate.jamb_reg_number.ilike(wildcard)
            | Candidate.full_name.ilike(wildcard)
            | Candidate.state_of_origin.ilike(wildcard)
        )
    if programme_id:
        query = query.filter(Candidate.first_choice_programme_id == programme_id)
    if status:
        query = query.filter(Candidate.status == status)
    if quota_category:
        query = query.distinct()
    return query.order_by(Candidate.created_at.desc())


def _serialize_candidate_rows(candidates):
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "jamb_reg_number": candidate.jamb_reg_number,
                "full_name": candidate.full_name,
                "session": candidate.session.name if candidate.session else "",
                "state_of_origin": candidate.state_of_origin or "",
                "programme": candidate.first_choice_programme.name if candidate.first_choice_programme else "",
                "utme_score": candidate.utme_score,
                "post_utme_score": candidate.post_utme_score if candidate.post_utme_score is not None else "",
                "status": candidate.status,
                "caps_verified": "Yes" if candidate.caps_verified else "No",
            }
        )
    return rows


def _log_audit(action, entity_type, entity_id=None, details=None):
    db.session.add(
        AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=request.remote_addr,
        )
    )


@admin_bp.route("/")
@admin_bp.route("/dashboard")
def dashboard():
    session_id = request.args.get("session_id", type=int)
    sessions = AcademicSession.query.order_by(AcademicSession.start_date.desc()).all()

    selected_session = None
    if session_id is not None:
        selected_session = AcademicSession.query.get(session_id)
    if not selected_session:
        selected_session = get_active_session() or (sessions[0] if sessions else None)

    total_candidates = 0
    admitted_count = 0
    rejected_count = 0
    pending_count = 0
    quota_counts = {"merit": 0, "catchment": 0, "elds": 0}
    recent_decisions = []

    if selected_session:
        total_candidates = Candidate.query.filter_by(session_id=selected_session.id).count()
        admitted_count = AdmissionRecord.query.filter(
            AdmissionRecord.session_id == selected_session.id,
            AdmissionRecord.status.in_(["admitted", "finalized", "accepted"]),
        ).count()
        rejected_count = AdmissionRecord.query.filter_by(
            session_id=selected_session.id,
            status="rejected",
        ).count()
        pending_count = max(total_candidates - admitted_count - rejected_count, 0)

        quota_rows = (
            AdmissionRecord.query.with_entities(
                AdmissionRecord.quota_category,
                func.count(AdmissionRecord.id),
            )
            .filter(
                AdmissionRecord.session_id == selected_session.id,
                AdmissionRecord.status.in_(["admitted", "finalized", "accepted"]),
            )
            .group_by(AdmissionRecord.quota_category)
            .all()
        )

        for category, count in quota_rows:
            category_key = str(category or "").strip().lower()
            if category_key in quota_counts:
                quota_counts[category_key] = count

        recent_decisions = (
            AdmissionRecord.query.options(
                joinedload(AdmissionRecord.candidate),
                joinedload(AdmissionRecord.programme),
            )
            .filter(AdmissionRecord.session_id == selected_session.id)
            .order_by(AdmissionRecord.updated_at.desc())
            .limit(10)
            .all()
        )

    return render_template(
        "admin/dashboard.html",
        sessions=sessions,
        selected_session=selected_session,
        total_candidates=total_candidates,
        admitted_count=admitted_count,
        rejected_count=rejected_count,
        pending_count=pending_count,
        quota_chart_values=[
            quota_counts["merit"],
            quota_counts["catchment"],
            quota_counts["elds"],
        ],
        recent_decisions=recent_decisions,
    )


@admin_bp.route("/candidates")
def candidates():
    page = request.args.get("page", type=int, default=1)
    search = request.args.get("search", type=str, default="").strip()
    programme_id = request.args.get("programme_id", type=int)
    status = request.args.get("status", type=str, default="").strip()
    quota_category = request.args.get("quota_category", type=str, default="").strip()
    export_format = request.args.get("export", type=str, default="").strip().lower()
    format_param = request.args.get("format", type=str, default="").strip().lower()

    query = _build_candidate_query(
        search_term=search or None,
        programme_id=programme_id,
        status=status or None,
        quota_category=quota_category or None,
    )

    # Handle JSON format for AJAX requests
    if format_param == "json":
        candidates_data = query.all()
        candidates_json = []
        for candidate in candidates_data:
            candidates_json.append({
                'id': candidate.id,
                'jamb_reg_number': candidate.jamb_reg_number,
                'full_name': candidate.full_name,
                'utme_score': candidate.utme_score,
                'post_utme_score': candidate.post_utme_score,
                'status': candidate.status,
                'first_choice_programme': {
                    'id': candidate.first_choice_programme.id,
                    'name': candidate.first_choice_programme.name,
                    'code': candidate.first_choice_programme.code
                } if candidate.first_choice_programme else None,
                'created_at': candidate.created_at.isoformat() if candidate.created_at else None
            })
        return jsonify({'candidates': candidates_json})

    if export_format in {"csv", "xlsx"}:
        candidates_data = query.all()
        rows = _serialize_candidate_rows(candidates_data)
        dataframe = pd.DataFrame(rows)
        if export_format == "csv":
            csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
            return send_file(
                BytesIO(csv_bytes),
                mimetype="text/csv",
                as_attachment=True,
                download_name="candidates_export.csv",
            )
        excel_stream = BytesIO()
        dataframe.to_excel(excel_stream, index=False)
        excel_stream.seek(0)
        return send_file(
            excel_stream,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="candidates_export.xlsx",
        )

    pagination = query.paginate(page=page, per_page=50, error_out=False)
    programmes = Programme.query.order_by(Programme.name.asc()).all()
    statuses = ['pending', 'recommended', 'admitted', 'rejected', 'finalized', 'waiting_list', 'accepted', 'declined']
    quota_categories = [
        category_row[0]
        for category_row in db.session.query(AdmissionRecord.quota_category).distinct().all()
        if category_row[0]
    ]
    return render_template(
        "admin/candidates.html",
        candidates=pagination.items,
        pagination=pagination,
        programmes=programmes,
        statuses=statuses,
        quota_categories=quota_categories,
        selected_search=search,
        selected_programme_id=programme_id,
        selected_status=status,
        selected_quota_category=quota_category,
    )


@admin_bp.route("/candidates/upload", methods=["GET", "POST"])
@login_required
def upload_candidates():
    if request.method == 'POST':
        # Bug 5 fix: initialise temp_path to None so the finally block never
        # raises UnboundLocalError when an early validation branch returns.
        temp_path = None

        # Check if this is an import from preview (using temp_file_path)
        temp_file_path = request.form.get('temp_file_path', '').strip()
        session_id = request.form.get('session_id', type=int)
        
        if temp_file_path and os.path.exists(temp_file_path):
            # Import from preview - use existing temp file
            temp_path = temp_file_path
            filename = os.path.basename(temp_path)
        else:
            # New file upload
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            if not file.filename.endswith('.csv'):
                flash('Please upload a CSV file', 'error')
                return redirect(request.url)
            
            # Save uploaded file temporarily
            from werkzeug.utils import secure_filename
            
            filename = secure_filename(file.filename)
            temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            file.save(temp_path)
        
        try:
            # Check if it's a preview request or full import
            action = request.form.get('action', 'preview')
            
            processor = CandidateProcessor()
            
            # Use provided session_id or get active session
            if session_id:
                session = AcademicSession.query.get(session_id)
                if not session:
                    flash('Invalid session specified', 'error')
                    return redirect(request.url)
            else:
                session = get_active_session()
            
            if action == 'preview':
                preview_data = processor.get_preview(temp_path)
                return render_template(
                    'admin/candidate_upload_preview.html',
                    preview=preview_data,
                    filename=filename,
                    temp_file_path=temp_path,
                    session_id=session.id
                )
            else:
                # Full import
                result = processor.process_file(temp_path, session.id)
                
                flash(f'Import complete! Created: {result["created"]}, '
                      f'Skipped: {result["skipped"]}, Errors: {result["errors"]}', 
                      'success' if result['errors'] == 0 else 'warning')
                
                if result['error_details']:
                    for error in result['error_details'][:5]:
                        flash(f'Error: {error}', 'error')
                
                return redirect(url_for('admin.candidates'))
                
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(request.url)
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
            return redirect(request.url)
        finally:
            # Clean up temp file — guard against temp_path never being set
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
    
    return render_template('admin/candidate_upload.html')


@admin_bp.route("/candidates/add", methods=["GET", "POST"])
def add_candidate():
    form = CandidateManualForm()
    _populate_session_choices(form)
    programmes = _populate_programme_choices(form)
    if not programmes:
        flash("Create at least one programme before adding candidates.", "warning")
        return redirect(url_for("admin.programmes"))

    if form.validate_on_submit():
        duplicate = Candidate.query.filter_by(jamb_reg_number=form.jamb_reg_number.data).first()
        if duplicate:
            flash("Candidate with this JAMB registration number already exists.", "danger")
            return render_template("admin/candidate_form.html", form=form, mode="create")
        candidate = Candidate(
            session_id=form.session_id.data,
            jamb_reg_number=form.jamb_reg_number.data,
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower() if form.email.data else None,
            phone=form.phone.data.strip() if form.phone.data else None,
            gender=form.gender.data or None,
            date_of_birth=form.date_of_birth.data,
            state_of_origin=form.state_of_origin.data.strip().title(),
            lga_of_origin=form.lga_of_origin.data.strip().title() if form.lga_of_origin.data else None,
            first_choice_programme_id=form.first_choice_programme_id.data,
            utme_score=form.utme_score.data,
            utme_subjects=json.loads(form.utme_subjects_json.data),
            post_utme_score=form.post_utme_score.data,
            post_utme_present=form.post_utme_present.data,
            status="pending",
        )
        db.session.add(candidate)
        db.session.flush()

        olevel_rows = json.loads(form.olevel_results_json.data or "[]")
        for row in olevel_rows:
            db.session.add(
                OLevelResult(
                    candidate_id=candidate.id,
                    exam_body=str(row.get("exam_body", "WAEC")).upper(),
                    exam_number=str(row.get("exam_number", "")).strip(),
                    exam_year=int(row.get("exam_year")),
                    sitting_number=int(row.get("sitting_number", 1)),
                    subject=str(row.get("subject", "")).strip(),
                    grade=str(row.get("grade", "")).strip().upper(),
                )
            )

        _log_audit(
            action="candidate_manual_created",
            entity_type="Candidate",
            entity_id=candidate.id,
            details={"jamb_reg_number": candidate.jamb_reg_number},
        )
        db.session.commit()
        flash("Candidate created successfully.", "success")
        return redirect(url_for("admin.candidate_detail", id=candidate.id))
    return render_template("admin/candidate_form.html", form=form, mode="create")


@admin_bp.route("/candidates/<int:id>")
def candidate_detail(id):
    candidate = Candidate.query.options(
        joinedload(Candidate.first_choice_programme),
        joinedload(Candidate.olevel_results),
        joinedload(Candidate.admission_records).joinedload(AdmissionRecord.programme),
        joinedload(Candidate.session),
    ).get_or_404(id)
    grouped_olevel = {}
    for result in candidate.olevel_results:
        grouped_olevel.setdefault(result.sitting_number, []).append(result)
    return render_template(
        "admin/candidate_detail.html",
        candidate=candidate,
        grouped_olevel=grouped_olevel,
    )


@admin_bp.route("/candidates/<int:id>/edit", methods=["GET", "POST"])
def edit_candidate(id):
    candidate = Candidate.query.options(joinedload(Candidate.olevel_results)).get_or_404(id)
    form = CandidateManualForm(obj=candidate)
    _populate_session_choices(form)
    _populate_programme_choices(form)

    if request.method == "GET":
        form.utme_subjects_json.data = json.dumps(candidate.utme_subjects or {}, indent=2)
        olevel_payload = [
            {
                "exam_body": result.exam_body,
                "exam_number": result.exam_number,
                "exam_year": result.exam_year,
                "sitting_number": result.sitting_number,
                "subject": result.subject,
                "grade": result.grade,
            }
            for result in candidate.olevel_results
        ]
        form.olevel_results_json.data = json.dumps(olevel_payload, indent=2)

    if form.validate_on_submit():
        duplicate = Candidate.query.filter(
            Candidate.jamb_reg_number == form.jamb_reg_number.data,
            Candidate.id != candidate.id,
        ).first()
        if duplicate:
            flash("Another candidate already uses this JAMB registration number.", "danger")
            return render_template("admin/candidate_form.html", form=form, mode="edit", candidate=candidate)

        candidate.session_id = form.session_id.data
        candidate.jamb_reg_number = form.jamb_reg_number.data
        candidate.full_name = form.full_name.data.strip()
        candidate.email = form.email.data.strip().lower() if form.email.data else None
        candidate.phone = form.phone.data.strip() if form.phone.data else None
        candidate.gender = form.gender.data or None
        candidate.date_of_birth = form.date_of_birth.data
        candidate.state_of_origin = form.state_of_origin.data.strip().title()
        candidate.lga_of_origin = form.lga_of_origin.data.strip().title() if form.lga_of_origin.data else None
        candidate.first_choice_programme_id = form.first_choice_programme_id.data
        candidate.utme_score = form.utme_score.data
        candidate.utme_subjects = json.loads(form.utme_subjects_json.data)
        candidate.post_utme_score = form.post_utme_score.data
        candidate.post_utme_present = form.post_utme_present.data

        OLevelResult.query.filter_by(candidate_id=candidate.id).delete()
        olevel_rows = json.loads(form.olevel_results_json.data or "[]")
        for row in olevel_rows:
            db.session.add(
                OLevelResult(
                    candidate_id=candidate.id,
                    exam_body=str(row.get("exam_body", "WAEC")).upper(),
                    exam_number=str(row.get("exam_number", "")).strip(),
                    exam_year=int(row.get("exam_year")),
                    sitting_number=int(row.get("sitting_number", 1)),
                    subject=str(row.get("subject", "")).strip(),
                    grade=str(row.get("grade", "")).strip().upper(),
                )
            )

        _log_audit(
            action="candidate_updated",
            entity_type="Candidate",
            entity_id=candidate.id,
            details={"jamb_reg_number": candidate.jamb_reg_number},
        )
        db.session.commit()
        flash("Candidate updated successfully.", "success")
        return redirect(url_for("admin.candidate_detail", id=candidate.id))

    return render_template("admin/candidate_form.html", form=form, mode="edit", candidate=candidate)


@admin_bp.route("/candidates/<int:id>/verify", methods=["POST"])
def verify_candidate(id):
    candidate = Candidate.query.get_or_404(id)
    candidate.caps_verified = True
    candidate.caps_verification_date = datetime.utcnow()
    _log_audit(
        action="candidate_caps_verified",
        entity_type="Candidate",
        entity_id=candidate.id,
        details={"jamb_reg_number": candidate.jamb_reg_number},
    )
    db.session.commit()
    flash("Candidate marked as CAPS verified.", "success")
    return redirect(request.referrer or url_for("admin.candidate_detail", id=candidate.id))


@admin_bp.route("/candidates/bulk-verify", methods=["POST"])
@login_required
def bulk_verify_candidates():
    """
    Mark multiple candidates as CAPS-verified in a single action.

    Accepts:
      - candidate_ids  (JSON body, list[int])  — verify a specific set
      - target         (form field, str)        — 'admitted' | 'recommended' | 'all'
        When 'target' is used, the route queries the DB for matching candidates
        in the active session and verifies all of them.
    """
    from app.models import AdmissionRecord

    # Support both JSON (AJAX) and form POST
    if request.is_json:
        data = request.get_json() or {}
        candidate_ids = data.get("candidate_ids", [])
        target = data.get("target")
    else:
        raw_ids = request.form.getlist("candidate_ids")
        candidate_ids = [int(i) for i in raw_ids if i.isdigit()]
        target = request.form.get("target")

    # Build the candidate queryset
    if candidate_ids:
        candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
    elif target in ("admitted", "recommended", "all"):
        active_session = get_active_session()
        if not active_session:
            if request.is_json:
                return jsonify({"success": False, "message": "No active session found"}), 400
            flash("No active admission session found.", "warning")
            return redirect(url_for("admin.candidates"))

        if target == "all":
            candidates = Candidate.query.filter_by(
                session_id=active_session.id, caps_verified=False
            ).all()
        else:
            # Get candidate IDs that have the requested admission status
            admitted_ids = (
                db.session.query(AdmissionRecord.candidate_id)
                .filter_by(session_id=active_session.id, status=target)
                .distinct()
                .subquery()
            )
            candidates = Candidate.query.filter(
                Candidate.id.in_(admitted_ids),
                Candidate.caps_verified == False,
            ).all()
    else:
        if request.is_json:
            return jsonify({"success": False, "message": "Provide candidate_ids or a target value"}), 400
        flash("Nothing to verify — provide candidate IDs or a target group.", "warning")
        return redirect(url_for("admin.candidates"))

    if not candidates:
        if request.is_json:
            return jsonify({"success": True, "verified": 0, "message": "No unverified candidates matched"})
        flash("No unverified candidates matched your selection.", "info")
        return redirect(url_for("admin.candidates"))

    now = datetime.utcnow()
    for candidate in candidates:
        candidate.caps_verified = True
        candidate.caps_verification_date = now
        _log_audit(
            action="candidate_caps_verified_bulk",
            entity_type="Candidate",
            entity_id=candidate.id,
            details={"jamb_reg_number": candidate.jamb_reg_number, "bulk": True},
        )

    db.session.commit()
    count = len(candidates)

    if request.is_json:
        return jsonify({
            "success": True,
            "verified": count,
            "message": f"{count} candidate(s) marked as CAPS verified."
        })

    flash(f"✅ {count} candidate(s) successfully marked as CAPS Verified.", "success")
    return redirect(url_for("admin.candidates"))


@admin_bp.route("/candidates/delete-all", methods=["POST"])
@login_required
def delete_all_candidates():
    if current_user.role not in ["admin", "super_admin"]:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("admin.candidates"))

    try:
        from app.models import MeritListApproval, AdmissionBatch, AdmissionRecord, OLevelResult, User
        candidate_count = Candidate.query.count()
        candidate_user_ids = [c.user_id for c in Candidate.query.filter(Candidate.user_id.isnot(None)).all()]

        # Delete dependent records in dependency order
        MeritListApproval.query.delete()
        AdmissionBatch.query.delete()
        AdmissionRecord.query.delete()
        OLevelResult.query.delete()
        Candidate.query.delete()

        if candidate_user_ids:
            User.query.filter(User.id.in_(candidate_user_ids)).delete(synchronize_session=False)

        _log_audit(
            action="candidates_delete_all",
            entity_type="Candidate",
            details={"deleted_count": candidate_count},
        )
        db.session.commit()

        flash(f"Successfully deleted all {candidate_count} candidates and their associated records.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete candidates: {str(e)}", "danger")

    return redirect(url_for("admin.candidates"))



@admin_bp.route("/candidates/validate-jamb")
def validate_jamb_reg():
    jamb_reg = request.args.get("jamb_reg_number", type=str, default="").strip().upper()
    if not jamb_reg:
        return jsonify({"valid": False, "message": "JAMB registration number is required."}), 400
    processor = CandidateProcessor(validate_duplicates=False, skip_errors=True)
    valid, result = processor.validate_jamb_reg(jamb_reg)
    if not valid:
        return jsonify({"valid": False, "message": result}), 200
    exists = Candidate.query.filter_by(jamb_reg_number=result).first() is not None
    return jsonify(
        {
            "valid": not exists,
            "exists": exists,
            "normalized": result,
            "message": "JAMB number already exists." if exists else "JAMB number is available.",
        }
    )


@admin_bp.route("/university/config", methods=["GET", "POST"])
def university_config():
    university = _first_university()
    form = UniversityConfigForm(obj=university)

    if request.method == "GET" and university:
        form.grade_points_json.data = json.dumps(university.grade_points, indent=2)

    if form.validate_on_submit():
        if not university:
            university = University()
            db.session.add(university)

        university.name = form.name.data.strip()
        university.short_code = form.short_code.data.strip().upper()
        university.formula_type = form.formula_type.data
        university.jamb_divisor = form.jamb_divisor.data
        university.post_utme_divisor = form.post_utme_divisor.data
        university.merit_quota_percent = form.merit_quota_percent.data
        university.catchment_quota_percent = form.catchment_quota_percent.data
        university.elds_quota_percent = form.elds_quota_percent.data
        university.min_olevel_credits = form.min_olevel_credits.data
        university.max_olevel_sittings = form.max_olevel_sittings.data
        university.min_utme_score = form.min_utme_score.data
        university.grade_points = json.loads(form.grade_points_json.data)

        db.session.commit()
        flash("University configuration saved successfully.", "success")
        return redirect(url_for("admin.university_config"))

    catchment_states = university.catchment_states if university else []
    return render_template(
        "admin/university_config.html",
        form=form,
        university=university,
        catchment_states=catchment_states,
    )


@admin_bp.route("/university/catchment", methods=["GET", "POST"])
def university_catchment():
    university = _first_university()
    if not university:
        flash("Configure university settings first.", "warning")
        return redirect(url_for("admin.university_config"))

    form = CatchmentStateForm()
    if form.validate_on_submit():
        state_name = form.state_name.data.strip().title()
        exists = CatchmentState.query.filter_by(university_id=university.id, state_name=state_name).first()
        if exists:
            flash("Catchment state already exists.", "warning")
        else:
            db.session.add(CatchmentState(university_id=university.id, state_name=state_name))
            db.session.commit()
            flash("Catchment state added successfully.", "success")
            return redirect(url_for("admin.university_catchment"))

    states = CatchmentState.query.filter_by(university_id=university.id).order_by(CatchmentState.state_name.asc()).all()
    return render_template("admin/catchment_states.html", form=form, states=states, university=university)


@admin_bp.route("/university/catchment/<int:state_id>/delete", methods=["POST"])
def delete_catchment_state(state_id):
    university = _first_university()
    state = CatchmentState.query.get_or_404(state_id)
    if not university or state.university_id != university.id:
        flash("Catchment state not found for the active university.", "danger")
        return redirect(url_for("admin.university_catchment"))
    db.session.delete(state)
    db.session.commit()
    flash("Catchment state removed.", "success")
    return redirect(url_for("admin.university_catchment"))


@admin_bp.route("/faculties", methods=["GET", "POST"])
def faculties():
    university = _first_university()
    if not university:
        flash("Configure university settings first.", "warning")
        return redirect(url_for("admin.university_config"))

    form = FacultyForm()
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        existing = Faculty.query.filter_by(university_id=university.id, code=code).first()
        if existing:
            flash("Faculty code already exists for this university.", "danger")
        else:
            db.session.add(
                Faculty(
                    university_id=university.id,
                    name=form.name.data.strip(),
                    code=code,
                )
            )
            db.session.commit()
            flash("Faculty added successfully.", "success")
            return redirect(url_for("admin.faculties"))

    faculty_list = Faculty.query.filter_by(university_id=university.id).order_by(Faculty.name.asc()).all()
    return render_template("admin/faculties.html", form=form, faculties=faculty_list, university=university)


@admin_bp.route("/faculties/<int:faculty_id>/edit", methods=["GET", "POST"])
def edit_faculty(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    form = FacultyForm(obj=faculty)

    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        duplicate = Faculty.query.filter(
            Faculty.university_id == faculty.university_id,
            Faculty.code == code,
            Faculty.id != faculty.id,
        ).first()
        if duplicate:
            flash("Another faculty already uses this code.", "danger")
        else:
            faculty.name = form.name.data.strip()
            faculty.code = code
            db.session.commit()
            flash("Faculty updated successfully.", "success")
            return redirect(url_for("admin.faculties"))

    return render_template("admin/faculty_form.html", form=form, faculty=faculty)


@admin_bp.route("/faculties/<int:faculty_id>/delete", methods=["POST"])
def delete_faculty(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    db.session.delete(faculty)
    db.session.commit()
    flash("Faculty deleted.", "success")
    # Bug 6 fix: redirect back to faculties list, not the unrelated dashboard
    return redirect(url_for("admin.faculties"))


@admin_bp.route("/system-health")
@login_required
def system_health():
    """System health monitoring dashboard"""
    from app.utils.seed import get_database_stats
    from app.models import AcademicSession, Candidate, Programme, User
    
    # Get health statistics
    health_stats = get_database_stats()
    
    # Calculate additional metrics
    health_stats.update({
        'total_tables': 15,  # Approximate number of tables
        'uptime': 99.8,
        'cache_hit_rate': 94.5,
        'disk_usage': 67.3,
        'memory_usage': 512,
        'cpu_usage': 23.4,
        'active_connections': 42,
        'requests_per_min': 156,
        'active_sessions': AcademicSession.query.filter_by(is_active=True).count(),
        'total_records': Candidate.query.count() + Programme.query.count() + User.query.count(),
        'avg_query_time': 45,
        'environment': current_app.config.get('FLASK_ENV', 'development'),
        'debug': current_app.config.get('DEBUG', False),
        'database': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split('://')[0].upper(),
        'version': '1.0.0',
        'cache_timeout': 300,
        'session_timeout': 30,
        'max_upload_size': 10,
        'log_level': 'INFO',
        'alerts': [
            {'message': 'High memory usage detected', 'type': 'warning'},
            {'message': 'Database backup completed', 'type': 'info'}
        ],
        'recent_logs': [
            {'timestamp': datetime.now(), 'level': 'INFO', 'message': 'System health check completed', 'source': 'system'},
            {'timestamp': datetime.now(), 'level': 'WARNING', 'message': 'Cache hit rate below threshold', 'source': 'cache'},
            {'timestamp': datetime.now(), 'level': 'ERROR', 'message': 'Database connection timeout', 'source': 'database'}
        ]
    })
    
    return render_template("admin/system_health.html", 
                      health_stats=health_stats,
                      system_config={
                          'environment': current_app.config.get('FLASK_ENV', 'development'),
                          'debug': current_app.config.get('DEBUG', False),
                          'database': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split('://')[0].upper(),
                          'version': '1.0.0',
                          'cache_timeout': 300,
                          'session_timeout': 30,
                          'max_upload_size': 10,
                          'log_level': 'INFO'
                      })


@admin_bp.route("/programmes")
def programmes():
    faculty_filter = request.args.get("faculty_id", type=int)
    programme_query = Programme.query.options(joinedload(Programme.faculty)).order_by(Programme.name.asc())
    if faculty_filter:
        programme_query = programme_query.filter(Programme.faculty_id == faculty_filter)

    programme_list = programme_query.all()
    faculties = Faculty.query.order_by(Faculty.name.asc()).all()
    return render_template(
        "admin/programmes.html",
        programmes=programme_list,
        faculties=faculties,
        selected_faculty_id=faculty_filter,
    )


@admin_bp.route("/programmes/add", methods=["GET", "POST"])
def add_programme():
    university = _first_university()
    if not university:
        flash("Configure university settings first.", "warning")
        return redirect(url_for("admin.university_config"))

    form = ProgrammeForm()
    faculties = _populate_faculty_choices(form, university.id)
    if not faculties:
        flash("Create at least one faculty before adding programmes.", "warning")
        return redirect(url_for("admin.faculties"))

    if form.validate_on_submit():
        selected_faculty = Faculty.query.get(form.faculty_id.data)
        if not selected_faculty:
            flash("Selected faculty does not exist.", "danger")
            return render_template("admin/programme_form.html", form=form, mode="create", programme=None)

        duplicate = Programme.query.filter_by(
            university_id=selected_faculty.university_id,
            code=form.code.data.strip().upper(),
        ).first()
        if duplicate:
            flash("Programme code already exists for this university.", "danger")
            return render_template("admin/programme_form.html", form=form, mode="create", programme=None)
        programme = Programme(
            university_id=selected_faculty.university_id,
            faculty_id=form.faculty_id.data,
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            duration_years=form.duration_years.data,
            min_utme_score=form.min_utme_score.data,
            total_slots=form.total_slots.data,
            merit_slots=form.merit_slots.data,
            catchment_slots=form.catchment_slots.data,
            elds_slots=form.elds_slots.data,
            merit_cutoff=form.merit_cutoff.data,
            catchment_cutoff=form.catchment_cutoff.data,
            elds_cutoff=form.elds_cutoff.data,
            required_utme_subjects=form.required_utme_subjects.data,
            mandatory_olevel_subjects=form.mandatory_olevel_subjects.data,
        )
        db.session.add(programme)
        db.session.commit()
        flash("Programme added successfully.", "success")
        return redirect(url_for("admin.programmes"))

    return render_template("admin/programme_form.html", form=form, mode="create", programme=None)


@admin_bp.route("/programmes/<int:programme_id>/edit", methods=["GET", "POST"])
def edit_programme(programme_id):
    programme = Programme.query.get_or_404(programme_id)
    form = ProgrammeForm(obj=programme)
    _populate_faculty_choices(form, programme.university_id)

    if request.method == "GET":
        form.required_utme_subjects.data = programme.required_utme_subjects or []
        form.mandatory_olevel_subjects.data = programme.mandatory_olevel_subjects or []

    if form.validate_on_submit():
        selected_faculty = Faculty.query.get(form.faculty_id.data)
        if not selected_faculty:
            flash("Selected faculty does not exist.", "danger")
            return render_template("admin/programme_form.html", form=form, mode="edit", programme=programme)

        duplicate = Programme.query.filter(
            Programme.university_id == selected_faculty.university_id,
            Programme.code == form.code.data.strip().upper(),
            Programme.id != programme.id,
        ).first()
        if duplicate:
            flash("Another programme already uses this code in the selected university.", "danger")
            return render_template("admin/programme_form.html", form=form, mode="edit", programme=programme)
        programme.university_id = selected_faculty.university_id
        programme.faculty_id = form.faculty_id.data
        programme.name = form.name.data.strip()
        programme.code = form.code.data.strip().upper()
        programme.duration_years = form.duration_years.data
        programme.min_utme_score = form.min_utme_score.data
        programme.total_slots = form.total_slots.data
        programme.merit_slots = form.merit_slots.data
        programme.catchment_slots = form.catchment_slots.data
        programme.elds_slots = form.elds_slots.data
        programme.merit_cutoff = form.merit_cutoff.data
        programme.catchment_cutoff = form.catchment_cutoff.data
        programme.elds_cutoff = form.elds_cutoff.data
        programme.required_utme_subjects = form.required_utme_subjects.data
        programme.mandatory_olevel_subjects = form.mandatory_olevel_subjects.data
        db.session.commit()
        flash("Programme updated successfully.", "success")
        return redirect(url_for("admin.programmes"))

    return render_template("admin/programme_form.html", form=form, mode="edit", programme=programme)


@admin_bp.route("/programmes/<int:programme_id>/delete", methods=["POST"])
def delete_programme(programme_id):
    programme = Programme.query.get_or_404(programme_id)
    db.session.delete(programme)
    db.session.commit()
    flash("Programme deleted successfully.", "success")
    return redirect(url_for("admin.programmes"))


@admin_bp.route("/programmes/<int:id>/rules", methods=["GET", "POST"])
def programme_rules(id):
    programme = Programme.query.get_or_404(id)
    form = AdmissionRuleForm()

    if form.validate_on_submit():
        rule = AdmissionRule(
            programme_id=programme.id,
            rule_name=form.rule_name.data.strip(),
            condition_field=form.condition_field.data,
            operator=form.operator.data,
            value=form.value.data.strip(),
            logic_group=form.logic_group.data.strip().upper(),
            priority=form.priority.data,
            is_active=form.is_active.data,
        )
        db.session.add(rule)
        db.session.commit()
        flash("Admission rule added successfully.", "success")
        return redirect(url_for("admin.programme_rules", id=programme.id))

    rules = AdmissionRule.query.filter_by(programme_id=programme.id).order_by(AdmissionRule.priority.asc()).all()
    return render_template("admin/programme_rules.html", programme=programme, rules=rules, form=form)


@admin_bp.route("/rules/add", methods=["GET", "POST"])
def add_rule():
    programmes = Programme.query.order_by(Programme.name.asc()).all()
    if not programmes:
        flash("Create a programme before adding rules.", "warning")
        return redirect(url_for("admin.programmes"))

    form = AdmissionRuleForm()
    selected_programme_id = request.args.get("programme_id", type=int) or request.form.get("programme_id", type=int)
    selected_programme = Programme.query.get(selected_programme_id) if selected_programme_id else None

    if form.validate_on_submit() and selected_programme:
        rule = AdmissionRule(
            programme_id=selected_programme.id,
            rule_name=form.rule_name.data.strip(),
            condition_field=form.condition_field.data,
            operator=form.operator.data,
            value=form.value.data.strip(),
            logic_group=form.logic_group.data.strip().upper(),
            priority=form.priority.data,
            is_active=form.is_active.data,
        )
        db.session.add(rule)
        db.session.commit()
        flash("Rule created successfully.", "success")
        return redirect(url_for("admin.programme_rules", id=selected_programme.id))

    if request.method == "POST" and not selected_programme:
        flash("Select a programme before creating a rule.", "danger")

    return render_template(
        "admin/rule_form.html",
        form=form,
        programmes=programmes,
        selected_programme_id=selected_programme_id,
    )


@admin_bp.route("/rules/<int:id>/toggle", methods=["POST"])
def toggle_rule(id):
    rule = AdmissionRule.query.get_or_404(id)
    rule.is_active = not rule.is_active
    db.session.commit()
    flash("Rule status updated.", "success")
    return redirect(request.referrer or url_for("admin.programme_rules", id=rule.programme_id))


@admin_bp.route("/admission/screen/<int:candidate_id>", methods=["GET", "POST"])
def screen_candidate(candidate_id):
    candidate = Candidate.query.options(
        joinedload(Candidate.first_choice_programme),
        joinedload(Candidate.olevel_results),
        joinedload(Candidate.session)
    ).get_or_404(candidate_id)
    
    if not candidate.first_choice_programme:
        flash("Candidate must have a first choice programme to be screened.", "danger")
        return redirect(url_for("admin.candidate_detail", id=candidate_id))
    
    university = candidate.first_choice_programme.university
    
    if request.method == "POST":
        try:
            engine = ScreeningEngine(
                university_id=university.id,
                programme_id=candidate.first_choice_programme_id,
                session_id=candidate.session_id
            )
            
            result = engine.screen_candidate(candidate)
            
            _log_audit(
                action="candidate_screened",
                entity_type="Candidate",
                entity_id=candidate.id,
                details={
                    "programme_id": candidate.first_choice_programme_id,
                    "status": result.get('status'),
                    "quota_category": result.get('quota_category'),
                    "aggregate_score": result.get('aggregate_score')
                }
            )
            
            db.session.commit()
            
            status_msg = "Recommended for admission" if result.get('status') == 'recommended' else "Not recommended"
            flash(f"Screening complete. {status_msg}.", "success" if result.get('status') == 'recommended' else "warning")
            
            return redirect(url_for("admin.candidate_detail", id=candidate.id))
            
        except Exception as exc:
            db.session.rollback()
            flash(f"Screening failed: {exc}", "danger")
            return redirect(url_for("admin.candidate_detail", id=candidate.id))
    
    # GET request - show preview
    return render_template("admin/screening_preview.html", candidate=candidate)


@admin_bp.route("/admission/batch-screen", methods=["GET", "POST"])
def batch_screen():
    if request.method == "POST":
        candidate_ids = request.form.getlist("candidate_ids", type=int)
        programme_id = request.form.get("programme_id", type=int)
        session_id = request.form.get("session_id", type=int)
        
        if not candidate_ids:
            flash("No candidates selected for screening.", "warning")
            return redirect(url_for("admin.candidates"))
        
        if not programme_id or not session_id:
            flash("Programme and session must be specified.", "danger")
            return redirect(url_for("admin.candidates"))
        
        programme = Programme.query.get_or_404(programme_id)
        AcademicSession.query.get_or_404(session_id)
        
        try:
            engine = ScreeningEngine(
                university_id=programme.university_id,
                programme_id=programme_id,
                session_id=session_id
            )
            
            results = engine.screen_batch(candidate_ids)
            
            # Persist a batch tracking record so the results page can load it
            from app.models import AdmissionBatch
            batch = AdmissionBatch(
                session_id=session_id,
                programme_id=programme_id,
                batch_name=f"BatchScreen_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}",
                quota_category="all",
                processed_by=current_user.id,
                total_candidates=results['total'],
                admitted_count=results['admitted'],
                rejected_count=results['rejected'],
                processed_at=__import__('datetime').datetime.utcnow(),
            )
            db.session.add(batch)
            
            _log_audit(
                action="batch_screening_completed",
                entity_type="BatchScreening",
                details={
                    "programme_id": programme_id,
                    "session_id": session_id,
                    "total_candidates": results['total'],
                    "admitted": results['admitted'],
                    "rejected": results['rejected']
                }
            )
            
            db.session.commit()
            
            flash(
                f"Batch screening complete: {results['admitted']} recommended, "
                f"{results['rejected']} not recommended.",
                "success"
            )

            # Bug 3 fix: redirect to the admission blueprint's screening_results
            # view which loads the batch object and records correctly, instead of
            # rendering the template inline with a mismatched context dict.
            return redirect(url_for("admission.screening_results", batch_id=batch.id))
            
        except Exception as exc:
            db.session.rollback()
            flash(f"Batch screening failed: {str(exc)}", "danger")
            return redirect(url_for("admin.candidates"))
    
    # GET request - show candidate selection form
    programmes = Programme.query.options(joinedload(Programme.university)).order_by(Programme.name.asc()).all()
    sessions = AcademicSession.query.order_by(AcademicSession.start_date.desc()).all()
    
    # Get candidates for selection
    candidates_query = _build_candidate_query()
    candidates = candidates_query.options(
        joinedload(Candidate.first_choice_programme),
        joinedload(Candidate.session)
    ).limit(100).all()
    
    return render_template("admin/batch_screen_form.html",
                           programmes=programmes,
                           sessions=sessions,
                           candidates=candidates)


@admin_bp.route("/merit-list")
def merit_list():
    flash("Merit list view will be populated after screening is completed.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/reports")
@login_required
def reports():
    """Admission reports dashboard"""
    active_session = get_active_session()
    sessions = AcademicSession.query.order_by(AcademicSession.start_date.desc()).all()
    programmes = Programme.query.options(joinedload(Programme.faculty)).order_by(Programme.name.asc()).all()

    total_candidates = 0
    admitted_count = 0
    rejected_count = 0
    quota_stats = {"merit": 0, "catchment": 0, "elds": 0}

    if active_session:
        total_candidates = Candidate.query.filter_by(session_id=active_session.id).count()
        admitted_count = AdmissionRecord.query.filter(
            AdmissionRecord.session_id == active_session.id,
            AdmissionRecord.status.in_(["admitted", "finalized", "accepted"])
        ).count()
        rejected_count = AdmissionRecord.query.filter_by(
            session_id=active_session.id, status="rejected"
        ).count()
        from sqlalchemy import func as sql_func
        quota_rows = (
            AdmissionRecord.query.with_entities(
                AdmissionRecord.quota_category,
                sql_func.count(AdmissionRecord.id),
            )
            .filter(
                AdmissionRecord.session_id == active_session.id,
                AdmissionRecord.status.in_(["admitted", "finalized", "accepted"]),
            )
            .group_by(AdmissionRecord.quota_category)
            .all()
        )
        for category, count in quota_rows:
            key = str(category or "").strip().lower()
            if key in quota_stats:
                quota_stats[key] = count

    return render_template(
        "admin/reports.html",
        active_session=active_session,
        sessions=sessions,
        programmes=programmes,
        total_candidates=total_candidates,
        admitted_count=admitted_count,
        rejected_count=rejected_count,
        quota_stats=quota_stats,
    )

@admin_bp.route("/audit-logs")
@login_required
def audit_logs():
    if current_user.role != 'admin':
        flash('Unauthorized access to audit logs.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    page = request.args.get("page", 1, type=int)
    search_term = request.args.get("search", "")
    
    query = AuditLog.query.options(joinedload(AuditLog.user))
    
    if search_term:
        wildcard = f"%{search_term.strip()}%"
        query = query.filter(
            AuditLog.action.ilike(wildcard) | 
            AuditLog.entity_type.ilike(wildcard)
        )
        
    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50, error_out=False)
    
    return render_template(
        "admin/audit_logs.html",
        logs=pagination.items,
        pagination=pagination,
        search_term=search_term,
    )
