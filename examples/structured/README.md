# Structured-data example

Run this after the Quickstart with the [synthetic healthcare fixture](../../tests/fixtures/healthcare.sql) loaded in `maskqltest`:

```sh
uv run python examples/structured/run.py
```

Set `MASKQL_HOST`, `MASKQL_PORT` and `MASKQL_SCHEME` for your installation (defaults: `localhost`, `443`, `https`). Authentication uses `MASKQL_ADMIN_USER` and `MASKQL_ADMIN_PASSWORD` (local demo defaults: `admin` / `admin`). For a local CA, set `API_VERIFY_SSL` to its certificate path; `false` disables verification for a disposable local setup.

The PostgreSQL connection defaults to `jdbc:postgresql://postgres:5432/maskqltest`, with the local demo credentials. Override `MASKQL_SOURCE_URL`, `MASKQL_SOURCE_USER` and `MASKQL_SOURCE_PASSWORD` when needed. Set `MASKQL_ENCRYPT_PASSWORD` to the running server's **test** encryption key to also verify decryption; it is never written to the artifacts.

The script creates a temporary user and catalog, runs [query.sql](query.sql) before and after applying [rules.json](rules.json), checks the preview API (five raw rows, three masked rows), and removes its temporary resources in `finally`. Existing users, catalogs, rules and source records are preserved.

Each run creates `results/<timestamp>/`: `input.json` records the 200 synthetic source rows; `result.json` records the returned patients, encrypted names, preview, optional decryption, checks and cleanup status. Use `--output /tmp/maskql-structured-results` to choose a new output directory. The SQL query contains no `WHERE`: the `patient_id <= 3` rule supplies the filter. Ciphertext depends on the server's encryption key and context.
