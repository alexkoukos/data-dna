-- Browser extension: paired devices and visit telemetry (no page or prompt text). Safe to run twice;
-- the brain also adds these at start.
CREATE TABLE IF NOT EXISTS devices (id SERIAL PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
  user_id INT REFERENCES users(id), team TEXT, label TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS ext_events (id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ NOT NULL,
  user_id INT REFERENCES users(id), team TEXT, tool_id INT REFERENCES ai_tools(id), tool TEXT,
  kind TEXT NOT NULL, action TEXT, expires_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS ext_events_day_idx ON ext_events (ts);
