local:
	make down
	docker compose --file ./compose.dev.yml --profile prod --env-file ./.env up -d

local-dev:
	make down
	docker compose --file ./compose.dev.yml --profile dev --env-file ./.env up -d --build

down:
	docker compose --file ./compose.dev.yml --env-file ./.env down --volumes --remove-orphans 