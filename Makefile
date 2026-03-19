COMPOSE_DEV = docker compose --file ./compose.dev.yml --profile dev --env-file ./.env
COMPOSE_PROD = docker compose --file ./compose.dev.yml --profile prod --env-file ./.env

.PHONY: local local-build local-prod local-prod-build rebuild-backend rebuild-frontend rebuild-trino restart-backend restart-frontend restart-trino down clean logs ps

local:
	$(COMPOSE_DEV) up -d

local-build:
	$(COMPOSE_DEV) up -d --build

local-prod:
	$(COMPOSE_PROD) up -d

local-prod-build:
	$(COMPOSE_PROD) up -d --build

rebuild-backend:
	$(COMPOSE_DEV) up -d --build maskql-dev

rebuild-frontend:
	$(COMPOSE_DEV) up -d --build frontend-dev

rebuild-trino:
	$(COMPOSE_DEV) up -d --build trino

restart-backend:
	$(COMPOSE_DEV) restart maskql-dev

restart-frontend:
	$(COMPOSE_DEV) restart frontend-dev

restart-trino:
	$(COMPOSE_DEV) restart trino

logs:
	$(COMPOSE_DEV) logs -f --tail=200

ps:
	$(COMPOSE_DEV) ps

down:
	$(COMPOSE_DEV) down --remove-orphans
	$(COMPOSE_PROD) down --remove-orphans

clean:
	$(COMPOSE_DEV) down --volumes --remove-orphans
	$(COMPOSE_PROD) down --volumes --remove-orphans
