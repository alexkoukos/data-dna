-- Schema for both vaults (vault-a and vault-b run the same file). Runs on a fresh volume only.
-- A row holds ONE share of a value plus an integrity tag. Neither vault holds the HMAC key, and
-- neither row on its own says anything about the value.
--   kind 'n' = number (share is an integer in [0, 2^127 - 1)), 's' = text, 'b' = bytes
--   num      = numeric share (kind 'n');  data = XOR share (kind 's' or 'b')
--   tag      = HMAC of this share (tag_a in vault-a, tag_b in vault-b)
--   value_tag = HMAC of the whole value; only vault-b stores it (NULL in vault-a)
CREATE TABLE IF NOT EXISTS shares (
  record_id TEXT NOT NULL,
  field     TEXT NOT NULL,
  kind      CHAR(1) NOT NULL CHECK (kind IN ('n', 's', 'b')),
  num       NUMERIC(39, 0),
  data      BYTEA,
  tag       BYTEA NOT NULL,
  value_tag BYTEA,
  PRIMARY KEY (record_id, field),
  CHECK ((kind = 'n' AND num IS NOT NULL AND data IS NULL)
      OR (kind <> 'n' AND data IS NOT NULL AND num IS NULL))
);
CREATE INDEX IF NOT EXISTS shares_field_idx ON shares (field);
-- Key canary (vault-b only, written by the app): HMAC of a constant under the key. It lets the
-- app say "wrong key" instead of reporting tampering. It reveals nothing about the key.
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value BYTEA NOT NULL);
