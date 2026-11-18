-- X28 break-it review queue. Safe to run twice; the brain also adds the table at start.
-- Raw text lives here only while a candidate waits for review (approve blanks it, reject deletes the row).
CREATE TABLE IF NOT EXISTS breakit_candidates (id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL, nickname TEXT, kind TEXT NOT NULL,
  expected_decision TEXT NOT NULL, got_decision TEXT NOT NULL, text TEXT,
  preview TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  reviewed_by TEXT, reviewed_at TIMESTAMPTZ, eval_id TEXT);
