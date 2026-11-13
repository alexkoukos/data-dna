"""Sealed identity (PRD section 12): incidents show a pseudonym. A real name appears only after
one person asks, with a reason, and a different person approves. Every step is written to the
audit log. There is no login yet, so "person" is the name typed in; see PROGRESS.md.
"""

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from brain.api.schemas import IdentityOut, RevealOut
from brain.db import tables as t
from brain.policy.store import audit_table


class RevealError(ValueError):
    """A refusal the person can act on. `status` is the HTTP status to answer with."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


def _out(r: Any) -> RevealOut:
    return RevealOut(
        id=r["id"],
        incident_id=r["incident_id"],
        requested_by=r["requested_by"],
        reason=r["reason"],
        approved_by=r["approved_by"],
        status=r["status"],
        ts=r["ts"],
    )


def _audit(
    conn: sa.Connection, actor: str, action: str, target: str, details: dict[str, Any]
) -> None:
    conn.execute(
        sa.insert(audit_table).values(
            ts=datetime.now(UTC), actor=actor, action=action, target=target, details=details
        )
    )


def _get(conn: sa.Connection, request_id: int) -> Any:
    row = (
        conn.execute(sa.select(t.reveal_requests).where(t.reveal_requests.c.id == request_id))
        .mappings()
        .first()
    )
    if row is None:
        raise RevealError("That reveal request does not exist.", 404)
    return row


def list_for_incident(conn: sa.Connection, incident_id: int) -> list[RevealOut]:
    rows = conn.execute(
        sa.select(t.reveal_requests)
        .where(t.reveal_requests.c.incident_id == incident_id)
        .order_by(t.reveal_requests.c.id.desc())
    ).mappings()
    return [_out(r) for r in rows]


def request_reveal(
    conn: sa.Connection, incident_id: int, requested_by: str, reason: str
) -> RevealOut:
    exists = conn.execute(
        sa.select(t.incidents.c.id).where(t.incidents.c.id == incident_id)
    ).first()
    if exists is None:
        raise RevealError("That incident does not exist.", 404)
    pending = conn.execute(
        sa.select(t.reveal_requests.c.id).where(
            t.reveal_requests.c.incident_id == incident_id,
            t.reveal_requests.c.status == "pending",
        )
    ).first()
    if pending is not None:
        raise RevealError("A reveal request for this incident is already waiting for approval.")
    res = conn.execute(
        sa.insert(t.reveal_requests).values(
            incident_id=incident_id,
            requested_by=requested_by.strip(),
            reason=reason.strip(),
            status="pending",
            ts=datetime.now(UTC),
        )
    )
    key = res.inserted_primary_key
    if key is None:
        raise sa.exc.SQLAlchemyError("request id not returned")
    _audit(
        conn,
        requested_by.strip(),
        "reveal.requested",
        f"incident:{incident_id}",
        {"reason": reason.strip()},
    )
    return _out(_get(conn, int(key[0])))


def decide(conn: sa.Connection, request_id: int, decided_by: str, approve: bool) -> RevealOut:
    row = _get(conn, request_id)
    if row["status"] != "pending":
        raise RevealError("This request has already been decided.")
    who = decided_by.strip()
    if approve and who.casefold() == row["requested_by"].strip().casefold():
        raise RevealError("A second person must approve. You cannot approve your own request.")
    status = "approved" if approve else "denied"
    conn.execute(
        sa.update(t.reveal_requests)
        .where(t.reveal_requests.c.id == request_id)
        .values(status=status, approved_by=who)
    )
    _audit(conn, who, f"reveal.{status}", f"incident:{row['incident_id']}", {"request": request_id})
    return _out(_get(conn, request_id))


def reveal_identity(
    conn: sa.Connection, incident_id: int, request_id: int, viewer: str
) -> IdentityOut:
    row = _get(conn, request_id)
    if row["incident_id"] != incident_id or row["status"] != "approved":
        raise RevealError("This identity is sealed. It needs an approved reveal request.", 403)
    person = conn.execute(
        sa.select(t.users.c.pseudonym, t.users.c.display_name)
        .select_from(t.incidents.join(t.users, t.users.c.id == t.incidents.c.user_id))
        .where(t.incidents.c.id == incident_id)
    ).first()
    if person is None:
        raise RevealError("No person is linked to this incident.", 404)
    _audit(
        conn,
        viewer.strip() or "unknown",
        "identity.revealed",
        f"incident:{incident_id}",
        {"request": request_id},
    )
    return IdentityOut(pseudonym=person[0], display_name=person[1])
