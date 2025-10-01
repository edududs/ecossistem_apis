from django.db.models.signals import post_save
from django.dispatch import receiver

from produto.models import Produto


@receiver(post_save, sender=Produto)
def create_produto(sender, instance, created, **kwargs):
    from produto.kiwi.publisher import send_product

    print(f"\nPassando dentro do Signal.\nInstância: {instance}\nCriada: {created}")
    if created:
        print(f"Produto criado: {instance}")
        send_product(instance)
