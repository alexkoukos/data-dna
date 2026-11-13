-- X4 honeytokens: decoy credentials planted in documents. Safe to run twice; the brain also adds the table at start.
CREATE TABLE IF NOT EXISTS honeytokens (id SERIAL PRIMARY KEY,
  document_id INT REFERENCES documents(id) ON DELETE CASCADE, kind TEXT NOT NULL,
  value TEXT NOT NULL UNIQUE, created_at TIMESTAMPTZ DEFAULT now());
