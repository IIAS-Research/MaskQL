# Clinical note example

One fictional English note and its searchable PDF exercise `text_pseudo(text, seed)`
and PDF text extraction through MaskQL. All identities are fictional. The files
[`clinical-note.txt`](clinical-note.txt) and [`clinical-note.pdf`](clinical-note.pdf)
are supplied, along with [expected results](expected.json).

Run from the repository root against a running MaskQL instance:

```bash
MASKQL_HOST=localhost MASKQL_PORT=443 \
MASKQL_USER=demo MASKQL_PASSWORD=demo TRINO_VERIFY_SSL=certs/server.crt.pem \
uv run --frozen python examples/unstructured/run_examples.py --seed fictional-patient-142
```

Start MaskQL using the [quickstart](../../docs/QUICKSTART.md), then adjust the host,
port and certificate path to your installation. No database import or masking
policy is required: the example directly calls these SQL functions, binding the
input and seed as parameters:

```sql
SELECT text_pseudo(?, ?);
SELECT from_utf8(pdf_to_text(from_base64(?)));
SELECT text_pseudo(from_utf8(pdf_to_text(from_base64(?))), ?);
```

The runner repeats both pseudonymization queries with the same input and seed,
for five `SELECT` calls in total. `pdf_to_text` returns UTF-8 bytes, converted with
`from_utf8` before calling `text_pseudo`. The PDF already contains searchable
text; this example does not exercise OCR of scanned documents.

## Expected results and verification

The runner checks all nine conditions described in [`expected.json`](expected.json):

- Extracted PDF text contains exactly the source note's tokens, in order,
  ignoring whitespace differences introduced by PDF line wrapping.
- Each of the two pseudonymized outputs is nonempty, differs from its input
  beyond whitespace, no longer contains the fictional IPP `8000000142`, and is
  reproduced exactly by a second call with the same seed (four checks per output).

Expected final counts are `queries_passed: 5`, `queries_failed: 0`,
`checks_passed: 9`, `checks_failed: 0`, and `success: true` in `report.json`.
Every check must pass for the runner to exit with status zero. The concrete
pseudonyms are recorded as actual outputs, rather than hard-coded: a model or
dependency update can change them.

This English fixture illustrates function composition and explicit IPP removal.
The EDS model is intended for French clinical text; the checks do not measure
its performance on English notes, nor establish that every identifier was
detected or removed. Review the recorded outputs to see what was transformed.

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

Outputs and `report.json` (input/output SHA-256 hashes, seed, SQL, expected
conditions, individual checks, counts and query error types) go to
`results/<timestamp>/`, ignored by Git. Use `--output /tmp/maskql-note-results`
to choose a new directory. A failed query or check produces a nonzero exit status.
The connection password is not included in the report.

To regenerate the PDF after editing the note, without extra dependencies:

```bash
python examples/unstructured/generate_pdf.py
```
