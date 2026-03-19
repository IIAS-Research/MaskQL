import unittest
from types import SimpleNamespace
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


class CatalogPreviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_table_runs_raw_and_masked_queries(self):
        catalog = _catalog(sgbd="postgresql")
        catalog.id = 7
        mocked_trino_sql = AsyncMock(
            side_effect=[
                {
                    "columns": ["id", "secret"],
                    "rows": [{"id": 1, "secret": "alpha"}],
                },
                {
                    "columns": ["id"],
                    "rows": [{"id": 1}],
                },
            ]
        )

        with (
            patch.object(CatalogService, "get", AsyncMock(return_value=catalog)),
            patch(
                "maskql.services.catalog_service.UserService.get",
                AsyncMock(return_value=SimpleNamespace(username="alice")),
            ),
            patch("maskql.services.catalog_service.trino_sql", mocked_trino_sql),
        ):
            preview = await CatalogService.preview_table(
                7,
                11,
                "public",
                'people"table',
                limit=10,
            )

        self.assertEqual(preview.before_maskql.columns, ["id", "secret"])
        self.assertEqual(preview.after_maskql.columns, ["id"])
        self.assertEqual(preview.before_maskql.rows, [{"id": 1, "secret": "alpha"}])
        self.assertEqual(preview.after_maskql.rows, [{"id": 1}])
        self.assertIsNone(preview.before_maskql.error)
        self.assertIsNone(preview.after_maskql.error)

        statements = [call.args[0] for call in mocked_trino_sql.await_args_list]
        self.assertEqual(
            statements,
            [
                'SELECT * FROM "sample"."public"."people""table" LIMIT 10',
                'SELECT * FROM "sample"."public"."people""table" LIMIT 10',
            ],
        )
        self.assertIsNone(mocked_trino_sql.await_args_list[0].kwargs.get("user"))
        self.assertEqual(mocked_trino_sql.await_args_list[1].kwargs.get("user"), "alice")

    async def test_preview_table_returns_error_payload_when_masked_query_fails(self):
        catalog = _catalog(sgbd="postgresql")
        catalog.id = 7
        mocked_trino_sql = AsyncMock(
            side_effect=[
                {
                    "columns": ["id"],
                    "rows": [{"id": 1}],
                },
                RuntimeError("Access denied for preview"),
            ]
        )

        with (
            patch.object(CatalogService, "get", AsyncMock(return_value=catalog)),
            patch(
                "maskql.services.catalog_service.UserService.get",
                AsyncMock(return_value=SimpleNamespace(username="alice")),
            ),
            patch("maskql.services.catalog_service.trino_sql", mocked_trino_sql),
        ):
            preview = await CatalogService.preview_table(
                7,
                11,
                "public",
                "people",
                limit=10,
            )

        self.assertEqual(preview.before_maskql.rows, [{"id": 1}])
        self.assertEqual(preview.after_maskql.columns, [])
        self.assertEqual(preview.after_maskql.rows, [])
        self.assertIn("Access denied for preview", preview.after_maskql.error)
