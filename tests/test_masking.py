import os
import unittest
import trino
import time
from trino.auth import BasicAuthentication


def _connect():
    auth = BasicAuthentication("demo", "demo")
    
    return trino.dbapi.connect(
        host=os.getenv("MASKQL_HOST", "localhost"),
        port=int(os.getenv("MASKQL_PORT", "443")),
        catalog=os.getenv("MASKQL_CATALOG", "demo"),
        schema=os.getenv("MASKQL_SCHEMA", "public"),
        http_scheme="https",
        auth=auth,
    )


class TestMasking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        time.sleep(5) # Wait for catalog init
        cls.conn = _connect()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

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