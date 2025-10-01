from core.celery import celery_app

from produto.models import Produto


def send_product(product: Produto):
    print(f"\n\nEnviando dados para fanout exchange: {product}\n\n")

    # Usa fanout exchange - não precisa especificar queue específica
    celery_app.send_task(
        "process_product_data",
        args=[product.to_dict()],
        exchange="product",
        queue="product_reply",
        routing_key="product_reply",  # Padrão específico
    )
