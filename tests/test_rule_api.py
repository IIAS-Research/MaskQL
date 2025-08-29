# tests/test_rules_api.py
import os
import uuid
import unittest
import requests
from typing import Optional, Dict, Any, List, Tuple
from requests.auth import HTTPBasicAuth


API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "8443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD_HASH", "admin")
AUTH = HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)

USERS_ENDPOINT = f"{API_BASE_URL}/users"
RULES_ENDPOINT = f"{API_BASE_URL}/rules"
CATALOGS_ENDPOINT = f"{API_BASE_URL}/catalogs"
HEADERS = {"Content-Type": "application/json"}

TEST_CATALOG_ID_ENV = os.getenv("MASKQL_TEST_CATALOG_ID")



def _rand_str(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


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
        """Track created users and rules so we can clean them up."""
        self.catalog_id: int = None
        self._created_rule_ids: List[int] = []
        
        # Create user
        user_payload = {"username": _rand_str("user"), "password": "password!"}
        self.user_id: int = requests.post(USERS_ENDPOINT, json=user_payload, **self._req_kw()).json()['id']

        # Create catalog
        user_payload = {
            "name": _rand_str('catlaog'),
            "url": "jdbc:postgresql://postgres:5432/appdb",
            "sgbd": "postgresql",
            "username": "postgres",
            "password": "postgres",
        }
        self.catalog_id: int = requests.post(CATALOGS_ENDPOINT, json=user_payload, **self._req_kw()).json()['id']


    def tearDown(self):
        """Delete any leftover rules, user and catalog."""
        # Cleanup
        for endpoint, values in [
                        (RULES_ENDPOINT, self._created_rule_ids), 
                        (USERS_ENDPOINT, [self.user_id]),
                        (CATALOGS_ENDPOINT, [self.catalog_id])]:
            for rid in list(values):
                try:
                    requests.delete(f"{endpoint}/{rid}", **self._req_kw())
                except Exception:
                    pass
                
    # HTTP helpers
    def _req_kw(self, *, with_auth: bool = True) -> Dict[str, Any]:
        """Common request kwargs."""
        return {
            "headers": HEADERS,
            "timeout": API_TIMEOUT,
            "auth": (AUTH if with_auth else None),
            "verify": API_VERIFY_SSL,
        }

    def _get_rules(self, *, with_auth=True) -> requests.Response:
        """GET /rules"""
        return requests.get(RULES_ENDPOINT, **self._req_kw(with_auth=with_auth))

    def _get_rule(self, rule_id: int, *, with_auth=True) -> requests.Response:
        """GET /rules/{id}"""
        return requests.get(f"{RULES_ENDPOINT}/{rule_id}", **self._req_kw(with_auth=with_auth))

    def _post_rule(self, payload: Dict[str, Any], *, with_auth=True) -> requests.Response:
        """POST /rules"""
        return requests.post(RULES_ENDPOINT, json=payload, **self._req_kw(with_auth=with_auth))

    def _patch_rule(self, rule_id: int, payload: Dict[str, Any], *, with_auth=True) -> requests.Response:
        """PATCH /rules/{id}"""
        return requests.patch(f"{RULES_ENDPOINT}/{rule_id}", json=payload, **self._req_kw(with_auth=with_auth))

    def _delete_rule(self, rule_id: int, *, with_auth=True) -> requests.Response:
        """DELETE /rules/{id}"""
        return requests.delete(f"{RULES_ENDPOINT}/{rule_id}", **self._req_kw(with_auth=with_auth))


    # Utils
    def _rule_payload(
        self,
        *,
        catalog_id: int,
        user_id: int,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        allow: Optional[bool] = None,
        effect: Optional[str] = None
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

    # Tests
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

        # CREATE
        payload = self._rule_payload(
            catalog_id=self.catalog_id,
            user_id=self.user_id)
        c = self._post_rule(payload)
        self.assertEqual(c.status_code, 201, f"POST /rules must be 201, got {c.status_code}: {c.text}")
        created = c.json()
        rule_id = created['id']
        self._created_rule_ids.append(rule_id)

        # LIST
        gl = self._get_rules()
        self.assertEqual(gl.status_code, 200, f"GET /rules must be 200, got {gl.status_code}: {gl.text}")
        items = gl.json()
        self.assertIsInstance(items, list)
        tuples: List[Tuple[int, int, str]] = [(it.get("catalog_id"), it.get("user_id"), it.get("table_name"), it.get("column_name"), it.get("schema_name")) for it in items]
        self.assertIn((payload["catalog_id"], payload["user_id"], payload["table_name"], payload["column_name"], payload["schema_name"]), tuples)

        # GET /rules/{id}
        g = self._get_rule(rule_id)
        self.assertEqual(g.status_code, 200, f"GET /rules/{rule_id} must be 200, got {g.status_code}: {g.text}")
        body = g.json()
        self.assertEqual((body.get("table_name"), body.get("column_name"), body.get("schema_name")), (payload["table_name"], payload["column_name"], payload["schema_name"]))
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
