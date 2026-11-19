"""Database engine. Empty DATABASE_URL means no database (unit tests, quick local runs)."""

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.config import settings


def make_engine() -> Engine | None:
    if not settings.database_url:
        return None
    return sa.create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def ensure_schema(engine: Engine) -> None:
    """Small additions made after the first release, so an older database keeps working.

    Init files run only on a fresh volume (infra/db/03-doc-chunk-lang.sql does the same thing),
    and a missing column would silently switch document matching off.
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS lang TEXT"))
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS honeytokens (id SERIAL PRIMARY KEY, "
                "document_id INT REFERENCES documents(id) ON DELETE CASCADE, kind TEXT NOT NULL, "
                "value TEXT NOT NULL UNIQUE, created_at TIMESTAMPTZ DEFAULT now())"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS devices (id SERIAL PRIMARY KEY, "
                "token_hash TEXT NOT NULL UNIQUE, user_id INT REFERENCES users(id), team TEXT, "
                "label TEXT, created_at TIMESTAMPTZ DEFAULT now())"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS ext_events (id BIGSERIAL PRIMARY KEY, "
                "ts TIMESTAMPTZ NOT NULL, user_id INT REFERENCES users(id), team TEXT, "
                "tool_id INT REFERENCES ai_tools(id), tool TEXT, kind TEXT NOT NULL, "
                "action TEXT, expires_at TIMESTAMPTZ)"
            )
        )
        conn.execute(sa.text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS trace JSONB"))
        conn.execute(
            sa.text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS shadow BOOLEAN DEFAULT FALSE")
        )
        conn.execute(
            sa.text("ALTER TABLE ai_tools ADD COLUMN IF NOT EXISTS allowed_categories TEXT[]")
        )
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS tool_requests (id SERIAL PRIMARY KEY, "
                "created_at TIMESTAMPTZ NOT NULL, requester TEXT NOT NULL, team TEXT NOT NULL, "
                "tool TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
                "decided_by TEXT, decided_at TIMESTAMPTZ, note TEXT, risk TEXT, "
                "allowed_categories TEXT[], alternative TEXT, tool_id INT, "
                "seen BOOLEAN NOT NULL DEFAULT FALSE)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS breakit_candidates (id SERIAL PRIMARY KEY, "
                "created_at TIMESTAMPTZ NOT NULL, nickname TEXT, kind TEXT NOT NULL, "
                "expected_decision TEXT NOT NULL, got_decision TEXT NOT NULL, text TEXT, "
                "preview TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
                "reviewed_by TEXT, reviewed_at TIMESTAMPTZ, eval_id TEXT)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, "
                "updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now())"
            )
        )
    from brain.ask.free import create_views

    create_views(engine)
