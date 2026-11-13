"""Fill the database with the synthetic company, once, when it is empty."""

import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.db import tables as t
from brain.seed import ingest
from brain.seed.generate import RETENTION_DAYS, Org, generate
from brain.seed.logs import write_logs
from brain.seed.spec import ToolSpec, load

log = logging.getLogger(__name__)


def _chunks(rows: list[dict[str, object]], size: int = 2000) -> list[list[dict[str, object]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def load_catalogue(conn: sa.Connection, tools: list[ToolSpec]) -> dict[str, int]:
    """Insert the AI tool catalogue when the table is empty. Returns name -> id."""
    if not conn.execute(sa.select(sa.func.count()).select_from(t.ai_tools)).scalar_one():
        conn.execute(
            sa.insert(t.ai_tools),
            [
                {
                    "name": x.name,
                    "vendor": x.vendor,
                    "domains": x.domains,
                    "category": x.category,
                    "approval": x.approval,
                    "risk": x.risk,
                    "reason": x.reason,
                    "alternative": x.alternative or None,
                }
                for x in tools
            ],
        )
    return {r.name: r.id for r in conn.execute(sa.select(t.ai_tools.c.id, t.ai_tools.c.name))}


def insert_org(
    conn: sa.Connection, org: Org, tools: list[ToolSpec], log_dir: Path, seed: int
) -> dict[str, int]:
    """Write the organisation, logs-derived usage, gateway counters and incidents."""
    now = datetime.now(UTC)
    for chunk in _chunks(
        [
            {
                "pseudonym": u.pseudonym,
                "display_name": u.display_name,
                "team": u.team,
                "role": u.role,
                "created_at": now,
            }
            for u in org.users
        ]
    ):
        conn.execute(sa.insert(t.users), chunk)
    user_id = {
        r.pseudonym: r.id for r in conn.execute(sa.select(t.users.c.id, t.users.c.pseudonym))
    }
    idx_to_id = {u.idx: user_id[u.pseudonym] for u in org.users}
    conn.execute(
        sa.insert(t.api_keys),
        [
            {"user_id": idx_to_id[u.idx], "key_hash": u.key_hash, "created_at": now}
            for u in org.users
        ],
    )
    if org.spec.clients:
        conn.execute(
            sa.insert(t.clients),
            [
                {"name": c["name"], "aliases": list(c.get("aliases") or [])}
                for c in org.spec.clients
            ],
        )
    first_in_team: dict[str, int] = {}
    for u in org.users:
        first_in_team.setdefault(u.team, idx_to_id[u.idx])
    doc_ids: list[int] = []
    for d in org.spec.documents:
        res = conn.execute(
            sa.insert(t.documents)
            .values(
                title=d["title"],
                owner_id=first_in_team.get(d.get("owner_team", "")),
                sensitivity=d["sensitivity"],
                created_at=now,
            )
            .returning(t.documents.c.id)
        )
        doc_ids.append(res.scalar_one())

    tool_id = load_catalogue(conn, tools)

    # Usage seen in the proxy and DNS logs (O2), plus usage that went through the gateway.
    paths = write_logs(org, log_dir, seed)
    leases = ingest.read_leases(paths["leases"])
    user_team = {u.pseudonym: u.team for u in org.users}
    index = ingest.build_domain_index(tools)
    with paths["squid"].open(encoding="utf-8") as sq, paths["zeek"].open(encoding="utf-8") as zk:
        rows = ingest.aggregate(
            ingest.parse_squid(sq), ingest.parse_zeek_dns(zk), leases, user_team, index
        )
    usage = [
        {
            "day": r.day,
            "tool_id": tool_id[r.tool],
            "team": r.team,
            "users": r.users,
            "requests": r.requests,
        }
        for r in rows
        if r.tool in tool_id
    ] + [
        {
            "day": g.day,
            "tool_id": tool_id[g.tool],
            "team": g.team,
            "users": g.users,
            "requests": g.requests,
        }
        for g in org.gateway_usage
        if g.tool in tool_id
    ]
    for chunk in _chunks(usage):
        conn.execute(sa.insert(t.tool_usage_daily), chunk)
    conn.execute(
        sa.insert(t.counters_daily),
        [
            {
                "day": c.day,
                "team": c.team,
                "allowed": c.allowed,
                "checked": c.checked,
                "zero_llm": c.zero_llm,
                "llm_tokens": c.llm_tokens,
            }
            for c in org.counters
        ],
    )
    for chunk in _chunks(
        [
            {
                "ts": i.ts,
                "user_id": idx_to_id[i.user_idx],
                "team": i.team,
                "tool": i.tool,
                "channel": "gateway",
                "decision": i.decision,
                "categories": i.categories,
                "document_id": doc_ids[i.document_idx]
                if i.document_idx is not None and doc_ids
                else None,
                "score": i.score,
                "reasons": i.reasons,
                "masked_preview": i.masked_preview,
                "expires_at": i.ts + timedelta(days=RETENTION_DAYS),
            }
            for i in org.incidents
        ]
    ):
        conn.execute(sa.insert(t.incidents), chunk)
    return tool_id


def run_seed(
    engine: Engine,
    data_dir: Path | None = None,
    log_dir: Path | None = None,
    seed: int = 42,
    anchor: date | None = None,
) -> bool:
    """Seed the demo company if the database has no users. Returns True when it seeded."""
    with engine.connect() as conn:
        if conn.execute(sa.select(sa.func.count()).select_from(t.users)).scalar_one():
            return False
    files = load(data_dir)
    org = generate(files.org, files.tools, seed, anchor)
    with engine.begin() as conn:
        insert_org(conn, org, files.tools, log_dir or Path("/var/dna/logs"), seed)
    log.info(
        "Seeded %s: %d users, %d incidents (spec: %s)",
        files.org.company,
        len(org.users),
        len(org.incidents),
        files.org.source,
    )
    return True
