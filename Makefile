ENV_FILE ?= ./.env

ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
endif

REGISTRY ?= docker.io/rudymerieux
REGISTRY_HOST ?= docker.io
PLATFORM ?= linux/amd64
GIT_SHA ?= $(shell git rev-parse --short HEAD)
IMAGE_TAG ?= $(GIT_SHA)
LATEST_TAG ?= latest

BACKEND_IMAGE = $(REGISTRY)/maskql
FRONTEND_IMAGE = $(REGISTRY)/maskql-frontend
TRINO_IMAGE = $(REGISTRY)/maskql-trino

COMPOSE_DEV = docker compose --file ./compose.dev.yml --profile dev --env-file $(ENV_FILE)
COMPOSE_PROD = docker compose --file ./compose.yml --env-file $(ENV_FILE)

export HF_TOKEN
export DOCKER_BUILDKIT ?= 1

.PHONY: local local-build local-prod local-prod-build rebuild-backend rebuild-frontend rebuild-trino restart-backend restart-frontend restart-trino down clean logs ps registry-info registry-login push push-app push-backend push-frontend push-trino check-registry check-hf-token

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

registry-info:
	@echo "REGISTRY=$(REGISTRY)"
	@echo "REGISTRY_HOST=$(REGISTRY_HOST)"
	@echo "PLATFORM=$(PLATFORM)"
	@echo "IMAGE_TAG=$(IMAGE_TAG)"
	@echo "LATEST_TAG=$(LATEST_TAG)"

registry-login:
	docker login $(REGISTRY_HOST)

check-registry:
	@test -n "$(REGISTRY)" || (echo "REGISTRY is required in $(ENV_FILE)" >&2; exit 1)
	@test -n "$(PLATFORM)" || (echo "PLATFORM is required in $(ENV_FILE)" >&2; exit 1)
	@test -n "$(IMAGE_TAG)" || (echo "IMAGE_TAG is required" >&2; exit 1)

check-hf-token:
	@test -n "$$HF_TOKEN" || (echo "HF_TOKEN is required for push-trino" >&2; exit 1)

push: push-app push-trino

push-app: push-backend push-frontend

push-backend: check-registry
	docker buildx build --platform "$(PLATFORM)" \
		-f maskql/dockerfile \
		-t "$(BACKEND_IMAGE):$(IMAGE_TAG)" \
		-t "$(BACKEND_IMAGE):$(LATEST_TAG)" \
		--push ./maskql

push-frontend: check-registry
	docker buildx build --platform "$(PLATFORM)" \
		-f frontend/dockerfile \
		-t "$(FRONTEND_IMAGE):$(IMAGE_TAG)" \
		-t "$(FRONTEND_IMAGE):$(LATEST_TAG)" \
		--push ./frontend

push-trino: check-registry check-hf-token
	docker buildx build --platform "$(PLATFORM)" \
		-f trino/Dockerfile \
		--secret id=HF_TOKEN,env=HF_TOKEN \
		-t "$(TRINO_IMAGE):$(IMAGE_TAG)" \
		-t "$(TRINO_IMAGE):$(LATEST_TAG)" \
		--push ./trino
