from celery import shared_task


@shared_task(name="process_product_data")
def process_product_data(product_data: dict):
    """Processa os dados do produto recebidos da fila."""
    print(f"Processando dados do produto: {product_data}")
    from feed.models import ProdutoMirror

    try:
        # Cria ou atualiza o ProdutoMirror
        produto_mirror, created = ProdutoMirror.objects.update_or_create(
            sku=product_data["sku"],
            defaults={
                "nome": product_data["nome"],
                "descricao": product_data["descricao"],
                "preco": product_data["preco"],
                "estoque": product_data["estoque"],
            },
        )

        action = "criado" if created else "atualizado"
        print(f"ProdutoMirror {action}: {produto_mirror}")

    except Exception as e:
        print(f"Erro ao processar produto: {e!s}")
        raise
