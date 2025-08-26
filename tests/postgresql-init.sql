CREATE DATABASE maskql;
CREATE DATABASE maskqltest;

\connect maskqltest

-- Test purpose 
CREATE TABLE IF NOT EXISTS client (
  id serial PRIMARY KEY,
  name text NOT NULL,
  email text
);
INSERT INTO client (name, email) VALUES
  ('Alice Dupont','alice@example.com'),
  ('Bob Martin','bob@example.com')
ON CONFLICT DO NOTHING;


CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL,
    file BYTEA NOT NULL
);
INSERT INTO documents (client_id, file)
VALUES (
    1,
    pg_read_binary_file('/docker-entrypoint-initdb.d/example.pdf')
);