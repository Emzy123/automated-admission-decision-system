"""
Candidate Routes
Handles candidate portal access and dashboard
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user, current_user

from app import db
from app.models import Candidate, User, AdmissionRecord

candidate_bp = Blueprint('candidate', __name__, url_prefix='/candidate')


@candidate_bp.before_request
def require_password_change():
    """Force password change for candidates using the default password"""
    if current_user.is_authenticated and current_user.role == 'candidate':
        # Ignore static files and auth endpoints
        if request.endpoint and request.endpoint not in ['candidate.change_password', 'candidate.logout', 'static']:
            if current_user.check_password('password'):
                flash('For security reasons, you must change your default password before accessing your dashboard.', 'warning')
                return redirect(url_for('candidate.change_password'))


@candidate_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Candidate login page"""
    if current_user.is_authenticated:
        if current_user.role == 'candidate':
            return redirect(url_for('candidate.dashboard'))
        else:
            return redirect(url_for('admin.dashboard'))
            
    if request.method == 'POST':
        jamb_reg_number = request.form.get('jamb_reg_number')
        password = request.form.get('password')
        
        if not jamb_reg_number or not password:
            flash('Please enter both JAMB Reg Number and Password.', 'warning')
            return render_template('candidate/login.html')
            
        candidate = Candidate.query.filter_by(jamb_reg_number=jamb_reg_number).first()
        if candidate:
            # Find linked user account (may have been created by CandidateProcessor)
            user = None
            if candidate.user_id:
                user = User.query.get(candidate.user_id)
            if not user:
                user = User.query.filter_by(username=jamb_reg_number).first()
            
            # If no account yet, create one
            if not user:
                user = User(
                    username=jamb_reg_number,
                    email=candidate.email or f"{jamb_reg_number}@candidate.custech.edu.ng",
                    full_name=candidate.full_name,
                    role='candidate'
                )
                user.set_password('password')  # Same default as CandidateProcessor
                db.session.add(user)
                db.session.flush()
                candidate.user_id = user.id
                db.session.commit()
            
            # Normalise role: 'applicant' is treated as 'candidate'
            if user.role == 'applicant':
                user.role = 'candidate'
                db.session.commit()
                
            if user.check_password(password):
                login_user(user)
                return redirect(url_for('candidate.dashboard'))
            else:
                flash('Invalid password. Your default password is "password" unless you changed it.', 'danger')
        else:
            flash('Candidate not found. Please check your JAMB Registration Number.', 'danger')
            
    return render_template('candidate/login.html')


@candidate_bp.route('/dashboard')
@login_required
def dashboard():
    """Candidate dashboard"""
    if current_user.role != 'candidate':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
        
    candidate = current_user.candidate_profile
    if not candidate:
        flash('Candidate profile not found.', 'danger')
        return redirect(url_for('auth.login'))
        
    # Get the latest admission record
    admission_record = AdmissionRecord.query.filter_by(candidate_id=candidate.id).order_by(AdmissionRecord.created_at.desc()).first()
    
    return render_template('candidate/dashboard.html', 
                          candidate=candidate, 
                          admission_record=admission_record)


@candidate_bp.route('/accept_admission/<int:record_id>', methods=['POST'])
@login_required
def accept_admission(record_id):
    """Candidate accepts admission offer"""
    from flask import abort
    if current_user.role != 'candidate':
        abort(403)
        
    record = AdmissionRecord.query.get_or_404(record_id)
    if record.candidate_id != current_user.candidate_profile.id:
        abort(403)
        
    if record.status == 'admitted':
        record.status = 'accepted'
        db.session.commit()
        flash('Congratulations! You have successfully accepted your admission offer.', 'success')
    else:
        flash('Invalid admission status or already accepted.', 'danger')
        
    return redirect(url_for('candidate.dashboard'))


@candidate_bp.route('/decline_admission/<int:record_id>', methods=['POST'])
@login_required
def decline_admission(record_id):
    """Candidate declines admission offer"""
    from flask import abort
    if current_user.role != 'candidate':
        abort(403)
        
    record = AdmissionRecord.query.get_or_404(record_id)
    if record.candidate_id != current_user.candidate_profile.id:
        abort(403)
        
    if record.status in ['admitted', 'accepted']:
        record.status = 'declined'
        db.session.commit()
        flash('You have successfully declined your admission offer.', 'info')
        
        # Trigger recalculation of the merit list for this quota to promote the next candidate
        try:
            from app.services.merit_list import MeritListGenerator
            generator = MeritListGenerator(record.programme_id, record.session_id)
            generator.generate_quota_list(record.quota_category)
        except Exception as e:
            # We don't want a crash here to break the user experience, though it should be logged.
            pass
            
    else:
        flash('Invalid admission status.', 'danger')
        
    return redirect(url_for('candidate.dashboard'))


@candidate_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Endpoint for candidates to change their default password"""
    if current_user.role != 'candidate':
        from flask import abort
        abort(403)
        
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('candidate.change_password'))
            
        if not current_user.check_password(current_password):
            flash('Incorrect current password.', 'danger')
            return redirect(url_for('candidate.change_password'))
            
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'danger')
            return redirect(url_for('candidate.change_password'))
            
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('candidate.change_password'))
            
        if new_password == 'password':
            flash('You cannot use the default password. Please choose a secure one.', 'danger')
            return redirect(url_for('candidate.change_password'))
            
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password successfully updated! Welcome to your dashboard.', 'success')
        return redirect(url_for('candidate.dashboard'))
        
    return render_template('candidate/change_password.html')


@candidate_bp.route('/logout')
@login_required
def logout():
    """Logout candidate"""
    logout_user()
    return redirect(url_for('candidate.login'))
