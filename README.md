# MaskQL

MaskQL is an open-source middleware based on [Trino](https://trino.io) that applies masking or transformation rules **on the fly** without altering the source databases.
It is designed for sensitive contexts (healthcare, finance, etc.) where certain columns must be pseudonymized, encrypted, or modified before being exposed.

---

## Features

* [WIP] Connect to multiple databases (PostgreSQL, MySQL, ClickHouse, etc.)
* [WIP] Configurable masking rules per column/table 
* [WIP] Support for simple SQL transformations or advanced logic (Java UDF, AI)
* [WIP] User authentication for data access
* [WIP] Deployable with Docker Compose

---

## Requirements

* [Docker](https://docs.docker.com/get-docker/)
* [uv](https://docs.astral.sh/uv/) for Python environment management
* `make` (GNU Make)

---

## Project Structure

```
.
├── Makefile          # Commands: local, down
├── compose/          # All about docker deployment
├── trino/            # Trino default configuration (access control, catalogs)
├── admin/            # Admin interface
├── tests/            # Python tests (unittest)
└── tox.ini           # Automated testing configuration
```

---

## Running Locally

### Start environment

```bash
make local
```

This starts Trino + Admin UI + test databases (via Docker Compose).

### Stop and clean up

```bash
make down
```

---

## Running Tests

All tests (unit + integration) are executed via [tox](https://tox.wiki/):

```bash
uv run tox
```

This will:

1. Start the Docker stack (`make local`)
2. Perform a Trino health check
3. Run `unittest` tests
4. Stop the stack (`make down`)

---

## Configuring Masking Rules

Masking rules are stored in `config/rules.json`.
Example: mask the client name except for the first two letters.

```json
{
  "tables": [
    {
      "catalog": "postgres",
      "schema": "public",
      "table": "client",
      "privileges": ["SELECT"],
      "columns": [
        {
          "name": "name",
          "mask": "CASE WHEN name IS NULL THEN NULL WHEN length(name) <= 2 THEN name ELSE rpad(substring(name, 1, 2), length(name), '*') END"
        }
      ]
    }
  ]
}
```

With `security.refresh-period` enabled in Trino, changes to the rules file will be reloaded automatically.

> [WIP] This will be updated as the goal is to create an IHM to configure this

