# Makefile for Hibiscus project using uv

.PHONY: install dev test coverage lint format build publish clean

# Install production dependencies
install:
	uv sync

# Install development dependencies
dev:
	uv sync --dev

# Run tests
test:
	PYTHONWARNINGS="ignore::DeprecationWarning" uv run pytest -n auto

# Run tests with coverage
coverage:
	PYTHONWARNINGS="ignore::DeprecationWarning" uv run pytest --cov=app --cov-report=term-missing -n auto

# Lint code using ruff and mypy
lint:
	uv run ruff check .
	uv run mypy app

# Format code using ruff
format:
	uv run ruff format .

# Build the package
build:
	uv build


# Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .coverage .pytest_cache coverage_html_report
	find . -type d -name '__pycache__' -exec rm -rf {} +