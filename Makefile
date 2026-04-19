.PHONY: up down test api-test web-build

up:
	docker compose -f infra/docker/docker-compose.yml up --build

down:
	docker compose -f infra/docker/docker-compose.yml down --remove-orphans

api-test:
	cd services/api && DATABASE_URL=sqlite+pysqlite:///:memory: pytest -q

web-build:
	cd services/web && npm run build
