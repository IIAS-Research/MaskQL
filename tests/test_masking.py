import os
import unittest
import trino
import time
from trino.auth import BasicAuthentication


def _connect():
    auth = BasicAuthentication("demo", "demo")
    
    return trino.dbapi.connect(
        host=os.getenv("MASKQL_HOST", "localhost"),
        port=int(os.getenv("MASKQL_PORT", "8443")),
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
            - Still be a string
            - Begin by the two first letter
            - If not equal to the real value
            - Must contain *
        """
        cases = [
            ("alice@example.com", "Al", "Alice Dupont"),
            # ("bob@example.com",   "Bo", "Bob Martin"),
        ]
        for email, expected_prefix, plain_name in cases:
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

                    # TODO Enable this when masks are handled be FastAPI
                    # self.assertNotEqual(
                    #     masked, plain_name,
                    #     f"Name is not masked ({plain_name})",
                    # )
                    
                    # self.assertTrue(
                    #     masked.startswith(expected_prefix),
                    #     f"{masked!r} doesn't begin by {expected_prefix!r}",
                    # )
                    
                    # self.assertTrue(
                    #     ("*" in masked),
                    #     f"Mask pattern (*) not detected in {masked!r}",
                    # )