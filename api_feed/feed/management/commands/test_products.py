from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test products"

    def handle(self, *args, **options):
        import requests

        response = requests.get("http://0.0.0.0:8001/", timeout=5)
        if response.status_code == 200:
            print(response.text)
        else:
            print(response.status_code)
