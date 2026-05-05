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
