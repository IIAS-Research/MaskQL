from sqlalchemy import text

def seed_test_data(conn):
    
    conn.execute(text("""
        INSERT INTO catalog(id, name, url, sgbd, username, password)
        VALUES (1, 'demo', 'jdbc:postgresql://postgres:5432/demo', 'postgresql', 'postgres', 'postgres')
        ON CONFLICT (id) DO NOTHING
    """))
    
    conn.commit()
