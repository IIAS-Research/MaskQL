# Clinical note example

One fictional English note and its searchable PDF exercise `text_pseudo(text, seed)`
and PDF text extraction through MaskQL. All identities are fictional.

Run from the repository root against a running MaskQL instance:

```bash
MASKQL_HOST=localhost MASKQL_PORT=443 \
MASKQL_USER=demo MASKQL_PASSWORD=demo TRINO_VERIFY_SSL=certs/ca.crt.pem \
uv run --frozen python examples/unstructured/run_examples.py --seed fictional-patient-142
```

Adjust the host, port and CA path to your installation. The runner makes three
`SELECT` queries: pseudonymize the note, extract PDF text, and pseudonymize that
extracted text. It binds the input and seed as SQL parameters. `pdf_to_text`
returns UTF-8 bytes, converted with `from_utf8` before calling `text_pseudo`.

## Model lifecycle

Trino loads the EDS pipeline and completes an initial inference while loading
the MaskQL plugin, before its health check reports startup complete. A model
initialization error fails startup and is included in the Trino logs.

Each Trino node keeps one model and one Python interpreter on a dedicated
thread. Calls to `text_pseudo` are processed sequentially on that node, including
calls from concurrent queries; this limits model memory use and isolates each
call's seed. NLP throughput is therefore limited to one inference at a time per
node. During graceful shutdown, the worker closes the interpreter on its owning
thread; the shutdown hook waits up to 10 seconds.

`EDS_PIPELINE_DIR` selects the model repository, which must contain an
`artifacts` directory; it defaults to `/opt/models/eds-pseudo-public` in the
Trino image. The legacy `EDS_REPO` override remains supported and takes
precedence when set.

## Outputs

Outputs and `report.json` (seed, SQL and any query errors) go to
`results/<timestamp>/`, ignored by Git. Use `--output /tmp/maskql-note-results`
to choose a new directory. A failed query produces a nonzero exit status.

To regenerate the PDF after editing the note, without extra dependencies:

```bash
python examples/unstructured/generate_pdf.py
```
