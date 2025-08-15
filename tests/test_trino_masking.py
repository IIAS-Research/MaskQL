import os
import unittest
import trino
# from trino.auth import BasicAuthentication


def _connect():
    # TODO make auth work
    # auth = BasicAuthentication(TRINO_USER, TRINO_PASSWORD) if TRINO_PASSWORD else None
    
    return trino.dbapi.connect(
        host=os.getenv("TRINO_HOST", "localhost"),
        port=int(os.getenv("TRINO_PORT", "8080")),
        user=os.getenv("TRINO_USER", "admin"),
        catalog=os.getenv("TRINO_CATALOG", "postgres"),
        schema=os.getenv("TRINO_SCHEMA", "public"),
        http_scheme="http",
        # auth=auth,
    )


class TestTrinoMasking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = _connect()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_trino_alive(self):
        """Check if why can execute a basic SELECT on Trino"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT 1")
            self.assertEqual(cur.fetchone(), [1])

    def test_masking_applied_on_name(self):
        """
        Check if column name is masked by Trino
            - Still be a string
            - Begin by the two first letter
            - If not equal to the real value
            - Must contain *
        """
        cases = [
            ("alice@example.com", "Al", "Alice Dupont"),
            ("bob@example.com",   "Bo", "Bob Martin"),
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

                    self.assertNotEqual(
                        masked, plain_name,
                        f"Name is not masked ({plain_name})",
                    )
                    
                    self.assertTrue(
                        masked.startswith(expected_prefix),
                        f"{masked!r} doesn't begin by {expected_prefix!r}",
                    )
                    
                    self.assertTrue(
                        ("*" in masked),
                        f"Mask pattern (*) not detected in {masked!r}",
                    )