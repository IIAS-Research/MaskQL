import os
import unittest

import trino
from trino.auth import BasicAuthentication


class TestUnstructuredFunctions(unittest.TestCase):
    def test_text_pseudo_uses_sql_seed(self):
        verify = os.getenv("TRINO_VERIFY_SSL", os.getenv("API_VERIFY_SSL", "true"))
        connection = trino.dbapi.connect(
            host=os.getenv("MASKQL_HOST", "localhost"),
            port=int(os.getenv("MASKQL_PORT", "443")),
            user="demo",
            http_scheme="https",
            auth=BasicAuthentication("demo", "demo"),
            verify=verify.lower() not in {"0", "false", "no"},
        )
        try:
            with connection.cursor() as cursor:
                # One row keeps these calls in the same execution context, so
                # different seeds must affect the replacement, not just timing.
                cursor.execute(
                    """
                    SELECT text_pseudo(body), text_pseudo(body, 'coucou'),
                           text_pseudo(body, patient_seed),
                           text_pseudo(body, CAST(NULL AS VARCHAR)),
                           text_pseudo(CAST(NULL AS VARCHAR), patient_seed)
                    FROM (VALUES (?, ?)) AS t(body, patient_seed)
                    """,
                    ["Medical record (IPP): 8000000142", "patient-é-'142'"],
                )
                legacy, explicit, other_seed, null_seed, null_text = cursor.fetchone()
                self.assertEqual(legacy, explicit)
                self.assertNotEqual(explicit, other_seed)
                for transformed in (explicit, other_seed):
                    self.assertIsInstance(transformed, str)
                    self.assertTrue(transformed)
                    self.assertNotIn("8000000142", transformed)
                self.assertIsNone(null_seed)
                self.assertIsNone(null_text)
        finally:
            connection.close()
