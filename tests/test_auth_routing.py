import os
import unittest
import socket
import requests
import trino
from trino.auth import BasicAuthentication

MASKQL_HOST = os.getenv("MASKQL_HOST", "localhost")
MASKQL_HTTP_PORT = int(os.getenv("MASKQL_HTTP_PORT", "80"))
MASKQL_HTTPS_PORT = int(os.getenv("MASKQL_HTTPS_PORT", "443"))

TRINO_BACKEND_HOST = os.getenv("TRINO_BACKEND_HOST", "trino")
TRINO_BACKEND_PORT = int(os.getenv("TRINO_BACKEND_PORT", "8080"))

MASKQL_USER = os.getenv("MASKQL_USER", "demo")
MASKQL_PASSWORD = os.getenv("MASKQL_PASSWORD", "demo")
MASKQL_CATALOG = os.getenv("MASKQL_CATALOG", "demo")
MASKQL_SCHEMA = os.getenv("MASKQL_SCHEMA", "public")

HEADERS = {
    "X-Trino-Catalog": MASKQL_CATALOG,
    "X-Trino-Schema": MASKQL_SCHEMA,
}

class TestAuthRouting(unittest.TestCase):
    def _tcp_connect(self, host: str, port: int, timeout=1.5):
        """Return true if TCP socket TCP if open, else False"""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def test_trino_direct_not_routable(self):
        """Test if Trino is directly routable, it must not"""
        reachable = self._tcp_connect(TRINO_BACKEND_HOST, TRINO_BACKEND_PORT, timeout=1.0)
        self.assertFalse(reachable, "Trino's backend should not be directly routable")

    def test_gateway_requires_auth(self):
        """
            MaskQL must requires auth
        """
        r = requests.post(
            f"https://{MASKQL_HOST}:{MASKQL_HTTPS_PORT}/v1/statement",
            headers=HEADERS, data="SELECT 1", timeout=3.0,
        )
        self.assertEqual(r.status_code, 401, f"Must be 401 without auth, received {r.status_code}")

    def test_gateway_https_with_auth_ok(self):
        """
            End-to-end test with auth, must work
        """
        conn = trino.dbapi.connect(
            host=MASKQL_HOST,
            port=MASKQL_HTTPS_PORT,
            user=MASKQL_USER,
            catalog=MASKQL_CATALOG,
            schema=MASKQL_SCHEMA,
            http_scheme="https",
            auth=BasicAuthentication(MASKQL_USER, MASKQL_PASSWORD),
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                self.assertEqual(cur.fetchone(), [1])
        finally:
            conn.close()

    def test_gateway_https_available_and_ok(self):
        """
            Is HTTPS working ?
        """
        # Ping /healthz with HTTPS
        try:
            r = requests.get(f"https://{MASKQL_HOST}:{MASKQL_HTTPS_PORT}/api/healthz",
                            timeout=3.0, verify=False)
        except requests.RequestException as e:
            self.fail(f"No HTTPS access to MaskQL: {e}")

        self.assertEqual(r.status_code, 200, f"/healthz must answer 200 with HTTPS, received {r.status_code}")

        # End-to-end
        conn = trino.dbapi.connect(
            host=MASKQL_HOST,
            port=MASKQL_HTTPS_PORT,
            user=MASKQL_USER,
            catalog=MASKQL_CATALOG,
            schema=MASKQL_SCHEMA,
            http_scheme="https",
            auth=BasicAuthentication(MASKQL_USER, MASKQL_PASSWORD),
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                self.assertEqual(cur.fetchone(), [1])
        finally:
            conn.close()