local:
	make down
	docker compose --file ./compose.dev.yml --env-file ./.env up -d

local-build:
	make down
	docker compose --file ./compose.dev.yml --env-file ./.env up -d --build

down:
	docker compose --file ./compose.dev.yml --env-file ./.env down --volumes --remove-orphans 