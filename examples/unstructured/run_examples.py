"""Run the fictional clinical note through MaskQL's text and PDF SQL functions."""

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import trino
from trino.auth import BasicAuthentication


HERE = Path(__file__).resolve().parent


def query(connection, sql, parameters):
    cursor = connection.cursor()
    try:
        cursor.execute(sql, parameters)
        value = cursor.fetchone()[0]
        if not isinstance(value, str):
            raise ValueError(f"Expected text, received {type(value).__name__}")
        return value
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", default="fictional-patient-142", help="Pseudonymization context, not a password.")
    parser.add_argument("--output", type=Path, default=HERE / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    username = os.getenv("MASKQL_USER", "demo")
    scheme = os.getenv("MASKQL_SCHEME", "https")
    tls_setting = os.getenv("TRINO_VERIFY_SSL", "true")
    if tls_setting.lower() in {"true", "1", "yes"}:
        verify = True
    elif tls_setting.lower() in {"false", "0", "no"}:
        verify = False
    else:
        verify = tls_setting  # Path to the local CA certificate.
    endpoint = {
        "host": os.getenv("MASKQL_HOST", "localhost"),
        "port": int(os.getenv("MASKQL_PORT", "443")),
        "http_scheme": scheme,
        "user": username,
    }
    source = (HERE / "clinical-note.txt").read_text(encoding="utf-8")
    pdf = base64.b64encode((HERE / "clinical-note.pdf").read_bytes()).decode("ascii")
    queries = {
        "text-pseudo": ("SELECT text_pseudo(?, ?)", [source, args.seed]),
        "pdf-extracted": ("SELECT from_utf8(pdf_to_text(from_base64(?)))", [pdf]),
        "pdf-text-pseudo": ("SELECT text_pseudo(from_utf8(pdf_to_text(from_base64(?))), ?)", [pdf, args.seed]),
    }
    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "seed": args.seed,
        "queries": {name: sql for name, (sql, _) in queries.items()},
        "results": {},
    }
    connection = trino.dbapi.connect(
        **endpoint,
        auth=BasicAuthentication(username, os.getenv("MASKQL_PASSWORD", "demo")) if scheme == "https" else None,
        verify=verify,
        request_timeout=float(os.getenv("TRINO_REQUEST_TIMEOUT", "120")),
        max_attempts=1,
    )
    failures = 0
    try:
        for name, (sql, parameters) in queries.items():
            try:
                value = query(connection, sql, parameters)
                filename = f"{name}.txt"
                (args.output / filename).write_text(value, encoding="utf-8")
                report["results"][name] = {"output": filename}
                print(f"{name}: OK")
            except Exception as error:
                report["results"][name] = {"error": str(error)}
                failures += 1
                print(f"{name}: failed; see report.json")
    finally:
        connection.close()
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output / "report.json")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
