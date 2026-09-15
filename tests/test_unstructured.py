import base64
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import unittest

import trino
from trino.auth import BasicAuthentication


class TestUnstructuredFunctions(unittest.TestCase):
    @staticmethod
    def _connect():
        verify = os.getenv("TRINO_VERIFY_SSL", os.getenv("API_VERIFY_SSL", "true"))
        return trino.dbapi.connect(
            host=os.getenv("MASKQL_HOST", "localhost"),
            port=int(os.getenv("MASKQL_PORT", "443")),
            user="demo",
            http_scheme="https",
            auth=BasicAuthentication("demo", "demo"),
            verify=verify.lower() not in {"0", "false", "no"},
        )

    def test_pdf_to_text(self):
        note = Path(__file__).resolve().parents[1] / "examples/unstructured/clinical-note"
        pdf = base64.b64encode(note.with_suffix(".pdf").read_bytes()).decode("ascii")
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT from_utf8(pdf_to_text(from_base64(?)))", [pdf])
                extracted = cursor.fetchone()[0]
                self.assertEqual(extracted.split(), note.with_suffix(".txt").read_text().split())
        finally:
            connection.close()

    def test_text_pseudo_concurrent_queries_preserve_seed(self):
        def repeated_queries(seed):
            connection = self._connect()
            try:
                with connection.cursor() as cursor:
                    results = []
                    for _ in range(2):
                        cursor.execute(
                            "SELECT text_pseudo(?, ?)",
                            ["Medical record (IPP): 8000000142", seed],
                        )
                        results.append(cursor.fetchone()[0])
                    return results
            finally:
                connection.close()

        # Independent connections exercise reuse across Trino tasks and expose
        # any cross-talk between the model's mutable seed state.
        with ThreadPoolExecutor(max_workers=4) as callers:
            results = list(callers.map(
                repeated_queries,
                ["coucou", "patient-é-'142'", "coucou", "patient-é-'142'"],
            ))
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[1], results[3])
        self.assertNotEqual(results[0][0], results[1][0])
        for first, repeated in results:
            self.assertEqual(first, repeated)
            self.assertIsInstance(first, str)
            self.assertTrue(first)
            self.assertNotIn("8000000142", first)

    def test_text_pseudo_uses_sql_seed(self):
        connection = self._connect()
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
