# MaskQL

**Protecting Gotham's citizens... and your database.**

MaskQL is an open-source middleware, built on top of [Trino](https://trino.io), that applies masking, filtering, and transformation rules on the fly, without changing the source databases. It is designed for sensitive environments (healthcare, finance, etc.) where some columns must be pseudonymized, encrypted, or transformed before they are exposed.

This is especially useful when you can read a database but cannot change it, and when making a masked replica is not possible or not desired.

---

## Features

* Connect to multiple databases: PostgreSQL, MySQL, ClickHouse, and more.
* Column masking with SQL expressions, for example: `regexp_replace(email, '(.+)@(.+)', '***@$2')`.
* Table filtering with a SQL WHERE clause.
* Advanced transformations:

  * extract text from binary PDF files,
  * pseudonymize unstructured text using Named Entity Recognition (NER).
  * Encrypt any column & preserve typing
* Per-user access control with allow, deny, and inheritance.
* Admin UI (Vue 3) to manage users, catalogs, and rules.
* Export and import rules as JSON by user and catalog.
* All-in-one Docker Compose deployment with Traefik as reverse proxy.

---

## Requirements

* [Docker](https://docs.docker.com/get-docker/)
* [uv](https://docs.astral.sh/uv/) for Python environment management
* `make` (GNU Make)

--

## Deploy MaskQL in production

All the necessary resources are included in the Docker images, so there is no need to clone this repository.
You will only need three files, available at the root of this repository:
1. `compose.yml` – Docker description of the containers to deploy and their interactions. This file must not be modified.
2. `.env.example` (to be renamed as `.env`) – Configuration of environment variables for deployment. MaskQL will work with the default values, but it is strongly recommended to set your own passwords and encryption keys.
3. `tls.yml` – Paths to the certificates required by MaskQL, which only works with HTTPS for security reasons. You will need to generate certificates and set their paths in this file.

Once these three files are copied and configured in your directory, you are almost done!
Simply run the following command:

```bash
docker compose up -d
```

MaskQL should be deployed within a few minutes. You can then access the interface via HTTPS at the address you defined in the `.env`.

---

## Run locally in development mode

### Start
Git clone the project and in the root dir run the following command.
```bash
make local
```

This starts the full stack with Docker Compose.

### Stop and clean

```bash
make down
```

---

## Project structure

```
.
├── Makefile          # Targets: local, local-dev, down
├── compose.yml       # Docker stack (Traefik, Backend, Trino, PostgreSQL, Frontend)
├── trino/            # Trino custom code (UDF, access control)
├── maskql/           # Backend (FastAPI): users, catalogs, rules, auth
├── frontend/         # Admin UI (Vue 3)
├── tests/            # Python tests (unittest)
├── docs/             # Documentation (work in progress)
├── certs/            # Certificates used by MaskQL
└── tox.ini           # Test configuration
```

---

## Components

* **MaskQL Backend**: FastAPI service. Manages users, catalogs, and rules. Handles auth and coordinates access through Trino.
* **Frontend**: Vue 3 admin UI to create users and catalogs, and to configure rules.
* **Custom Trino**: data gateway to the databases. Applies functions and access control.
* **PostgreSQL**: stores users, catalogs, and rules.
* **Traefik**: reverse proxy and entry point to the stack.

---

## Tests

Run tests with [tox](https://tox.wiki/) using `uv`:

```bash
uv run tox
```

This will:

1. Build and start the stack (`make local`)
2. Health check
3. Run `unittest` tests
4. Stop and clean the stack (`make down`)

---

## How it works

```mermaid
flowchart TD
A[Client (SQL / App / BI)] --> B[MaskQL Backend (FastAPI)]
B -->|Auth and rules| C[Maskql-Trino]
C --> D[(Databases)]
C -->|Filtered and masked result| B
B --> A
```

1. The client sends a query to the MaskQL backend.
2. The backend checks auth and fetches the rules for the current user and target catalog.
3. Trino runs the query and applies filters, masking, and transformations.
4. The backend returns a result that already respects the rules.

---

## Rule model and inheritance

Each rule targets a user and a catalog. A rule can apply at different levels:

| Level  | schema\_name | table\_name | column\_name | effect usage           |
| ------ | ------------ | ----------- | ------------ | ---------------------- |
| DB     | ""           | ""          | ""           | not used               |
| Schema | X            | ""          | ""           | not used               |
| Table  | X            | Y           | ""           | used as WHERE filter   |
| Column | X            | Y           | Z            | used as SQL expression |

* `allow: true` allows the target and all its children, unless there is a local deny.
* `allow: false` denies the target and all its children, unless there is a local allow.
* If there is no local rule, the status is inherited from the parent.

Examples:

* Table filter: `effect = "is_active = TRUE AND region = 'EU'"`.
* Column transform: `effect = "price * 1.2"` or `"COALESCE(email, 'hidden')"`.
* Default deny on a whole schema: set a deny rule at schema level, then allow specific tables or columns.

The backend enforces a unique constraint on `(user_id, catalog_id, schema_name, table_name, column_name)`.

---

## Admin UI

* Login for admins
* Catalogs: create, edit, delete
* Users: create, edit, delete, and a manage permissions
* Permissions: four panels (Database, Schemas, Tables, Columns) to define rules
  * Also export and import JSON for the current user and the selected catalog

### Export and import format

Export produces a file like this:

```json
{
  "version": 1,
  "user_id": 123,
  "catalog_id": 7,
  "exported_at": "2025-09-02T10:00:00Z",
  "rules": [
    { "schema_name": "public", "table_name": "", "column_name": "", "allow": true, "effect": "" },
    { "schema_name": "public", "table_name": "orders", "column_name": "", "allow": true, "effect": "is_active = TRUE" },
    { "schema_name": "public", "table_name": "orders", "column_name": "price", "allow": true, "effect": "price * 1.2" }
  ]
}
```

On import, the UI ignores any `id`, `user_id`, and `catalog_id` inside the file. The rules are applied as upserts for the current user and the currently selected catalog.

---

## Authentication

Admin endpoints:

* `POST /admin/login` (Basic auth, server-side session)
* `POST /admin/logout`
* `GET /admin/health` (guard for protected routes)

The frontend redirects to `/login` if not authenticated.

---

## Configuration

See `compose.dev.yml` and `.env.example` for defaults values.