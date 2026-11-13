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
