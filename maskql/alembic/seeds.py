from sqlalchemy import text

def seed_test_data(conn):
    
    conn.execute(text("""
        INSERT INTO catalogs(name, url, sgbd, username, password)
        VALUES ('demo', 'jdbc:postgresql://postgres:5432/demo', 'postgresql', 'postgres', 'postgres')
        ON CONFLICT (id) DO NOTHING
    """))
    conn.execute(text("""
        INSERT INTO users(username, password)
        VALUES ('demo', '$2y$12$VnjzEofIAag/jcy0D/uOj.Uxthaa4S1ccfNiWSNdywec2JOynVmXe')
        ON CONFLICT (id) DO NOTHING
    """))
    
    conn.commit()
