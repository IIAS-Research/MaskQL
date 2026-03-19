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
CATALOG_STATUS_ENDPOINT = f"{CATALOG_ENDPOINT}/status"
USERS_ENDPOINT = f"{API_BASE_URL}/users"
RULES_ENDPOINT = f"{API_BASE_URL}/rules"
LOGIN_ENDPOINT = f"{API_BASE_URL}/admin/login"
LOGOUT_ENDPOINT = f"{API_BASE_URL}/admin/logout"

HEADERS = {"Content-Type": "application/json"}


def _rand_name(prefix: str = "ut") -> str:
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    return f"{prefix}{suffix}"


class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        self._created_ids: List[int] = []
        self._created_user_ids: List[int] = []
        self._created_rule_ids: List[int] = []
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
        for rid in list(self._created_rule_ids):
            try:
                self.http.delete(f"{RULES_ENDPOINT}/{rid}", timeout=API_TIMEOUT)
            except Exception:
                pass
        for uid in list(self._created_user_ids):
            try:
                self.http.delete(f"{USERS_ENDPOINT}/{uid}", timeout=API_TIMEOUT)
            except Exception:
                pass
        # Logout (cookie supprimé)
        try:
            self.http.post(LOGOUT_ENDPOINT, timeout=API_TIMEOUT)
        except Exception:
            pass

    # Helpers
    def _payload(self, *, name: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        return {
            "name": name or _rand_name(),
            "url": url or "jdbc:postgresql://postgres:5432/appdb",
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

    def test_list_connection_statuses(self):
        item = self._post_catalog_with_assert(self._payload())

        r = self.http.get(CATALOG_STATUS_ENDPOINT, timeout=API_TIMEOUT)
        self.assertEqual(r.status_code, 200, f"GET /catalogs/status failed: {r.status_code} {r.text}")

        items = r.json()
        self.assertIsInstance(items, list)

        by_id = {it["catalog_id"]: it for it in items}
        self.assertIn(item["id"], by_id)

        status = by_id[item["id"]]
        self.assertIn(status["state"], {"ok", "error"})
        self.assertIsInstance(status["message"], str)

    def test_catalog_schema_is_scanned_on_create(self):
        item = self._post_catalog_with_assert(
            self._payload(url="jdbc:postgresql://postgres:5432/maskqltest")
        )

        r = self._get(f"/catalogs/{item['id']}/schema")
        self.assertEqual(r.status_code, 200, f"GET /catalogs/{{id}}/schema failed: {r.status_code} {r.text}")

        entries = r.json()
        self.assertIsInstance(entries, list)
        self.assertTrue(entries, "Expected scanned schema entries right after catalog creation")
        self.assertIn(
            ("public", "client", "name"),
            {
                (it["schema_name"], it["table_name"], it["column_name"])
                for it in entries
            },
        )

    def test_sync_catalog_schema_keeps_valid_rules_and_drops_stale_ones(self):
        catalog = self._post_catalog_with_assert(
            self._payload(url="jdbc:postgresql://postgres:5432/maskqltest")
        )

        user_resp = self.http.post(
            USERS_ENDPOINT,
            json={"username": _rand_name("user"), "password": "password!"},
            timeout=API_TIMEOUT,
        )
        self.assertEqual(user_resp.status_code, 201, f"POST /users failed: {user_resp.status_code} {user_resp.text}")
        user = user_resp.json()
        self._created_user_ids.append(user["id"])

        valid_rule = self.http.post(
            RULES_ENDPOINT,
            json={
                "catalog_id": catalog["id"],
                "user_id": user["id"],
                "schema_name": "public",
                "table_name": "client",
                "column_name": "name",
                "allow": False,
                "effect": "",
            },
            timeout=API_TIMEOUT,
        )
        self.assertEqual(valid_rule.status_code, 201, f"POST /rules valid failed: {valid_rule.status_code} {valid_rule.text}")
        self._created_rule_ids.append(valid_rule.json()["id"])

        stale_rule = self.http.post(
            RULES_ENDPOINT,
            json={
                "catalog_id": catalog["id"],
                "user_id": user["id"],
                "schema_name": "public",
                "table_name": "missing_table",
                "column_name": "ghost_column",
                "allow": True,
                "effect": "",
            },
            timeout=API_TIMEOUT,
        )
        self.assertEqual(stale_rule.status_code, 201, f"POST /rules stale failed: {stale_rule.status_code} {stale_rule.text}")
        self._created_rule_ids.append(stale_rule.json()["id"])

        sync = self.http.post(
            f"{CATALOG_ENDPOINT}/{catalog['id']}/schema/sync",
            timeout=API_TIMEOUT,
        )
        self.assertEqual(sync.status_code, 200, f"POST /catalogs/{{id}}/schema/sync failed: {sync.status_code} {sync.text}")
        body = sync.json()
        self.assertGreaterEqual(body["deleted_rules"], 1)

        rules = self.http.get(
            RULES_ENDPOINT,
            params={"catalog_id": catalog["id"], "user_id": user["id"]},
            timeout=API_TIMEOUT,
        )
        self.assertEqual(rules.status_code, 200, f"GET /rules failed: {rules.status_code} {rules.text}")
        tuples = {
            (it["schema_name"], it["table_name"], it["column_name"])
            for it in rules.json()
        }
        self.assertIn(("public", "client", "name"), tuples)
        self.assertNotIn(("public", "missing_table", "ghost_column"), tuples)
