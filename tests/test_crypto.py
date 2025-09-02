import os
import unittest
import trino
import time
from trino.auth import BasicAuthentication


def _connect():
    # Build a secure connection to Trino
    auth = BasicAuthentication("demo", "demo")
    return trino.dbapi.connect(
        host=os.getenv("MASKQL_HOST", "localhost"),
        port=int(os.getenv("MASKQL_PORT", "443")),
        catalog=os.getenv("MASKQL_CATALOG", "demo"),
        schema=os.getenv("MASKQL_SCHEMA", "public"),
        http_scheme="https",
        auth=auth,
    )


class TestCryptoFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        time.sleep(5)
        cls.conn = _connect()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    # Helpers
    def _scalar(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            self.assertIsNotNone(row, "Query returned no row")
            self.assertGreaterEqual(len(row), 1, "Query returned no column")
            return row[0]

    def _row(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            self.assertIsNotNone(row, "Query returned no row")
            return row

    # VARCHAR
    def test_encrypt_decrypt_varchar(self):
        original = "Hello MaskQL"
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS VARCHAR)) AS enc,
                typeof(encrypt(CAST(? AS VARCHAR))) AS enc_type,
                decrypt(encrypt(CAST(? AS VARCHAR))) AS dec,
                typeof(decrypt(encrypt(CAST(? AS VARCHAR)))) AS dec_type
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, str, "Encrypted VARCHAR must be a string")
        self.assertNotEqual(enc, original, "Encrypted VARCHAR must be different")
        self.assertEqual(enc_type, "varchar", "Type must be VARCHAR after encrypt")
        self.assertEqual(dec, original, "Decrypt must restore original VARCHAR")
        self.assertEqual(dec_type, "varchar", "Type must stay VARCHAR after decrypt")

    # VARBINARY
    def test_encrypt_decrypt_varbinary(self):
        original_hex = "00010241FF"
        row = self._row(
            """
            SELECT
                to_hex(encrypt(from_hex(?))) AS enc_hex,
                typeof(encrypt(from_hex(?))) AS enc_type,
                to_hex(decrypt(encrypt(from_hex(?)))) AS dec_hex,
                typeof(decrypt(encrypt(from_hex(?)))) AS dec_type
            """,
            (original_hex, original_hex, original_hex, original_hex),
        )
        enc_hex, enc_type, dec_hex, dec_type = row
        self.assertIsInstance(enc_hex, str, "Encrypted VARBINARY must be hex string")
        self.assertNotEqual(enc_hex, original_hex, "Encrypted VARBINARY must differ")
        self.assertEqual(enc_type, "varbinary", "Type must be VARBINARY after encrypt")
        self.assertEqual(dec_hex, original_hex, "Decrypt must restore original bytes")
        self.assertEqual(dec_type, "varbinary", "Type must stay VARBINARY after decrypt")

    # BIGINT
    def test_encrypt_decrypt_bigint(self):
        original = 9223372036854770000
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS BIGINT)),
                typeof(encrypt(CAST(? AS BIGINT))),
                decrypt(encrypt(CAST(? AS BIGINT))),
                typeof(decrypt(encrypt(CAST(? AS BIGINT))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, int, "Encrypted BIGINT must be an int")
        self.assertNotEqual(enc, original, "Encrypted BIGINT must differ")
        self.assertEqual(enc_type, "bigint")
        self.assertEqual(dec, original, "Decrypt must restore original BIGINT")
        self.assertEqual(dec_type, "bigint")

    # INTEGER
    def test_encrypt_decrypt_integer(self):
        original = 2147481000
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS INTEGER)),
                typeof(encrypt(CAST(? AS INTEGER))),
                decrypt(encrypt(CAST(? AS INTEGER))),
                typeof(decrypt(encrypt(CAST(? AS INTEGER))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, int)
        self.assertNotEqual(enc, original)
        self.assertEqual(enc_type, "integer")
        self.assertEqual(dec, original)
        self.assertEqual(dec_type, "integer")

    # SMALLINT
    def test_encrypt_decrypt_smallint(self):
        original = 12345
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS SMALLINT)),
                typeof(encrypt(CAST(? AS SMALLINT))),
                decrypt(encrypt(CAST(? AS SMALLINT))),
                typeof(decrypt(encrypt(CAST(? AS SMALLINT))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, int)
        self.assertNotEqual(enc, original)
        self.assertEqual(enc_type, "smallint")
        self.assertEqual(dec, original)
        self.assertEqual(dec_type, "smallint")

    # TINYINT
    def test_encrypt_decrypt_tinyint(self):
        original = 123
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS TINYINT)),
                typeof(encrypt(CAST(? AS TINYINT))),
                decrypt(encrypt(CAST(? AS TINYINT))),
                typeof(decrypt(encrypt(CAST(? AS TINYINT))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, int)
        self.assertNotEqual(enc, original)
        self.assertEqual(enc_type, "tinyint")
        self.assertEqual(dec, original)
        self.assertEqual(dec_type, "tinyint")

    # DOUBLE
    def test_encrypt_decrypt_double(self):
        original = 12345.6789
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS DOUBLE)),
                typeof(encrypt(CAST(? AS DOUBLE))),
                decrypt(encrypt(CAST(? AS DOUBLE))),
                typeof(decrypt(encrypt(CAST(? AS DOUBLE))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, float)
        self.assertNotEqual(enc, original)
        self.assertEqual(enc_type, "double")
        self.assertEqual(dec, original)
        self.assertEqual(dec_type, "double")

    # REAL
    def test_encrypt_decrypt_real(self):
        original = 3.1415927
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS REAL)),
                typeof(encrypt(CAST(? AS REAL))),
                decrypt(encrypt(CAST(? AS REAL))),
                typeof(decrypt(encrypt(CAST(? AS REAL))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec, dec_type = row
        self.assertIsInstance(enc, float)
        self.assertNotEqual(enc, original)
        self.assertEqual(enc_type, "real")
        self.assertEqual(dec, original)
        self.assertEqual(dec_type, "real")

    # DATE
    def test_encrypt_decrypt_date(self):
        original = "2024-01-02"
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS DATE)),
                typeof(encrypt(CAST(? AS DATE))),
                CAST(decrypt(encrypt(CAST(? AS DATE))) AS VARCHAR),
                typeof(decrypt(encrypt(CAST(? AS DATE))))
            """,
            (original, original, original, original),
        )
        enc, enc_type, dec_str, dec_type = row
        
        self.assertNotEqual(str(enc), original, "Encrypted DATE must differ")
        self.assertEqual(enc_type, "date")
        self.assertEqual(dec_str, original, "Decrypt must restore original DATE")
        self.assertEqual(dec_type, "date")

    # TIMESTAMP
    def test_encrypt_decrypt_timestamp(self):
        original_ts = "2024-01-02 03:04:05.123"
        row = self._row(
            """
            SELECT
                encrypt(CAST(? AS TIMESTAMP(3))),
                typeof(encrypt(CAST(? AS TIMESTAMP(3)))),
                CAST(decrypt(encrypt(CAST(? AS TIMESTAMP(3)))) AS VARCHAR),
                typeof(decrypt(encrypt(CAST(? AS TIMESTAMP(3)))))
            """,
            (original_ts, original_ts, original_ts, original_ts),
        )
        enc, enc_type, dec_str, dec_type = row
        
        self.assertNotEqual(str(enc), original_ts, "Encrypted TIMESTAMP must differ")
        self.assertEqual(enc_type, "timestamp(3)")
        self.assertEqual(dec_str, original_ts, "Decrypt must restore original TIMESTAMP")
        self.assertEqual(dec_type, "timestamp(3)")


if __name__ == "__main__":
    unittest.main()
