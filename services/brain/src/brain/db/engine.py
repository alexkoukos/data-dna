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
