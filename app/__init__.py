import os

from flask import Flask, render_template, redirect
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "index"
login_manager.login_message_category = "warning"
login_manager.login_message = "Please sign in to continue."

# Global celery instance — initialised inside create_app()
celery = None


def create_app(config_name=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="static",
        template_folder="templates",
    )

    selected_config = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config.get(selected_config, config["default"]))

    os.makedirs(app.instance_path, exist_ok=True)
    configure_upload_folder(app)
    initialize_extensions(app)

    from app.routes import register_blueprints
    register_blueprints(app)

    from app.models import Programme, Faculty, AcademicSession
    
    @app.context_processor
    def inject_global_stats():
        if not hasattr(app, '_database_initialized'):
            try:
                # Basic check to avoid errors during initial migration
                active_session = AcademicSession.query.filter_by(is_active=True).first()
                total_progs = Programme.query.count()
                total_facs = Faculty.query.count()
                return {
                    'global_active_session': active_session,
                    'global_total_programmes': total_progs,
                    'global_total_faculties': total_facs
                }
            except Exception:
                return {
                    'global_active_session': None,
                    'global_total_programmes': 0,
                    'global_total_faculties': 0
                }
        return {}

    # Add root route
    @app.route('/', methods=['GET', 'POST'])
    def index():
        from flask_login import current_user, login_user
        from flask import request, flash
        from app.models import Programme, Faculty, Candidate, User
        from app.routes.auth import LoginForm
        
        if current_user.is_authenticated:
            if getattr(current_user, 'role', '') == 'candidate':
                return redirect('/candidate/dashboard')
            return redirect('/admin/dashboard')
            
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            password = form.password.data
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=form.remember_me.data)
                flash("Welcome back.", "success")
                if getattr(user, 'role', '') == 'candidate':
                    return redirect('/candidate/dashboard')
                return redirect('/admin/dashboard')
            else:
                flash("Invalid username or password.", "danger")
                # When login fails, render the home page with the modal automatically open (via JS/Jinja logic)
            
        try:
            programmes_count = Programme.query.count() or 40
            candidates_count = Candidate.query.count() or 1250
            faculties_count = Faculty.query.count() or 7
        except Exception:
            programmes_count = 40
            candidates_count = 1250
            faculties_count = 7
            
        return render_template('home.html',
                             form=form,
                             programmes_count=programmes_count,
                             candidates_count=candidates_count,
                             faculties_count=faculties_count)

    register_error_handlers(app)
    register_cli_commands(app)

    # Initialise Celery and bind it to this Flask app
    global celery  # noqa: PLW0603
    from app.celery_app import make_celery
    celery = make_celery(app)

    return app

def configure_upload_folder(app):
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    upload_folder = os.path.abspath(upload_folder)
    app.config["UPLOAD_FOLDER"] = upload_folder
    os.makedirs(upload_folder, exist_ok=True)


def initialize_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def register_cli_commands(app):
    from app.utils.seed import register_cli_commands as register_seed_commands
    
    # Register seed commands
    register_seed_commands(app)
