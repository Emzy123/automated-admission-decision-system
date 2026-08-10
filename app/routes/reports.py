"""
Reports Routes
Handles report generation and admission letter creation
"""

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required

from app.models import AdmissionRecord, Programme
from app.services.report_generator import ReportGenerator
from app.utils.helpers import get_active_session

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.before_request
def require_staff_except_personal_letters():
    from flask import request
    candidate_allowed_endpoints = ['reports.preview_letter', 'reports.admission_letter']
    
    from flask_login import current_user
    if not current_user.is_authenticated:
        from flask import redirect, url_for, flash
        flash("Please sign in to continue.", "warning")
        return redirect(url_for('index'))
        
    if request.endpoint not in candidate_allowed_endpoints:
        if current_user.role not in ["admin", "super_admin", "admission_officer", "faculty_officer"]:
            from flask import abort
            abort(403)
    elif current_user.role == 'candidate':
        record_id = request.view_args.get('record_id') if request.view_args else None
        if record_id:
            from app.models import AdmissionRecord
            record = AdmissionRecord.query.get(record_id)
            if not record or not current_user.candidate_profile or record.candidate_id != current_user.candidate_profile.id:
                from flask import abort
                abort(403)


@reports_bp.route('/dashboard')
@login_required
def dashboard_data():
    """API endpoint for dashboard charts"""
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        generator = ReportGenerator(session.id)
        data = generator.generate_summary_dashboard_data()
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': f'Failed to load dashboard data: {str(e)}'}), 500


@reports_bp.route('/admission-letter/<int:record_id>')
@login_required
def admission_letter(record_id):
    """Generate and download admission letter PDF"""
    record = AdmissionRecord.query.get_or_404(record_id)
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        generator = ReportGenerator(session.id)
        pdf = generator.generate_admission_letter(record)
        
        filename = f"Admission_Letter_{record.candidate.jamb_reg_number}.pdf"
        return send_file(pdf, download_name=filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate letter: {str(e)}'}), 500


@reports_bp.route('/statistics')
@login_required
def statistics_report():
    """Generate statistics report"""
    programme_id = request.args.get('programme_id', type=int)
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        generator = ReportGenerator(session.id)
        pdf = generator.generate_statistics_report(programme_id)
        
        filename = f"Admission_Statistics_{session.name}.pdf"
        return send_file(pdf, download_name=filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate statistics: {str(e)}'}), 500


@reports_bp.route('/export/<int:programme_id>')
@login_required
def export_excel(programme_id):
    """Export admission list to Excel"""
    quota = request.args.get('quota')
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        generator = ReportGenerator(session.id)
        excel_file = generator.generate_excel_export(programme_id, quota)
        
        programme = Programme.query.get(programme_id)
        filename = f"{programme.code}_Admission_List_{quota or 'ALL'}.xlsx"
        return send_file(excel_file, download_name=filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': f'Failed to export data: {str(e)}'}), 500


@reports_bp.route('/bulk-letters/<int:programme_id>')
@login_required
def bulk_admission_letters(programme_id):
    """Generate ZIP file with all admission letters for a programme"""
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        generator = ReportGenerator(session.id)
        zip_file = generator.generate_batch_letters(programme_id)
        
        programme = Programme.query.get(programme_id)
        filename = f"{programme.code}_Admission_Letters.zip"
        return send_file(zip_file, download_name=filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate bulk letters: {str(e)}'}), 500


@reports_bp.route('/admitted-candidates/<int:programme_id>')
@login_required
def get_admitted_candidates(programme_id):
    """Get all admitted candidates for a programme"""
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        from sqlalchemy.orm import joinedload
        
        # Get admitted candidates for this programme
        records = AdmissionRecord.query.options(
            joinedload(AdmissionRecord.candidate)
        ).filter(
            AdmissionRecord.programme_id == programme_id,
            AdmissionRecord.session_id == session.id,
            AdmissionRecord.status == 'admitted'
        ).all()
        
        candidates = []
        for record in records:
            candidates.append({
                'id': record.id,
                'name': record.candidate.full_name,
                'jamb_reg': record.candidate.jamb_reg_number
            })
        
        return jsonify({'candidates': candidates})
        
    except Exception as e:
        return jsonify({'error': f'Failed to load candidates: {str(e)}'}), 500


@reports_bp.route('/preview/<int:record_id>')
@login_required
def preview_letter(record_id):
    """Preview admission letter in browser"""
    record = AdmissionRecord.query.get_or_404(record_id)
    session = get_active_session()
    if not session:
        return jsonify({'error': 'No active session found'}), 400
    
    try:
        generator = ReportGenerator(session.id)
        pdf = generator.generate_admission_letter(record)
        
        # Return PDF for inline display
        from flask import Response
        response = Response(pdf.getvalue(), mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'inline; filename="Admission_Letter_{record.candidate.jamb_reg_number}.pdf"'
        return response
        
    except Exception as e:
        return jsonify({'error': f'Failed to preview letter: {str(e)}'}), 500
