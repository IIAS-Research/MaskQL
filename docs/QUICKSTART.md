# Quickstart

This is a short local walkthrough for reviewers and contributors.
It uses the development stack because the test database from `tests/postgresql-init.sql` is already loaded there.

In a few minutes, you will:

1. start MaskQL locally on `https://localhost`,
2. inspect the seeded source data directly in PostgreSQL,
3. create a fresh MaskQL user,
4. create a catalog that points to the seeded test database,
5. create two rules,
6. run the same SQL query through MaskQL and compare the result before and after masking.

The example uses the `maskqltest.public.client` table:

| id | name | email |
| --- | --- | --- |
| 1 | Alice Dupont | alice@example.com |
| 2 | Bob Martin | bob@example.com |
| 3 | Amandine Durant | amandine@example.com |

The two rules in this example are:

1. a table-level allow rule with the row filter `email like 'a%'`,
2. a column-level masking rule `encrypt(name)`.

At the end:

1. the row for `bob@example.com` disappears,
2. the `name` column is still queryable, but no longer contains the clear text.

## Prerequisites

- Docker and Docker Compose
- OpenSSL
- `uv`
- Java 24+ or Docker for `scripts/build-trino-plugin.sh`

Run the commands below from the repository root.

## 1. Prepare a local review configuration

Create a small local `.env` file for `localhost`:

```bash
cat > .env <<'EOF'
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
MASKQL_HOST=localhost
MASKQL_PORT=443
MASKQL_ADMIN_USER=admin
MASKQL_ADMIN_PASSWORD=admin
MASKQL_JWT_SECRET=change-me-32+chars
MASKQL_ENCRYPT_PASSWORD=change-me-16+chars
MASKQL_TRINO_SHARED_SECRET=change-me-32+chars
MASKQL_TRINO_DNS_SEARCH=.
EOF
```

Generate a short-lived self-signed certificate for `localhost`.
The filenames below match `tls.yml`.

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -days 7 \
  -keyout certs/server.key.pem \
  -out certs/server.crt.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

## 2. Build the Trino plugin and start the minimal stack

The development stack mounts the MaskQL Trino plugin from your local workspace, so build it once before starting the services:

```bash
bash ./scripts/build-trino-plugin.sh
```

Define a small helper for the development compose file, then start the services needed for this walkthrough:

```bash
compose() {
  docker compose --file ./compose.dev.yml --profile dev --env-file ./.env "$@"
}

compose up -d reverse-proxy postgres trino maskql-dev
```

Wait until the API is up:

```bash
until curl -sk https://localhost/api/healthz >/dev/null; do sleep 2; done
compose ps
```

Notes:

- `HF_TOKEN` is not required here because this guide uses the published Trino image, not a local Trino build.
- The Vue frontend is optional for this walkthrough. If you want it too, run `compose up -d frontend-dev`.

## 3. Inspect the source data before MaskQL

Query PostgreSQL directly inside the stack:

```bash
compose exec -T postgres \
  psql -U postgres -d maskqltest \
  -c "SELECT id, name, email FROM client ORDER BY id;"
```

You should see the clear-text rows from `tests/postgresql-init.sql`:

```text
 id |       name       |        email
----+------------------+----------------------
  1 | Alice Dupont     | alice@example.com
  2 | Bob Martin       | bob@example.com
  3 | Amandine Durant  | amandine@example.com
```

## 4. Create a user, a catalog, and two rules

MaskQL already seeds a demo user and a demo catalog for the test suite, but here we create a fresh user and a fresh catalog so every step is visible.

First, authenticate as admin and keep the session cookie:

```bash
export COOKIE_JAR=/tmp/maskql-admin.cookies
curl -sk -c "$COOKIE_JAR" -u admin:admin -X POST \
  https://localhost/api/admin/login >/dev/null
```

Create a user and a catalog for this run:

```bash
export RUN_ID=$(date +%s)
export QS_USER="quickstart_${RUN_ID}"
export QS_PASSWORD="quickstart"
export QS_CATALOG="quickstart_${RUN_ID}"

export USER_ID=$(
  curl -sk -b "$COOKIE_JAR" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$QS_USER\",\"password\":\"$QS_PASSWORD\"}" \
    https://localhost/api/users \
  | uv run python -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)

export CATALOG_ID=$(
  curl -sk -b "$COOKIE_JAR" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"$QS_CATALOG\",\"url\":\"jdbc:postgresql://postgres:5432/maskqltest\",\"sgbd\":\"postgresql\",\"username\":\"postgres\",\"password\":\"postgres\"}" \
    https://localhost/api/catalogs \
  | uv run python -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)

printf 'USER_ID=%s\nCATALOG_ID=%s\nCATALOG=%s\n' "$USER_ID" "$CATALOG_ID" "$QS_CATALOG"
```

Create the two rules:

```bash
curl -sk -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":$USER_ID,\"catalog\":\"$QS_CATALOG\",\"schema_name\":\"public\",\"table_name\":\"client\",\"allow\":true,\"effect\":\"email like 'a%'\"}" \
  https://localhost/api/rules

curl -sk -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":$USER_ID,\"catalog\":\"$QS_CATALOG\",\"schema_name\":\"public\",\"table_name\":\"client\",\"column_name\":\"name\",\"allow\":true,\"effect\":\"encrypt(name)\"}" \
  https://localhost/api/rules
```

What these rules do:

- the table rule gives that user access to `public.client` and filters rows to emails starting with `a`,
- the column rule rewrites `name` on the fly with `encrypt(name)`.

## 5. Run the same SQL query through MaskQL

Now query MaskQL over HTTPS as the user you just created.
This is the same SQL query as above:

```bash
uv run python - <<'PY'
import os
import trino
from trino.auth import BasicAuthentication

conn = trino.dbapi.connect(
    host="localhost",
    port=443,
    user=os.environ["QS_USER"],
    catalog=os.environ["QS_CATALOG"],
    schema="public",
    http_scheme="https",
    auth=BasicAuthentication(os.environ["QS_USER"], os.environ["QS_PASSWORD"]),
    verify=False,
)

try:
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM client ORDER BY id")
    for row in cur.fetchall():
        print(row)
finally:
    conn.close()
PY
```

You should now get only two rows, and the `name` values should no longer match the clear text:

```text
(1, '<encrypted value>', 'alice@example.com')
(3, '<encrypted value>', 'amandine@example.com')
```

The exact encrypted strings depend on `MASKQL_ENCRYPT_PASSWORD`, but the result should stay the same:

1. `Bob Martin` is filtered out by the table rule.
2. `Alice Dupont` and `Amandine Durant` are still present.
3. `name` is masked with `encrypt(name)`.
4. `email` stays readable because no masking rule was applied to that column.

## 6. Optional checks

If you want, you can also check that the catalog schema was scanned automatically:

```bash
curl -sk -b "$COOKIE_JAR" \
  "https://localhost/api/catalogs/$CATALOG_ID/schema" \
  | uv run python -m json.tool
```

Run the full automated test suite:

```bash
uv run tox
```

## 7. Clean up

```bash
rm -f "$COOKIE_JAR"
compose down
```

## Troubleshooting

- If HTTPS requests fail because of the self-signed certificate, use `curl -k` and `verify=False` only for this local quickstart.
- If `compose up` fails at Trino startup, rebuild the plugin with `bash ./scripts/build-trino-plugin.sh`.
- If catalog creation fails, inspect `compose logs trino maskql-dev`.
