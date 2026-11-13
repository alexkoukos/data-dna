"""Read-side queries for the dashboard: metrics, incident list and AI tool inventory."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

import sqlalchemy as sa

from brain.api.schemas import (
    DocumentMatch,
    DocumentOut,
    IncidentDetail,
    IncidentOut,
    IncidentPage,
    MetricsOut,
    ToolOut,
)
from brain.db import tables as t
from brain.reveal import list_for_incident


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def reference_time(conn: sa.Connection) -> datetime | None:
    """The newest incident, so '7 days' means the last 7 days of data, not of the clock."""
    latest = conn.execute(sa.select(sa.func.max(t.incidents.c.ts))).scalar_one()
    return _aware(latest) if latest else None


def metrics(conn: sa.Connection, demo_data: bool) -> MetricsOut:
    totals = conn.execute(
        sa.select(
            sa.func.coalesce(sa.func.sum(t.counters_daily.c.checked), 0),
            sa.func.coalesce(sa.func.sum(t.counters_daily.c.zero_llm), 0),
        )
    ).one()
    checked, zero = int(totals[0]), int(totals[1])
    ref = reference_time(conn)
    recent = previous = 0
    if ref:
        week = timedelta(days=7)
        count = sa.select(sa.func.count()).select_from(t.incidents)
        recent = conn.execute(count.where(t.incidents.c.ts > ref - week)).scalar_one()
        previous = conn.execute(
            count.where(t.incidents.c.ts <= ref - week, t.incidents.c.ts > ref - 2 * week)
        ).scalar_one()
    unapproved = conn.execute(
        sa.select(sa.func.count(sa.distinct(t.ai_tools.c.id)))
        .select_from(
            t.ai_tools.join(t.tool_usage_daily, t.tool_usage_daily.c.tool_id == t.ai_tools.c.id)
        )
        .where(t.ai_tools.c.approval == "unapproved")
    ).scalar_one()
    return MetricsOut(
        prompts_checked=checked,
        zero_llm_share=round(zero / checked, 3) if checked else None,
        incidents_7d=recent,
        incidents_prev_7d=previous,
        unapproved_tools=unapproved,
        demo_data=demo_data,
        as_of=ref,
    )


def incidents(
    conn: sa.Connection,
    decision: str | None = None,
    team: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> IncidentPage:
    where: list[Any] = []
    if decision:
        where.append(t.incidents.c.decision == decision)
    if team:
        where.append(t.incidents.c.team == team)
    total = conn.execute(
        sa.select(sa.func.count()).select_from(t.incidents).where(*where)
    ).scalar_one()
    rows = conn.execute(
        sa.select(t.incidents, t.users.c.pseudonym)
        .select_from(t.incidents.outerjoin(t.users, t.users.c.id == t.incidents.c.user_id))
        .where(*where)
        .order_by(t.incidents.c.ts.desc(), t.incidents.c.id.desc())
        .limit(limit)
        .offset(offset)
    ).mappings()
    return IncidentPage(
        total=total,
        items=[
            IncidentOut(
                id=r["id"],
                ts=_aware(r["ts"]),
                user=r["pseudonym"] or "unknown",
                team=r["team"],
                tool=r["tool"],
                decision=r["decision"],
                categories=list(r["categories"] or []),
                reasons=[str(x) for x in (r["reasons"] or [])],
                masked_preview=r["masked_preview"],
                score=r["score"],
            )
            for r in rows
        ],
    )


def inventory(conn: sa.Connection) -> list[ToolOut]:
    usage = conn.execute(sa.select(t.tool_usage_daily)).mappings().all()
    latest = max((r["day"] for r in usage), default=None)
    by_tool: dict[int, list[Any]] = defaultdict(list)
    for r in usage:
        by_tool[r["tool_id"]].append(r)
    out: list[ToolOut] = []
    for tool in conn.execute(sa.select(t.ai_tools).order_by(t.ai_tools.c.name)).mappings():
        rows = by_tool.get(tool["id"], [])
        per_day_users: dict[date, int] = defaultdict(int)
        per_day_requests: dict[date, int] = defaultdict(int)
        for r in rows:
            per_day_users[r["day"]] += r["users"] or 0
            per_day_requests[r["day"]] += r["requests"] or 0
        trend = (
            [per_day_requests.get(latest - timedelta(days=6 - i), 0) for i in range(7)]
            if latest
            else [0] * 7
        )
        out.append(
            ToolOut(
                id=tool["id"],
                name=tool["name"],
                vendor=tool["vendor"],
                category=tool["category"],
                approval=tool["approval"] or "unapproved",
                risk=tool["risk"] or "medium",
                reason=tool["reason"],
                alternative=tool["alternative"],
                teams=sorted({r["team"] for r in rows}),
                peak_users=max(per_day_users.values(), default=0),
                requests=sum(per_day_requests.values()),
                trend=trend,
                first_seen=min(per_day_requests).isoformat() if per_day_requests else None,
            )
        )
    return out


def documents(conn: sa.Connection) -> list[DocumentOut]:
    counted = conn.execute(
        sa.select(t.incidents.c.document_id, sa.func.count())
        .where(t.incidents.c.document_id.is_not(None))
        .group_by(t.incidents.c.document_id)
    ).all()
    hits: dict[int, int] = {int(doc_id): int(n) for doc_id, n in counted}
    rows = conn.execute(sa.select(t.documents).order_by(t.documents.c.title)).mappings()
    return [
        DocumentOut(
            id=r["id"],
            title=r["title"],
            sensitivity=r["sensitivity"],
            dna_enabled=bool(r["dna_enabled"]),
            created_at=r["created_at"],
            incidents=int(hits.get(r["id"], 0)),
        )
        for r in rows
    ]


def _incident_out(r: Any) -> IncidentOut:
    return IncidentOut(
        id=r["id"],
        ts=_aware(r["ts"]),
        user=r["pseudonym"] or "unknown",
        team=r["team"],
        tool=r["tool"],
        decision=r["decision"],
        categories=list(r["categories"] or []),
        reasons=[str(x) for x in (r["reasons"] or [])],
        masked_preview=r["masked_preview"],
        score=r["score"],
    )


def incident_detail(conn: sa.Connection, incident_id: int) -> IncidentDetail | None:
    """One incident, the same person's other incidents (newest first), and the matched document.
    Only the pseudonym is ever returned here; the real name needs the reveal flow."""
    base = sa.select(t.incidents, t.users.c.pseudonym).select_from(
        t.incidents.outerjoin(t.users, t.users.c.id == t.incidents.c.user_id)
    )
    row = conn.execute(base.where(t.incidents.c.id == incident_id)).mappings().first()
    if row is None:
        return None
    timeline = conn.execute(
        base.where(t.incidents.c.user_id == row["user_id"], t.incidents.c.id != incident_id)
        .order_by(t.incidents.c.ts.desc(), t.incidents.c.id.desc())
        .limit(20)
    ).mappings()
    doc = None
    if row["document_id"] is not None:
        d = (
            conn.execute(sa.select(t.documents).where(t.documents.c.id == row["document_id"]))
            .mappings()
            .first()
        )
        if d is not None:
            doc = DocumentMatch(id=d["id"], title=d["title"], sensitivity=d["sensitivity"])
    return IncidentDetail(
        incident=_incident_out(row),
        copy_code=row["copy_code"],
        document=doc,
        timeline=[_incident_out(r) for r in timeline],
        reveals=list_for_incident(conn, incident_id),
    )
