-- X29 tool approval requests. Safe to run twice; the brain also adds these at start.
ALTER TABLE ai_tools ADD COLUMN IF NOT EXISTS allowed_categories TEXT[];
CREATE TABLE IF NOT EXISTS tool_requests (id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL, requester TEXT NOT NULL, team TEXT NOT NULL,
  tool TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  decided_by TEXT, decided_at TIMESTAMPTZ, note TEXT, risk TEXT,
  allowed_categories TEXT[], alternative TEXT, tool_id INT,
  seen BOOLEAN NOT NULL DEFAULT FALSE);
