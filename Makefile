local:
	docker compose --file ./compose/compose.dev.yml --env-file ./compose/.env up -d

down:
	docker compose --file ./compose/compose.dev.yml --env-file ./compose/.env down --volumes --remove-orphans 