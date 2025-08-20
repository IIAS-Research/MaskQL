import os
import uuid
import unittest
import requests
from typing import Optional, Dict, Any, List
from requests.auth import HTTPBasicAuth

API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "8443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")  # use "http" if needed
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = os.getenv("API_VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD_HASH", "admin")
AUTH = HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)

USERS_ENDPOINT = f"{API_BASE_URL}/users"
HEADERS = {"Content-Type": "application/json"}


def _rand_username(prefix: str = "utuser") -> str:
    """Create a short random username."""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class UserApiTests(unittest.TestCase):
    """
    Integration tests for /users router.
        - Admin auth is required on all routes (require_admin_auth).
        - POST /users -> 201 + UserRead (id, username). Business errors -> 400.
        - GET  /users -> 200 + list[UserRead].
        - PATCH /users/{id} -> 200 + UserRead, or 404 if not found.
        - DELETE /users/{id} -> 204, or 404 if not found.
    """

    def setUp(self):
        """Keep track of created user ids so we can clean up."""
        self._created_ids: List[int] = []

    def tearDown(self):
        """Try to delete any user that still exists."""
        for uid in list(self._created_ids):
            try:
                requests.delete(f"{USERS_ENDPOINT}/{uid}", **self._query_params())
            except Exception:
                pass

    # Helpers
    def _query_params(self, with_auth: bool = True) -> Dict[str, Any]:
        """Build common request kwargs."""
        return {
            "headers": HEADERS,
            "timeout": API_TIMEOUT,
            "auth": (AUTH if with_auth else None),
            "verify": API_VERIFY_SSL,
        }

    def _payload(self, *, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """Build a valid user payload."""
        return {
            "username": username or _rand_username(),
            "password": password or "password!",
        }

    def _post_user(self, payload: Dict[str, Any], *, with_auth: bool = True) -> requests.Response:
        """POST /users"""
        return requests.post(USERS_ENDPOINT, json=payload, **self._query_params(with_auth=with_auth))

    def _post_user_with_assert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /users and assert 201. Track the created id."""
        r = self._post_user(payload)
        self.assertEqual(r.status_code, 201, f"POST /users must be 201, got {r.status_code}: {r.text}")
        data = r.json()
        self._created_ids.append(data["id"])
        return data

    def _patch_user(self, user_id: int, payload: Dict[str, Any], *, with_auth: bool = True) -> requests.Response:
        """PATCH /users/{id}"""
        return requests.patch(f"{USERS_ENDPOINT}/{user_id}", json=payload, **self._query_params(with_auth=with_auth))

    def _get_users(self, *, with_auth: bool = True) -> requests.Response:
        """GET /users"""
        return requests.get(USERS_ENDPOINT, **self._query_params(with_auth=with_auth))

    def _delete_user(self, user_id: int, *, with_auth: bool = True) -> requests.Response:
        """DELETE /users/{id}"""
        return requests.delete(f"{USERS_ENDPOINT}/{user_id}", **self._query_params(with_auth=with_auth))

    # Tests

    def test_admin_auth_needed(self):
        """All /users routes must require admin auth."""
        # POST without auth -> 401
        r_post = self._post_user(self._payload(), with_auth=False)
        self.assertEqual(r_post.status_code, 401, f"POST without auth must be 401, got {r_post.status_code}: {r_post.text}")

        # GET without auth -> 401
        r_get = self._get_users(with_auth=False)
        self.assertEqual(r_get.status_code, 401, f"GET without auth must be 401, got {r_get.status_code}: {r_get.text}")

        # PATCH without auth -> 401 (auth check happens before existence check)
        r_patch = self._patch_user(1, {"username": _rand_username()}, with_auth=False)
        self.assertEqual(r_patch.status_code, 401, f"PATCH without auth must be 401, got {r_patch.status_code}: {r_patch.text}")

        # DELETE without auth -> 401
        r_del = self._delete_user(1, with_auth=False)
        self.assertEqual(r_del.status_code, 401, f"DELETE without auth must be 401, got {r_del.status_code}: {r_del.text}")

    def test_register_and_list(self):
        """Create a user, then check it appears in the list."""
        user = self._post_user_with_assert(self._payload())

        # GET list should contain this user
        gl = self._get_users()
        self.assertEqual(gl.status_code, 200, f"GET /users must be 200, got {gl.status_code}: {gl.text}")
        items = gl.json()
        self.assertIsInstance(items, list, "GET /users must return a list")
        ids = {u["id"] for u in items}
        self.assertIn(user["id"], ids)

        # Each item should be a UserRead (no password)
        for it in items:
            self.assertIn("id", it)
            self.assertIn("username", it)
            self.assertNotIn("password", it)

    def test_conflict_on_unique_username(self):
        """
        Creating two users with the same username:
        one should succeed (201), the other should fail with 400 (ValueError -> 400).
        """
        username = _rand_username()
        c1 = self._post_user(self._payload(username=username))
        c2 = self._post_user(self._payload(username=username))

        # Track the one that actually got created
        if c1.status_code == 201:
            self._created_ids.append(c1.json()["id"])
        if c2.status_code == 201:
            self._created_ids.append(c2.json()["id"])

        statuses = sorted([c1.status_code, c2.status_code])
        self.assertEqual(
            statuses,
            [201, 400],
            f"Expected [201, 400] for duplicate username, got {c1.status_code} and {c2.status_code}. "
            f"c1.text={c1.text!r}, c2.text={c2.text!r}",
        )

        # The list should contain the username only once
        gl = self._get_users()
        self.assertEqual(gl.status_code, 200)
        users = [u for u in gl.json() if u["username"] == username]
        self.assertEqual(len(users), 1, f"Expected exactly one '{username}' in list, found {len(users)}")

    def test_patch_username(self):
        """Patch the username of an existing user."""
        user = self._post_user_with_assert(self._payload())

        # Patch only the username
        new_name = _rand_username("renamed")
        r = self._patch_user(user["id"], {"username": new_name})
        self.assertEqual(r.status_code, 200, f"PATCH /users/{user['id']} must be 200, got {r.status_code}: {r.text}")

        data = r.json()
        self.assertEqual(data["id"], user["id"])
        self.assertEqual(data["username"], new_name)
        self.assertNotIn("password", data)

        # Verify the change via list
        gl = self._get_users()
        self.assertEqual(gl.status_code, 200)
        items = gl.json()
        self.assertIn(new_name, {u["username"] for u in items})

    def test_patch_not_found(self):
        """Patching a non-existing user must return 404."""
        r = self._patch_user(999999, {"username": _rand_username("ghost")})
        self.assertEqual(r.status_code, 404, f"PATCH non-existing must be 404, got {r.status_code}: {r.text}")

    def test_delete_and_404(self):
        """Delete a user, then ensure it cannot be found or modified."""
        user = self._post_user_with_assert(self._payload())
        uid = user["id"]

        # Delete should return 204
        d = self._delete_user(uid)
        self.assertEqual(d.status_code, 204, f"DELETE /users/{uid} must be 204, got {d.status_code}: {d.text}")

        # We deleted it ourselves, so remove from cleanup list
        if uid in self._created_ids:
            self._created_ids.remove(uid)

        # The id should not be present in the list anymore
        gl = self._get_users()
        self.assertEqual(gl.status_code, 200)
        ids = {u["id"] for u in gl.json()}
        self.assertNotIn(uid, ids, f"Deleted id {uid} must not be listed")

        # PATCH on the deleted id should return 404
        r = self._patch_user(uid, {"username": _rand_username("afterdel")})
        self.assertEqual(r.status_code, 404, f"PATCH after delete must be 404, got {r.status_code}: {r.text}")

        # DELETE again should return 404
        d2 = self._delete_user(uid)
        self.assertEqual(d2.status_code, 404, f"Second DELETE must be 404, got {d2.status_code}: {d2.text}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
