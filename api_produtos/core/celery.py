import celery

celery_app = celery.Celery("produtos")

celery_app.config_from_object("django.conf:settings", namespace="CELERY")

celery_app.autodiscover_tasks()

__all__ = ("celery_app",)
