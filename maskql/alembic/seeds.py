from sqlalchemy import text

def seed_test_data(conn):
    
    conn.execute(text("""
        INSERT INTO catalogs(name, url, sgbd, username, password)
        VALUES ('demo', 'jdbc:postgresql://postgres:5432/demo', 'postgresql', 'postgres', 'postgres')
        ON CONFLICT (id) DO NOTHING
    """))
    conn.execute(text("""
        INSERT INTO users(username, password)
        VALUES
            ('demo', '$argon2id$v=19$m=65536,t=3,p=4$aU0JYQxBqJUSYkxJiVHKuQ$ubzb5ljGTqoSXxwv58VV2lgM/D1Iu/koIlk29ngwMeg'),
            ('demo1', '$argon2id$v=19$m=65536,t=3,p=4$aU0JYQxBqJUSYkxJiVHKuQ$ubzb5ljGTqoSXxwv58VV2lgM/D1Iu/koIlk29ngwMeg')
        ON CONFLICT (id) DO NOTHING
    """))
    conn.execute(text("""
        INSERT INTO rules(path, allow, effect, catalog_id, user_id)
        VALUES 
            ('client.name', true, 'UPPER(name)', 1, 1),
            ('client', true, 'name like \'Al%\'', 1, 1)
        ON CONFLICT (id) DO NOTHING
    """))
    
    conn.commit()
