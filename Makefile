.PHONY: help install test format lint clean docker-build docker-test docker-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies using uv
	cd backend && uv pip install -r requirements.txt

install-dev: ## Install all dependencies including dev tools
	cd backend && uv pip install -r requirements.txt

test: ## Run tests
	cd backend && pytest -v --tb=short

test-cov: ## Run tests with coverage
	cd backend && pytest -v --tb=short --cov=app --cov-report=term-missing --cov-report=html

format: ## Format code with ruff
	cd backend && ruff format .

lint: ## Lint code with ruff
	cd backend && ruff check .

lint-fix: ## Lint and fix code with ruff
	cd backend && ruff check --fix .

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

clean: ## Clean up cache and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.coverage backend/htmlcov

docker-build: ## Build Docker image (runs tests)
	docker build -t mfa-backend:latest backend/

docker-build-no-test: ## Build Docker image without running tests
	docker build --target=runtime -t mfa-backend:latest backend/

docker-test: ## Build and run tests in Docker
	docker build --target=test -t mfa-backend-test backend/

docker-run: ## Run the application in Docker
	docker-compose up

docker-down: ## Stop Docker containers
	docker-compose down

docker-clean: ## Remove Docker containers, images, and volumes
	docker-compose down -v
	docker rmi mfa-backend:latest 2>/dev/null || true
