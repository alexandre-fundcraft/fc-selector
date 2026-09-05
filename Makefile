.PHONY: help sync test test-unit test-integration test-e2e test-coverage clean lint format \
        example-setup example-run example-clean seed-data docs-serve docs-build

help:
	@echo "FC Selector - Development Commands"
	@echo ""
	@echo "  make sync             Sync dependencies with uv (creates venv automatically)"
	@echo ""
	@echo "  make test             Run all tests (unit + integration + e2e)"
	@echo "  make test-unit        Run only unit tests (fast)"
	@echo "  make test-integration Run only integration tests"
	@echo "  make test-e2e         Run end-to-end tests"
	@echo "  make test-coverage    Run tests with an HTML coverage report"
	@echo ""
	@echo "  make lint             Run code linters (ruff, mypy)"
	@echo "  make format           Format code with ruff"
	@echo ""
	@echo "  make example-setup    Set up example application database"
	@echo "  make example-run      Run example application server"
	@echo "  make example-clean    Remove the example application database"
	@echo "  make seed-data        Seed example application with fake data"
	@echo ""
	@echo "  make docs-serve       Serve documentation locally (localhost:9999)"
	@echo "  make docs-build       Build static documentation site"
	@echo ""
	@echo "  make clean            Remove build artifacts and cache files"
	@echo ""
	@echo "Quick start: make sync && make example-setup && make example-run"

sync:
	uv sync --group dev

# Testing (settings, pythonpath and flags come from pyproject.toml)
test:
	uv run pytest tests/ --ignore=tests/performance/ --cov=fc_selector --cov-report=term

test-unit:
	uv run pytest tests/core/

test-integration:
	uv run pytest tests/integration/

test-e2e:
	uv run pytest tests/e2e/

test-coverage:
	uv run pytest tests/ --ignore=tests/performance/ --cov=fc_selector --cov-report=html --cov-report=term
	@echo "Open htmlcov/index.html to view the report"

# Code Quality
lint:
	-uv run ruff check fc_selector tests
	-uv run mypy fc_selector

format:
	uv run ruff check --fix --unsafe-fixes fc_selector tests
	uv run ruff format fc_selector tests

# Example Application
example-setup:
	cd example && DJANGO_SETTINGS_MODULE=example.settings uv run python manage.py migrate --run-syncdb
	cd example && DJANGO_SETTINGS_MODULE=example.settings uv run python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(email='test@test.com').exists() or User.objects.create_superuser('test', 'test@test.com', 'test')"
	@echo ""
	@echo "Example application ready (test@test.com / test)"
	@echo "  - OData:  http://localhost:8000/odata/posts/"
	@echo "  - Admin:  http://localhost:8000/admin/"

example-run:
	PYTHONPATH=. DJANGO_SETTINGS_MODULE=example.example.settings uv run python example/manage.py runserver

example-clean:
	rm -f example/db.sqlite3
	@echo "Database removed. Run 'make example-setup' to recreate."

seed-data:
	DJANGO_SETTINGS_MODULE=example.example.settings uv run python example/manage.py seed_data

# Documentation
docs-serve:
	uv run python -m mkdocs serve -a localhost:9999

docs-build:
	uv run python -m mkdocs build

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.py[co]" -delete
