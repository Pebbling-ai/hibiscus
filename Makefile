# Hibiscus Docker Development Makefile

# Variables
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = backend
DOCKER_REGISTRY = # Add your registry here if needed

.PHONY: help build up down restart logs ps clean prune generate-jwt-secret clean-all deep-clean

# Default target
.DEFAULT_GOAL := help

# Help command to show available commands
help: ## Show this help
	@echo "Hibiscus Docker Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Docker Compose commands
build: ## Build the containers
	docker-compose -f $(COMPOSE_FILE) build

up: ## Start the containers in detached mode
	docker-compose -f $(COMPOSE_FILE) up -d

dev: ## Start the containers in foreground mode for development
	docker-compose -f $(COMPOSE_FILE) up

down: ## Stop and remove the containers
	docker-compose -f $(COMPOSE_FILE) down

restart: ## Restart the containers
	docker-compose -f $(COMPOSE_FILE) restart

logs: ## View the logs
	docker-compose -f $(COMPOSE_FILE) logs -f

ps: ## List running containers
	docker-compose -f $(COMPOSE_FILE) ps

clean: ## Remove containers, networks, and volumes
	docker-compose -f $(COMPOSE_FILE) down --volumes --remove-orphans

prune: ## Prune unused Docker data (containers, networks, volumes, images)
	docker system prune -a --volumes

clean-all: clean ## Remove all containers, networks, volumes AND related images
	@echo "Removing Docker images for this project..."
	-docker rmi $$(docker images | grep $(SERVICE_NAME) | awk '{print $$3}') 2>/dev/null || true
	@echo "Cleanup complete. All project containers, networks, volumes, and images have been removed."

deep-clean: clean-all ## Complete system cleanup - CAUTION: Removes ALL Docker resources
	@echo "WARNING: This will remove ALL Docker resources on your system, not just for this project."
	@read -p "Are you sure you want to continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "Removing all Docker containers..."; \
		docker rm -f $$(docker ps -aq) 2>/dev/null || true; \
		echo "Removing all Docker images..."; \
		docker rmi -f $$(docker images -q) 2>/dev/null || true; \
		echo "Removing all Docker volumes..."; \
		docker volume rm $$(docker volume ls -q) 2>/dev/null || true; \
		echo "Removing all Docker networks..."; \
		docker network prune -f; \
		echo "Deep clean complete."; \
	else \
		echo "Deep clean cancelled."; \
	fi

# Backend-specific commands
backend-shell: ## Start a shell in the backend container
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) bash

backend-logs: ## View only backend logs
	docker-compose -f $(COMPOSE_FILE) logs -f $(SERVICE_NAME)

backend-test: ## Run tests in the backend container
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python -m pytest

backend-coverage: ## Run tests with coverage in the backend container
	docker-compose -f $(COMPOSE_FILE) exec $(SERVICE_NAME) python -m pytest --cov=app

# Utility commands
generate-jwt-secret: ## Generate a secure JWT secret and print it
	@echo "Generated JWT Secret (copy this to your .env file):"
	@openssl rand -base64 42

check-health: ## Check the backend health endpoint
	@curl -s http://localhost:8000/health || echo "Health check failed"

uv-lock-update: ## Update uv.lock file for dependencies
	cd backend && uv pip compile pyproject.toml -o uv.lock

# Environment setup
setup-env: ## Check if .env file exists, create from example if not
	@if [ ! -f ./backend/.env ]; then \
		if [ -f ./backend/.env.example ]; then \
			cp ./backend/.env.example ./backend/.env; \
			echo "Created .env file from example. Please update with your specific values."; \
			echo "You can run 'make generate-jwt-secret' to create a secure JWT secret."; \
		else \
			echo "No .env.example file found. Please create a .env file manually."; \
		fi \
	else \
		echo ".env file already exists."; \
	fi