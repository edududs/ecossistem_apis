# CQRS com Django e RabbitMQ

## Visão Geral

Este guia documenta a implementação de **CQRS (Command Query Responsibility Segregation)** utilizando `django-cqrs`, RabbitMQ e Redis em um ecossistema de microsserviços Django.

### Tecnologias Utilizadas

- **django-cqrs**: Framework para replicação de dados entre serviços
- **RabbitMQ**: Message broker para comunicação assíncrona
- **Redis**: Backend para resultados do Celery e cache
- **Celery**: Task queue para processamento assíncrono
- **Django**: Framework web para APIs

### Arquitetura

```
┌─────────────────────┐         ┌─────────────────────┐
│   API Produtos      │         │     API Feed        │
│   (Master)          │         │     (Replica)       │
├─────────────────────┤         ├─────────────────────┤
│ Produto Model       │         │ ProdutoMirror Model │
│ + MasterMixin       │         │ + ReplicaMixin      │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           │ Publish                       │ Consume
           ▼                               ▼
    ┌─────────────────────────────────────────┐
    │           RabbitMQ                      │
    │  ┌──────────────┐    ┌──────────────┐   │
    │  │ Exchange:    │───▶│ Queue:       │   │
    │  │ cqrs (topic) │    │ feed_replica │   │
    │  └──────────────┘    └──────┬───────┘   │
    │                             │           │
    │                             ▼           │
    │                      ┌──────────────┐   │
    │                      │ DLQ:         │   │
    │                      │ dead_letter_ │   │
    │                      │ feed_replica │   │
    │                      └──────────────┘   │
    └─────────────────────────────────────────┘
```

## Instalação e Configuração

### 1. Dependências

Adicione ao `pyproject.toml`:

```toml
dependencies = [
    "django>=5.2.6",
    "django-cqrs>=2.8.1",
    "celery>=5.5.3",
    "redis>=6.4.0",
    "pydantic>=2.11.9",
]
```

### 2. Configuração do Master Service (API Produtos)

#### settings.py

```python
from pathlib import Path
from django_tools.settings import DjangoSettings

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = f"{BASE_DIR}/.env.produtos"

base_settings = DjangoSettings(env_file=ENV_FILE)

# Django Apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "produto",
    "dj_cqrs",  # ← Adicionar
]

# CQRS Configuration
CQRS = {
    "transport": "dj_cqrs.transport.RabbitMQTransport",
    "url": base_settings.effective_broker_url,
}

# Celery Configuration
for key, value in base_settings.celery_config.items():
    celery_key = f"CELERY_{key.upper()}"
    globals()[celery_key] = value

# Redis Configuration
for key, value in base_settings.redis_config.items():
    redis_key = f"REDIS_{key.upper()}"
    globals()[redis_key] = value
```

#### models.py (Master)

```python
from dj_cqrs.mixins import MasterMixin
from django.db import models

class Produto(MasterMixin, models.Model):
    CQRS_ID = "produto"  # Identificador único para replicação
    
    sku = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=255)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nome} - {self.preco}"
```

#### Migrations

```bash
cd api_produtos
python manage.py makemigrations
python manage.py migrate
```

### 3. Configuração do Replica Service (API Feed)

#### settings.py

```python
from pathlib import Path
from django_tools.settings import DjangoSettings

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = f"{BASE_DIR}/.env.feed"

base_settings = DjangoSettings(env_file=ENV_FILE)

# Django Apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "feed",
    "dj_cqrs",  # ← Adicionar
]

# CQRS Configuration
CQRS = {
    "transport": "dj_cqrs.transport.RabbitMQTransport",
    "url": base_settings.effective_broker_url,
    "queue": "feed_replica",  # ← Nome único da queue
    "replica": {
        # Retry Configuration
        "CQRS_MAX_RETRIES": 3,
        "CQRS_RETRY_DELAY": 5,
        "CQRS_DELAY_QUEUE_MAX_SIZE": 1000,
        
        # Dead Letter Queue Configuration
        "dead_letter_queue": "dead_letter_feed_replica",
        "dead_message_ttl": 604800,  # 7 dias em segundos
    },
}

# Celery Configuration
for key, value in base_settings.celery_config.items():
    celery_key = f"CELERY_{key.upper()}"
    globals()[celery_key] = value

# Redis Configuration
for key, value in base_settings.redis_config.items():
    redis_key = f"REDIS_{key.upper()}"
    globals()[redis_key] = value

# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": base_settings.effective_redis_url,
        "KEY_PREFIX": "feed_cache",
        "TIMEOUT": 300,
    }
}
```

#### models.py (Replica)

```python
from dj_cqrs.mixins import ReplicaMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models

class ProdutoMirror(ReplicaMixin, models.Model):
    """Replica do modelo Produto da API de Produtos.
    
    Características:
    - Replicação automática via CQRS
    - Retry com backoff exponencial
    - Dead Letter Queue para falhas
    - Idempotência garantida via cqrs_revision
    """
    
    CQRS_ID = "produto"  # ← Deve ser igual ao Master
    
    # Mapeamento de campos Master → Replica
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
    
    def __str__(self):
        return f"{self.nome} - {self.preco}"
    
    @classmethod
    def get_cqrs_retry_delay(cls, current_retry: int) -> int:
        """Define intervalo entre retries com backoff exponencial.
        
        Args:
            current_retry: Número da tentativa atual (0-indexed)
            
        Returns:
            Intervalo em segundos (máximo 60s)
        """
        return min(2 ** current_retry, 60)
    
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
```

#### Migrations

```bash
cd api_feed
python manage.py makemigrations
python manage.py migrate
```

### 4. Variáveis de Ambiente

Crie arquivos `.env.produtos` e `.env.feed`:

```bash
# .env.produtos
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,0.0.0.0,127.0.0.1
API_NAME=PRODUTOS

# Broker Configuration (RabbitMQ)
BROKER_HOST=localhost
BROKER_PORT=5672
BROKER_USER=admin
BROKER_PASSWORD=admin
BROKER_VHOST=/

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Celery Configuration
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

```bash
# .env.feed
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,0.0.0.0,127.0.0.1
API_NAME=FEED

# Broker Configuration (RabbitMQ)
BROKER_HOST=localhost
BROKER_PORT=5672
BROKER_USER=admin
BROKER_PASSWORD=admin
BROKER_VHOST=/

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Celery Configuration
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## Uso

### Iniciando os Serviços

#### Terminal 1: RabbitMQ e Redis

```bash
docker-compose up -d
```

#### Terminal 2: API Produtos (Master)

```bash
cd api_produtos
uv run manage.py runserver 0:8001
```

#### Terminal 3: API Feed (Replica)

```bash
cd api_feed
uv run manage.py runserver 0:8000
```

#### Terminal 4: Consumer CQRS

```bash
cd api_feed
uv run manage.py cqrs_consume -w 2
```

### Testando a Replicação

#### Criar um Produto

```bash
cd api_produtos
uv run manage.py shell -i ipython
```

```python
from produto.models import Produto

# Criar produto
produto = Produto.objects.create(
    sku=12345,
    nome="Notebook Dell",
    descricao="Notebook Dell Inspiron 15",
    preco=3500.00,
    estoque=10
)

# Logs esperados:
# INFO CQRS is published: pk = 12345 (produto), correlation_id = <UUID>
```

#### Verificar Replicação

```bash
cd api_feed
uv run manage.py shell -i ipython
```

```python
from feed.models import ProdutoMirror

# Verificar produto replicado
ProdutoMirror.objects.all()
# Output: <QuerySet [<ProdutoMirror: Notebook Dell - 3500.00>]>

# Verificar campos
produto = ProdutoMirror.objects.get(sku=12345)
print(f"Nome: {produto.nome}")
print(f"Preço: {produto.preco}")
print(f"Estoque: {produto.estoque}")
print(f"Revisão CQRS: {produto.cqrs_revision}")
```

## Retry e Dead Letter Queue

### Funcionamento do Retry

Quando uma mensagem falha no processamento, o django-cqrs aplica retry automático:

```
Tentativa 1 → Falha → Aguarda 2s  (backoff: 2^1)
Tentativa 2 → Falha → Aguarda 4s  (backoff: 2^2)
Tentativa 3 → Falha → Aguarda 8s  (backoff: 2^3)
Tentativa 4 → Falha → Move para DLQ
```

### Configuração de Retry

```python
CQRS = {
    "replica": {
        "CQRS_MAX_RETRIES": 3,        # Número máximo de tentativas
        "CQRS_RETRY_DELAY": 5,        # Intervalo inicial (sobrescrito por get_cqrs_retry_delay)
        "CQRS_DELAY_QUEUE_MAX_SIZE": 1000,
    },
}
```

### Estratégias de Retry

#### 1. Retry Simples (Fixo)

```python
# Usar apenas configuração no settings.py
CQRS_MAX_RETRIES = 3
CQRS_RETRY_DELAY = 5  # Sempre 5 segundos
```

#### 2. Backoff Exponencial

```python
@classmethod
def get_cqrs_retry_delay(cls, current_retry: int) -> int:
    """Dobra o tempo a cada tentativa."""
    return min(2 ** current_retry, 60)  # Máximo 60s
```

#### 3. Backoff Linear

```python
@classmethod
def get_cqrs_retry_delay(cls, current_retry: int) -> int:
    """Aumenta linearmente o tempo."""
    return min(current_retry * 5, 60)  # 5s, 10s, 15s, 20s...
```

#### 4. Retry Seletivo por Exceção

```python
@classmethod
def should_retry_cqrs(cls, current_retry: int, exception: Exception) -> bool:
    """Decide retry baseado no tipo de erro."""
    
    # Nunca fazer retry para erros de lógica
    if isinstance(exception, (ValueError, ValidationError)):
        return False
    
    # Mais tentativas para erros de rede
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return current_retry < 5
    
    # Menos tentativas para outros erros
    return current_retry < 3
```

### Dead Letter Queue (DLQ)

A DLQ armazena mensagens que falharam após todas as tentativas de retry.

#### Comandos de Gerenciamento

```bash
# Ver mensagens na DLQ
python manage.py cqrs_dead_letters dump

# Reprocessar todas as mensagens
python manage.py cqrs_dead_letters retry

# Reprocessar mensagens específicas
python manage.py cqrs_dead_letters retry --cqrs-id produto

# Limpar DLQ
python manage.py cqrs_dead_letters purge

# Limpar mensagens específicas
python manage.py cqrs_dead_letters purge --cqrs-id produto
```

#### Verificar DLQ no RabbitMQ

Acesse: `http://localhost:15672` (admin/admin)

- **Queues** → `dead_letter_feed_replica`
- Verifique número de mensagens
- Inspecione detalhes das mensagens falhadas

## Idempotência

O django-cqrs garante idempotência automaticamente através do campo `cqrs_revision`:

### Como Funciona

```python
# Master: cqrs_revision = 1
Produto.objects.create(sku=1, nome="A", preco=100)
# → Publica evento com revision=1

# Replica: cqrs_revision = 1
ProdutoMirror criado com dados do evento

# Master: cqrs_revision = 2
Produto.objects.filter(sku=1).update(preco=150)
# → Publica evento com revision=2

# Replica: cqrs_revision = 2
ProdutoMirror atualizado (revision 1 → 2)

# Reprocessamento do evento revision=1
# → Ignorado (revision atual = 2 > 1)
```

### Benefícios

- ✅ Mensagens duplicadas são automaticamente ignoradas
- ✅ Ordem de processamento não importa (última versão prevalece)
- ✅ Reprocessamento da DLQ é seguro
- ✅ Não precisa implementar lógica customizada

## Monitoramento

### RabbitMQ Management

Acesse: `http://localhost:15672` (admin/admin)

#### Exchanges

```
cqrs (type: topic)
└── Bindings
    └── feed_replica (routing_key: produto)
```

#### Queues

```
feed_replica
├── Ready: Mensagens aguardando processamento
├── Unacked: Mensagens em processamento
└── Total: Total de mensagens

dead_letter_feed_replica
├── Ready: Mensagens falhadas
└── TTL: 7 dias
```

#### Métricas Importantes

- **Message rate**: Taxa de mensagens/segundo
- **Consumer utilization**: Utilização dos consumers (ideal: 70-90%)
- **Ready messages**: Deve ser próximo de 0 em operação normal
- **Unacked messages**: Deve ser baixo (indica processamento lento)

### Logs de Aplicação

#### Logs do Consumer

```bash
cd api_feed
uv run manage.py cqrs_consume -w 2 --verbosity 2
```

**Logs esperados:**

```
INFO Consumer process with pid 12345 started
INFO Pika version 1.3.2 connecting to ('localhost', 5672)
INFO Created channel=1
INFO Created new queue consumer generator <_QueueConsumerGeneratorInfo params=('feed_replica', False, False)>
INFO Successfully replicated produto with pk=12345
```

#### Logs de Retry

```
INFO Retry 1/3 for produto pk=12345, waiting 2s
INFO Retry 2/3 for produto pk=12345, waiting 4s
INFO Retry 3/3 for produto pk=12345, waiting 8s
WARNING Moving message to dead letter queue: produto pk=12345
```

## Troubleshooting

### Problema: Queue não é criada

**Sintoma**: Exchange `cqrs` existe, mas queue `feed_replica` não aparece no RabbitMQ.

**Causa**: Queue só é criada quando o consumer inicia.

**Solução**:

```bash
# Iniciar consumer
cd api_feed
uv run manage.py cqrs_consume -w 2
```

### Problema: Mensagens não são consumidas

**Sintoma**: Mensagens aparecem na exchange mas não chegam na queue.

**Causas possíveis**:

1. `CQRS_ID` diferente entre Master e Replica
2. Binding incorreto no RabbitMQ
3. Consumer não está rodando

**Solução**:

```python
# Verificar CQRS_ID
# Master
class Produto(MasterMixin, models.Model):
    CQRS_ID = "produto"  # ← Deve ser igual

# Replica
class ProdutoMirror(ReplicaMixin, models.Model):
    CQRS_ID = "produto"  # ← Deve ser igual
```

### Problema: Campos não são replicados

**Sintoma**: Produto é criado na replica mas alguns campos estão vazios.

**Causa**: Campos não mapeados em `CQRS_MAPPING`.

**Solução**:

```python
class ProdutoMirror(ReplicaMixin, models.Model):
    CQRS_MAPPING = {
        "sku": "sku",
        "nome": "nome",
        "descricao": "descricao",
        "preco": "preco",
        "estoque": "estoque",
        # ← Adicionar todos os campos necessários
    }
```

**Observação**: Campos `criado_em` e `atualizado_em` do Master não são replicados. O django-cqrs usa seus próprios campos: `cqrs_revision` e `cqrs_updated`.

### Problema: URL do broker está None

**Sintoma**: Erro ao iniciar: `'url': None` na configuração CQRS.

**Causa**: Variáveis de ambiente não configuradas.

**Solução**:

```bash
# Adicionar no .env
BROKER_HOST=localhost
BROKER_PORT=5672
BROKER_USER=admin
BROKER_PASSWORD=admin
BROKER_VHOST=/
```

E usar `effective_broker_url` no settings:

```python
CQRS = {
    "url": base_settings.effective_broker_url,  # ← Não usar broker_url
}
```

### Problema: Consumer consome mas não processa

**Sintoma**: Mensagens saem da queue mas não aparecem no banco.

**Causa**: Exceção silenciosa no processamento.

**Solução**:

```bash
# Rodar consumer com verbosidade máxima
uv run manage.py cqrs_consume -w 1 --verbosity 2

# Verificar logs de erro
# Adicionar try/except no modelo se necessário
```

## Comandos Úteis

### Gerenciamento de Dados

```bash
# Limpar produtos no Master
cd api_produtos
uv run manage.py shell -c "from produto.models import Produto; Produto.objects.all().delete()"

# Limpar produtos na Replica
cd api_feed
uv run manage.py shell -c "from feed.models import ProdutoMirror; ProdutoMirror.objects.all().delete()"

# Verificar configuração CQRS
uv run manage.py shell -c "from django.conf import settings; print(settings.CQRS)"
```

### Logs Detalhados

```bash
# Consumer com verbosidade máxima
uv run manage.py cqrs_consume -w 2 --verbosity 2

# Ver apenas mensagens de erro
uv run manage.py cqrs_consume -w 2 2>&1 | grep -i error
```

### Testes de Integração

```bash
# Script para testar replicação completa
cd api_produtos
uv run manage.py shell << EOF
from produto.models import Produto
p = Produto.objects.create(sku=999, nome="Test", descricao="Test", preco=100, estoque=10)
print(f"Created: {p}")
EOF

cd api_feed
uv run manage.py shell << EOF
from feed.models import ProdutoMirror
import time
time.sleep(2)  # Aguardar replicação
p = ProdutoMirror.objects.get(sku=999)
print(f"Replicated: {p}")
EOF
```

## Boas Práticas

### 1. Configuração de Retry

- Use **3-5 retries** para a maioria dos casos
- Implemente **backoff exponencial** para evitar sobrecarga
- Configure **TTL adequado** na DLQ (7-30 dias)
- Não faça retry para erros de validação/lógica

### 2. Modelagem

- Mantenha `CQRS_ID` único e descritivo
- Documente o `CQRS_MAPPING` claramente
- Não replique campos auto-gerados (`criado_em`, `atualizado_em`)
- Use campos do django-cqrs para tracking (`cqrs_revision`, `cqrs_updated`)

### 3. Monitoramento

- Configure alertas quando DLQ > 10 mensagens
- Monitore taxa de falhas (> 5% indica problema)
- Revise DLQ regularmente
- Configure dashboards no RabbitMQ Management

### 4. Operação

- Use múltiplos workers em produção (`-w 4` ou mais)
- Configure health checks no consumer
- Implemente graceful shutdown
- Faça backup regular das configurações

### 5. Segurança

- Nunca exponha credenciais no código
- Use variáveis de ambiente para configurações
- Configure SSL/TLS para RabbitMQ em produção
- Limite acesso ao RabbitMQ Management

## Referências

- [django-cqrs Documentation](https://django-cqrs.readthedocs.io/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/tutorials)
- [Celery Documentation](https://docs.celeryproject.org/)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)

---

**Versão**: 1.0  
**Data**: Outubro 2025  
**Branch**: `cqrs`  
**Autor**: Lab APIs Ecosystem
