from django.conf import settings  # noqa: F401
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica a conexão com o broker do Celery (RabbitMQ)"

    def handle(self, *args, **options):
        """Testa a conectividade com o broker configurado no Celery.

        Antes de testar, exibe as variáveis de configuração relevantes.
        """
        try:
            from core.celery import celery_app

            broker_url = celery_app.conf.broker_url
            result_backend = celery_app.conf.result_backend
            broker_transport_options = celery_app.conf.broker_transport_options
            broker_connection_timeout = celery_app.conf.broker_connection_timeout
            broker_heartbeat = celery_app.conf.broker_heartbeat

            config_info = (
                f"Celery connection settings:\n"
                f"  Broker URL: {broker_url}\n"
                f"  Result Backend: {result_backend}\n"
                f"  Broker Transport Options: {broker_transport_options}\n"
                f"  Broker Connection Timeout: {broker_connection_timeout}\n"
                f"  Broker Heartbeat: {broker_heartbeat}\n"
            )
            self.stdout.write(config_info)
            self.stdout.write("Testando conexão com o broker do Celery...")

            # Tenta estabelecer conexão com o broker
            with celery_app.connection() as connection:
                connection.ensure_connection(max_retries=3)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Conexão com o broker estabelecida com sucesso!\n"
                        f"Broker URL: {broker_url}"
                    )
                )

        except Exception as e:
            error_msg = f"❌ Falha na conexão com o broker: {e!s}"
            self.stdout.write(self.style.ERROR(error_msg))
            return
