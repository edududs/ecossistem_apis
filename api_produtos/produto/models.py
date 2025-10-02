from dj_cqrs.mixins import MasterMixin
from django.db import models
from django.db.models import Manager


# Create your models here.
class Produto(MasterMixin, models.Model):
    CQRS_ID = "produto"
    sku = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=255)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

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
            "criado_em": self.criado_em,
            "atualizado_em": self.atualizado_em,
        }
