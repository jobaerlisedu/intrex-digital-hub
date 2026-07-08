.PHONY: install dev migrate run test lint build clean

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	npm install

dev:
	python manage.py runserver

migrate:
	python manage.py migrate

run:
	gunicorn config.wsgi:application --bind 0.0.0.0:$${PORT:-8000} --workers 4

test:
	pytest

test-cov:
	pytest --cov --cov-report=term --cov-report=html

lint:
	ruff check .
	npm run lint

build:
	npm run build
	python manage.py collectstatic --no-input

clean:
	rm -rf staticfiles/
	rm -rf static/dist/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
