"""Write what the gateway decided: an incident for every non-allow, a counter for every check.

Best effort: if the database is down the answer to the user must not fail, so errors are
logged and swallowed. No raw prompt is stored, only the masked preview and the reasons.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain import siem
from brain.db import tables as t

log = logging.getLogger(__name__)
RETENTION_DAYS = 30


def user_row_id(conn: sa.Connection, pseudonym: str, team: str) -> int:
    found = conn.execute(
        sa.select(t.users.c.id).where(t.users.c.pseudonym == pseudonym)
    ).scalar_one_or_none()
    if found is not None:
        return int(found)
    res = conn.execute(
        sa.insert(t.users).values(
            pseudonym=pseudonym, team=team, role="employee", created_at=datetime.now(UTC)
        )
    )
    key = res.inserted_primary_key
    if key is None:
        raise sa.exc.SQLAlchemyError("user id not returned")
    return int(key[0])


def _bump_counter(conn: sa.Connection, day: date, team: str, allowed: bool) -> None:
    where = (t.counters_daily.c.day == day, t.counters_daily.c.team == team)
    exists = conn.execute(
        sa.select(sa.literal(1)).select_from(t.counters_daily).where(*where)
    ).first()
    if exists is None:
        conn.execute(
            sa.insert(t.counters_daily).values(
                day=day, team=team, allowed=int(allowed), checked=1, zero_llm=1, llm_tokens=0
            )
        )
        return
    conn.execute(
        sa.update(t.counters_daily)
        .where(*where)
        .values(
            checked=t.counters_daily.c.checked + 1,
            zero_llm=t.counters_daily.c.zero_llm + 1,
            allowed=t.counters_daily.c.allowed + int(allowed),
        )
    )


def record_decision(
    engine: Engine | None,
    *,
    user: str,
    team: str,
    decision: str,
    categories: list[str],
    reasons: list[str],
    masked_preview: str | None,
    tool: str = "Company AI",
    document_id: int | None = None,
    score: float | None = None,
    copy_code: str | None = None,
    trace: list[dict[str, Any]] | None = None,
    shadow: bool = False,
    channel: str = "gateway",
) -> None:
    if engine is None:
        return
    now = datetime.now(UTC)
    new_id: int | None = None
    try:
        with engine.begin() as conn:
            uid = user_row_id(conn, user, team)
            _bump_counter(conn, now.date(), team, decision == "allow")
            if decision != "allow":
                res = conn.execute(
                    sa.insert(t.incidents).values(
                        ts=now,
                        user_id=uid,
                        team=team,
                        tool=tool,
                        channel=channel,
                        decision=decision,
                        categories=sorted(set(categories)),
                        reasons=reasons,
                        masked_preview=masked_preview,
                        document_id=document_id,
                        score=score,
                        copy_code=copy_code,
                        trace=trace,
                        shadow=shadow,
                        expires_at=now + timedelta(days=RETENTION_DAYS),
                    )
                )
                key = res.inserted_primary_key
                new_id = int(key[0]) if key else None
    except sa.exc.SQLAlchemyError:
        log.warning("Could not record a decision, continuing")
        return
    if decision != "allow":
        # X30: after the row is saved, tell the SOC. The event is built from names fields only.
        siem.push(
            siem.event(
                incident_id=new_id,
                ts=now,
                user_key_id=user,
                team=team,
                tool=tool,
                decision=decision,
                categories=categories,
                document_id=document_id,
                trace=trace,
                shadow=shadow,
            )
        )


def record_ack(engine: Engine | None, user: str, reason: str) -> None:
    """X27: add "sent anyway" to the person's latest browser warning, within the last 10 minutes."""
    if engine is None:
        return
    since = datetime.now(UTC) - timedelta(minutes=10)
    note = "Sent anyway by the user" + (f": {reason.strip()}" if reason.strip() else "")
    try:
        with engine.begin() as conn:
            uid = conn.execute(
                sa.select(t.users.c.id).where(t.users.c.pseudonym == user)
            ).scalar_one_or_none()
            if uid is None:
                return
            row = conn.execute(
                sa.select(t.incidents.c.id, t.incidents.c.reasons)
                .where(
                    t.incidents.c.user_id == uid,
                    t.incidents.c.channel == "browser",
                    t.incidents.c.decision == "warn",
                    t.incidents.c.ts >= since,
                )
                .order_by(t.incidents.c.ts.desc())
                .limit(1)
            ).first()
            if row is None:
                return
            conn.execute(
                sa.update(t.incidents)
                .where(t.incidents.c.id == row.id)
                .values(reasons=[*(row.reasons or []), note])
            )
    except sa.exc.SQLAlchemyError:
        log.warning("Could not record an acknowledgement, continuing")
