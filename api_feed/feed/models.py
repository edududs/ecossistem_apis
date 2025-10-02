from dj_cqrs.mixins import ReplicaMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.db.models import Manager


class ProdutoMirror(ReplicaMixin, models.Model):
    """Replica do modelo Produto da API de Produtos.

    Este modelo replica dados via CQRS (django-cqrs) e inclui:
    - Retry com backoff exponencial
    - Dead Letter Queue para mensagens falhadas
    - Idempotência garantida via cqrs_revision
    """

    CQRS_ID = "produto"
    CQRS_MAPPING = {
        "sku": "sku",
        "nome": "nome",
        "descricao": "descricao",
        "preco": "preco",
        "estoque": "estoque",
    }

    sku = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=255)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField()

    objects = Manager()

    def __str__(self):
        return f"{self.nome} - {self.preco}"

    def to_dict(self):
        return {
            "sku": self.sku,
            "nome": self.nome,
            "descricao": self.descricao,
            "preco": self.preco,
            "estoque": self.estoque,
        }

    @classmethod
    def get_cqrs_retry_delay(cls, current_retry: int) -> int:
        """Define o intervalo entre retries com backoff exponencial.

        Args:
            current_retry: Número da tentativa atual (0-indexed)

        Returns:
            Intervalo em segundos (máximo 60s)

        """
        return min(2**current_retry, 60)

    @classmethod
    def should_retry_cqrs(cls, current_retry: int, exception: Exception) -> bool:
        """Decide se deve fazer retry baseado no tipo de exceção.

        Args:
            current_retry: Número da tentativa atual
            exception: Exceção que ocorreu

        Returns:
            True se deve fazer retry, False caso contrário

        """
        # Não fazer retry para erros de validação ou integridade
        if isinstance(exception, (ValueError, ValidationError, IntegrityError)):
            return False

        # Fazer retry para erros de rede/timeout (até 5 tentativas)
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return current_retry < 5

        # Default: retry até 3 tentativas
        return current_retry < 3
