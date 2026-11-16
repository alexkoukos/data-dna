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
        conn.execute(sa.text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS trace JSONB"))
        conn.execute(
            sa.text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS shadow BOOLEAN DEFAULT FALSE")
        )
        conn.execute(
            sa.text(
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, "
                "updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now())"
            )
        )
    from brain.ask.free import create_views

    create_views(engine)
