"""Run the structured-data example against a seeded MaskQL installation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import string
from datetime import datetime, timezone

import requests
import trino
from trino.auth import BasicAuthentication


HERE = Path(__file__).resolve().parent


def ssl_verify(value):
    if value.lower() in {"false", "no", "0"}:
        return False
    if value.lower() in {"true", "yes", "1"}:
        return True
    return value  # A CA certificate path is also accepted.


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=(
        HERE / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    ))
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=False)
    host = os.getenv("MASKQL_HOST", "localhost")
    port = int(os.getenv("MASKQL_PORT", "443"))
    scheme = os.getenv("MASKQL_SCHEME", "https")
    base_url = f"{scheme}://{host}:{port}/api"
    timeout = float(os.getenv("API_TIMEOUT", "60"))
    verify = os.getenv("API_VERIFY_SSL", "true")
    suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(16))
    catalog_name = "structured" + suffix
    username = "structured_" + suffix
    password = secrets.token_urlsafe(24)
    query = (HERE / "query.sql").read_text(encoding="utf-8").strip().rstrip(";")
    rules = json.loads((HERE / "rules.json").read_text(encoding="utf-8"))["rules"]
    expected = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
    write_json(output / "expected.json", expected)
    fixture = HERE.parents[1] / "tests/fixtures/healthcare.sql"
    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "fixture": "tests/fixtures/healthcare.sql",
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "query": query,
        "rules": rules,
        "expected": expected,
        "checks": {},
        "cleanup": {},
        "passed": False,
    }
    connection = None
    stage = "logging in"

    with requests.Session() as http:
        http.verify = ssl_verify(verify)

        def api(method, path, **kwargs):
            response = http.request(method, base_url + path, timeout=timeout, **kwargs)
            if not response.ok:
                # Responses can include source connection details; do not publish them.
                raise RuntimeError(f"{method} {path}: HTTP {response.status_code}")
            return response.json() if response.content else None

        login = api("POST", "/admin/login", auth=(
            os.getenv("MASKQL_ADMIN_USER", "admin"),
            os.getenv("MASKQL_ADMIN_PASSWORD", "admin"),
        ))
        http.headers["Authorization"] = "Bearer " + login["access_token"]
        original_ids = {
            kind: {item["id"] for item in api("GET", "/" + kind)}
            for kind in ("users", "catalogs")
        }

        try:
            stage = "creating the temporary user and catalog"
            user = api("POST", "/users", json={"username": username, "password": password})
            catalog = api("POST", "/catalogs", json={
                "name": catalog_name,
                "sgbd": "postgresql",
                "url": os.getenv("MASKQL_SOURCE_URL", "jdbc:postgresql://postgres:5432/maskqltest"),
                "username": os.getenv("MASKQL_SOURCE_USER", "postgres"),
                "password": os.getenv("MASKQL_SOURCE_PASSWORD", "postgres"),
            })
            target = {"user_id": user["id"], "catalog_id": catalog["id"]}
            # Read the baseline before adding the filter and encryption mask.
            table_rule = api("POST", "/rules", json={**target, **rules[0], "effect": ""})
            connection = trino.dbapi.connect(
                host=host, port=port, user=username, catalog=catalog_name,
                schema="administrative", http_scheme=scheme,
                auth=BasicAuthentication(username, password),
                verify=ssl_verify(os.getenv("TRINO_VERIFY_SSL", verify)),
                request_timeout=timeout,
            )

            def rows(sql, parameters=None):
                with connection.cursor() as cursor:
                    cursor.execute(sql, parameters)
                    values = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in values]

            stage = "reading the synthetic source"
            source = rows(query)
            assert [row["patient_id"] for row in source] == list(range(1, expected["source_row_count"] + 1)), "Expected patient IDs 1 through 200."
            assert source[:3] == expected["decrypted_rows"], "Source names differ from the fixture."
            assert all(row["last_name"].startswith("Fictional-") for row in source), "Source contains unexpected names."
            write_json(output / "input.json", {"query": query, "row_count": len(source), "rows": source})
            result["checks"]["source_has_200_synthetic_patients"] = True
            result["source_row_count"] = len(source)

            stage = "applying the filter and mask"
            api("PATCH", f"/rules/{table_rule['id']}", json={"effect": rules[0]["effect"]})
            api("POST", "/rules", json={**target, **rules[1]})

            stage = "querying the masked data"
            masked = rows(query)
            result["rows"] = masked
            result["checks"]["only_patient_ids_1_2_3"] = (
                [row["patient_id"] for row in masked] == expected["visible_patient_ids"]
            )
            source_names = {row["patient_id"]: row["last_name"] for row in source}
            result["checks"]["last_names_are_masked"] = bool(masked) and all(
                isinstance(row["last_name"], str) and row["last_name"]
                and row["last_name"] != source_names[row["patient_id"]]
                for row in masked
            )
            assert all(result["checks"].values()), "The row filter or encryption mask did not match expectations."

            stage = "checking the before/after preview API"
            preview = api("POST", f"/catalogs/{catalog['id']}/schema/preview", json={
                "user_id": user["id"], "schema_name": "administrative",
                "table_name": "patients", "limit": expected["preview"]["limit"],
            })
            result["preview"] = preview
            before = preview["before_maskql"]
            after = preview["after_maskql"]
            result["checks"]["preview_has_five_raw_rows"] = (
                before["error"] is None and len(before["rows"]) == expected["preview"]["before_row_count"]
                and all(row["last_name"] == source_names[row["patient_id"]] for row in before["rows"])
            )
            result["checks"]["preview_matches_three_masked_rows"] = (
                after["error"] is None
                and len(after["rows"]) == expected["preview"]["after_row_count"]
                and sorted(
                    ({"patient_id": row["patient_id"], "last_name": row["last_name"]} for row in after["rows"]),
                    key=lambda row: row["patient_id"],
                ) == masked
            )
            assert all(result["checks"].values()), "Before/after preview differs from the SQL results."

            secret = os.getenv("MASKQL_ENCRYPT_PASSWORD")
            if secret:
                stage = "checking decryption with the configured test key"
                decrypted = rows(
                    "SELECT patient_id, decrypt(last_name, ?) AS last_name "
                    "FROM administrative.patients ORDER BY patient_id", [secret],
                )
                result["decrypted_rows"] = decrypted
                result["checks"]["decryption_matches_source"] = decrypted == expected["decrypted_rows"]
                assert result["checks"]["decryption_matches_source"], "Decrypted names differ from the source."
            else:
                result["decryption"] = "Skipped: MASKQL_ENCRYPT_PASSWORD was not supplied."
            result["passed"] = True
        except Exception as error:
            message = str(error)
            for sensitive in (
                password, login["access_token"],
                os.getenv("MASKQL_ADMIN_PASSWORD", "admin"),
                os.getenv("MASKQL_SOURCE_PASSWORD", "postgres"),
                os.getenv("MASKQL_ENCRYPT_PASSWORD"),
            ):
                if sensitive:
                    message = message.replace(sensitive, "[redacted]")
                    message = message.replace(sensitive.replace("'", "''"), "[redacted]")
            result["error"] = {"stage": stage, "type": type(error).__name__, "message": message}
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    result["cleanup"]["connection"] = False
            # Creation can commit before an HTTP error. Discover only our unique
            # names, excluding every resource that existed before this run.
            for kind, key, name in (
                ("catalogs", "name", catalog_name), ("users", "username", username),
            ):
                try:
                    for item in api("GET", "/" + kind):
                        if item[key] == name and item["id"] not in original_ids[kind]:
                            api("DELETE", f"/{kind}/{item['id']}")
                    result["cleanup"][kind] = not any(
                        item[key] == name for item in api("GET", "/" + kind)
                    )
                except Exception:
                    result["cleanup"][kind] = False
            result["passed"] = result["passed"] and all(result["cleanup"].values())
            write_json(output / "result.json", result)

    if not result["passed"]:
        raise SystemExit(f"Example failed; inspect {output / 'result.json'}.")
    print("PASS: 200 source patients -> IDs 1, 2, 3 with encrypted last names.")
    print("Before/after preview verified; temporary user, catalog and rules removed.")
    print(output / "result.json")


if __name__ == "__main__":
    run()
