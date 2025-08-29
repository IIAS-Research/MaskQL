local:
	make down
	docker compose --file ./compose.dev.yml --env-file ./.env up -d

build-trino:
	docker build --secret id=HF_TOKEN,env=HF_TOKEN ./trino/

local-build:
	make down
	docker compose --file ./compose.dev.yml --env-file ./.env up -d --build

down:
	docker compose --file ./compose.dev.yml --env-file ./.env down --volumes --remove-orphans 