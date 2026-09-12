from sqlalchemy import text

def seed_test_data(conn):
    conn.execute(text("""
        INSERT INTO catalogs(name, url, sgbd, username, password)
        VALUES ('demo', 'jdbc:postgresql://postgres:5432/maskqltest', 'postgresql', 'postgres', 'postgres')
        ON CONFLICT (name) DO UPDATE
        SET
            url = EXCLUDED.url,
            sgbd = EXCLUDED.sgbd,
            username = EXCLUDED.username,
            password = EXCLUDED.password
    """))
    conn.execute(text("""
        INSERT INTO users(username, password)
        VALUES
            ('demo', '$argon2id$v=19$m=65536,t=3,p=4$aU0JYQxBqJUSYkxJiVHKuQ$ubzb5ljGTqoSXxwv58VV2lgM/D1Iu/koIlk29ngwMeg'),
            ('demo1', '$argon2id$v=19$m=65536,t=3,p=4$aU0JYQxBqJUSYkxJiVHKuQ$ubzb5ljGTqoSXxwv58VV2lgM/D1Iu/koIlk29ngwMeg')
        ON CONFLICT (username) DO UPDATE
        SET password = EXCLUDED.password
    """))
    conn.execute(text("""
        INSERT INTO rules(schema_name, table_name, column_name, allow, effect, catalog_id, user_id)
        SELECT 'public', 'client', 'name', true, 'encrypt(name)', c.id, u.id
        FROM catalogs c
        JOIN users u ON u.username = 'demo'
        WHERE c.name = 'demo'
          AND NOT EXISTS (
              SELECT 1
              FROM rules r
              WHERE r.catalog_id = c.id
                AND r.user_id = u.id
                AND r.schema_name = 'public'
                AND r.table_name = 'client'
                AND r.column_name = 'name'
          )
    """))
    conn.execute(text("""
        INSERT INTO rules(schema_name, table_name, column_name, allow, effect, catalog_id, user_id)
        SELECT 'public', 'client', 'char_code', true, 'encrypt(char_code)', c.id, u.id
        FROM catalogs c
        JOIN users u ON u.username = 'demo'
        WHERE c.name = 'demo'
          AND NOT EXISTS (
              SELECT 1
              FROM rules r
              WHERE r.catalog_id = c.id
                AND r.user_id = u.id
                AND r.schema_name = 'public'
                AND r.table_name = 'client'
                AND r.column_name = 'char_code'
          )
    """))
    conn.execute(text("""
        INSERT INTO rules(schema_name, table_name, column_name, allow, effect, catalog_id, user_id)
        SELECT 'public', 'client', NULL, true, 'email like ''a%''', c.id, u.id
        FROM catalogs c
        JOIN users u ON u.username = 'demo'
        WHERE c.name = 'demo'
          AND NOT EXISTS (
              SELECT 1
              FROM rules r
              WHERE r.catalog_id = c.id
                AND r.user_id = u.id
                AND r.schema_name = 'public'
                AND r.table_name = 'client'
                AND r.column_name IS NULL
          )
    """))

    seed_healthcare_rules(conn)
    conn.commit()


def seed_healthcare_rules(conn):
    """Add healthcare examples without replacing rules edited in the UI."""
    rules = [
        ("administrative", None, None, True, ""),
        ("clinical", None, None, True, ""),
        ("research", None, None, True, ""),
        ("administrative", "patients", "last_name", True, "encrypt(last_name)"),
        ("administrative", "patients", "first_name", True, "encrypt(first_name)"),
        ("administrative", "patients", "email", True, "NULL"),
        ("administrative", "patients", "phone", False, ""),
    ]
    for schema, table, column, allow, effect in rules:
        conn.execute(text("""
            INSERT INTO rules(schema_name, table_name, column_name, allow, effect, catalog_id, user_id)
            SELECT CAST(:schema AS text), CAST(:table AS text), CAST(:column AS text),
                   :allow, :effect, c.id, u.id
            FROM catalogs c
            JOIN users u ON u.username = 'demo'
            WHERE c.name = 'demo'
              AND NOT EXISTS (
                  SELECT 1 FROM rules r
                  WHERE r.catalog_id = c.id AND r.user_id = u.id
                    AND r.schema_name = :schema
                    AND r.table_name IS NOT DISTINCT FROM :table
                    AND r.column_name IS NOT DISTINCT FROM :column
              )
        """), {"schema": schema, "table": table, "column": column,
               "allow": allow, "effect": effect})


async def load_healthcare_demo():
    """Finish `make demo-data` on an existing development stack."""
    import os
    from maskql.db import engine
    from maskql.services.catalog_service import CatalogService

    if os.getenv("TEST_ENV") != "true":
        raise RuntimeError("Demo data requires TEST_ENV=true")
    try:
        catalog = await CatalogService.get_by_name("demo")
        if catalog is None or catalog.url != "jdbc:postgresql://postgres:5432/maskqltest":
            raise RuntimeError("The demo catalog must point to the local maskqltest database")
        async with engine.begin() as connection:
            await connection.run_sync(seed_healthcare_rules)
        await CatalogService.sync_schema(catalog.id, ensure_catalog_in_trino=False)
        print("Healthcare demo ready in catalog demo (administrative, clinical, research).")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(load_healthcare_demo())
