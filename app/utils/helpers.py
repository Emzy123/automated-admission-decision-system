from datetime import date

from app.models import AcademicSession
ALLOWED_UPLOAD_EXTENSIONS = {"xlsx", "xls", "csv"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def normalize_name(value):
    return " ".join(value.strip().split()).title() if value else ""


def get_active_session():
    return (
        AcademicSession.query.filter_by(is_active=True)
        .order_by(AcademicSession.start_date.desc())
        .first()
    )


def format_nigerian_currency(amount):
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0
    return f"₦{value:,.2f}"


def calculate_age(date_of_birth):
    if not date_of_birth:
        return None
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def log_audit(action, entity_type, entity_id=None, details=None):
    """Write an audit log entry immediately using a separate session,
    ensuring it is persisted independently of request transactions.
    """
    from flask import request, has_request_context
    from flask_login import current_user
    from app import db
    from app.models import AuditLog
    from sqlalchemy.orm import Session

    try:
        try:
            user_id = current_user.id if (current_user and current_user.is_authenticated) else None
        except Exception:
            user_id = None

        try:
            ip_addr = request.remote_addr if has_request_context() else None
        except Exception:
            ip_addr = None

        with Session(db.engine) as sess:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details or {},
                ip_address=ip_addr,
            )
            sess.add(entry)
            sess.commit()
    except Exception:
        pass  # Never crash request due to audit logging failure
