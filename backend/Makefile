.PHONY: up down build logs shell migrate revision seed test lint fmt typecheck

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f api worker

shell:
	docker compose exec api bash

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed:
	docker compose exec api python -m app.db.seed

test:
	docker compose exec api pytest -v

lint:
	docker compose exec api ruff check .

fmt:
	docker compose exec api ruff format .

typecheck:
	docker compose exec api mypy app
