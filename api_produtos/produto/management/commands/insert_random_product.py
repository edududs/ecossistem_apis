from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Insert random product"

    def handle(self, *args, **options):
        """Inserts a randomly generated Produto into the database."""
        import logging
        import random
        import string

        from produto.models import Produto

        logger = logging.getLogger(__name__)

        def random_string(length=10):
            """Generate a random string of fixed length."""
            return "".join(random.choices(string.ascii_letters + string.digits, k=length))

        def random_sku():
            """Generate a random SKU (integer between 10000 and 99999)."""
            return random.randint(10000, 99999)

        def random_price():
            """Generate a random price between 10.00 and 1000.00."""
            return round(random.uniform(10.0, 1000.0), 2)

        def random_stock():
            """Generate a random stock quantity between 0 and 500."""
            return random.randint(0, 500)

        product_data = {
            "sku": random_sku(),
            "nome": f"Product {random_string(6)}",
            "descricao": f"Description {random_string(20)}",
            "preco": random_price(),
            "estoque": random_stock(),
        }

        produto = Produto.objects.create(**product_data)
        logger.info(f"Inserted random product: {produto}")

        self.stdout.write(self.style.SUCCESS(f"Inserted random product: {produto}"))
