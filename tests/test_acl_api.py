# tests/test_acl_and_rules.py
import os
import uuid
import unittest
import requests
from typing import Optional, Dict, Any, List
from requests.auth import HTTPBasicAuth

# Config
API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "8443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

# Admin auth for /users and /rules (require_admin_auth)
ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD_HASH", "admin")
AUTH = HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)

HEADERS = {"Content-Type": "application/json"}

USERS_ENDPOINT = f"{API_BASE_URL}/users"
RULES_ENDPOINT = f"{API_BASE_URL}/rules"
ACL_ENDPOINT = f"{API_BASE_URL}/acl"


# Helpers
def _rand_username(prefix: str = "acl_tester") -> str:
    """Create a short random username."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _api_kwargs(with_auth: bool = True) -> Dict[str, Any]:
    """Common request kwargs."""
    return {
        "headers": HEADERS,
        "timeout": API_TIMEOUT,
        "verify": API_VERIFY_SSL,
        "auth": (AUTH if with_auth else None),
    }


class AclAndRulesTests(unittest.TestCase):
    """
    Integration tests for /acl and /rules.
        - A direct rule with allow == false blocks only the focused element.
        - A parent allow makes the child allowed (catalog -> schema -> table -> column).
        - A direct rule with allow == true allows the element even without parent allow.
        - effect carries a row filter (table-level) or a mask (column-level).
    """

    # Test lifecycle
    def setUp(self):
        # track created resources
        self._created_user_id: Optional[int] = None
        self._created_rules: List[int] = []

        # create a fresh test user (so seeded rules do not apply)
        payload = {"username": _rand_username(), "password": "password!"}
        r = requests.post(USERS_ENDPOINT, json=payload, **_api_kwargs(with_auth=True))
        self.assertEqual(r.status_code, 201, f"Cannot create test user: {r.status_code} {r.text}")
        data = r.json()
        self.test_user_id = data["id"]
        self.test_username = data["username"]
        self._created_user_id = self.test_user_id

        self.demo_catalog = "demo"
        self.demo_schema = "public"
        self.demo_table = "client"

    def tearDown(self):
        # delete rules created here
        for rid in list(self._created_rules):
            try:
                requests.delete(f"{RULES_ENDPOINT}/{rid}", **_api_kwargs(with_auth=True))
            except Exception:
                pass

        # delete the test user
        if self._created_user_id is not None:
            try:
                requests.delete(f"{USERS_ENDPOINT}/{self._created_user_id}", **_api_kwargs(with_auth=True))
            except Exception:
                pass

    # Rules API helpers
    def _rule_payload(
        self,
        *,
        user_id: int,
        allow: bool,
        catalog: Optional[str] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        effect: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a RuleCreate payload
        """
        payload: Dict[str, Any] = {"user_id": user_id, "allow": allow}
        if catalog is not None:
            payload["catalog"] = catalog
        if schema_name is not None:
            payload["schema_name"] = schema_name
        if table_name is not None:
            payload["table_name"] = table_name
        if column_name is not None:
            payload["column_name"] = column_name
        if effect is not None:
            payload["effect"] = effect
        return payload

    def _create_rule(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /rules and assert success. Track the id for cleanup."""
        r = requests.post(RULES_ENDPOINT, json=payload, **_api_kwargs(with_auth=True))
        
        self.assertIn(r.status_code, (201, 200), f"POST /rules failed: {r.status_code} {r.text}")
        rule = r.json()
        self._created_rules.append(rule["id"])
        return rule

    # ACL API helpers
    def _acl_post(self, path: str, body: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None):
        url = f"{ACL_ENDPOINT}{path}"
        return requests.post(url, json=body, params=(query or {}), **_api_kwargs(with_auth=False))

    def acl_catalogs(self, user: str, catalogs: List[str]):
        return self._acl_post(f"/{user}/catalog", {"catalogs": catalogs})

    def acl_schemas(self, user: str, catalog: str, schemas: List[str]):
        return self._acl_post(f"/{user}/{catalog}/schemas", {"schemas": schemas})

    def acl_tables(self, user: str, catalog: str, schema: Optional[str], tables: List[str]):
        q = {"schema": schema} if schema else None
        return self._acl_post(f"/{user}/{catalog}/tables", {"tables": tables}, query=q)

    def acl_columns(self, user: str, catalog: str, table: str, schema: Optional[str], columns: List[str]):
        q = {"schema": schema} if schema else None
        return self._acl_post(f"/{user}/{catalog}/{table}/columns", {"columns": columns}, query=q)

    def acl_row_filter(self, user: str, catalog: str, table: str, schema: Optional[str] = None):
        q = {"schema": schema} if schema else None
        return self._acl_post(f"/{user}/{catalog}/{table}/row_filter", query=q)

    def acl_mask(self, user: str, catalog: str, table: str, column: str, schema: Optional[str] = None):
        q = {"schema": schema} if schema else None
        return self._acl_post(f"/{user}/{catalog}/{table}/{column}/mask", query=q)

    def acl_can_access_catalog(self, user: str, catalog: str):
        return self._acl_post(f"/{user}/{catalog}/can_access")

    # Tests
    def test_rules_admin_auth_required(self):
        """All /rules routes must require admin auth."""
        r_post = requests.post(RULES_ENDPOINT, json={"allow": True}, **_api_kwargs(with_auth=False))
        self.assertEqual(r_post.status_code, 401, f"POST /rules without auth must be 401, got {r_post.status_code}: {r_post.text}")

        r_get = requests.get(RULES_ENDPOINT, **_api_kwargs(with_auth=False))
        self.assertEqual(r_get.status_code, 401, f"GET /rules without auth must be 401, got {r_get.status_code}: {r_get.text}")

        r_patch = requests.patch(f"{RULES_ENDPOINT}/1", json={"allow": False}, **_api_kwargs(with_auth=False))
        self.assertEqual(r_patch.status_code, 401, f"PATCH /rules without auth must be 401, got {r_patch.status_code}: {r_patch.text}")

        r_del = requests.delete(f"{RULES_ENDPOINT}/1", **_api_kwargs(with_auth=False))
        self.assertEqual(r_del.status_code, 401, f"DELETE /rules without auth must be 401, got {r_del.status_code}: {r_del.text}")

    def test_acl_default_for_new_user(self):
        """A fresh user has no allow rules, so ACL returns empty/false/empty effects."""
        u = self.test_username

        r1 = self.acl_catalogs(u, [self.demo_catalog, "unknown"])
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(r1.json(), [], "No catalogs should be allowed by default")

        r2 = self.acl_schemas(u, self.demo_catalog, [self.demo_schema, "x"])
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json(), [], "No schemas should be allowed by default")

        r3 = self.acl_tables(u, self.demo_catalog, self.demo_schema, [self.demo_table, "x"])
        self.assertEqual(r3.status_code, 200, r3.text)
        self.assertEqual(r3.json(), [], "No tables should be allowed by default")

        r4 = self.acl_columns(u, self.demo_catalog, self.demo_table, self.demo_schema, ["name", "email"])
        self.assertEqual(r4.status_code, 200, r4.text)
        self.assertEqual(r4.json(), [], "No columns should be allowed by default")

        rf = self.acl_row_filter(u, self.demo_catalog, self.demo_table, self.demo_schema)
        self.assertEqual(rf.status_code, 200, rf.text)
        self.assertEqual(rf.json(), {"filter": ""}, "Row filter is empty for user without rule")

        mk = self.acl_mask(u, self.demo_catalog, self.demo_table, "name", self.demo_schema)
        self.assertEqual(mk.status_code, 200, mk.text)
        self.assertEqual(mk.json(), {"mask": ""}, "Mask is empty for user without rule")

        acc = self.acl_can_access_catalog(u, self.demo_catalog)
        self.assertEqual(acc.status_code, 200, acc.text)
        self.assertEqual(acc.json(), {"allowed": False})

    def test_parent_allow_and_direct_deny(self):
        """Parent allow should propagate; direct deny should block only the focused element."""
        u = self.test_username
        uid = self.test_user_id

        # allow the whole catalog
        self._create_rule(self._rule_payload(user_id=uid, allow=True, catalog=self.demo_catalog))

        # catalog check
        rc = self.acl_catalogs(u, [self.demo_catalog, "other"])
        self.assertEqual(rc.status_code, 200, rc.text)
        self.assertEqual(rc.json(), [self.demo_catalog])

        # schemas in allowed catalog should be allowed
        rs = self.acl_schemas(u, self.demo_catalog, [self.demo_schema, "x"])
        self.assertEqual(rs.status_code, 200, rs.text)
        self.assertIn(self.demo_schema, rs.json())

        # tables in allowed schema should be allowed
        rt = self.acl_tables(u, self.demo_catalog, self.demo_schema, [self.demo_table, "x"])
        self.assertEqual(rt.status_code, 200, rt.text)
        self.assertIn(self.demo_table, rt.json())

        # columns are allowed for now
        cols = ["name", "email"]
        rc1 = self.acl_columns(u, self.demo_catalog, self.demo_table, self.demo_schema, cols)
        self.assertEqual(rc1.status_code, 200, rc1.text)
        self.assertEqual(sorted(rc1.json()), sorted(cols))

        # add a direct deny on a column
        self._create_rule(self._rule_payload(
            user_id=uid, allow=False,
            catalog=self.demo_catalog, schema_name=self.demo_schema,
            table_name=self.demo_table, column_name="email"
        ))

        # now "email" must be filtered out while "name" remains
        rc2 = self.acl_columns(u, self.demo_catalog, self.demo_table, self.demo_schema, cols)
        self.assertEqual(rc2.status_code, 200, rc2.text)
        self.assertEqual(rc2.json(), ["name"])

    def test_direct_allow_without_parent(self):
        """A direct allow on a table should allow it even with no parent allow."""
        u = self.test_username
        uid = self.test_user_id

        # direct allow for one table only
        allowed_table = self.demo_table
        other_table = "x"

        self._create_rule(self._rule_payload(
            user_id=uid, allow=True,
            catalog=self.demo_catalog, schema_name=self.demo_schema, table_name=allowed_table
        ))

        rt = self.acl_tables(u, self.demo_catalog, self.demo_schema, [allowed_table, other_table])
        self.assertEqual(rt.status_code, 200, rt.text)
        
        self.assertEqual(rt.json(), [allowed_table])
        

    def test_row_filter_and_mask_via_effect(self):
        """
        Set table-level filter and column-level mask using 'effect',
        then verify the dedicated endpoints return the exact strings.
        """
        u = self.test_username
        uid = self.test_user_id

        # table filter
        expected_filter = "name like 'Al%'"  # simple filter example
        self._create_rule(self._rule_payload(
            user_id=uid, allow=True,
            catalog=self.demo_catalog, schema_name=self.demo_schema, table_name=self.demo_table,
            effect=expected_filter  # effect is a table row filter here
        ))

        # column mask
        expected_mask = "UPPER(name)"
        self._create_rule(self._rule_payload(
            user_id=uid, allow=True,
            catalog=self.demo_catalog, schema_name=self.demo_schema,
            table_name=self.demo_table, column_name="name",
            effect=expected_mask  # effect is a column mask here
        ))

        # assert row_filter endpoint
        rf = self.acl_row_filter(u, self.demo_catalog, self.demo_table, self.demo_schema)
        self.assertEqual(rf.status_code, 200, rf.text)
        self.assertEqual(rf.json(), {"filter": expected_filter})

        # assert mask endpoint
        mk = self.acl_mask(u, self.demo_catalog, self.demo_table, "name", self.demo_schema)
        self.assertEqual(mk.status_code, 200, mk.text)
        self.assertEqual(mk.json(), {"mask": expected_mask})

    def test_rules_patch_and_delete(self):
        """Flip allow via PATCH then DELETE the rule and check behavior."""
        u = self.test_username
        uid = self.test_user_id

        # ensure parents are allowed
        self._create_rule(self._rule_payload(user_id=uid, allow=True, catalog=self.demo_catalog))
        self._create_rule(self._rule_payload(
            user_id=uid, allow=True,
            catalog=self.demo_catalog, schema_name=self.demo_schema, table_name=self.demo_table
        ))

        # create a deny on column "phone"
        rule = self._create_rule(self._rule_payload(
            user_id=uid, allow=False,
            catalog=self.demo_catalog, schema_name=self.demo_schema,
            table_name=self.demo_table, column_name="phone"
        ))

        r1 = self.acl_columns(u, self.demo_catalog, self.demo_table, self.demo_schema, ["name", "phone"])
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(r1.json(), ["name"])

        # flip allow to True
        rp = requests.patch(f"{RULES_ENDPOINT}/{rule['id']}", json={"allow": True}, **_api_kwargs(with_auth=True))
        self.assertEqual(rp.status_code, 200, f"PATCH /rules must be 200, got {rp.status_code}: {rp.text}")

        r2 = self.acl_columns(u, self.demo_catalog, self.demo_table, self.demo_schema, ["name", "phone"])
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(sorted(r2.json()), sorted(["name", "phone"]))

        # delete the rule
        rd = requests.delete(f"{RULES_ENDPOINT}/{rule['id']}", **_api_kwargs(with_auth=True))
        self.assertEqual(rd.status_code, 204, f"DELETE /rules must be 204, got {rd.status_code}: {rd.text}")

        if rule["id"] in self._created_rules:
            self._created_rules.remove(rule["id"])

    def test_can_access_catalog(self):
        u = self.test_username
        uid = self.test_user_id

        r0 = self.acl_can_access_catalog(u, self.demo_catalog)
        self.assertEqual(r0.status_code, 200)
        self.assertEqual(r0.json(), {"allowed": False})

        self._create_rule(self._rule_payload(user_id=uid, allow=True, catalog=self.demo_catalog))
        r1 = self.acl_can_access_catalog(u, self.demo_catalog)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json(), {"allowed": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)
