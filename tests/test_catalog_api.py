import os
import time
import uuid
import unittest
import requests
from typing import Optional, Dict, Any, List, Iterable
from requests.auth import HTTPBasicAuth


API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "8443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")  # "http" si besoin
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

API_BASIC_USER = os.getenv("API_BASIC_USER", "test")
API_BASIC_PASS = os.getenv("API_BASIC_PASS", "test")
AUTH = HTTPBasicAuth(API_BASIC_USER, API_BASIC_PASS)

CATALOG_ENDPOINT = f"{API_BASE_URL}/catalogs"
HEADERS = {"Content-Type": "application/json"}

def _rand_name(prefix: str = "ut") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

#############
# Tests API #
#############
class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        self._created_ids: List[int] = []

    def tearDown(self):
        # Delete catalogs
        for cid in list(self._created_ids):
            try:
                requests.delete(
                    f"{CATALOG_ENDPOINT}/{cid}",
                    timeout=API_TIMEOUT,
                    headers=HEADERS,
                    auth=AUTH,
                    verify=API_VERIFY_SSL,
                )
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
        
    def _query_params(self):
        return {'headers': HEADERS,
            'timeout': API_TIMEOUT,
            'auth': AUTH,
            'verify': API_VERIFY_SSL}

    def _post_catalog(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return requests.post(
            CATALOG_ENDPOINT,
            json=payload,
            **self._query_params(),
        )
        
    def _post_catalog_with_assert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = self._post_catalog(payload)
        self.assertIn(r.status_code, (201, 409), f"POST error: {r.status_code} {r.text}")
        if r.status_code == 201:
            data = r.json()
            self._created_ids.append(data["id"])
            return data
        raise AssertionError(f"Unable to create catalog (HTTPS {r.status_code}): {r.text}")

    def _get(self, path: str):
        return requests.get(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            **self._query_params(),
        )

    def _put(self, path: str, json: dict):
        return requests.put(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            json=json,
            **self._query_params(),
        )

    def _patch(self, path: str, json: dict):
        return requests.patch(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            json=json,
            **self._query_params(),
        )

    def _delete(self, path: str):
        return requests.delete(
            f"{API_BASE_URL}{path}" if path.startswith("/") else path,
            **self._query_params(),
        )

    # Tests CRUD

    def test_create_and_get_by_id_and_list(self):
        payload = self._payload()
        created = self._post_catalog_with_assert(payload)
        cid = created["id"]
        self._created_ids.append(cid)

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

    def test_put_replace(self):
        base = self._post_catalog_with_assert(self._payload())
        new_payload = self._payload() # with Random name

        r = self._put(f"/catalogs/{base['id']}", new_payload)
        self.assertEqual(r.status_code, 200, f"PUT failed: {r.status_code} {r.text}")
        updated = r.json()
        self.assertEqual(updated["name"], new_payload["name"])

        # GET to check in base
        g = self._get(f"/catalogs/{base['id']}")
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()["name"], new_payload["name"])

    def test_put_conflict(self):
        a = self._post_catalog_with_assert(self._payload())
        b = self._post_catalog_with_assert(self._payload())
        # Try to rename a with the same name as b
        conflict = self._put(f"/catalogs/{a['id']}", self._payload(name=b["name"]))
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

        # Clean up _created_ids because with deleted it manually
        if cid in self._created_ids:
            self._created_ids.remove(cid)

        # Waiting for 404
        g = self._get(f"/catalogs/{cid}")
        self.assertEqual(g.status_code, 404, f"After delete, 404 must be received. {g.status_code}: {g.text}")

