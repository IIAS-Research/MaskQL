# Structured-data example

Run this after the [Quickstart](../../docs/QUICKSTART.md) with the [synthetic healthcare fixture](../../tests/fixtures/healthcare.sql) loaded in `maskqltest`:

```sh
export API_VERIFY_SSL=certs/server.crt.pem
export TRINO_VERIFY_SSL="$API_VERIFY_SSL"
export MASKQL_ENCRYPT_PASSWORD='change-me-16+chars'
uv run --frozen python examples/structured/run.py
```

These values match the local certificate and disposable encryption key created in the Quickstart. Run the commands from the repository root; adjust the paths and key if your configuration differs.

Set `MASKQL_HOST`, `MASKQL_PORT` and `MASKQL_SCHEME` for your installation (defaults: `localhost`, `443`, `https`). Authentication uses `MASKQL_ADMIN_USER` and `MASKQL_ADMIN_PASSWORD` (local demo defaults: `admin` / `admin`). For a local CA, set `API_VERIFY_SSL` to its certificate path; `false` disables verification for a disposable local setup.

The PostgreSQL connection defaults to `jdbc:postgresql://postgres:5432/maskqltest`, with the local demo credentials. Override `MASKQL_SOURCE_URL`, `MASKQL_SOURCE_USER` and `MASKQL_SOURCE_PASSWORD` when needed. Set `MASKQL_ENCRYPT_PASSWORD` to the running server's **test** encryption key to also verify decryption; it is never written to the artifacts.

## Data, rules and expected result

The fixture contains 200 fictional patients in `administrative.patients`. The
[rules](rules.json) grant access with the row filter `patient_id <= 3` and encrypt
the `last_name` column with `encrypt(last_name)`. The [query](query.sql) is:

```sql
SELECT patient_id, last_name
FROM administrative.patients
ORDER BY patient_id;
```

The SQL contains no `WHERE`: the access rule supplies the filter. The expected
result has exactly these three patient IDs, with encrypted names:

| patient_id | Source last_name | Returned last_name |
| --- | --- | --- |
| 1 | Fictional-Martin | Ciphertext of Fictional-Martin |
| 2 | Fictional-Lefèvre | Ciphertext of Fictional-Lefèvre |
| 3 | Fictional-O'Connor | Ciphertext of Fictional-O'Connor |

Patients 4 through 200 must be excluded. Ciphertext depends on the server's
encryption key and context, so these labels are not literal expected SQL values.
The runner checks that each returned name is nonempty and differs from its source;
with the configured test key, it also decrypts the result and compares it exactly
with the three original names in [expected.json](expected.json). The same file
defines the expected source count, visible IDs and preview counts (five raw rows,
three masked rows).

## Verification and saved outputs

The script creates a temporary user and catalog, runs the query before and after
applying the rules, checks all expectations, and removes its temporary resources
in `finally`. Existing users, catalogs, rules and source records are preserved.

Each run creates `results/<timestamp>/`: `input.json` records the 200 synthetic
source rows; `expected.json` preserves the expected result; `result.json` records
the returned patients, actual encrypted names, preview, optional decryption,
checks and cleanup status. A successful run prints `PASS` and sets `passed` to
`true`; a failed check or cleanup exits with an error. Without
`MASKQL_ENCRYPT_PASSWORD`, decryption is explicitly marked as skipped. Use
`--output /tmp/maskql-structured-results` to choose a new output directory.
