CREATE TABLE IF NOT EXISTS client (
  id serial PRIMARY KEY,
  name text NOT NULL,
  email text
);
INSERT INTO client (name, email) VALUES
  ('Alice Dupont','alice@example.com'),
  ('Bob Martin','bob@example.com')
ON CONFLICT DO NOTHING;
