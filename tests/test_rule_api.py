# tests/test_rules_api.py
import os
import uuid
import unittest
import requests
import random
import string
from typing import Optional, Dict, Any, List, Tuple
from requests.auth import HTTPBasicAuth

API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}/api"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
# /admin/login attend le mot de passe en clair (pas le hash)
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD", "admin")
AUTH = HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)

USERS_ENDPOINT = f"{API_BASE_URL}/users"
RULES_ENDPOINT = f"{API_BASE_URL}/rules"
CATALOGS_ENDPOINT = f"{API_BASE_URL}/catalogs"
LOGIN_ENDPOINT = f"{API_BASE_URL}/admin/login"
LOGOUT_ENDPOINT = f"{API_BASE_URL}/admin/logout"

HEADERS = {"Content-Type": "application/json"}

TEST_CATALOG_ID_ENV = os.getenv("MASKQL_TEST_CATALOG_ID")


def _rand_str(prefix: str) -> str:
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    return f"{prefix}{suffix}"


class RuleApiTests(unittest.TestCase):
    """
    Integration tests for the /rules router.

    What we check:
    - All routes require admin auth.
    - POST /rules -> 201 + RuleRead. Business errors -> 400.
    - GET  /rules -> 200 + list[RuleRead].
    - GET  /rules/{id} -> 200 + RuleRead, or 404 if not found.
    - PATCH /rules/{id} -> 200 + RuleRead, or 404 if not found.
    - DELETE /rules/{id} -> 204, or 404 if not found.

    Notes:
    - Foreign keys must exist (catalog_id and user_id), otherwise 400.
    - For the happy path, set MASKQL_TEST_CATALOG_ID to a valid catalog id.
    """

    def setUp(self):
        """Create authenticated session (cookie) and seed a user & a catalog."""
        self._created_rule_ids: List[int] = []
        self.user_id: Optional[int] = None
        self.catalog_id: Optional[int] = None

        # Session authentifiée via cookie admin_token
        self.http = requests.Session()
        self.http.verify = API_VERIFY_SSL
        self.http.headers.update(HEADERS)

        lr = self.http.post(LOGIN_ENDPOINT, auth=AUTH, timeout=API_TIMEOUT)
        self.assertEqual(lr.status_code, 200, f"Admin login failed: {lr.status_code} {lr.text}")

        # Create user (auth via session)
        user_payload = {"username": _rand_str("user"), "password": "password!"}
        ur = self.http.post(USERS_ENDPOINT, json=user_payload, timeout=API_TIMEOUT)
        self.assertEqual(ur.status_code, 201, f"Create user failed: {ur.status_code} {ur.text}")
        self.user_id = ur.json()["id"]

        # Create catalog (auth via session)
        catalog_payload = {
            "name": _rand_str("catalog"),
            "url": "jdbc:postgresql://postgres:5432/appdb",
            "sgbd": "postgresql",
            "username": "postgres",
            "password": "postgres",
        }
        cr = self.http.post(CATALOGS_ENDPOINT, json=catalog_payload, timeout=API_TIMEOUT)
        self.assertEqual(cr.status_code, 201, f"Create catalog failed: {cr.status_code} {cr.text}")
        self.catalog_id = cr.json()["id"]

    def tearDown(self):
        """Delete any leftover rules, user and catalog, then logout."""
        # Rules
        for rid in list(self._created_rule_ids):
            try:
                self.http.delete(f"{RULES_ENDPOINT}/{rid}", timeout=API_TIMEOUT)
            except Exception:
                pass

        # User
        if self.user_id is not None:
            try:
                self.http.delete(f"{USERS_ENDPOINT}/{self.user_id}", timeout=API_TIMEOUT)
            except Exception:
                pass

        # Catalog
        if self.catalog_id is not None:
            try:
                self.http.delete(f"{CATALOGS_ENDPOINT}/{self.catalog_id}", timeout=API_TIMEOUT)
            except Exception:
                pass

        # Logout (nettoyage cookie)
        try:
            self.http.post(LOGOUT_ENDPOINT, timeout=API_TIMEOUT)
        except Exception:
            pass

    # ---------- HTTP helpers ----------
    def _unauth_kwargs(self) -> Dict[str, Any]:
        """Kwargs pour requêtes SANS auth (pas de cookie) — pour tester les 401."""
        return {"headers": HEADERS, "verify": API_VERIFY_SSL, "timeout": API_TIMEOUT}

    def _get_rules(self, *, with_auth: bool = True) -> requests.Response:
        if with_auth:
            return self.http.get(RULES_ENDPOINT, timeout=API_TIMEOUT)
        return requests.get(RULES_ENDPOINT, **self._unauth_kwargs())

    def _get_rule(self, rule_id: int, *, with_auth: bool = True) -> requests.Response:
        if with_auth:
            return self.http.get(f"{RULES_ENDPOINT}/{rule_id}", timeout=API_TIMEOUT)
        return requests.get(f"{RULES_ENDPOINT}/{rule_id}", **self._unauth_kwargs())

    def _post_rule(self, payload: Dict[str, Any], *, with_auth: bool = True) -> requests.Response:
        if with_auth:
            return self.http.post(RULES_ENDPOINT, json=payload, timeout=API_TIMEOUT)
        return requests.post(RULES_ENDPOINT, json=payload, **self._unauth_kwargs())

    def _patch_rule(self, rule_id: int, payload: Dict[str, Any], *, with_auth: bool = True) -> requests.Response:
        if with_auth:
            return self.http.patch(f"{RULES_ENDPOINT}/{rule_id}", json=payload, timeout=API_TIMEOUT)
        return requests.patch(f"{RULES_ENDPOINT}/{rule_id}", json=payload, **self._unauth_kwargs())

    def _delete_rule(self, rule_id: int, *, with_auth: bool = True) -> requests.Response:
        if with_auth:
            return self.http.delete(f"{RULES_ENDPOINT}/{rule_id}", timeout=API_TIMEOUT)
        return requests.delete(f"{RULES_ENDPOINT}/{rule_id}", **self._unauth_kwargs())

    # ---------- Utils ----------
    def _rule_payload(
        self,
        *,
        catalog_id: int,
        user_id: int,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        allow: Optional[bool] = None,
        effect: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a valid rule payload."""
        return {
            "table_name": table_name or _rand_str("table"),
            "column_name": column_name or _rand_str("column"),
            "schema_name": schema_name or _rand_str("schema"),
            "allow": True if allow is None else allow,
            "effect": effect or "UPPER(column) AS column",
            "catalog_id": catalog_id,
            "user_id": user_id,
        }

    # ---------- Tests ----------
    def test_admin_auth_needed(self):
        """All /rules routes must require admin auth."""
        dummy_payload = {
            "table_name": _rand_str("table"),
            "column_name": _rand_str("column"),
            "schema_name": _rand_str("schema"),
            "allow": True,
            "effect": "MASK(col) AS col",
            "catalog_id": 123456,
            "user_id": 654321,
        }

        # POST without auth -> 401
        r_post = self._post_rule(dummy_payload, with_auth=False)
        self.assertEqual(r_post.status_code, 401, f"POST without auth must be 401, got {r_post.status_code}: {r_post.text}")

        # GET without auth -> 401
        r_get = self._get_rules(with_auth=False)
        self.assertEqual(r_get.status_code, 401, f"GET without auth must be 401, got {r_get.status_code}: {r_get.text}")

        # PATCH without auth -> 401
        r_patch = self._patch_rule(1, {"allow": False}, with_auth=False)
        self.assertEqual(r_patch.status_code, 401, f"PATCH without auth must be 401, got {r_patch.status_code}: {r_patch.text}")

        # DELETE without auth -> 401
        r_del = self._delete_rule(1, with_auth=False)
        self.assertEqual(r_del.status_code, 401, f"DELETE without auth must be 401, got {r_del.status_code}: {r_del.text}")

    def test_create_with_invalid_fks(self):
        """Creating a rule with invalid FKs must return 400."""
        assert self.user_id is not None and self.catalog_id is not None

        # invalid catalog -> 400
        payload = self._rule_payload(catalog_id=-1, user_id=self.user_id)
        r = self._post_rule(payload)
        self.assertEqual(r.status_code, 400, f"POST with invalid catalog_id must be 400, got {r.status_code}: {r.text}")

        # invalid user -> 400
        payload2 = self._rule_payload(catalog_id=self.catalog_id, user_id=-1)
        r2 = self._post_rule(payload2)
        self.assertEqual(r2.status_code, 400, f"POST with invalid user_id must be 400, got {r2.status_code}: {r2.text}")

    def test_full_rule_life(self):
        """Create > list > get > patch > delete for /rules."""
        assert self.user_id is not None and self.catalog_id is not None

        # CREATE
        payload = self._rule_payload(catalog_id=self.catalog_id, user_id=self.user_id)
        c = self._post_rule(payload)
        self.assertEqual(c.status_code, 201, f"POST /rules must be 201, got {c.status_code}: {c.text}")
        created = c.json()
        rule_id = created["id"]
        self._created_rule_ids.append(rule_id)

        # LIST
        gl = self._get_rules()
        self.assertEqual(gl.status_code, 200, f"GET /rules must be 200, got {gl.status_code}: {gl.text}")
        items = gl.json()
        self.assertIsInstance(items, list)
        tuples: List[Tuple[int, int, str, str, str]] = [
            (it.get("catalog_id"), it.get("user_id"), it.get("table_name"), it.get("column_name"), it.get("schema_name"))
            for it in items
        ]
        self.assertIn(
            (payload["catalog_id"], payload["user_id"], payload["table_name"], payload["column_name"], payload["schema_name"]),
            tuples,
        )

        # GET /rules/{id}
        g = self._get_rule(rule_id)
        self.assertEqual(g.status_code, 200, f"GET /rules/{rule_id} must be 200, got {g.status_code}: {g.text}")
        body = g.json()
        self.assertEqual(
            (body.get("table_name"), body.get("column_name"), body.get("schema_name")),
            (payload["table_name"], payload["column_name"], payload["schema_name"]),
        )
        self.assertEqual(body.get("catalog_id"), payload["catalog_id"])
        self.assertEqual(body.get("user_id"), payload["user_id"])

        # PATCH /rules/{id}
        new_mask = "MASK(col1) AS col1"
        p = self._patch_rule(rule_id, {"effect": new_mask, "allow": False})
        self.assertEqual(p.status_code, 200, f"PATCH /rules/{rule_id} must be 200, got {p.status_code}: {p.text}")
        pdata = p.json()
        self.assertEqual(pdata.get("effect"), new_mask)
        self.assertEqual(pdata.get("allow"), False)

        # DELETE /rules/{id}
        d = self._delete_rule(rule_id)
        self.assertEqual(d.status_code, 204, f"DELETE /rules/{rule_id} must be 204, got {d.status_code}: {d.text}")
        # remove from cleanup since it is already gone
        if rule_id in self._created_rule_ids:
            self._created_rule_ids.remove(rule_id)

        # It should not appear in the list anymore
        gl2 = self._get_rules()
        self.assertEqual(gl2.status_code, 200)
        ids = {it.get("id") for it in gl2.json() if "id" in it}
        if ids:  # only if API exposes id in list
            self.assertNotIn(rule_id, ids, f"Deleted rule id {rule_id} must not be listed")

        # GET after delete -> 404
        g404 = self._get_rule(rule_id)
        self.assertEqual(g404.status_code, 404, f"GET after delete must be 404, got {g404.status_code}: {g404.text}")

        # PATCH after delete -> 404
        p404 = self._patch_rule(rule_id, {"allow": True})
        self.assertEqual(p404.status_code, 404, f"PATCH after delete must be 404, got {p404.status_code}: {p404.text}")

        # Second DELETE -> 404
        d404 = self._delete_rule(rule_id)
        self.assertEqual(d404.status_code, 404, f"Second DELETE must be 404, got {d404.status_code}: {d404.text}")
