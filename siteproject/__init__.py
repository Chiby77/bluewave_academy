# Make the Celery app available when Django starts (required for @shared_task)
try:
    from .celery import app as celery_app  # noqa: F401
    __all__ = ("celery_app",)
except ImportError:
    celery_app = None
    __all__ = ()
