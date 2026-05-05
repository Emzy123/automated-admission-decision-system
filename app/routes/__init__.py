from app.routes.admin import admin_bp
from app.routes.admission import admission_bp
from app.routes.api import api_bp
from app.routes.reports import reports_bp
from app.routes.auth import auth_bp
from app.routes.candidate import candidate_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admission_bp, url_prefix="/admission")
    app.register_blueprint(api_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(candidate_bp)

__all__ = ["auth_bp", "admin_bp", "admission_bp", "api_bp", "reports_bp", "candidate_bp", "register_blueprints"]
