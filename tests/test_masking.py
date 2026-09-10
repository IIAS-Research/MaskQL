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
        cls.char_table = f"masking_char_{uuid.uuid4().hex[:8]}"
        cls.partial_table = f"masking_partial_{uuid.uuid4().hex[:8]}"
        cls._created_rule_ids = []

        cls._setup_varchar_fixture()
        cls._setup_char_fixture()
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
                    cur.execute(f"DROP TABLE IF EXISTS {cls.char_table}")
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
    def _setup_char_fixture(cls):
        with psycopg.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {cls.char_table}")
                cur.execute(
                    f"""
                    CREATE TABLE {cls.char_table} (
                        id integer PRIMARY KEY,
                        code char(100) NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"INSERT INTO {cls.char_table} (id, code) VALUES (%s, %s)",
                    (1, "CharSecret42"),
                )

        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.char_table,
                "allow": True,
                "effect": "",
            }
        )
        cls._create_rule(
            {
                "user_id": cls.demo_user_id,
                "catalog": "demo",
                "schema_name": "public",
                "table_name": cls.char_table,
                "column_name": "code",
                "allow": True,
                "effect": "encrypt(code)",
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

    def test_healthcare_patient_identity_is_masked(self):
        """English patient fields keep names encrypted and contacts hidden."""
        cases = [
            (1, "Fictional-Martin", "Élodie"),
            (3, "Fictional-O'Connor", "Élodie"),
        ]
        for patient_id, plain_last_name, plain_first_name in cases:
            with self.subTest(patient_id=patient_id):
                last_name, first_name, email, phone = self._row(
                    "SELECT last_name, first_name, email, phone "
                    "FROM administrative.patients WHERE patient_id = ?",
                    (patient_id,),
                )
                for masked, plain in [(last_name, plain_last_name), (first_name, plain_first_name)]:
                    self.assertIsInstance(masked, str)
                    self.assertTrue(masked)
                    self.assertNotEqual(masked, plain)
                self.assertIsNone(email)
                self.assertIsNone(phone)

    def test_healthcare_tables_are_readable(self):
        """Read values as well as counts to exercise every seeded SQL type."""
        tables = {
            "administrative.departments": 6,
            "administrative.patients": 200,
            "administrative.practitioners": 20,
            "clinical.encounters": 600,
            "clinical.observations": 1800,
            "clinical.prescriptions": 600,
            "clinical.clinical_notes": 200,
            "research.studies": 3,
            "research.consents": 200,
            "research.enrollments": 100,
        }
        for table, expected_count in tables.items():
            with self.subTest(table=table), self.conn.cursor() as cur:
                rows = cur.execute(f"SELECT * FROM {table}").fetchall()
                self.assertEqual(len(rows), expected_count)

    def test_healthcare_relationships(self):
        """Clinical records stay linked and enrollments have prior consent."""
        self.assertEqual(self._row("""
            SELECT count(*), count(DISTINCT p.patient_id), count(DISTINCT e.encounter_id)
            FROM administrative.patients p
            JOIN clinical.encounters e ON e.patient_id = p.patient_id
            JOIN clinical.observations o ON o.encounter_id = e.encounter_id
            JOIN administrative.practitioners pr ON pr.practitioner_id = e.practitioner_id
            WHERE pr.department_id = e.department_id
              AND o.observed_at BETWEEN e.admitted_at AND e.discharged_at
        """), [1800, 200, 600])
        self.assertEqual(self._row("""
            SELECT count(*) FROM research.enrollments e
            JOIN research.consents c ON c.consent_id = e.consent_id
            JOIN research.studies s ON s.study_id = e.study_id
            WHERE c.patient_id = e.patient_id AND c.accepted
              AND c.signed_at <= e.enrolled_at
              AND CAST(e.enrolled_at AS date) >= s.start_date
              AND (s.end_date IS NULL OR CAST(e.enrolled_at AS date) <= s.end_date)
        """), [100])

    def test_seeded_row_filter(self):
        """Check the original client filter without depending on contact masks."""
        cases = [
            (2, False),  # bob@example.com
            (1, True),   # alice@example.com
            (3, True),   # amandine@example.com
        ]
        for client_id, must_be_present in cases:
            with self.subTest(client_id=client_id):
                with self.conn.cursor() as cur:
                    row = cur.execute(
                        "SELECT id FROM public.client WHERE id = ?",
                        (client_id,),
                    ).fetchone()
                    if must_be_present:
                        self.assertIsNotNone(row)
                    else:
                        self.assertIsNone(row)

    def test_encrypt_mask_keeps_queryable_bounded_varchar(self):
        """A masked varchar(n) column must stay queryable without a manual CAST in the rule."""
        row = self._row(
            f"SELECT secret, typeof(secret) FROM {self.varchar_table} LIMIT 1"
        )
        masked, masked_type = row

        self.assertIsInstance(masked, str, "Masked VARCHAR must stay queryable as a string")
        self.assertNotEqual(masked, "Alpha42", "Masked value must differ from the clear text")
        self.assertEqual(masked_type, "varchar(100)", "Mask must preserve the bounded VARCHAR type")

    def test_encrypt_mask_supports_char_column(self):
        """A masked char(n) column must resolve encrypt(char(n)) and stay queryable."""
        row = self._row(
            f"SELECT code, typeof(code) FROM {self.char_table} LIMIT 1"
        )
        masked, masked_type = row

        self.assertIsInstance(masked, str, "Masked CHAR must stay queryable as a string")
        self.assertNotEqual(masked.strip(), "CharSecret42", "Masked value must differ from the clear text")
        self.assertEqual(masked_type, "char(100)", "Mask must preserve the CHAR type")

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
