# APIs Ecosystem - Laboratory

Laboratório de experimentação para padrões de comunicação assíncrona entre microsserviços Django.

## Objetivo

Este projeto simula um ecossistema de microsserviços onde múltiplas APIs Django se comunicam de forma assíncrona através de RabbitMQ, Redis e Celery, explorando diferentes padrões arquiteturais.

## Estrutura do Projeto

```
apis_ecossistem/
├── api_produtos/          # API Master - Gerencia produtos
│   └── produto/           # App com modelo Produto
├── api_feed/              # API Replica - Feed de produtos
│   └── feed/              # App com modelo ProdutoMirror
├── django_tools/          # Biblioteca compartilhada (git submodule)
├── docker-compose.yaml    # RabbitMQ e Redis
└── CQRS.md               # Documentação CQRS completa
```

## Branches

Este repositório contém diferentes implementações de padrões arquiteturais:

### `main`

Implementação básica com Celery tasks diretas.

### `cqrs` ⭐

Implementação de **CQRS (Command Query Responsibility Segregation)** utilizando `django-cqrs`.

**Características:**

- Replicação automática de dados entre APIs
- Retry com backoff exponencial
- Dead Letter Queue (DLQ) para falhas
- Idempotência garantida
- Monitoramento via RabbitMQ Management

**Documentação completa**: [CQRS.md](./CQRS.md)

## Quick Start

### 1. Pré-requisitos

- Python 3.12+
- uv (gerenciador de pacotes)
- Docker e Docker Compose

### 2. Instalar dependências

```bash
uv sync
```

### 3. Iniciar infraestrutura

```bash
docker-compose up -d
```

### 4. Configurar variáveis de ambiente

Crie os arquivos `.env.produtos` e `.env.feed` (veja exemplos em `CQRS.md`).

### 5. Rodar migrations

```bash
cd api_produtos && uv run manage.py migrate
cd api_feed && uv run manage.py migrate
```

### 6. Iniciar serviços

```bash
# Terminal 1: API Produtos
cd api_produtos && uv run manage.py runserver 0:8001

# Terminal 2: API Feed
cd api_feed && uv run manage.py runserver 0:8000

# Terminal 3: Consumer (apenas na branch cqrs)
cd api_feed && uv run manage.py cqrs_consume -w 2
```

## Tecnologias

- **Django 5.2**: Framework web
- **Django Ninja**: API REST framework
- **RabbitMQ**: Message broker
- **Redis**: Cache e backend do Celery
- **Celery**: Task queue
- **django-cqrs**: Framework CQRS (branch `cqrs`)
- **Pydantic**: Validação de dados

## Documentação

- [CQRS.md](./CQRS.md) - Documentação completa do padrão CQRS
- [CURRENT_TASK.md](./CURRENT_TASK.md) - Plano de implementação e roadmap

## Monitoramento

- **RabbitMQ Management**: <http://localhost:15672> (admin/admin)
- **API Produtos**: <http://localhost:8001>
- **API Feed**: <http://localhost:8000>

## Comandos Úteis

```bash
# Ver queues e mensagens
uv run manage.py cqrs_dead_letters dump

# Reprocessar DLQ
uv run manage.py cqrs_dead_letters retry

# Shell interativo
uv run manage.py shell -i ipython
```

## Contribuição

Este é um projeto de laboratório. Sinta-se livre para:

- Explorar diferentes implementações
- Criar novas branches com padrões alternativos
- Documentar descobertas e learnings

## License

MIT
