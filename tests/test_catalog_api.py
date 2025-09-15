import os
import uuid
import unittest
import requests
from typing import Optional, Dict, Any, List
from requests.auth import HTTPBasicAuth
import random
import string

API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}/api"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD", "admin")  # mot de passe clair attendu par /admin/login
AUTH = HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)

CATALOG_ENDPOINT = f"{API_BASE_URL}/catalogs"
LOGIN_ENDPOINT = f"{API_BASE_URL}/admin/login"
LOGOUT_ENDPOINT = f"{API_BASE_URL}/admin/logout"

HEADERS = {"Content-Type": "application/json"}


def _rand_name(prefix: str = "ut") -> str:
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    return f"{prefix}{suffix}"


class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        self._created_ids: List[int] = []
        # Session avec cookie admin_token
        self.http = requests.Session()
        self.http.verify = API_VERIFY_SSL
        self.http.headers.update(HEADERS)

        # Login admin (Basic pour /admin/login uniquement)
        lr = self.http.post(LOGIN_ENDPOINT, auth=AUTH, timeout=API_TIMEOUT)
        self.assertEqual(lr.status_code, 200, f"Admin login failed: {lr.status_code} {lr.text}")

    def tearDown(self):
        # Delete catalogs créés
        for cid in list(self._created_ids):
            try:
                self.http.delete(f"{CATALOG_ENDPOINT}/{cid}", timeout=API_TIMEOUT)
            except Exception:
                pass
        # Logout (cookie supprimé)
        try:
            self.http.post(LOGOUT_ENDPOINT, timeout=API_TIMEOUT)
        except Exception:
            pass

    # Helpers
    def _payload(self, *, name: Optional[str] = None) -> Dict[str, Any]:
        return {
            "name": name or _rand_name(),
            "url": "jdbc:postgresql://postgres:5432/appdb",
            "sgbd": "postgresql",
            "username": "postgres",
            "password": "postgres",
        }

    def _post_catalog(self, payload: Dict[str, Any], *, with_auth=True):
        if with_auth:
            return self.http.post(CATALOG_ENDPOINT, json=payload, timeout=API_TIMEOUT)
        return requests.post(CATALOG_ENDPOINT, json=payload, headers=HEADERS, verify=API_VERIFY_SSL, timeout=API_TIMEOUT)

    def _post_catalog_with_assert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self._post_catalog(payload)
        self.assertEqual(r.status_code, 201, f"POST error: {r.status_code} {r.text}")
        data = r.json()
        self._created_ids.append(data["id"])
        return data

    def _get(self, path: str):
        return self.http.get(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            timeout=API_TIMEOUT,
        )

    def _put(self, path: str, json: dict):
        return self.http.put(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            json=json,
            timeout=API_TIMEOUT,
        )

    def _patch(self, path: str, json: dict):
        return self.http.patch(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            json=json,
            timeout=API_TIMEOUT,
        )

    def _delete(self, path: str):
        return self.http.delete(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            timeout=API_TIMEOUT,
        )

    # Tests CRUD
    def test_admin_auth_needed(self):
        r = self._post_catalog(self._payload(), with_auth=False)
        self.assertEqual(r.status_code, 401, f"Must be Unauthorized : {r.status_code} {r.text}")

    def test_create_and_get_by_id_and_list(self):
        payload = self._payload()
        created = self._post_catalog_with_assert(payload)
        cid = created["id"]

        # GET by id
        g = self._get(f"/catalogs/{cid}")
        self.assertEqual(g.status_code, 200, f"GET/{cid} failed: {g.status_code} {g.text}")
        self.assertEqual(g.json()["name"], payload["name"])

        # GET list
        gl = self._get("/catalogs")
        self.assertEqual(gl.status_code, 200, f"GET List failed: {gl.status_code} {gl.text}")
        items = gl.json()
        self.assertIsInstance(items, list)
        ids = {it["id"] for it in items}
        self.assertIn(cid, ids)

    def test_conflict_on_unique_name(self):
        name = _rand_name()
        c1 = self._post_catalog(self._payload(name=name))
        c2 = self._post_catalog(self._payload(name=name))

        self.assertEqual(sorted([c1.status_code, c2.status_code]), [201, 409],
                         f"Wanted 201 and 409, received c1={c1.status_code}, c2={c2.status_code}. "
                         f"c1.text={c1.text!r}, c2.text={c2.text!r}")

        created = c1 if c1.status_code == 201 else c2
        rid = created.json()["id"]
        g = self._get(f"/catalogs/{rid}")
        self.assertEqual(g.status_code, 200, f"GET must work id={rid}, received {g.status_code}: {g.text}")

    def test_patch_conflict(self):
        a = self._post_catalog_with_assert(self._payload())
        b = self._post_catalog_with_assert(self._payload())
        # Try to rename a with the same name as b
        conflict = self._patch(f"/catalogs/{a['id']}", self._payload(name=b["name"]))
        self.assertEqual(conflict.status_code, 409, f"Successfully failed 409 , received {conflict.status_code}: {conflict.text}")

    def test_patch_partial(self):
        item = self._post_catalog_with_assert(self._payload())
        patch_doc = {"url": "jdbc:postgresql://postgres:5432/newdb", "username": "newuser"}
        r = self._patch(f"/catalogs/{item['id']}", patch_doc)
        self.assertEqual(r.status_code, 200, f"PATCH failed: {r.status_code} {r.text}")

        data = r.json()
        self.assertEqual(data["url"], patch_doc["url"])
        self.assertEqual(data["username"], patch_doc["username"])
        self.assertEqual(data["name"], item["name"])  # name not updated

        g = self._get(f"/catalogs/{item['id']}")
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()["url"], patch_doc["url"])

    def test_delete_and_404(self):
        item = self._post_catalog_with_assert(self._payload())
        cid = item["id"]

        d = self._delete(f"/catalogs/{cid}")
        self.assertEqual(d.status_code, 204, f"DELETE failed: {d.status_code} {d.text}")

        # Clean up _created_ids because we deleted it manually
        if cid in self._created_ids:
            self._created_ids.remove(cid)

        # Waiting for 404
        g = self._get(f"/catalogs/{cid}")
        self.assertEqual(g.status_code, 404, f"After delete, 404 must be received. {g.status_code}: {g.text}")
