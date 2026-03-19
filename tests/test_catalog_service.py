import unittest
from unittest.mock import AsyncMock, patch

from maskql.models.catalog import Catalog
from maskql.services.catalog_service import CatalogService, _should_skip_schema


def _catalog(*, sgbd: str) -> Catalog:
    return Catalog(
        name="sample",
        url="jdbc:placeholder://host/db",
        sgbd=sgbd,
        username="user",
        password="password",
    )


class CatalogServiceScanTests(unittest.IsolatedAsyncioTestCase):
    async def test_scan_schema_paths_uses_information_schema_and_skips_sqlserver_system_schemas(self):
        catalog = _catalog(sgbd="sqlserver")
        mocked_trino_sql = AsyncMock(
            side_effect=[
                {
                    "rows": [
                        ["agenda"],
                        ["dbo"],
                        ["sys"],
                        ["db_owner"],
                        ["guest"],
                        ["information_schema"],
                    ]
                },
                {
                    "rows": [
                        ["agenda", "appointments"],
                        ["dbo", "users"],
                        ["sys", "all_columns"],
                    ]
                },
                {
                    "rows": [
                        ["agenda", "appointments", "id"],
                        ["agenda", "appointments", "title"],
                        ["dbo", "users", "id"],
                        ["sys", "all_columns", "name"],
                    ]
                },
            ]
        )

        with patch("maskql.services.catalog_service.trino_sql", mocked_trino_sql):
            paths = await CatalogService._scan_schema_paths(catalog, timeout=5)

        self.assertEqual(
            paths,
            {
                ("agenda", None, None),
                ("agenda", "appointments", None),
                ("agenda", "appointments", "id"),
                ("agenda", "appointments", "title"),
                ("dbo", None, None),
                ("dbo", "users", None),
                ("dbo", "users", "id"),
            },
        )
        self.assertEqual(mocked_trino_sql.await_count, 3)

        statements = [call.args[0] for call in mocked_trino_sql.await_args_list]
        self.assertTrue(all("information_schema" in statement for statement in statements))
        self.assertIn("lower(schema_name) <> 'sys'", statements[0])
        self.assertIn("lower(table_schema) <> 'sys'", statements[1])
        self.assertIn("lower(table_schema) NOT LIKE 'db_%'", statements[2])


class CatalogSchemaSkipTests(unittest.TestCase):
    def test_should_skip_sqlserver_system_schemas_case_insensitively(self):
        catalog = _catalog(sgbd="sqlserver")

        self.assertTrue(_should_skip_schema(catalog, "information_schema"))
        self.assertTrue(_should_skip_schema(catalog, "INFORMATION_SCHEMA"))
        self.assertTrue(_should_skip_schema(catalog, "sys"))
        self.assertTrue(_should_skip_schema(catalog, "SYS"))
        self.assertTrue(_should_skip_schema(catalog, "guest"))
        self.assertTrue(_should_skip_schema(catalog, "db_owner"))
        self.assertFalse(_should_skip_schema(catalog, "dbo"))
        self.assertFalse(_should_skip_schema(catalog, "agenda"))
