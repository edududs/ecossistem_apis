from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica a saúde do RabbitMQ através do Celery"

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout", type=int, default=10, help="Timeout para conexão em segundos (padrão: 10)"
        )
        parser.add_argument(
            "--check-queues",
            action="store_true",
            help="Verifica se as filas existem e estão acessíveis",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        """Executa verificações de saúde do RabbitMQ via Celery."""
        import logging

        logger = logging.getLogger(__name__)
        timeout = options["timeout"]
        check_queues = options["check_queues"]

        try:
            from core.celery import celery_app

            self.stdout.write("🔍 Iniciando verificação de saúde do RabbitMQ...")
            self.stdout.write("=" * 50)

            # 1. Verificar configurações do Celery
            self._check_celery_config(celery_app)

            # 2. Testar conexão com o broker
            self._check_broker_connection(celery_app, timeout)

            # 3. Verificar filas (se solicitado)
            if check_queues:
                self._check_queues(celery_app)

            # 4. Teste de ping
            self._test_ping(celery_app)

            self.stdout.write("=" * 50)
            self.stdout.write(self.style.SUCCESS("✅ RabbitMQ está saudável e funcionando!"))

        except Exception as e:
            self.stdout.write("=" * 50)
            self.stdout.write(self.style.ERROR(f"❌ Falha na verificação: {e}"))
            logger.exception("RabbitMQ health check failed")
            return

    def _check_celery_config(self, celery_app):
        """Verifica as configurações do Celery."""
        self.stdout.write("📋 Verificando configurações do Celery...")

        broker_url = celery_app.conf.broker_url
        result_backend = celery_app.conf.result_backend
        broker_transport_options = celery_app.conf.broker_transport_options

        self.stdout.write(f"  Broker URL: {broker_url}")
        self.stdout.write(f"  Result Backend: {result_backend}")
        self.stdout.write(f"  Transport Options: {broker_transport_options}")

        if not broker_url or broker_url == "memory://":
            msg = "Broker URL não configurado ou usando memória"
            raise ValueError(msg)

        self.stdout.write(self.style.SUCCESS("  ✅ Configurações OK"))

    def _check_broker_connection(self, celery_app, timeout):
        """Testa a conexão com o broker."""
        import time

        self.stdout.write("🔌 Testando conexão com o broker...")

        start_time = time.time()

        try:
            with celery_app.connection() as connection:
                connection.ensure_connection(max_retries=3, timeout=timeout)

                elapsed = time.time() - start_time
                self.stdout.write(f"  ✅ Conexão estabelecida em {elapsed:.2f}s")

        except Exception as e:
            msg = f"Falha na conexão com o broker: {e}"
            raise ConnectionError(msg) from e

    def _check_queues(self, celery_app):
        """Verifica se as filas existem e estão acessíveis."""
        self.stdout.write("📦 Verificando filas...")

        try:
            with celery_app.connection() as connection, connection.channel() as channel:
                # Lista filas disponíveis
                # Tenta declarar uma fila de teste
                test_queue = channel.queue_declare("health_check_test", passive=False)
                self.stdout.write(f"  ✅ Fila de teste criada: {test_queue.method.queue}")

                # Remove a fila de teste
                channel.queue_delete("health_check_test")
                self.stdout.write("  ✅ Fila de teste removida")

        except Exception as e:
            msg = f"Falha ao verificar filas: {e}"
            raise RuntimeError(msg) from e

    def _test_ping(self, celery_app):
        """Executa um ping para testar a comunicação."""
        self.stdout.write("🏓 Testando ping...")

        try:
            # Usa o método ping do Celery
            result = celery_app.control.ping(timeout=5)

            if result:
                self.stdout.write(f"  ✅ Ping bem-sucedido: {len(result)} workers respondendo")
                for worker, response in result.items():
                    self.stdout.write(f"    - {worker}: {response}")
            else:
                self.stdout.write("  ⚠️ Nenhum worker ativo encontrado")

        except Exception as e:
            self.stdout.write(f"  ⚠️ Ping falhou: {e}")
            # Não falha o teste completo, apenas avisa
