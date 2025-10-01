import celery
from django_tools.utils import setup_django_if_needed

setup_django_if_needed()

celery_app = celery.Celery("feed")

celery_app.config_from_object("django.conf:settings", namespace="CELERY")

celery_app.autodiscover_tasks()

__all__ = ("celery_app",)
