"""Read-side views built on incidents: history per person or document (X24), ROI (X18),
the weekly CISO summary (X20) and the retention purge (X16).

Only masked previews and reasons are ever returned. A real name needs the reveal flow.
"""

from collections import Counter
from datetime import timedelta
from typing import Any

import sqlalchemy as sa

from brain.db import tables as t
from brain.queries import _aware, _incident_out, reference_time

# X18 assumptions. Illustrative euro figures per stopped leak, written down in
# docs/business/business-case.md. "likelihood" is the share of stopped leaks assumed to have
# become a real incident had nothing stopped them. Change them there and here together.
LIKELIHOOD = 0.10
UNIT_COST_EUR: dict[str, int] = {
    "secret": 5000,
    "honeytoken": 8000,
    "source_code": 2000,
    "client_name": 1500,
    "iban": 150,
    "card": 200,
    "greek_id": 150,
    "person_email_phone": 100,
    "injection": 300,
}
DOC_COST_EUR = {"restricted": 10000, "confidential": 4000, "internal": 500}
RISK_WEIGHT = {"low": 1, "medium": 2, "high": 3, "critical": 4}
STOPPED = ("mask", "block", "local", "rerouted")  # X31: rerouted counts as stopped


def _base() -> Any:
    return sa.select(t.incidents, t.users.c.pseudonym).select_from(
        t.incidents.outerjoin(t.users, t.users.c.id == t.incidents.c.user_id)
    )


def history_for_user(conn: sa.Connection, pseudonym: str, limit: int = 100) -> dict[str, Any]:
    rows = (
        conn.execute(
            _base()
            .where(t.users.c.pseudonym == pseudonym)
            .order_by(t.incidents.c.ts.desc(), t.incidents.c.id.desc())
            .limit(limit)
        )
        .mappings()
        .all()
    )
    return _history(pseudonym, [_incident_out(r) for r in rows])


def history_for_document(conn: sa.Connection, document_id: int, limit: int = 100) -> dict[str, Any]:
    title = conn.execute(
        sa.select(t.documents.c.title).where(t.documents.c.id == document_id)
    ).scalar()
    rows = (
        conn.execute(
            _base()
            .where(t.incidents.c.document_id == document_id)
            .order_by(t.incidents.c.ts.desc(), t.incidents.c.id.desc())
            .limit(limit)
        )
        .mappings()
        .all()
    )
    out = _history(title, [_incident_out(r) for r in rows])
    out["found"] = title is not None
    return out


def _history(subject: str | None, items: list[Any]) -> dict[str, Any]:
    return {
        "subject": subject,
        "found": bool(items),
        "total": len(items),
        "by_decision": dict(Counter(i.decision for i in items)),
        "items": items,
    }


def _cost(categories: list[str], sensitivity: str | None) -> float:
    """The costliest thing in one incident counts, not the sum, so a prompt is not counted twice."""
    costs = [UNIT_COST_EUR.get(c, 0) for c in categories]
    if sensitivity:
        costs.append(DOC_COST_EUR.get(sensitivity, 0))
    return float(max(costs, default=0))


def roi(conn: sa.Connection, days: int = 30) -> dict[str, Any]:
    ref = reference_time(conn)
    rows: list[Any] = []
    if ref is not None:
        rows = list(
            conn.execute(
                sa.select(
                    t.incidents.c.decision,
                    t.incidents.c.categories,
                    t.incidents.c.shadow,
                    t.documents.c.sensitivity,
                )
                .select_from(
                    t.incidents.outerjoin(
                        t.documents, t.documents.c.id == t.incidents.c.document_id
                    )
                )
                .where(t.incidents.c.ts > ref - timedelta(days=days))
            ).mappings()
        )
    stopped = [r for r in rows if r["decision"] in STOPPED and not r["shadow"]]
    would = [r for r in rows if r["shadow"]]
    exposure = sum(_cost(list(r["categories"] or []), r["sensitivity"]) for r in stopped)
    by_cat: Counter[str] = Counter()
    for r in stopped:
        by_cat.update(set(r["categories"] or []))
    tools = []
    for tool in conn.execute(sa.select(t.ai_tools).order_by(t.ai_tools.c.name)).mappings():
        requests = (
            conn.execute(
                sa.select(sa.func.coalesce(sa.func.sum(t.tool_usage_daily.c.requests), 0)).where(
                    t.tool_usage_daily.c.tool_id == tool["id"]
                )
            ).scalar_one()
            or 0
        )
        weight = RISK_WEIGHT.get(tool["risk"] or "medium", 2)
        if tool["approval"] == "approved":
            weight = max(1, weight - 1)
        tools.append(
            {
                "name": tool["name"],
                "approval": tool["approval"] or "unapproved",
                "risk": tool["risk"] or "medium",
                "requests": int(requests),
                "risk_score": weight * int(requests),
            }
        )
    tools.sort(key=lambda x: -x["risk_score"])
    return {
        "days": days,
        "leaks_stopped": len(stopped),
        "would_have_stopped": len(would),
        "by_category": dict(by_cat.most_common()),
        "exposure_eur": round(exposure),
        "cost_avoided_eur": round(exposure * LIKELIHOOD),
        "assumptions": {
            "likelihood": LIKELIHOOD,
            "unit_cost_eur": UNIT_COST_EUR,
            "document_cost_eur": DOC_COST_EUR,
            "note": "Illustrative estimates, see docs/business/business-case.md.",
        },
        "tools": tools[:10],
    }


def weekly_summary(conn: sa.Connection) -> dict[str, Any]:
    """A short plain-language summary for the CISO: this week against the one before."""
    ref = reference_time(conn)
    if ref is None:
        return {"headline": "No activity recorded yet.", "lines": [], "week": {}, "previous": {}}
    week = timedelta(days=7)

    def window(start: Any, end: Any) -> list[Any]:
        return list(
            conn.execute(
                _base().where(t.incidents.c.ts > start, t.incidents.c.ts <= end)
            ).mappings()
        )

    this = window(ref - week, ref)
    prev = window(ref - 2 * week, ref - week)
    decisions = Counter(r["decision"] for r in this)
    cats: Counter[str] = Counter()
    teams: Counter[str] = Counter()
    for r in this:
        cats.update(set(r["categories"] or []))
        teams[r["team"] or "unknown"] += 1
    users = Counter(r["pseudonym"] or "unknown" for r in this)
    change = len(this) - len(prev)
    word = "up" if change > 0 else "down" if change < 0 else "unchanged"
    lines = [
        f"{len(this)} incidents this week, {word}"
        + (f" by {abs(change)} on last week ({len(prev)})." if change else f" ({len(prev)})."),
    ]
    if decisions:
        lines.append("Outcomes: " + ", ".join(f"{n} {d}" for d, n in decisions.most_common()) + ".")
    if cats:
        top = ", ".join(f"{c.replace('_', ' ')} ({n})" for c, n in cats.most_common(3))
        lines.append(f"Most common data types: {top}.")
    if teams:
        team, n = teams.most_common(1)[0]
        lines.append(f"Busiest team: {team} with {n} incidents.")
    repeat = [u for u, n in users.items() if n >= 3]
    if repeat:
        lines.append(
            f"{len(repeat)} people had three or more incidents. Consider coaching: "
            + ", ".join(sorted(repeat)[:5])
            + "."
        )
    blocked = decisions.get("block", 0)
    return {
        "headline": f"{blocked} blocked, {len(this)} incidents in the last 7 days",
        "lines": lines,
        "week": dict(decisions),
        "previous": dict(Counter(r["decision"] for r in prev)),
        "as_of": _aware(ref),
    }


def purge_expired(conn: sa.Connection, retention_days: int, now: Any) -> dict[str, int]:
    """X16: delete incidents past their expiry or older than RETENTION_DAYS.

    Reveal requests that point at a deleted incident go first, so no foreign key is left hanging.
    """
    cutoff = now - timedelta(days=retention_days)
    old = sa.select(t.incidents.c.id).where(
        sa.or_(t.incidents.c.expires_at < now, t.incidents.c.ts < cutoff)
    )
    reveals = conn.execute(
        sa.delete(t.reveal_requests).where(t.reveal_requests.c.incident_id.in_(old))
    ).rowcount
    incidents = conn.execute(
        sa.delete(t.incidents).where(
            sa.or_(t.incidents.c.expires_at < now, t.incidents.c.ts < cutoff)
        )
    ).rowcount
    return {"incidents": incidents, "reveal_requests": reveals}
