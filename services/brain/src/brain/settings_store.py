"""Small on/off settings kept in the database (X11 shadow mode). Fails safe: off."""

import logging
import time
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.db import tables as t
from brain.policy.store import audit_table

log = logging.getLogger(__name__)
SHADOW = "shadow_mode"


_cache: dict[tuple[int, str], tuple[float, bool]] = {}
_TTL = 3.0


def get_bool(engine: Engine | None, key: str) -> bool:
    """Read a setting, cached for a few seconds so a check never waits for the database."""
    if engine is None:
        return False
    hit = _cache.get((id(engine), key))
    if hit is not None and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    value = _read(engine, key)
    _cache[(id(engine), key)] = (time.monotonic(), value)
    return value


def _read(engine: Engine, key: str) -> bool:
    try:
        with engine.connect() as conn:
            v = conn.execute(sa.select(t.settings.c.value).where(t.settings.c.key == key)).scalar()
    except sa.exc.SQLAlchemyError:
        log.warning("Could not read setting %s, treating it as off", key)
        return False
    return v == "on"


def set_bool(conn: sa.Connection, key: str, on: bool, actor: str) -> None:
    _cache.clear()
    now = datetime.now(UTC)
    value = "on" if on else "off"
    updated = conn.execute(
        sa.update(t.settings)
        .where(t.settings.c.key == key)
        .values(value=value, updated_by=actor, updated_at=now)
    )
    if updated.rowcount == 0:
        conn.execute(
            sa.insert(t.settings).values(key=key, value=value, updated_by=actor, updated_at=now)
        )
    conn.execute(
        sa.insert(audit_table).values(
            ts=now, actor=actor, action="setting.update", target=key, details={"to": value}
        )
    )
