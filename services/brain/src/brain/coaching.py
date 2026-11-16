"""X19: employee coaching. A warning offers a safe rewrite, and we count how many people take it.

Counts only, kept in the settings table, no text is stored.
"""

import sqlalchemy as sa

from brain.db import tables as t

SHOWN = "coaching_shown"
ACCEPTED = "coaching_accepted"


def bump(conn: sa.Connection, key: str) -> None:
    row = conn.execute(sa.select(t.settings.c.value).where(t.settings.c.key == key)).scalar()
    if row is None:
        conn.execute(sa.insert(t.settings).values(key=key, value="1", updated_by="coaching"))
    else:
        conn.execute(
            sa.update(t.settings).where(t.settings.c.key == key).values(value=str(int(row) + 1))
        )


def stats(conn: sa.Connection) -> dict[str, float | int]:
    def get(key: str) -> int:
        v = conn.execute(sa.select(t.settings.c.value).where(t.settings.c.key == key)).scalar()
        return int(v) if v else 0

    shown, accepted = get(SHOWN), get(ACCEPTED)
    return {
        "shown": shown,
        "accepted": accepted,
        "acceptance_rate": round(accepted / shown, 3) if shown else 0.0,
    }
