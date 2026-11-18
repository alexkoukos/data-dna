"""X29: request and approve an AI tool.

An employee asks for a tool, with a reason. A security user approves (with a risk rating, the
data categories the tool may receive and an optional approved alternative) or rejects. Approval
updates `ai_tools`, so the inventory and "risk per tool" change at once. Every step is written
to `audit_log`. Nothing here holds prompt text.
"""

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from brain.db import tables as t
from brain.policy.store import audit_table

RISKS = ("low", "medium", "high")
MAX_PENDING_PER_USER = 5


class RequestError(ValueError):
    """A refusal the person can act on. `status` is the HTTP status to answer with."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


def _audit(
    conn: sa.Connection, actor: str, action: str, target: str, details: dict[str, Any]
) -> None:
    conn.execute(
        sa.insert(audit_table).values(
            ts=datetime.now(UTC), actor=actor, action=action, target=target, details=details
        )
    )


def _find_tool(conn: sa.Connection, name: str) -> Any:
    return (
        conn.execute(
            sa.select(t.ai_tools).where(sa.func.lower(t.ai_tools.c.name) == name.strip().lower())
        )
        .mappings()
        .first()
    )


def create(conn: sa.Connection, *, requester: str, team: str, tool: str, reason: str) -> int:
    tool, reason = tool.strip(), reason.strip()
    if not tool or not reason:
        raise RequestError("Say which tool you need and why.")
    c = t.tool_requests.c
    pending = conn.execute(
        sa.select(sa.func.count()).where(c.requester == requester, c.status == "pending")
    ).scalar_one()
    if pending >= MAX_PENDING_PER_USER:
        raise RequestError("You already have several requests waiting. Wait for a decision.", 429)
    existing = _find_tool(conn, tool)
    if existing is not None and existing["approval"] == "approved":
        raise RequestError(f"{existing['name']} is already approved. You can use it.", 409)
    res = conn.execute(
        sa.insert(t.tool_requests).values(
            created_at=datetime.now(UTC),
            requester=requester,
            team=team,
            tool=tool,
            reason=reason,
            status="pending",
            tool_id=existing["id"] if existing is not None else None,
        )
    )
    key = res.inserted_primary_key
    if key is None:
        raise sa.exc.SQLAlchemyError("request id not returned")
    rid = int(key[0])
    _audit(conn, requester, "tool.request", str(rid), {"tool": tool, "team": team})
    return rid


def get(conn: sa.Connection, request_id: int) -> dict[str, Any]:
    row = (
        conn.execute(sa.select(t.tool_requests).where(t.tool_requests.c.id == request_id))
        .mappings()
        .first()
    )
    if row is None:
        raise RequestError("That request does not exist.", 404)
    return dict(row)


def listing(conn: sa.Connection, status: str | None = None) -> list[dict[str, Any]]:
    q = sa.select(t.tool_requests).order_by(
        t.tool_requests.c.created_at.desc(), t.tool_requests.c.id.desc()
    )
    if status:
        q = q.where(t.tool_requests.c.status == status)
    return [dict(r) for r in conn.execute(q).mappings()]


def decide(
    conn: sa.Connection,
    request_id: int,
    *,
    reviewer: str,
    approve: bool,
    risk: str | None,
    allowed_categories: list[str],
    alternative: str | None,
    note: str,
) -> dict[str, Any]:
    row = get(conn, request_id)
    if row["status"] != "pending":
        raise RequestError("This request was already decided.", 409)
    now = datetime.now(UTC)
    tool_id = row["tool_id"]
    if approve:
        if risk not in RISKS:
            raise RequestError("Give the tool a risk rating: low, medium or high.")
        existing = _find_tool(conn, row["tool"])
        values = {
            "approval": "approved",
            "risk": risk,
            "allowed_categories": sorted(set(allowed_categories)),
            "alternative": (alternative or None),
            "reason": row["reason"][:300],
        }
        if existing is not None:
            tool_id = existing["id"]
            conn.execute(sa.update(t.ai_tools).where(t.ai_tools.c.id == tool_id).values(**values))
        else:
            res = conn.execute(
                sa.insert(t.ai_tools).values(
                    name=row["tool"], vendor=None, domains=[], category="chat", **values
                )
            )
            key = res.inserted_primary_key
            if key is None:
                raise sa.exc.SQLAlchemyError("tool id not returned")
            tool_id = int(key[0])
        _audit(
            conn,
            reviewer,
            "tool.approve",
            row["tool"],
            {
                "request": request_id,
                "risk": risk,
                "allowed_categories": sorted(set(allowed_categories)),
                "alternative": alternative or "",
            },
        )
    else:
        _audit(conn, reviewer, "tool.reject", row["tool"], {"request": request_id})
    conn.execute(
        sa.update(t.tool_requests)
        .where(t.tool_requests.c.id == request_id)
        .values(
            status="approved" if approve else "rejected",
            decided_by=reviewer,
            decided_at=now,
            note=note.strip() or None,
            risk=risk if approve else None,
            allowed_categories=sorted(set(allowed_categories)) if approve else None,
            alternative=(alternative or None) if approve else None,
            tool_id=tool_id,
            seen=False,
        )
    )
    return get(conn, request_id)


def collect_outcomes(conn: sa.Connection, requester: str) -> list[dict[str, Any]]:
    """Decisions this person has not seen yet. Marks them seen, so each shows once."""
    c = t.tool_requests.c
    rows = [
        dict(r)
        for r in conn.execute(
            sa.select(t.tool_requests)
            .where(c.requester == requester, c.status != "pending", c.seen.is_(False))
            .order_by(c.decided_at)
        ).mappings()
    ]
    if rows:
        conn.execute(
            sa.update(t.tool_requests).where(c.id.in_([r["id"] for r in rows])).values(seen=True)
        )
        for r in rows:
            _audit(conn, requester, "tool.outcome_seen", str(r["id"]), {"status": r["status"]})
    return rows
