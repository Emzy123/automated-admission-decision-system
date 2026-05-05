import json

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    DateField,
    FloatField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

UTME_SUBJECT_CHOICES = [
    ("English", "English"),
    ("Mathematics", "Mathematics"),
    ("Physics", "Physics"),
    ("Chemistry", "Chemistry"),
    ("Biology", "Biology"),
    ("Economics", "Economics"),
    ("Government", "Government"),
    ("Literature", "Literature"),
    ("Geography", "Geography"),
    ("Agricultural Science", "Agricultural Science"),
    ("Commerce", "Commerce"),
    ("CRS", "CRS"),
    ("IRS", "IRS"),
]


class UniversityConfigForm(FlaskForm):
    name = StringField("University Name", validators=[DataRequired(), Length(min=3, max=150)])
    short_code = StringField("Short Code", validators=[DataRequired(), Length(min=2, max=20)])
    formula_type = SelectField(
        "Formula Type",
        choices=[
            ("STANDARD", "STANDARD"),
            ("CUSTECH", "CUSTECH"),
            ("OAU", "OAU"),
            ("UNILAG", "UNILAG"),
        ],
        validators=[DataRequired()],
    )
    jamb_divisor = FloatField(
        "JAMB Divisor",
        default=8.0,
        validators=[DataRequired(), NumberRange(min=0.01)],
    )
    post_utme_divisor = FloatField(
        "Post-UTME Divisor",
        default=4.0,
        validators=[DataRequired(), NumberRange(min=0.01)],
    )
    merit_quota_percent = FloatField(
        "Merit Quota (%)",
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    catchment_quota_percent = FloatField(
        "Catchment Quota (%)",
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    elds_quota_percent = FloatField(
        "ELDS Quota (%)",
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    min_olevel_credits = IntegerField(
        "Minimum O'Level Credits",
        validators=[DataRequired(), NumberRange(min=1, max=9)],
    )
    max_olevel_sittings = IntegerField(
        "Maximum O'Level Sittings",
        validators=[DataRequired(), NumberRange(min=1, max=3)],
    )
    min_utme_score = IntegerField(
        "Minimum UTME Score",
        validators=[DataRequired(), NumberRange(min=0, max=400)],
    )
    grade_points_json = TextAreaField(
        "Grade Points Mapping (JSON)",
        validators=[DataRequired()],
        default='{"A1": 8, "B2": 7, "B3": 6, "C4": 5, "C5": 4, "C6": 3}',
    )
    submit = SubmitField("Save Configuration")

    def validate_grade_points_json(self, field):
        try:
            parsed = json.loads(field.data)
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError("Grade points mapping must be a non-empty JSON object.")
            for grade, point in parsed.items():
                if not isinstance(grade, str) or not grade.strip():
                    raise ValueError("Each grade key must be a non-empty string.")
                if not isinstance(point, (int, float)):
                    raise ValueError("Each grade point value must be numeric.")
        except ValueError as exc:
            raise ValidationError(f"Invalid JSON for grade points: {exc}") from exc

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False
        total = (
            (self.merit_quota_percent.data or 0)
            + (self.catchment_quota_percent.data or 0)
            + (self.elds_quota_percent.data or 0)
        )
        if round(total, 2) != 100.00:
            self.elds_quota_percent.errors.append("Merit + Catchment + ELDS quotas must equal 100%.")
            return False
        return True


class CatchmentStateForm(FlaskForm):
    state_name = StringField("State Name", validators=[DataRequired(), Length(min=2, max=64)])
    submit = SubmitField("Add State")


class FacultyForm(FlaskForm):
    name = StringField("Faculty Name", validators=[DataRequired(), Length(min=2, max=120)])
    code = StringField("Faculty Code", validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField("Save Faculty")


class ProgrammeForm(FlaskForm):
    name = StringField("Programme Name", validators=[DataRequired(), Length(min=2, max=150)])
    code = StringField("Programme Code", validators=[DataRequired(), Length(min=2, max=20)])
    faculty_id = SelectField("Faculty", coerce=int, validators=[DataRequired()])
    duration_years = IntegerField(
        "Duration (Years)",
        validators=[DataRequired(), NumberRange(min=1, max=10)],
        default=4,
    )
    min_utme_score = IntegerField(
        "Minimum UTME Score",
        validators=[DataRequired(), NumberRange(min=0, max=400)],
        default=140,
    )
    total_slots = IntegerField("Total Slots", validators=[DataRequired(), NumberRange(min=0)], default=0)
    merit_slots = IntegerField("Merit Slots", validators=[DataRequired(), NumberRange(min=0)], default=0)
    catchment_slots = IntegerField(
        "Catchment Slots",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    elds_slots = IntegerField("ELDS Slots", validators=[DataRequired(), NumberRange(min=0)], default=0)
    merit_cutoff = FloatField("Merit Cutoff", validators=[Optional(), NumberRange(min=0, max=100)])
    catchment_cutoff = FloatField(
        "Catchment Cutoff",
        validators=[Optional(), NumberRange(min=0, max=100)],
    )
    elds_cutoff = FloatField("ELDS Cutoff", validators=[Optional(), NumberRange(min=0, max=100)])
    required_utme_subjects = SelectMultipleField(
        "Required UTME Subjects",
        choices=UTME_SUBJECT_CHOICES,
        validators=[DataRequired()],
    )
    mandatory_olevel_subjects = SelectMultipleField(
        "Mandatory O'Level Subjects",
        choices=UTME_SUBJECT_CHOICES,
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Programme")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False
        slot_sum = (
            (self.merit_slots.data or 0)
            + (self.catchment_slots.data or 0)
            + (self.elds_slots.data or 0)
        )
        if slot_sum > (self.total_slots.data or 0):
            self.total_slots.errors.append("Sum of quota slots cannot exceed total slots.")
            return False
        return True


class AdmissionRuleForm(FlaskForm):
    rule_name = StringField("Rule Name", validators=[DataRequired(), Length(min=3, max=120)])
    condition_field = SelectField(
        "Condition Field",
        validators=[DataRequired()],
        choices=[
            ("utme_score", "UTME Score"),
            ("post_utme_score", "Post-UTME Score"),
            ("aggregate_score", "Aggregate Score"),
            ("olevel_english", "O'Level English"),
            ("olevel_math", "O'Level Mathematics"),
            ("state_of_origin", "State of Origin"),
        ],
    )
    operator = SelectField(
        "Operator",
        validators=[DataRequired()],
        choices=[
            (">=", ">="),
            ("<=", "<="),
            ("==", "=="),
            ("!=", "!="),
            (">", ">"),
            ("<", "<"),
            ("IN", "IN"),
            ("NOT_IN", "NOT_IN"),
        ],
    )
    value = StringField("Value", validators=[DataRequired(), Length(min=1, max=255)])
    logic_group = SelectField(
        "Logic Group",
        validators=[DataRequired()],
        choices=[("AND", "AND"), ("OR", "OR")],
        default="AND",
    )
    priority = IntegerField("Priority", validators=[DataRequired(), NumberRange(min=1, max=999)], default=100)
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Rule")


class CandidateUploadForm(FlaskForm):
    file = FileField(
        "Candidate File",
        validators=[
            FileRequired(),
            FileAllowed(["csv", "xlsx", "xls"], "Only .csv, .xlsx, and .xls files are allowed."),
        ],
    )
    session_id = SelectField("Academic Session", coerce=int, validators=[DataRequired()])
    validate_duplicates = BooleanField("Validate Duplicates", default=True)
    skip_errors = BooleanField("Skip Invalid Rows", default=False)
    submit = SubmitField("Upload & Preview")


class OLevelResultForm(FlaskForm):
    exam_body = SelectField(
        "Exam Body",
        choices=[("WAEC", "WAEC"), ("NECO", "NECO"), ("NABTEB", "NABTEB")],
        validators=[DataRequired()],
    )
    exam_number = StringField("Exam Number", validators=[DataRequired(), Length(min=4, max=40)])
    exam_year = IntegerField(
        "Exam Year",
        validators=[DataRequired(), NumberRange(min=1980, max=2100)],
    )
    sitting_number = SelectField(
        "Sitting Number",
        choices=[(1, "1"), (2, "2")],
        coerce=int,
        validators=[DataRequired()],
    )
    subjects_grades_json = TextAreaField(
        "Subjects and Grades (JSON)",
        validators=[Optional()],
        default="[]",
    )

    def validate_subjects_grades_json(self, field):
        if not field.data or not str(field.data).strip():
            return
        try:
            parsed = json.loads(field.data)
            if not isinstance(parsed, list):
                raise ValueError("Expected a JSON array.")
            for entry in parsed:
                if not isinstance(entry, dict):
                    raise ValueError("Each subject entry must be an object.")
                if not entry.get("subject") or not entry.get("grade"):
                    raise ValueError("Each entry must include subject and grade.")
        except ValueError as exc:
            raise ValidationError(f"Invalid subjects/grades JSON: {exc}") from exc


class CandidateManualForm(FlaskForm):
    jamb_reg_number = StringField("JAMB Reg Number", validators=[DataRequired(), Length(min=10, max=30)])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField("Email", validators=[Optional(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    gender = SelectField(
        "Gender",
        choices=[("", "Select Gender"), ("Male", "Male"), ("Female", "Female")],
        validators=[Optional()],
    )
    date_of_birth = DateField("Date of Birth", validators=[Optional()], format="%Y-%m-%d")
    state_of_origin = StringField("State of Origin", validators=[DataRequired(), Length(min=2, max=64)])
    lga_of_origin = StringField("LGA of Origin", validators=[Optional(), Length(max=64)])
    session_id = SelectField("Academic Session", coerce=int, validators=[DataRequired()])
    first_choice_programme_id = SelectField("First Choice Programme", coerce=int, validators=[DataRequired()])
    utme_score = IntegerField("UTME Score", validators=[DataRequired(), NumberRange(min=0, max=400)])
    utme_subjects_json = TextAreaField(
        "UTME Subjects JSON",
        validators=[DataRequired()],
        default='{"English": 65, "Mathematics": 70}',
    )
    post_utme_score = FloatField("Post-UTME Score", validators=[Optional(), NumberRange(min=0, max=100)])
    post_utme_present = BooleanField("Post-UTME Present", default=False)
    olevel_results_json = TextAreaField("O'Level Results JSON", validators=[Optional()], default="[]")
    submit = SubmitField("Save Candidate")

    def validate_jamb_reg_number(self, field):
        cleaned = field.data.strip().upper() if field.data else ""
        field.data = cleaned
        if len(cleaned) < 10:
            raise ValidationError("JAMB registration number looks too short.")

    def validate_utme_subjects_json(self, field):
        try:
            parsed = json.loads(field.data)
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError("UTME subjects must be a non-empty JSON object.")
            for subject, score in parsed.items():
                if not isinstance(subject, str) or not subject.strip():
                    raise ValueError("Subject names must be non-empty strings.")
                if not isinstance(score, (int, float)):
                    raise ValueError("Each UTME subject score must be numeric.")
        except ValueError as exc:
            raise ValidationError(f"Invalid UTME subjects JSON: {exc}") from exc

    def validate_olevel_results_json(self, field):
        if not field.data or not str(field.data).strip():
            return
        try:
            parsed = json.loads(field.data)
            if not isinstance(parsed, list):
                raise ValueError("O'Level results must be a JSON array.")
            for entry in parsed:
                if not isinstance(entry, dict):
                    raise ValueError("Each O'Level result entry must be an object.")
                required = ["exam_body", "exam_number", "exam_year", "sitting_number", "subject", "grade"]
                missing = [key for key in required if key not in entry]
                if missing:
                    raise ValueError(f"Missing keys: {', '.join(missing)}")
        except ValueError as exc:
            raise ValidationError(f"Invalid O'Level JSON: {exc}") from exc
