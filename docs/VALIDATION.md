# Tests and reproducible examples

## Run the tests

With Docker, Docker Compose, OpenSSL and `uv` installed, run from the repository root:

```bash
uv run tox
```

Tox builds the plugin, loads the healthcare fixture into a fresh `maskql-tox`
stack, runs the Python integration suite, and removes its test containers and volumes.
Java 24+ and Maven are used when available; otherwise the build runs in Docker.
Ports default to 8443 and 15432; override them with `MASKQL_TEST_PORT` and
`MASKQL_TEST_POSTGRES_PORT` if needed.

Results appear in the terminal. Logs stay in `.tox/int/log/`, ignored by Git;
CI retains them as downloadable artifacts for seven days.

Run the frontend tests separately with Node.js and npm:

```bash
npm --prefix frontend ci
npm --prefix frontend run test:unit -- --run
```

## Run the examples

To run just the examples, prepare the dependencies and start a disposable
stack directly:

```bash
uv sync --frozen
uv run --frozen python scripts/test_stack.py start
```

Alternatively, keep the disposable stack after running the full test suite:

```bash
KEEP_TEST_STACK=1 uv run tox
```

Then run both examples against it:

```bash
export MASKQL_HOST=localhost MASKQL_PORT=8443
export MASKQL_ADMIN_USER=admin MASKQL_ADMIN_PASSWORD=admin
export MASKQL_USER=demo MASKQL_PASSWORD=demo
export MASKQL_ENCRYPT_PASSWORD='change-me-16+chars'
export API_VERIFY_SSL=.tox/int/tmp/certs/server.crt.pem
export TRINO_VERIFY_SSL="$API_VERIFY_SSL"
uv run --frozen python examples/structured/run.py
uv run --frozen python examples/unstructured/run_examples.py --seed fictional-patient-142
```

- [Structured data](../examples/structured/README.md): filter 200 patients to three,
  encrypt their names, verify decryption and the before/after preview.
- [Text and PDF](../examples/unstructured/README.md): verify extraction of a
  fictional clinical note from PDF, pseudonymization and repeatability with
  an explicit seed. This is a functional illustration, not an accuracy study.

Outputs are generated in `examples/*/results/`, ignored by Git.
Finally, remove the test stack:

```bash
KEEP_TEST_STACK=0 uv run --frozen python scripts/test_stack.py stop
```
