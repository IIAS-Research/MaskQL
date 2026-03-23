# Quickstart

This is a short local walkthrough for reviewers, contributors, or anyone who wants to see MaskQL working on a real example in a few minutes.

It uses the development stack because the sample PostgreSQL database from `tests/postgresql-init.sql` is already loaded there.

In this quickstart, you will:

1. start MaskQL on `https://localhost`,
2. log in to the admin interface,
3. create one user,
4. create one catalog,
5. add two rules from the UI,
6. check the built-in before/after preview,
7. run one SQL query as the user you just created.

The example uses the seeded table `public.client`:

| id | name | email |
| --- | --- | --- |
| 1 | Alice Dupont | alice@example.com |
| 2 | Bob Martin | bob@example.com |
| 3 | Amandine Durant | amandine@example.com |

The two rules used in this walkthrough are:

1. a table rule with the filter `email like 'a%'`,
2. a column rule on `name` with `encrypt(name)`.

At the end:

1. the row for `bob@example.com` is filtered out,
2. the `name` column is still visible, but no longer in clear text.

## Prerequisites

- Docker and Docker Compose
- OpenSSL
- `uv`
- Java 24+ or Docker for `scripts/build-trino-plugin.sh`

Run everything below from the repository root.

## 1. Prepare a local `.env`

Create a small local configuration for `localhost`:

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

Create a short-lived self-signed certificate for `localhost`:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -days 7 \
  -keyout certs/server.key.pem \
  -out certs/server.crt.pem \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

## 2. Start the local stack

Build the Trino plugin once, then start the development stack:

```bash
bash ./scripts/build-trino-plugin.sh
make local
```

Wait until the API is ready:

```bash
until curl -sk https://localhost/api/healthz >/dev/null; do sleep 2; done
```

Notes:

- `HF_TOKEN` is not required here as long as you are not rebuilding the Trino image locally.
- `make local` also starts the frontend, so the admin UI is available at `https://localhost`.

## 3. Sign in to the admin UI

Open `https://localhost` in your browser.

Because this is a local self-signed certificate, your browser will warn you. Accept the warning for this quickstart.

Log in with:

- username: `admin`
- password: `admin`

You should land on the main interface, with `Databases` and `Users` in the sidebar.

## 4. Create a test user

In the UI:

1. open `Users`,
2. click `Create user`,
3. enter:
   - username: `quickstart`
   - password: `quickstart`
4. click `Create`.

You should now see the new user in the users list.

## 5. Create a catalog for the seeded PostgreSQL data

Open `Databases`, then click `Create database`.

Use these values:

- Name: `quickstartdemo`
- JDBC URL: `jdbc:postgresql://postgres:5432/maskqltest`
- DBMS: `PostgreSQL`
- Username: `postgres`
- Password: `postgres`

Click `Create`.

Back on the databases page:

1. check that the new catalog appears,
2. click `Sync schema` once for that catalog.

After a moment, the catalog should be usable and the scanned schema should include `public.client`.

## 6. Add the two rules from the UI

Open `Users`, find `quickstart`, then click `Manage access`.

On that page:

1. in `Databases`, select `quickstartdemo`,
2. in `Schemas`, select `public`,
3. in `Tables`, find `client`,
4. click the gear icon on `client` to open `Configure table`.

In the table dialog:

1. set the table to `allow`,
2. in `Row filter`, enter:

```text
email like 'A%'
```

Then in the `Columns` section:

1. find the `name` column,
2. set it to `allow`,
3. in `Mask / transform`, enter:

```text
encrypt(name)
```

Changes are saved automatically. You do not need to submit a form.

## 7. Check the built-in before/after preview

Stay in the same `Configure table` dialog and look at the `Preview` section on the right.

It shows:

- `Before MaskQL`: the raw rows from the source database,
- `After MaskQL`: the same table after applying the current rules.

What you should see:

- in `Before MaskQL`, the three clear-text rows are visible,
- in `After MaskQL`, `Bob Martin` is gone because `bob@example.com` does not match `email like 'A%'`,
- in `After MaskQL`, the `name` values for Alice and Amandine are encrypted.

This is the quickest way to understand what MaskQL is doing, because you can change the rules and see the preview refresh immediately.

## 8. Run one SQL query as the new user

The preview is useful, but MaskQL is still a SQL gateway. To confirm that the same behavior is visible from a client, run one query as the `quickstart` user.

Use any Trino-compatible client you like. If you do not already have one, the small Python snippet below works with the dependencies already used in this repository:

```bash
uv run python - <<'PY'
import trino
from trino.auth import BasicAuthentication

conn = trino.dbapi.connect(
    host="localhost",
    port=443,
    user="quickstart",
    catalog="quickstartdemo",
    schema="public",
    http_scheme="https",
    auth=BasicAuthentication("quickstart", "quickstart"),
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

You should get two rows, not three:

```text
(1, '<encrypted value>', 'alice@example.com')
(3, '<encrypted value>', 'amandine@example.com')
```

The exact encrypted strings depend on `MASKQL_ENCRYPT_PASSWORD`, so they will differ from one setup to another. The important part is:

1. Bob is filtered out,
2. Alice and Amandine are still returned,
3. `name` is encrypted,
4. `email` stays readable.

## 9. Stop the stack

When you are done:

```bash
make down
```

## Troubleshooting

- If the browser warns about the certificate, this is expected for the local self-signed setup.
- If the UI does not load, check that `make local` finished and that `https://localhost/api/healthz` responds.
- If `public.client` does not appear in the access page, go back to `Databases` and click `Sync schema` again.
- If Trino does not start, rebuild the plugin with `bash ./scripts/build-trino-plugin.sh`.
