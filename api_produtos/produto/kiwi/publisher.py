from core.celery import celery_app

from produto.models import Produto


def send_product(product: Produto):
    celery_app.send_task(
        "process_product_data",
        args=[product.to_dict()],
        exchange="product_events",
        queue="product_reply",
    )
    print(f"\n\nProduto enviado para a fila: {product}")
