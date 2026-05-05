"""
Celery Application Factory
Binds Celery to the Flask application context so tasks can access DB.
"""
import logging
from celery import Celery

logger = logging.getLogger(__name__)


def make_celery(app):
    """Create and configure a Celery instance bound to the Flask app."""
    celery = Celery(
        app.import_name,
        broker=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )

    # Pull celery-prefixed keys from Flask config
    celery.conf.update(
        task_serializer=app.config.get("CELERY_TASK_SERIALIZER", "json"),
        result_serializer=app.config.get("CELERY_RESULT_SERIALIZER", "json"),
        accept_content=app.config.get("CELERY_ACCEPT_CONTENT", ["json"]),
        task_always_eager=app.config.get("CELERY_TASK_ALWAYS_EAGER", False),
        task_eager_propagates=app.config.get("CELERY_TASK_EAGER_PROPAGATES", True),
        task_track_started=True,
        result_expires=3600,  # Results expire after 1 hour
    )

    # Ensure tasks run inside Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Auto-discover tasks module
    celery.autodiscover_tasks(["app"])

    return celery
