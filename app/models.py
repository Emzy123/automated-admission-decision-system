from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

ELDS_STATES = [
    "Adamawa",
    "Bauchi",
    "Bayelsa",
    "Benue",
    "Borno",
    "Cross River",
    "Ebonyi",
    "Gombe",
    "Jigawa",
    "Kaduna",
    "Kano",
    "Katsina",
    "Kebbi",
    "Kogi",
    "Kwara",
    "Nasarawa",
    "Niger",
    "Plateau",
    "Rivers",
    "Sokoto",
    "Taraba",
    "Yobe",
    "Zamfara",
]


class AcademicSession(db.Model):
    __tablename__ = "academic_sessions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    candidates = db.relationship(
        "Candidate",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    admission_records = db.relationship(
        "AdmissionRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    admission_batches = db.relationship(
        "AdmissionBatch",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<AcademicSession {self.name}>"


class University(db.Model):
    __tablename__ = "universities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    short_code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    formula_type = db.Column(db.String(30), nullable=False, default="STANDARD")
    jamb_divisor = db.Column(db.Float, nullable=False, default=8.0)
    post_utme_divisor = db.Column(db.Float, nullable=False, default=4.0)
    olevel_max_points = db.Column(db.Integer, nullable=False, default=10)
    grade_points = db.Column(
        db.JSON,
        nullable=False,
        default=lambda: {
            "A1": 8,
            "B2": 7,
            "B3": 6,
            "C4": 5,
            "C5": 4,
            "C6": 3,
        },
    )
    merit_quota_percent = db.Column(db.Float, nullable=False, default=45.0)
    catchment_quota_percent = db.Column(db.Float, nullable=False, default=35.0)
    elds_quota_percent = db.Column(db.Float, nullable=False, default=20.0)
    min_olevel_credits = db.Column(db.Integer, nullable=False, default=5)
    max_olevel_sittings = db.Column(db.Integer, nullable=False, default=2)
    min_utme_score = db.Column(db.Integer, nullable=False, default=140)

    catchment_states = db.relationship(
        "CatchmentState",
        back_populates="university",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    faculties = db.relationship(
        "Faculty",
        back_populates="university",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    programmes = db.relationship(
        "Programme",
        back_populates="university",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def get_grade_point(self, grade):
        return (self.grade_points or {}).get(str(grade).upper())

    def __repr__(self):
        return f"<University {self.short_code}>"


class CatchmentState(db.Model):
    __tablename__ = "catchment_states"

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(
        db.Integer,
        db.ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    state_name = db.Column(db.String(64), nullable=False)

    university = db.relationship("University", back_populates="catchment_states")

    __table_args__ = (
        db.UniqueConstraint("university_id", "state_name", name="uq_catchment_university_state"),
    )

    def __repr__(self):
        return f"<CatchmentState {self.state_name}>"


class ELDSState(db.Model):
    __tablename__ = "elds_states"

    id = db.Column(db.Integer, primary_key=True)
    state_name = db.Column(db.String(64), unique=True, nullable=False, index=True)

    @classmethod
    def seed_defaults(cls, db_session):
        existing = {name for (name,) in db_session.query(cls.state_name).all()}
        missing = [cls(state_name=state) for state in ELDS_STATES if state not in existing]
        if missing:
            db_session.add_all(missing)
        return len(missing)

    def __repr__(self):
        return f"<ELDSState {self.state_name}>"


class Faculty(db.Model):
    __tablename__ = "faculties"

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(
        db.Integer,
        db.ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), nullable=False)

    university = db.relationship("University", back_populates="faculties")
    programmes = db.relationship(
        "Programme",
        back_populates="faculty",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    users = db.relationship("User", back_populates="faculty", passive_deletes=True)

    __table_args__ = (
        db.UniqueConstraint("university_id", "code", name="uq_faculty_university_code"),
    )

    def __repr__(self):
        return f"<Faculty {self.code}>"


class Programme(db.Model):
    __tablename__ = "programmes"

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(
        db.Integer,
        db.ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )
    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculties.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    duration_years = db.Column(db.Integer, nullable=False, default=4)
    min_utme_score = db.Column(db.Integer, nullable=True)
    total_slots = db.Column(db.Integer, nullable=False, default=0)
    merit_slots = db.Column(db.Integer, nullable=False, default=0)
    catchment_slots = db.Column(db.Integer, nullable=False, default=0)
    elds_slots = db.Column(db.Integer, nullable=False, default=0)
    merit_cutoff = db.Column(db.Float, nullable=True)
    catchment_cutoff = db.Column(db.Float, nullable=True)
    elds_cutoff = db.Column(db.Float, nullable=True)
    required_utme_subjects = db.Column(db.JSON, nullable=False, default=lambda: [])
    mandatory_olevel_subjects = db.Column(db.JSON, nullable=False, default=lambda: [])

    university = db.relationship("University", back_populates="programmes")
    faculty = db.relationship("Faculty", back_populates="programmes")
    rules = db.relationship(
        "AdmissionRule",
        back_populates="programme",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    first_choice_candidates = db.relationship(
        "Candidate",
        foreign_keys="Candidate.first_choice_programme_id",
        back_populates="first_choice_programme",
    )
    second_choice_candidates = db.relationship(
        "Candidate",
        foreign_keys="Candidate.second_choice_programme_id",
        back_populates="second_choice_programme",
    )
    admission_records = db.relationship(
        "AdmissionRecord",
        back_populates="programme",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    admission_batches = db.relationship(
        "AdmissionBatch",
        back_populates="programme",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        db.UniqueConstraint("university_id", "code", name="uq_programme_university_code"),
    )

    def allocate_quota_slots(self, merit_percent, catchment_percent, elds_percent):
        self.merit_slots = round(self.total_slots * (merit_percent / 100))
        self.catchment_slots = round(self.total_slots * (catchment_percent / 100))
        self.elds_slots = max(self.total_slots - (self.merit_slots + self.catchment_slots), 0)

    def __repr__(self):
        return f"<Programme {self.code}>"


class AdmissionRule(db.Model):
    __tablename__ = "admission_rules"

    id = db.Column(db.Integer, primary_key=True)
    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_name = db.Column(db.String(120), nullable=False)
    condition_field = db.Column(db.String(80), nullable=False)
    operator = db.Column(db.String(20), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    logic_group = db.Column(db.String(30), nullable=False, default="default")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.Integer, default=100, nullable=False)

    programme = db.relationship("Programme", back_populates="rules")

    def __repr__(self):
        return f"<AdmissionRule {self.rule_name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="admin")
    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculties.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    faculty = db.relationship("Faculty", back_populates="users")
    verified_candidates = db.relationship(
        "Candidate",
        foreign_keys="Candidate.data_verified_by",
        back_populates="verified_by",
    )
    candidate_profile = db.relationship(
        "Candidate",
        foreign_keys="Candidate.user_id",
        back_populates="user",
        uselist=False,
    )
    dept_approved_records = db.relationship(
        "AdmissionRecord",
        foreign_keys="AdmissionRecord.dept_approved_by",
        back_populates="dept_approver",
    )
    faculty_approved_records = db.relationship(
        "AdmissionRecord",
        foreign_keys="AdmissionRecord.faculty_approved_by",
        back_populates="faculty_approver",
    )
    senate_approved_records = db.relationship(
        "AdmissionRecord",
        foreign_keys="AdmissionRecord.senate_approved_by",
        back_populates="senate_approver",
    )
    processed_batches = db.relationship(
        "AdmissionBatch",
        foreign_keys="AdmissionBatch.processed_by",
        back_populates="processor",
    )
    audit_logs = db.relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"



class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    jamb_reg_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    state_of_origin = db.Column(db.String(64), nullable=True, index=True)
    lga_of_origin = db.Column(db.String(64), nullable=True)
    first_choice_programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id", ondelete="SET NULL"),
        nullable=True,
    )
    second_choice_programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id", ondelete="SET NULL"),
        nullable=True,
    )
    utme_score = db.Column(db.Integer, nullable=False)
    utme_subjects = db.Column(db.JSON, nullable=False, default=lambda: [])
    post_utme_score = db.Column(db.Float, nullable=True)
    post_utme_present = db.Column(db.Boolean, nullable=False, default=False)
    caps_verified = db.Column(db.Boolean, nullable=False, default=False)
    caps_verification_date = db.Column(db.DateTime, nullable=True)
    caps_verification_issues = db.Column(db.JSON, nullable=True, default=lambda: [])
    caps_status = db.Column(db.String(30), nullable=False, default="pending")
    caps_upload_id = db.Column(db.String(50), nullable=True)
    caps_uploaded_at = db.Column(db.DateTime, nullable=True)
    caps_acceptance_status = db.Column(db.String(20), nullable=True)
    caps_acceptance_date = db.Column(db.DateTime, nullable=True)
    data_verified_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    status = db.Column(db.String(30), nullable=False, default="pending")
    rejection_reasons = db.Column(db.JSON, nullable=True, default=lambda: [])
    utme_cutoff_passed = db.Column(db.Boolean, nullable=False, default=True)
    subject_combination_passed = db.Column(db.Boolean, nullable=False, default=True)
    olevel_credits_passed = db.Column(db.Boolean, nullable=False, default=True)
    olevel_sittings_passed = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    session = db.relationship("AcademicSession", back_populates="candidates")
    first_choice_programme = db.relationship(
        "Programme",
        foreign_keys=[first_choice_programme_id],
        back_populates="first_choice_candidates",
    )
    second_choice_programme = db.relationship(
        "Programme",
        foreign_keys=[second_choice_programme_id],
        back_populates="second_choice_candidates",
    )
    verified_by = db.relationship(
        "User",
        foreign_keys=[data_verified_by],
        back_populates="verified_candidates",
    )
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="candidate_profile",
        uselist=False,
    )
    olevel_results = db.relationship(
        "OLevelResult",
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    admission_records = db.relationship(
        "AdmissionRecord",
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Candidate {self.jamb_reg_number}>"


class OLevelResult(db.Model):
    __tablename__ = "olevel_results"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    exam_body = db.Column(db.String(20), nullable=False)
    exam_number = db.Column(db.String(40), nullable=False)
    exam_year = db.Column(db.Integer, nullable=False)
    sitting_number = db.Column(db.Integer, nullable=False, default=1)
    subject = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.String(5), nullable=False)

    candidate = db.relationship("Candidate", back_populates="olevel_results")

    __table_args__ = (
        db.UniqueConstraint(
            "candidate_id",
            "sitting_number",
            "subject",
            name="uq_olevel_candidate_sitting_subject",
        ),
    )

    def __repr__(self):
        return f"<OLevelResult {self.exam_body}-{self.subject}:{self.grade}>"


class AdmissionRecord(db.Model):
    __tablename__ = "admission_records"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    utme_cutoff_passed = db.Column(db.Boolean, nullable=False, default=False)
    subject_combination_passed = db.Column(db.Boolean, nullable=False, default=False)
    olevel_credits_passed = db.Column(db.Boolean, nullable=False, default=False)
    olevel_sittings_passed = db.Column(db.Boolean, nullable=False, default=False)
    quota_category = db.Column(db.String(20), nullable=True)
    jamb_component = db.Column(db.Float, nullable=False, default=0.0)
    post_utme_component = db.Column(db.Float, nullable=False, default=0.0)
    olevel_component = db.Column(db.Float, nullable=False, default=0.0)
    aggregate_score = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(30), nullable=False, default="pending")
    rejection_reason = db.Column(db.Text, nullable=True)
    dept_approved = db.Column(db.Boolean, nullable=False, default=False)
    dept_approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    dept_approved_at = db.Column(db.DateTime, nullable=True)
    faculty_approved = db.Column(db.Boolean, nullable=False, default=False)
    faculty_approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    faculty_approved_at = db.Column(db.DateTime, nullable=True)
    senate_approved = db.Column(db.Boolean, nullable=False, default=False)
    senate_approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    senate_approved_at = db.Column(db.DateTime, nullable=True)
    caps_status = db.Column(db.String(30), nullable=False, default="not_uploaded")
    caps_uploaded_at = db.Column(db.DateTime, nullable=True)
    caps_approved_at = db.Column(db.DateTime, nullable=True)
    caps_letter_generated = db.Column(db.Boolean, nullable=False, default=False)
    admitted_at = db.Column(db.DateTime, nullable=True)
    evaluation_log = db.Column(db.JSON, nullable=False, default=lambda: {})
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    candidate = db.relationship("Candidate", back_populates="admission_records")
    programme = db.relationship("Programme", back_populates="admission_records")
    session = db.relationship("AcademicSession", back_populates="admission_records")
    dept_approver = db.relationship(
        "User",
        foreign_keys=[dept_approved_by],
        back_populates="dept_approved_records",
    )
    faculty_approver = db.relationship(
        "User",
        foreign_keys=[faculty_approved_by],
        back_populates="faculty_approved_records",
    )
    senate_approver = db.relationship(
        "User",
        foreign_keys=[senate_approved_by],
        back_populates="senate_approved_records",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "candidate_id",
            "programme_id",
            "session_id",
            name="uq_admission_candidate_programme_session",
        ),
    )

    def mark_department_approval(self, user_id):
        self.dept_approved = True
        self.dept_approved_by = user_id
        self.dept_approved_at = datetime.utcnow()

    def __repr__(self):
        return f"<AdmissionRecord candidate={self.candidate_id} status={self.status}>"


class AdmissionBatch(db.Model):
    __tablename__ = "admission_batches"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_name = db.Column(db.String(80), nullable=False)
    quota_category = db.Column(db.String(20), nullable=False)
    processed_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    processed_at = db.Column(db.DateTime, nullable=True)
    total_candidates = db.Column(db.Integer, nullable=False, default=0)
    admitted_count = db.Column(db.Integer, nullable=False, default=0)
    rejected_count = db.Column(db.Integer, nullable=False, default=0)

    session = db.relationship("AcademicSession", back_populates="admission_batches")
    programme = db.relationship("Programme", back_populates="admission_batches")
    processor = db.relationship(
        "User",
        foreign_keys=[processed_by],
        back_populates="processed_batches",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "programme_id",
            "batch_name",
            "quota_category",
            name="uq_batch_session_programme_name_quota",
        ),
    )

    def update_counts(self, admitted_count):
        self.admitted_count = admitted_count
        self.rejected_count = max(self.total_candidates - admitted_count, 0)

    def __repr__(self):
        return f"<AdmissionBatch {self.batch_name}:{self.quota_category}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.JSON, nullable=False, default=lambda: {})
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type}>"


class MeritListApproval(db.Model):
    __tablename__ = "merit_list_approvals"

    id = db.Column(db.Integer, primary_key=True)
    programme_id = db.Column(
        db.Integer,
        db.ForeignKey("programmes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    department_approved = db.Column(db.Boolean, default=False, nullable=False)
    department_approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    department_approved_at = db.Column(db.DateTime, nullable=True)
    faculty_approved = db.Column(db.Boolean, default=False, nullable=False)
    faculty_approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    faculty_approved_at = db.Column(db.DateTime, nullable=True)
    senate_approved = db.Column(db.Boolean, default=False, nullable=False)
    senate_approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    senate_approved_at = db.Column(db.DateTime, nullable=True)
    finalized = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    programme = db.relationship("Programme")
    session = db.relationship("AcademicSession")
    department_approver = db.relationship(
        "User",
        foreign_keys=[department_approved_by],
        post_update=True
    )
    faculty_approver = db.relationship(
        "User",
        foreign_keys=[faculty_approved_by],
        post_update=True
    )
    senate_approver = db.relationship(
        "User",
        foreign_keys=[senate_approved_by],
        post_update=True
    )

    __table_args__ = (
        db.UniqueConstraint("programme_id", "session_id", name="uq_merit_approval_programme_session"),
    )

    def can_approve(self, user, level):
        """Check if user can approve at given level"""
        if level == "department":
            return user.role in ["admin", "admission_officer"]
        elif level == "faculty":
            return user.role in ["admin", "admission_officer", "faculty_officer"]
        elif level == "senate":
            return user.role == "admin"
        return False

    def approve(self, user, level):
        """Approve merit list at given level"""
        if not self.can_approve(user, level):
            raise PermissionError(f"User cannot approve at {level} level")
        
        if level == "department":
            self.department_approved = True
            self.department_approved_by = user.id
            self.department_approved_at = datetime.utcnow()
        elif level == "faculty":
            self.faculty_approved = True
            self.faculty_approved_by = user.id
            self.faculty_approved_at = datetime.utcnow()
        elif level == "senate":
            self.senate_approved = True
            self.senate_approved_by = user.id
            self.senate_approved_at = datetime.utcnow()
            self.finalized = True
        
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f"<MeritListApproval {self.programme.name}:{self.session.name}>"


def seed_reference_data(db_session):
    return {"elds_states_added": ELDSState.seed_defaults(db_session)}
