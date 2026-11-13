-- Schema from PRD section 14. Change it with a new numbered file, never edit applied files.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (id SERIAL PRIMARY KEY, pseudonym TEXT UNIQUE NOT NULL, display_name TEXT,
  team TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'employee', created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE api_keys (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id), key_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(), revoked_at TIMESTAMPTZ);
CREATE TABLE clients (id SERIAL PRIMARY KEY, name TEXT NOT NULL, aliases TEXT[] DEFAULT '{}');
CREATE TABLE documents (id SERIAL PRIMARY KEY, title TEXT NOT NULL, owner_id INT REFERENCES users(id),
  sensitivity TEXT NOT NULL CHECK (sensitivity IN ('internal','confidential','restricted')),
  dna_enabled BOOLEAN DEFAULT false, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE doc_chunks (id SERIAL PRIMARY KEY, document_id INT REFERENCES documents(id) ON DELETE CASCADE,
  idx INT NOT NULL, minhash BYTEA, embedding vector(384), text_demo TEXT);
CREATE TABLE doc_marks (id SERIAL PRIMARY KEY, document_id INT REFERENCES documents(id) ON DELETE CASCADE,
  position INT NOT NULL, variants TEXT[] NOT NULL);
CREATE TABLE doc_copies (id SERIAL PRIMARY KEY, document_id INT REFERENCES documents(id) ON DELETE CASCADE,
  copy_code TEXT NOT NULL, recipient_user_id INT REFERENCES users(id), variant_vector INT[] NOT NULL);
CREATE TABLE incidents (id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT now(), user_id INT REFERENCES users(id),
  team TEXT, tool TEXT, channel TEXT, decision TEXT NOT NULL, categories TEXT[] DEFAULT '{}',
  document_id INT REFERENCES documents(id), copy_code TEXT, score REAL, reasons JSONB DEFAULT '[]',
  masked_preview TEXT, expires_at TIMESTAMPTZ);
CREATE TABLE session_coverage (user_id INT, document_id INT, chunk_idx INT[] DEFAULT '{}', prompts INT DEFAULT 0,
  window_start TIMESTAMPTZ DEFAULT now(), PRIMARY KEY (user_id, document_id));
CREATE TABLE ai_tools (id SERIAL PRIMARY KEY, name TEXT NOT NULL, vendor TEXT, domains TEXT[] NOT NULL,
  category TEXT, approval TEXT CHECK (approval IN ('approved','tolerated','unapproved')),
  risk TEXT CHECK (risk IN ('low','medium','high')), reason TEXT, alternative TEXT);
CREATE TABLE tool_usage_daily (day DATE, tool_id INT REFERENCES ai_tools(id), team TEXT, users INT, requests INT,
  PRIMARY KEY (day, tool_id, team));
CREATE TABLE policies (id SERIAL PRIMARY KEY, scope TEXT NOT NULL, key TEXT NOT NULL, action TEXT NOT NULL,
  updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now(), UNIQUE (scope, key));
CREATE TABLE reveal_requests (id SERIAL PRIMARY KEY, incident_id BIGINT REFERENCES incidents(id),
  requested_by TEXT NOT NULL, reason TEXT NOT NULL, approved_by TEXT, status TEXT DEFAULT 'pending',
  ts TIMESTAMPTZ DEFAULT now());
CREATE TABLE audit_log (id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT now(), actor TEXT NOT NULL,
  action TEXT NOT NULL, target TEXT, details JSONB DEFAULT '{}');
CREATE TABLE counters_daily (day DATE, team TEXT, allowed INT DEFAULT 0, checked INT DEFAULT 0,
  zero_llm INT DEFAULT 0, llm_tokens INT DEFAULT 0, PRIMARY KEY (day, team));

-- Read-only role for analyst questions (PRD section 13). Views are added with the feature.
CREATE ROLE analyst_ro NOLOGIN;
-- audit_log is append-only for the app role: grant INSERT/SELECT only when the app role is created.
