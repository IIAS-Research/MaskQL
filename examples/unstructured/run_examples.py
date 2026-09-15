"""Run the fictional clinical note through MaskQL's text and PDF SQL functions."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import trino
from trino.auth import BasicAuthentication


HERE = Path(__file__).resolve().parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


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
    inputs = {name: (HERE / name).read_bytes() for name in (
        "clinical-note.txt", "clinical-note.pdf", "expected.json"
    )}
    source = inputs["clinical-note.txt"].decode("utf-8")
    expected = json.loads(inputs["expected.json"])
    identifiers = expected["removed_literal_identifiers"]
    if not identifiers or any(not item or item not in source for item in identifiers):
        raise ValueError("Expected identifiers must be nonempty literals present in the source note")
    pdf = base64.b64encode(inputs["clinical-note.pdf"]).decode("ascii")
    args.output.mkdir(parents=True, exist_ok=False)
    queries = {
        "text-pseudo": ("SELECT text_pseudo(?, ?)", [source, args.seed]),
        "pdf-extracted": ("SELECT from_utf8(pdf_to_text(from_base64(?)))", [pdf]),
        "pdf-text-pseudo": ("SELECT text_pseudo(from_utf8(pdf_to_text(from_base64(?))), ?)", [pdf, args.seed]),
        "text-pseudo-repeat": ("SELECT text_pseudo(?, ?)", [source, args.seed]),
        "pdf-text-pseudo-repeat": ("SELECT text_pseudo(from_utf8(pdf_to_text(from_base64(?))), ?)", [pdf, args.seed]),
    }
    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "seed": args.seed,
        "inputs": {name: {"sha256": sha256(data)} for name, data in inputs.items()},
        "expected": expected,
        "queries": {name: sql for name, (sql, _) in queries.items()},
        "results": {},
        "checks": {},
    }
    connection = trino.dbapi.connect(
        **endpoint,
        auth=BasicAuthentication(username, os.getenv("MASKQL_PASSWORD", "demo")) if scheme == "https" else None,
        verify=verify,
        request_timeout=float(os.getenv("TRINO_REQUEST_TIMEOUT", "120")),
        max_attempts=1,
    )
    failures = 0
    values = {}
    try:
        for name, (sql, parameters) in queries.items():
            try:
                value = query(connection, sql, parameters)
                filename = f"{name}.txt"
                (args.output / filename).write_text(value, encoding="utf-8")
                values[name] = value
                report["results"][name] = {
                    "output": filename, "sha256": sha256(value.encode("utf-8"))
                }
                print(f"{name}: OK")
            except Exception as error:
                # Client exceptions can include URLs and connection details.
                report["results"][name] = {"error": {
                    "type": type(error).__name__,
                    "message": "Query failed; inspect the MaskQL/Trino service logs.",
                }}
                failures += 1
                print(f"{name}: failed; see report.json")
        extracted = values.get("pdf-extracted")
        report["checks"]["pdf-extraction-matches-source"] = (
            extracted is not None and extracted.split() == source.split()
        )
        for name, original in (("text-pseudo", source), ("pdf-text-pseudo", extracted)):
            value = values.get(name)
            report["checks"][f"{name}-nonempty"] = bool(value and value.strip())
            report["checks"][f"{name}-changed"] = (
                value is not None and original is not None and value.split() != original.split()
            )
            report["checks"][f"{name}-identifiers-removed"] = (
                value is not None and all(item not in value for item in identifiers)
            )
            report["checks"][f"{name}-repeatable"] = (
                value is not None and value == values.get(f"{name}-repeat")
            )
    finally:
        connection.close()
        checks_passed = sum(report["checks"].values())
        report["summary"] = {
            "queries_passed": len(values), "queries_failed": failures,
            "checks_passed": checks_passed,
            "checks_failed": len(report["checks"]) - checks_passed,
            "success": failures == 0 and len(report["checks"]) == 9 and checks_passed == 9,
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, passed in report["checks"].items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print(args.output / "report.json")
    return 0 if report["summary"]["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
