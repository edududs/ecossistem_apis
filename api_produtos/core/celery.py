from django_tools.utils import setup_django_if_needed

setup_django_if_needed()

from django_tools.kiwi import app as celery_app

__all__ = ("celery_app",)
