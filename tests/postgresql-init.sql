CREATE DATABASE maskql;
CREATE DATABASE maskqltest;

\connect maskqltest

-- Test purpose 
CREATE TABLE IF NOT EXISTS client (
  id serial PRIMARY KEY,
  name text NOT NULL,
  email text,
  char_code char(100) NOT NULL DEFAULT 'CHAR-SEED-DEFAULT'
);
ALTER TABLE client
  ADD COLUMN IF NOT EXISTS char_code char(100) NOT NULL DEFAULT 'CHAR-SEED-DEFAULT';
INSERT INTO client (name, email, char_code) VALUES
  ('Alice Dupont', 'alice@example.com', 'ALICE-CHAR-CODE'),
  ('Bob Martin', 'bob@example.com', 'BOB-CHAR-CODE'),
  ('Amandine Durant', 'amandine@example.com', 'AMANDINE-CHAR-CODE')
ON CONFLICT DO NOTHING;
UPDATE client
SET char_code = CASE email
  WHEN 'alice@example.com' THEN 'ALICE-CHAR-CODE'
  WHEN 'bob@example.com' THEN 'BOB-CHAR-CODE'
  WHEN 'amandine@example.com' THEN 'AMANDINE-CHAR-CODE'
  ELSE char_code
END
WHERE email IN ('alice@example.com', 'bob@example.com', 'amandine@example.com');


CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL,
    file BYTEA NOT NULL
);
INSERT INTO documents (client_id, file)
VALUES 
  (1, pg_read_binary_file('/docker-entrypoint-initdb.d/example.pdf')),
  (1, pg_read_binary_file('/docker-entrypoint-initdb.d/example2.pdf'));
