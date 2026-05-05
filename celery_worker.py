"""
Celery Worker Entry Point
Run with:
    celery -A celery_worker.celery worker --loglevel=info

Or start Flower monitoring dashboard with:
    celery -A celery_worker.celery flower --port=5555
"""
from app import create_app
from app.celery_app import make_celery

flask_app = create_app()
celery = make_celery(flask_app)

# Ensure tasks are registered with this Celery instance
import app.tasks  # noqa: F401, E402
