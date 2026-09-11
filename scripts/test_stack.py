"""Manage the disposable integration stack without touching local development data."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("MASKQL_TEST_WORK_DIR", ROOT / ".tox/int/tmp")).resolve()
ENV = os.environ.copy()
DEFAULTS = {
    "COMPOSE_PROJECT_NAME": "maskql-tox",
    "MASKQL_HOST": "localhost",
    "MASKQL_PORT": "8443",
    "POSTGRES_PORT": "15432",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "MASKQL_ADMIN_USER": "admin",
    "MASKQL_ADMIN_PASSWORD": "admin",
    "MASKQL_ENCRYPT_PASSWORD": "change-me-16+chars",
    "HF_TOKEN": "",
}
for key, value in DEFAULTS.items():
    ENV.setdefault(key, value)
ENV["COMPOSE_PROJECT_NAME"] = ENV.get("MASKQL_TEST_PROJECT", ENV["COMPOSE_PROJECT_NAME"])
ENV["MASKQL_PORT"] = ENV.get("MASKQL_TEST_PORT", ENV["MASKQL_PORT"])
ENV["POSTGRES_PORT"] = ENV.get("MASKQL_TEST_POSTGRES_PORT", ENV["POSTGRES_PORT"])
ENV["MASKQL_TLS_DIR"] = str(WORK / "certs")
ENV["MASKQL_PLUGIN_PROJECT_DIR"] = str(WORK / "plugin")
ENV["MASKQL_PLUGIN_DIR"] = str(WORK / "plugin/target")
ENV["MASKQL_TEST_WORK_DIR"] = str(WORK)
COMPOSE = ["docker", "compose", "--file", str(ROOT / "compose.dev.yml"),
           "--file", str(ROOT / "compose.test.yml"),
           "--profile", "dev", "--env-file", str(ROOT / ".env.example")]


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, env=ENV, check=True, **kwargs)


def compose(*arguments, **kwargs):
    return run([*COMPOSE, *arguments], **kwargs)


def probe_demo():
    from trino.auth import BasicAuthentication
    from trino.dbapi import connect

    connection = connect(
        host=ENV["MASKQL_HOST"], port=int(ENV["MASKQL_PORT"]), http_scheme="https",
        auth=BasicAuthentication("demo", "demo"),
        verify=str(WORK / "certs/server.crt.pem"), request_timeout=5, max_attempts=1,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT patient_id FROM demo.administrative.patients LIMIT 1")
            if cursor.fetchone() is None:
                raise RuntimeError("The healthcare fixture contains no patients")
    finally:
        connection.close()


def start():
    compose("down", "--volumes", "--remove-orphans")
    certs = WORK / "certs"
    certs.mkdir(parents=True, exist_ok=True)
    config = (ROOT / "trino/etc-template/config.properties").read_text()
    (WORK / "config.properties").write_text(config.rstrip() + "\nquery.max-run-time=2m\n")
    run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "7",
         "-keyout", str(certs / "server.key.pem"), "-out", str(certs / "server.crt.pem"),
         "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"])
    plugin = WORK / "plugin"
    if plugin.exists():
        shutil.rmtree(plugin)
    plugin.mkdir()
    source = ROOT / "trino/plugins/maskql-plugin"
    shutil.copy2(source / "pom.xml", plugin / "pom.xml")
    shutil.copytree(source / "src", plugin / "src")
    run(["bash", str(ROOT / "scripts/build-trino-plugin.sh")])
    compose("up", "-d", "--no-build", "reverse-proxy", "postgres", "trino", "maskql-dev")
    deadline = time.monotonic() + 180
    services = ("reverse-proxy", "trino", "maskql-dev")
    last_error = "Services are not healthy yet"
    while time.monotonic() < deadline:
        ready = True
        for service in services:
            result = subprocess.run(
                ["docker", "inspect", f"{ENV['COMPOSE_PROJECT_NAME']}-{service}-1", "--format",
                 "{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}"],
                env=ENV, capture_output=True, text=True, timeout=10,
            )
            ready = ready and result.returncode == 0 and result.stdout.strip() == "healthy"
        if ready:
            try:
                probe_demo()
            except Exception as error:
                last_error = str(error)
            else:
                print(f"Integration stack ready at https://localhost:{ENV['MASKQL_PORT']}", flush=True)
                return
        time.sleep(2)
    raise RuntimeError(f"Integration stack was not ready within 180 seconds: {last_error}")


def stop():
    log = WORK.parent / "log/compose.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log.open("w") as output:
            compose("logs", "--no-color", "--timestamps", stdout=output, stderr=subprocess.STDOUT)
        print(f"Container logs: {log}", flush=True)
    finally:
        if ENV.get("KEEP_TEST_STACK") == "1":
            print("KEEP_TEST_STACK=1: integration stack kept running.", flush=True)
        else:
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop", "status"))
    action = parser.parse_args().action
    project = ENV["COMPOSE_PROJECT_NAME"]
    if project != "maskql-tox" and not project.startswith("maskql-tox-"):
        parser.error("Integration project names must be maskql-tox or start with maskql-tox-")
    {"start": start, "stop": stop, "status": lambda: compose("ps")}[action]()
