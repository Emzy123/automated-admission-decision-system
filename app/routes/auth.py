from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app import db
from app.models import Faculty, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class RegisterUserForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=3, max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField(
        "Role",
        choices=[
            ("admin", "Administrator"),
            ("faculty_officer", "Faculty Officer"),
            ("admission_officer", "Admission Officer"),
        ],
        validators=[DataRequired()],
    )
    faculty_id = SelectField("Faculty (optional)", coerce=int, validators=[Optional()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


@auth_bp.route("/")
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Deprecated auth login endpoint, redirect to home page
    return redirect(url_for("index"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
@admin_required
def register():
    form = RegisterUserForm()
    faculty_choices = [(0, "Not Assigned")]
    faculty_choices.extend(
        (faculty.id, f"{faculty.name} ({faculty.code})")
        for faculty in Faculty.query.order_by(Faculty.name).all()
    )
    form.faculty_id.choices = faculty_choices

    if form.validate_on_submit():
        existing_user = User.query.filter(
            (User.username == form.username.data.strip())
            | (User.email == form.email.data.strip().lower())
        ).first()

        if existing_user:
            flash("Username or email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        new_user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
            faculty_id=form.faculty_id.data or None,
            is_active=True,
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash("User account created successfully.", "success")
        return redirect(url_for("auth.register"))

    return render_template("auth/register.html", form=form)
