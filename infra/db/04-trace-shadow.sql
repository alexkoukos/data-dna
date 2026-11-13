-- X23 "Why?" trace and X11 shadow mode. Safe to run twice; the brain also adds these at start.
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS trace JSONB;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS shadow BOOLEAN DEFAULT FALSE;
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now());
