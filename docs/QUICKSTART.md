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

The example uses the 200 synthetic patients in `administrative.patients`, with columns `patient_id`, `last_name` (`TEXT`), `first_name` (`TEXT`), `email`, `phone`, and `birth_date`.

The two rules used in this walkthrough are:

1. a table rule with the filter `patient_id <= 3`,
2. a column rule on `last_name` with `encrypt(last_name)`.

At the end:

1. only patients 1, 2, and 3 are returned,
2. the `last_name` column is still visible, but no longer in clear text.

For an executable replay with saved inputs, rules, query and actual outputs, see
the [structured example](../examples/structured/README.md) and
[test procedure](VALIDATION.md).

## Prerequisites

- Docker and Docker Compose
- OpenSSL
- `uv`
- `make` and `curl`
- Java 24+ and Maven for a native plugin build; otherwise `scripts/build-trino-plugin.sh` uses Docker

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

Wait until the API and admin interface are ready:

```bash
attempt=0
until curl --fail --silent --cacert certs/server.crt.pem \
  --connect-timeout 2 --max-time 5 https://localhost/api/healthz >/dev/null &&
  curl --fail --silent --cacert certs/server.crt.pem \
    --connect-timeout 2 --max-time 5 https://localhost/ >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 90 ]; then
    echo "MaskQL did not become ready; inspect the stack with make ps and make logs." >&2
    exit 1
  fi
  sleep 2
done
```

If you already have a PostgreSQL volume, run `make demo-data`, then click `Sync schema` for your catalog.

Notes:

- `HF_TOKEN` is not required here as long as you are not rebuilding the Trino image locally.
- `make local` also starts the frontend, so the admin UI is available at `https://localhost`.
- The readiness check requires successful HTTP responses from both the API and frontend, and stops after 90 failed attempts.

## 3. Sign in to the admin UI

Open `https://localhost` in your browser.

Because this is a local self-signed certificate, your browser will warn you. Accept the warning for this quickstart.

Log in with:

- username: `admin`
- password: `admin`

The home dashboard summarizes users, databases and rules, with database connection statuses.
Open a user's access rules directly from the dashboard, or expand the guide at the bottom for setup instructions.

## 4. Create a test user

In the UI:

1. open `Users`,
2. click `Create user`,
3. enter:
   - username: `quickstart`
   - password: `quickstart`
4. click `Create user`.

You should now see the new user in the users list.

## 5. Create a catalog for the seeded PostgreSQL data

Open `Databases`, then click `Connect database`.

Use these values:

- Name: `quickstartdemo`
- JDBC URL: `jdbc:postgresql://postgres:5432/maskqltest`
- Database type: `PostgreSQL`
- Username: `postgres`
- Password: `postgres`

Click `Connect database`.

Back on the databases page:

1. check that the new catalog appears,
2. click `Sync schema` once for that catalog.

After a moment, the catalog should be usable and the scanned schema should include `administrative.patients`.

## 6. Add the two rules from the UI

Open `Users`, find `quickstart`, then click `Manage access`.

On that page:

1. in `Databases`, select `quickstartdemo`,
2. in `Schemas`, select `administrative`,
3. in `Tables`, find `patients`,
4. click the gear icon on `patients` to open `Configure table`.

In the table dialog:

1. set the table to `allow`,
2. in `Row filter`, select `Visual editor` and click `Add condition`,
3. choose `patient_id` and `at most`, then enter `3`; the column determines the value type.

Then in the `Columns` section:

1. click the `last_name` column to open its editor,
2. set it to `allow`,
3. select `Visual editor`, click `Select a transformation`, then choose the `Encrypt` card in the function library dialog.

Valid expressions are saved automatically. Switch to `SQL editor` to enter raw expressions directly, such as `patient_id <= 3` or `encrypt(last_name)`.

## 7. Check the built-in before/after preview

Stay in the same `Configure table` dialog and look at the `Preview` section on the right.

It shows:

- `Before MaskQL`: the raw rows from the source database,
- `After MaskQL`: the same table after applying the current rules.

What you should see:

- in `Before MaskQL`, a sample of five clear-text rows is visible,
- in `After MaskQL`, only patients 1, 2, and 3 remain out of the 200 patients,
- in `After MaskQL`, the `last_name` values are encrypted.

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
    schema="administrative",
    http_scheme="https",
    auth=BasicAuthentication("quickstart", "quickstart"),
    verify=False,
)

try:
    cur = conn.cursor()
    cur.execute("SELECT patient_id, last_name FROM patients ORDER BY patient_id")
    for row in cur.fetchall():
        print(row)
finally:
    conn.close()
PY
```

You should get three rows:

```text
[1, '<encrypted value>']
[2, '<encrypted value>']
[3, '<encrypted value>']
```

The exact encrypted strings depend on `MASKQL_ENCRYPT_PASSWORD`, so they will differ from one setup to another. The important part is:

1. only patients 1, 2, and 3 are returned,
2. `last_name` is encrypted.

### Save and verify the example

The [structured replay](../examples/structured/README.md) uses the same
200-patient fixture, filter and encryption rule. From the repository root:

```bash
export MASKQL_HOST=localhost MASKQL_PORT=443
export MASKQL_ADMIN_USER=admin MASKQL_ADMIN_PASSWORD=admin
export API_VERIFY_SSL=certs/server.crt.pem
export TRINO_VERIFY_SSL="$API_VERIFY_SSL"
export MASKQL_ENCRYPT_PASSWORD='change-me-16+chars'
uv run --frozen python examples/structured/run.py
```

It creates its own temporary user and catalog, saves the source and returned
rows, checks the before/after preview and decryption, and removes those
temporary resources. The expected retained names before encryption are
`Fictional-Martin`, `Fictional-Lefèvre` and `Fictional-O'Connor` (patients 1–3).
The query has no `WHERE`: the table rule supplies the filter.

For a separate illustration of text processing and PDF extraction, run the
[fictional clinical note example](../examples/unstructured/README.md):

```bash
MASKQL_USER=demo MASKQL_PASSWORD=demo \
uv run --frozen python examples/unstructured/run_examples.py --seed fictional-patient-142
```

## 9. Stop the stack

When you are done:

```bash
make down
```

## Troubleshooting

- If the browser warns about the certificate, this is expected for the local self-signed setup.
- If the UI does not load, check that `make local` finished and that `https://localhost/api/healthz` responds.
- If `administrative.patients` does not appear in the access page, go back to `Databases` and click `Sync schema` again.
- If Trino does not start, rebuild the plugin with `bash ./scripts/build-trino-plugin.sh`.
- On the first start, the frontend installs its npm dependencies. If its logs report `ECONNRESET`, restore access to `https://registry.npmjs.org`, then rerun the installation and start the frontend:

  ```bash
  docker compose --file compose.dev.yml --profile dev --env-file .env run --rm --no-deps frontend-dev npm ci
  docker compose --file compose.dev.yml --profile dev --env-file .env up -d --no-deps frontend-dev
  ```

  Repeat the readiness check above. These commands affect only the development frontend.
