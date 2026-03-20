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

    conn.commit()
