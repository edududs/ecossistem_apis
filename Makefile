.PHONY: help run-feed run-produtos

help: ## Mostra este menu de ajuda
	@echo "Comandos disponíveis:"
	@echo "  run-feed     - Executa a API de feed"
	@echo "  run-produtos - Executa a API de produtos"

run-feed: ## Executa a API de feed
	@echo "🚀 Iniciando API de feed..."
	cd api_feed && uv run python manage.py runserver 0.0.0.0:8000

run-produtos: ## Executa a API de produtos
	@echo "🚀 Iniciando API de produtos..."
	cd api_produtos && uv run python manage.py runserver 0.0.0.0:8001

add-rand-product:
	@echo "🚀 Inserindo produto aleatório..."
	cd api_produtos && uv run python manage.py insert_random_product