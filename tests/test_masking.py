import os
import uuid
import unittest
import trino
import time
import requests
import psycopg
from trino.auth import BasicAuthentication
from requests.auth import HTTPBasicAuth


def _env_ssl_verify(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() not in {"0", "false", "no"}


def _connect():
    auth = BasicAuthentication("demo", "demo")
    
    return trino.dbapi.connect(
        host=os.getenv("MASKQL_HOST", "localhost"),
        port=int(os.getenv("MASKQL_PORT", "443")),
        catalog=os.getenv("MASKQL_CATALOG", "demo"),
        schema=os.getenv("MASKQL_SCHEMA", "public"),
        http_scheme="https",
        auth=auth,
        verify=_env_ssl_verify("TRINO_VERIFY_SSL", os.getenv("API_VERIFY_SSL", "true")),
    )

API_HOST = os.getenv("MASKQL_HOST", "localhost")
API_PORT = os.getenv("MASKQL_PORT", "443")
API_SCHEME = os.getenv("MASKQL_SCHEME", "https")
API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}/api"
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
API_VERIFY_SSL = _env_ssl_verify("API_VERIFY_SSL")

ADMIN_USER = os.getenv("MASKQL_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("MASKQL_ADMIN_PASSWORD", "admin")

LOGIN_ENDPOINT = f"{API_BASE_URL}/admin/login"
LOGOUT_ENDPOINT = f"{API_BASE_URL}/admin/logout"
USERS_ENDPOINT = f"{API_BASE_URL}/users"
RULES_ENDPOINT = f"{API_BASE_URL}/rules"

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("MASKQL_SCHEMA_TEST_DB", "maskqltest")
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


class TestMasking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        time.sleep(5)  # Wait for catalog init
        cls.http = requests.Session()
        cls.http.verify = API_VERIFY_SSL
        cls.http.headers.update({"Content-Type": "application/json"})

        login = cls.http.post(
            LOGIN_ENDPOINT,
            auth=HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD),
            timeout=API_TIMEOUT,
        )
        if login.status_code != 200:
            raise AssertionError(f"Admin login failed: {login.status_code} {login.text}")

        users = cls.http.get(USERS_ENDPOINT, timeout=API_TIMEOUT)
        if users.status_code != 200:
            raise AssertionError(f"Cannot list users: {users.status_code} {users.text}")

        demo_user = next((user for user in users.json() if user["username"] == "demo"), None)
        if demo_user is None:
            raise AssertionError("Seeded demo user not found")

        cls.demo_user_id = demo_user["id"]
        cls.varchar_table = f"masking_varchar_{uuid.uuid4().hex[:8]}"
        cls.partial_table = f"masking_partial_{uuid.uuid4().hex[:8]}"
        cls._created_rule_ids = []

        cls._setup_varchar_fixture()
        cls._setup_partial_access_fixture()
        time.sleep(2)
        cls.conn = _connect()

    @classmethod
    def tearDownClass(cls):
        for rule_id in reversed(getattr(cls, "_created_rule_ids", [])):
            try:
                cls.http.delete(f"{RULES_ENDPOINT}/{rule_id}", timeout=API_TIMEOUT)
            except Exception:
                pass

        try:
            with psycopg.connect(
                host=PG_HOST,
                port=PG_PORT,
                dbname=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"DROP TABLE IF EXISTS {cls.varchar_table}")
                    cur.execute(f"DROP TABLE IF EXISTS {cls.partial_table}")
        except Exception:
            pass

        try:
            cls.http.post(LOGOUT_ENDPOINT, timeout=API_TIMEOUT)
        except Exception:
            pass

        cls.http.close()
        cls.conn.close()

    @classmethod
    def _create_rule(cls, payload):
        response = cls.http.post(RULES_ENDPOINT, json=payload, timeout=API_TIMEOUT)
        if response.status_code not in (200, 201):
            raise AssertionError(f"Cannot create rule: {response.status_code} {response.text}")
        rule = response.json()
        cls._created_rule_ids.append(rule["id"])
        return rule

    @classmethod
    def _setup_varchar_fixture(cls):
        with psycopg.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {cls.varchar_table}")
                cur.execute(
                    f"""
                    CREATE TABLE {cls.varchar_table} (
                        id integer PRIMARY KEY,
                        secret varchar(100) NOT NULL,
                        blocked_value varchar(100) NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"INSERT INTO {cls.varchar_table} (id, secret, blocked_value) VALUES (%s, %s, %s)",
                    (1, "Alpha42", "TopSecret"),
                )

        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.varchar_table,
                "allow": True,
                "effect": "",
            }
        )
        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.varchar_table,
                "column_name": "secret",
                "allow": True,
                "effect": "encrypt(secret)",
            }
        )
        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.varchar_table,
                "column_name": "blocked_value",
                "allow": False,
                "effect": "",
            }
        )

    @classmethod
    def _setup_partial_access_fixture(cls):
        with psycopg.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {cls.partial_table}")
                cur.execute(
                    f"""
                    CREATE TABLE {cls.partial_table} (
                        id integer PRIMARY KEY,
                        allowed_value varchar(100) NOT NULL,
                        blocked_value varchar(100) NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"INSERT INTO {cls.partial_table} (id, allowed_value, blocked_value) VALUES (%s, %s, %s)",
                    (1, "Visible42", "Hidden42"),
                )

        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.partial_table,
                "allow": False,
                "effect": "",
            }
        )
        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.partial_table,
                "column_name": "allowed_value",
                "allow": True,
                "effect": "",
            }
        )

    def _row(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            self.assertIsNotNone(row, "Query returned no row")
            return row

    def test_maskql_alive(self):
        """Check if why can execute a basic SELECT"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1")
            self.assertEqual(cur.fetchone(), [1])

    def test_masking_applied_on_name(self):
        """
        Check if column name is masked
        """
        cases = [
            ("alice@example.com", "Alice Dupont"),
            ("amandine@example.com", "Amandine Durant")
        ]
        for email, plain_name in cases:
            with self.subTest(email=email):
                with self.conn.cursor() as cur:
                    row = cur.execute(
                        "SELECT name FROM client WHERE email = ?",
                        (email,),
                    ).fetchone()
                    
                    # Basic tests
                    self.assertIsNotNone(row, f"No row for {email}")
                    masked = row[0]
                    self.assertIsInstance(masked, str, "name must be a string")

                    self.assertNotEqual(
                        masked, plain_name,
                        f"Name is not masked ({plain_name})",
                    )
                    
    def test_filter_applied_on_name(self):
        """
        Check if row filter is applied of column email
        """
        cases = [
            ("bob@example.com", False),
            ("alice@example.com", True),
            ("amandine@example.com", True)
        ]
        for email, must_be_present in cases:
            with self.subTest(email=email):
                with self.conn.cursor() as cur:
                    row = cur.execute(
                        "SELECT name FROM client WHERE email = ?",
                        (email,),
                    ).fetchone()
                    
                    if must_be_present:
                        self.assertIsNotNone(row, f"No row for {email}, it should be present")
                    else:
                        self.assertIsNone(row, f"Row for {email}, it shouldn't be present")

    def test_encrypt_mask_keeps_queryable_bounded_varchar(self):
        """A masked varchar(n) column must stay queryable without a manual CAST in the rule."""
        row = self._row(
            f"SELECT secret, typeof(secret) FROM {self.varchar_table} LIMIT 1"
        )
        masked, masked_type = row

        self.assertIsInstance(masked, str, "Masked VARCHAR must stay queryable as a string")
        self.assertNotEqual(masked, "Alpha42", "Masked value must differ from the clear text")
        self.assertEqual(masked_type, "varchar(100)", "Mask must preserve the bounded VARCHAR type")

    def test_deny_mask_returns_null_without_hiding_column(self):
        """A denied column must stay selectable, but every value must be replaced by NULL."""
        row = self._row(
            f"SELECT blocked_value, typeof(blocked_value) FROM {self.varchar_table} LIMIT 1"
        )
        blocked_value, blocked_type = row

        self.assertIsNone(blocked_value, "Denied column values must be replaced by NULL")
        self.assertEqual(blocked_type, "varchar(100)", "NULL mask must preserve the original column type")

    def test_table_deny_with_one_allowed_column_keeps_other_columns_null(self):
        """A denied table with one allowed column must remain selectable, masking the rest to NULL."""
        row = self._row(
            f"""
            SELECT
                id,
                allowed_value,
                blocked_value,
                typeof(id),
                typeof(allowed_value),
                typeof(blocked_value)
            FROM {self.partial_table}
            LIMIT 1
            """
        )
        (
            row_id,
            allowed_value,
            blocked_value,
            id_type,
            allowed_type,
            blocked_type,
        ) = row

        self.assertIsNone(row_id, "Columns inherited from a denied table must be masked to NULL")
        self.assertEqual(allowed_value, "Visible42", "Explicitly allowed column must stay readable")
        self.assertIsNone(blocked_value, "Non-allowed columns must be masked to NULL")
        self.assertEqual(id_type, "integer", "NULL mask must preserve the original integer type")
        self.assertEqual(
            allowed_type,
            "varchar(100)",
            "Allowed column must keep its original VARCHAR type",
        )
        self.assertEqual(
            blocked_type,
            "varchar(100)",
            "NULL mask must preserve the original VARCHAR type",
        )
