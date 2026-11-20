"""API for the browser extension: check a prompt, report visits, serve the policy, pair a device.

The extension runs its own cheap checks (L1) in the browser. `/v1/check` is L2: the same pipeline
the gateway uses, plus who is asking and which AI site it is. Visit events carry a tool name and a
time, never page or prompt text.
"""

import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine

from brain.api.schemas import Attachment, InspectRequest, Message
from brain.config import settings
from brain.db import tables as t
from brain.policy import groups
from brain.policy.store import audit_table
from brain.records import record_decision, user_row_id
from brain.seed.ingest import aggregate, build_domain_index, match_tool, parse_squid, parse_zeek_dns
from brain.seed.spec import ToolSpec
from brain.sessions import sessions

log = logging.getLogger(__name__)
router = APIRouter()

EVENT_RETENTION_DAYS = 30
PAIR_TTL_SECONDS = 600
_codes: dict[str, tuple[str, float]] = {}  # code -> (pseudonym, expires)


# --- identity -------------------------------------------------------------------------------


class Who(BaseModel):
    user: str = "anonymous"
    team: str = "unknown"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _engine() -> Engine | None:
    from brain.main import policy_store

    return policy_store.engine


def identify(authorization: str | None, demo_user: str | None) -> Who:
    """Device token first, then (demo only) a chosen demo user, otherwise nobody in particular."""
    engine = _engine()
    if engine is None:
        return Who()
    try:
        with engine.connect() as conn:
            if authorization and authorization.lower().startswith("bearer "):
                row = conn.execute(
                    sa.select(t.users.c.pseudonym, t.users.c.team)
                    .select_from(t.devices.join(t.users, t.devices.c.user_id == t.users.c.id))
                    .where(t.devices.c.token_hash == _hash(authorization[7:].strip()))
                ).first()
                if row:
                    return Who(user=row[0], team=row[1])
            if demo_user and settings.demo_mode:
                row = conn.execute(
                    sa.select(t.users.c.pseudonym, t.users.c.team).where(
                        t.users.c.pseudonym == demo_user
                    )
                ).first()
                if row:
                    return Who(user=row[0], team=row[1])
    except sa.exc.SQLAlchemyError:
        log.warning("Could not look up the extension user")
    return Who()


# --- tools ----------------------------------------------------------------------------------

_tools_cache: tuple[float, list[dict[str, Any]]] = (0.0, [])


def _tools() -> list[dict[str, Any]]:
    global _tools_cache
    engine = _engine()
    if engine is None:
        return []
    if time.monotonic() - _tools_cache[0] < 30 and _tools_cache[1]:
        return _tools_cache[1]
    try:
        with engine.connect() as conn:
            rows = [dict(r) for r in conn.execute(sa.select(t.ai_tools)).mappings()]
    except sa.exc.SQLAlchemyError:
        return _tools_cache[1]
    _tools_cache = (time.monotonic(), rows)
    return rows


def _domain_index() -> dict[str, str]:
    return build_domain_index(
        ToolSpec(
            name=r["name"],
            vendor=r["vendor"] or "",
            domains=list(r["domains"] or []),
            category=r["category"] or "",
            approval=r["approval"] or "unapproved",
            risk=r["risk"] or "medium",
            reason=r["reason"] or "",
            alternative=r["alternative"] or "",
        )
        for r in _tools()
    )


def tool_for_host(host: str, fallback: str) -> str:
    return match_tool(host, _domain_index()) or fallback


def _host(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0].rsplit(":", 1)[0]


# --- /v1/check ------------------------------------------------------------------------------


class CheckRequest(BaseModel):
    text: str = Field(default="", max_length=200_000)
    tool: str = "unknown"
    url: str = ""
    # Files attached on the page, base64. A stamped file (RESTRICTED...) never goes out.
    attachments: list[Attachment] = Field(default_factory=list, max_length=5)


class DocumentView(BaseModel):
    title: str
    sensitivity: str
    coverage: float | None = None


class FindingView(BaseModel):
    entity: str
    category: str
    masked_preview: str


class CheckResponse(BaseModel):
    action: str
    reasons: list[str]
    findings: list[FindingView] = Field(default_factory=list)
    masked_text: str | None = None
    placeholders: dict[str, str] | None = None
    rewrite: str | None = None
    document: DocumentView | None = None
    alternative: str | None = None
    # Where Company AI lives, so the extension can send a person there (with a stopped file's name).
    alternative_url: str | None = None
    policy_version: int = 0
    evasion_signals: list[str] = Field(default_factory=list)


def _doc_titles(ids: list[int]) -> dict[int, str]:
    engine = _engine()
    if engine is None or not ids:
        return {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sa.select(t.documents.c.id, t.documents.c.title).where(t.documents.c.id.in_(ids))
            ).all()
    except sa.exc.SQLAlchemyError:
        return {}
    return {int(i): str(title) for i, title in rows}


@router.post("/v1/check", response_model=CheckResponse)
def check(
    req: CheckRequest,
    background: BackgroundTasks,
    response: Response,
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
) -> CheckResponse:
    from brain.main import inspect

    who = identify(authorization, x_demo_user)
    tool = tool_for_host(_host(req.url), req.tool) if req.url else req.tool
    out = inspect(
        InspectRequest(
            user_id=who.user,
            team=who.team,
            messages=[Message(role="user", content=req.text)],
            tool=tool,
            channel="extension",
            attachments=req.attachments,
        ),
        background,
        response,
    )
    masked = out.masked_messages[-1].content if out.masked_messages else None
    placeholders = sessions.get(out.session_id, who.user) if out.session_id else None
    document = None
    if out.documents:
        rank = {"restricted": 2, "confidential": 1}
        top = max(out.documents, key=lambda d: (rank.get(d.sensitivity, 0), d.score))
        title = _doc_titles([top.document_id]).get(top.document_id, f"Document {top.document_id}")
        coverage = len(top.matched_chunks) / max(top.total_chunks, 1)
        document = DocumentView(
            title=title, sensitivity=top.sensitivity, coverage=round(coverage, 2) or None
        )
    return CheckResponse(
        action=out.decision,
        reasons=out.reasons,
        findings=[FindingView(**f.model_dump()) for f in out.findings],
        masked_text=masked,
        placeholders=placeholders,
        rewrite=out.suggested_rewrite,
        document=document,
        alternative="Company AI" if out.decision in ("local", "block", "warn") else None,
        alternative_url=(
            settings.company_ai_url if out.decision in ("local", "block", "warn") else None
        ),
        policy_version=_policy_version(),
        evasion_signals=out.evasion_signals,
    )


# --- /v1/policy -----------------------------------------------------------------------------


def _policy_version() -> int:
    from brain.main import policy_store

    engine = policy_store.engine
    if engine is None:
        return 1
    try:
        with engine.connect() as conn:
            newest = conn.execute(sa.select(sa.func.max(t_policies().c.updated_at))).scalar()
            grp = conn.execute(
                sa.select(t.settings.c.updated_at).where(t.settings.c.key == "group_policies")
            ).scalar()
    except sa.exc.SQLAlchemyError:
        return 1
    stamps = [x for x in (newest, grp) if x is not None]
    return int(max(stamps).timestamp()) if stamps else 1


def t_policies() -> sa.Table:
    from brain.policy.store import policies_table

    return policies_table


def _client_names() -> list[str]:
    """Client names and aliases, so the browser can spot them without asking the server."""
    engine = _engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.select(t.clients.c.name, t.clients.c.aliases)).all()
    except sa.exc.SQLAlchemyError:
        return []
    return sorted({n for name, aliases in rows for n in [name, *(aliases or [])] if n})


@router.get("/v1/policy")
def get_policy(
    response: Response,
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
    if_none_match: str | None = Header(default=None),
) -> Any:
    """What the extension caches: the actions for this person and the AI tool list."""
    from brain.main import policy_store

    who = identify(authorization, x_demo_user)
    effective = groups.effective(policy_store.engine, policy_store.current(), who.user, who.team)
    tools: dict[str, dict[str, str]] = {}
    for r in _tools():
        for domain in r["domains"] or []:
            tools[domain.lower()] = {
                "name": r["name"],
                "approval": r["approval"] or "unapproved",
                "risk": r["risk"] or "medium",
                "alternative": r["alternative"] or "",
            }
    body = {
        "version": _policy_version(),
        "clients": _client_names(),
        "categories": {k: str(v) for k, v in effective.categories.items()},
        "sensitivity": {k: str(v) for k, v in effective.sensitivity.items()},
        "failMode": {"restricted": "fail_closed", "other": "fail_open"},
        "tools": tools,
        "user": who.user,
        "team": who.team,
    }
    etag = (
        '"'
        + hashlib.sha256(repr(sorted(body.items(), key=lambda x: x[0])).encode()).hexdigest()[:16]
        + '"'
    )
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return body


# --- /v1/events -----------------------------------------------------------------------------


class ExtEvent(BaseModel):
    ts: int  # milliseconds since the epoch
    tool: str
    kind: str  # visit | decision | override
    host: str = ""
    action: str | None = None
    category: str | None = None
    reason: str | None = None
    offline: bool = False


class EventsIn(BaseModel):
    events: list[ExtEvent] = Field(max_length=1000)


@router.post("/v1/events")
def post_events(
    req: EventsIn,
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
) -> dict[str, int]:
    engine = _engine()
    who = identify(authorization, x_demo_user)
    if engine is None:
        return {"stored": 0}
    index = _domain_index()
    stored = 0
    try:
        with engine.begin() as conn:
            uid = user_row_id(conn, who.user, who.team)
            tool_ids = {r["name"]: r["id"] for r in _tools()}
            seen_today: set[tuple[date, str]] = set()
            for e in req.events:
                when = datetime.fromtimestamp(e.ts / 1000, tz=UTC)
                tool = (match_tool(e.host, index) if e.host else None) or e.tool
                if e.kind == "visit":
                    stored += _store_visit(conn, uid, who, when, tool, tool_ids, seen_today)
                elif e.kind == "override":
                    conn.execute(
                        sa.insert(audit_table).values(
                            ts=when,
                            actor=who.user,
                            action="extension.override",
                            target=tool,
                            details={"reason": (e.reason or "")[:300]},
                        )
                    )
                    stored += 1
    except sa.exc.SQLAlchemyError:
        log.warning("Could not store extension events")
        raise HTTPException(status_code=503, detail="Could not store events.") from None
    # Decisions made while the server was out of reach are recorded now, so incidents stay complete.
    for e in req.events:
        if e.kind == "decision" and e.offline and e.action and e.action != "allow":
            record_decision(
                engine,
                user=who.user,
                team=who.team,
                decision=e.action,
                categories=[e.category] if e.category else [],
                reasons=["Decided in the browser while the company server was not reachable."],
                masked_preview=None,
                tool=match_tool(e.host, index) or e.tool if e.host else e.tool,
                channel="extension",
            )
            stored += 1
    return {"stored": stored}


def _store_visit(
    conn: sa.Connection,
    uid: int,
    who: Who,
    when: datetime,
    tool: str,
    tool_ids: dict[str, int],
    seen_today: set[tuple[date, str]],
) -> int:
    tool_id = tool_ids.get(tool)
    if tool_id is None:
        return 0  # not in the catalogue: nothing to put in the inventory
    day = when.date()
    first_today = (
        conn.execute(
            sa.select(sa.literal(1))
            .select_from(t.ext_events)
            .where(
                t.ext_events.c.user_id == uid,
                t.ext_events.c.tool_id == tool_id,
                sa.func.date(t.ext_events.c.ts) == day,
            )
            .limit(1)
        ).first()
        is None
    ) and (day, tool) not in seen_today
    seen_today.add((day, tool))
    conn.execute(
        sa.insert(t.ext_events).values(
            ts=when,
            user_id=uid,
            team=who.team,
            tool_id=tool_id,
            tool=tool,
            kind="visit",
            action="counted",  # also added to the daily usage just below
            expires_at=when + timedelta(days=EVENT_RETENTION_DAYS),
        )
    )
    _bump_usage(conn, day, tool_id, who.team, requests=1, users=1 if first_today else 0)
    return 1


def _bump_usage(
    conn: sa.Connection, day: date, tool_id: int, team: str, requests: int, users: int
) -> None:
    u = t.tool_usage_daily
    where = (u.c.day == day, u.c.tool_id == tool_id, u.c.team == team)
    if conn.execute(sa.select(sa.literal(1)).select_from(u).where(*where)).first() is None:
        conn.execute(
            sa.insert(u).values(day=day, tool_id=tool_id, team=team, users=users, requests=requests)
        )
    else:
        conn.execute(
            sa.update(u)
            .where(*where)
            .values(requests=u.c.requests + requests, users=u.c.users + users)
        )


# --- /v1/pair -------------------------------------------------------------------------------


class PairCodeRequest(BaseModel):
    user: str


class PairRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
    label: str = "Chrome"


class PairResponse(BaseModel):
    token: str
    user: str
    team: str


@router.post("/v1/pair/code")
def pair_code(req: PairCodeRequest) -> dict[str, Any]:
    """Demo: the dashboard shows a six-digit code for a user. In production the browser gets its
    identity from the company's Chrome policy instead."""
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Pairing codes are a demo feature.")
    who = identify(None, req.user)
    if who.user == "anonymous":
        raise HTTPException(status_code=404, detail="Unknown user.")
    now = time.monotonic()
    for k in [k for k, (_, exp) in _codes.items() if exp < now]:
        del _codes[k]
    code = f"{secrets.randbelow(1_000_000):06d}"
    _codes[code] = (who.user, now + PAIR_TTL_SECONDS)
    return {"code": code, "user": who.user, "team": who.team, "expires_in": PAIR_TTL_SECONDS}


@router.post("/v1/pair", response_model=PairResponse)
def pair(req: PairRequest) -> PairResponse:
    engine = _engine()
    hit = _codes.pop(req.code, None)
    if engine is None or hit is None or hit[1] < time.monotonic():
        raise HTTPException(status_code=400, detail="That code is wrong or has expired.")
    who = identify(None, hit[0])
    token = "sentry_" + secrets.token_urlsafe(24)
    with engine.begin() as conn:
        uid = user_row_id(conn, who.user, who.team)
        conn.execute(
            sa.insert(t.devices).values(
                token_hash=_hash(token),
                user_id=uid,
                team=who.team,
                label=req.label,
                created_at=datetime.now(UTC),
            )
        )
    return PairResponse(token=token, user=who.user, team=who.team)


@router.get("/v1/demo-users")
def demo_users() -> list[dict[str, str]]:
    """Demo only: people the options page can pretend to be."""
    engine = _engine()
    if engine is None or not settings.demo_mode:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            sa.select(t.users.c.pseudonym, t.users.c.team)
            .order_by(t.users.c.team, t.users.c.pseudonym)
            .limit(300)
        ).all()
    return [{"user": r[0], "team": r[1]} for r in rows]


# --- /v1/ask-local --------------------------------------------------------------------------


class AskLocalRequest(BaseModel):
    prompt: str = Field(max_length=20_000)


class AskLocalResponse(BaseModel):
    answer: str
    ready: bool
    model: str


@router.post("/v1/ask-local", response_model=AskLocalResponse)
def ask_local(req: AskLocalRequest) -> AskLocalResponse:
    """The company AI. Answered by the local model, so the text never leaves the company.

    If the local model is not running (it is optional, `make local`), a clearly labelled stand-in
    answer is returned, so the demo path still works.
    """
    try:
        r = httpx.post(
            f"{settings.local_llm_url}/api/chat",
            json={
                "model": "dna-local",
                "messages": [{"role": "user", "content": req.prompt}],
                "stream": False,
                "options": {"num_predict": 300},
            },
            timeout=120,
        )
        r.raise_for_status()
        return AskLocalResponse(
            answer=str(r.json()["message"]["content"]), ready=True, model="dna-local"
        )
    except (httpx.HTTPError, KeyError, ValueError):
        return AskLocalResponse(
            answer=(
                "The local model is not running, so this is a stand-in answer. Your text stayed "
                "inside the company. Start the model with `make local` to get real answers."
            ),
            ready=False,
            model="stand-in",
        )


# --- /v1/logs/ingest ------------------------------------------------------------------------


class LogsIn(BaseModel):
    format: str = Field(pattern="^(squid|zeek)$")
    lines: list[str] = Field(max_length=200_000)
    leases: dict[str, str] = Field(default_factory=dict)  # ip -> pseudonym


@router.post("/v1/logs/ingest")
def ingest_logs(req: LogsIn, authorization: str | None = Header(default=None)) -> dict[str, int]:
    """Add proxy or DNS log lines to the inventory. Same matching as the start-up seed.

    Needs "Authorization: Bearer <INGEST_TOKEN>": the lease map decides who the traffic is filed
    under, so an anonymous caller must never reach it. Off (503) until a token is set.
    """
    token = settings.ingest_token
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Log ingest is off. Set INGEST_TOKEN in .env and restart the brain.",
        )
    if not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="Log ingest needs the ingest token.")
    engine = _engine()
    if engine is None:
        return {"rows": 0}
    index = _domain_index()
    with engine.begin() as conn:
        user_team = {
            r[0]: r[1] for r in conn.execute(sa.select(t.users.c.pseudonym, t.users.c.team)).all()
        }
        tool_ids = {r["name"]: r["id"] for r in _tools()}
        squid = list(parse_squid(req.lines)) if req.format == "squid" else []
        dns = list(parse_zeek_dns(req.lines)) if req.format == "zeek" else []
        rows = aggregate(squid, dns, req.leases, user_team, index)
        per: dict[tuple[date, int, str], list[int]] = defaultdict(lambda: [0, 0])
        for row in rows:
            tid = tool_ids.get(row.tool)
            if tid is not None:
                per[(row.day, tid, row.team)][0] += row.requests
                per[(row.day, tid, row.team)][1] += row.users
        for (day, tid, team), (n, users) in per.items():
            _bump_usage(conn, day, tid, team, requests=n, users=users)
    return {"rows": len(per)}
