"""FastAPI entrypoint for the brain service."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import sqlalchemy as sa
from fastapi import FastAPI, HTTPException

from brain import queries, reveal
from brain.api.schemas import (
    AskOut,
    AskRequest,
    DocumentOut,
    FindingOut,
    IdentityOut,
    IncidentDetail,
    IncidentPage,
    InspectOutputRequest,
    InspectOutputResponse,
    InspectRequest,
    InspectResponse,
    KeyRequest,
    KeyResponse,
    Message,
    MetricsOut,
    PolicyOut,
    PolicyUpdate,
    PresetOut,
    RevealDecision,
    RevealOut,
    RevealRequest,
    SeenOut,
    ToolOut,
    UnmaskRequest,
    UnmaskResponse,
)
from brain.ask.presets import BY_ID, PRESETS, run_preset
from brain.clients import ClientStore
from brain.config import settings
from brain.db import tables as t
from brain.db.engine import make_engine
from brain.detection.entities import EntityDetector
from brain.detection.normalize import normalise
from brain.detection.patterns import find_patterns, mask, unmask
from brain.detection.pipeline import Finder, inspect_text
from brain.detection.yara_rules import find_yara
from brain.keys import KeyError_, create_key, default_model
from brain.policy.engine import Decision
from brain.policy.store import PolicyError, PolicyStore
from brain.records import record_decision
from brain.seed.load import run_seed
from brain.sessions import sessions

log = logging.getLogger(__name__)
policy_store = PolicyStore(make_engine())
entity_detector = EntityDetector()
_client_store: ClientStore | None = None


def _finders() -> list[Finder]:
    """Looser detectors that run after the checksum checks: people, emails, phones, clients."""
    global _client_store
    if _client_store is None or _client_store.engine is not policy_store.engine:
        _client_store = ClientStore(policy_store.engine)
    return [find_yara, entity_detector.find, _client_store.find]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        added = policy_store.seed_if_empty()
        if added:
            log.info("Seeded %d policies", added)
    except sa.exc.SQLAlchemyError:
        log.warning("Could not seed policies, using the seed file until the database is up")
    try:
        await asyncio.to_thread(entity_detector.warm_up)
    except Exception:  # the pattern checks still work without the language models
        log.exception("Could not load the language models; people and phones are not detected")
    engine = policy_store.engine
    if engine is not None and settings.demo_mode and settings.seed_on_start:
        try:
            await asyncio.to_thread(
                run_seed,
                engine,
                Path(settings.data_dir) if settings.data_dir else None,
                Path(settings.log_dir),
            )
        except Exception:  # the app must still start; the dashboard just shows no demo data
            log.exception("Seeding the demo company failed")
    yield


app = FastAPI(title="Data DNA brain", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/inspect", response_model=InspectResponse)
def inspect(req: InspectRequest) -> InspectResponse:
    # Only the last user message is inspected in this first slice.
    last = next((m for m in reversed(req.messages) if m.role == "user"), None)
    if last is None:
        return InspectResponse(decision=Decision.ALLOW, reasons=[])
    result = inspect_text(last.content, policy_store.current(), _finders())
    masked = None
    session_id = None
    if result.verdict.decision == Decision.MASK:
        masked = [
            m if m is not last else Message(role="user", content=result.masked_text)
            for m in req.messages
        ]
        session_id = sessions.create(req.user_id, result.placeholders)
    record_decision(
        policy_store.engine,
        user=req.user_id,
        team=req.team,
        decision=str(result.verdict.decision),
        categories=[f.category for f in result.findings],
        reasons=result.verdict.reasons,
        masked_preview=result.findings[0].masked_preview if result.findings else None,
    )
    return InspectResponse(
        session_id=session_id,
        decision=result.verdict.decision,
        reasons=result.verdict.reasons,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in result.findings
        ],
        masked_messages=masked,
        evasion_signals=result.evasion_signals,
    )


@app.post("/v1/unmask", response_model=UnmaskResponse)
def unmask_answer(req: UnmaskRequest) -> UnmaskResponse:
    """Restore masked values in an answer, only for the user who sent them."""
    mapping = sessions.get(req.session_id, req.user_id)
    if mapping is None:
        return UnmaskResponse(text=req.text, restored=0)
    restored = sum(1 for token in mapping if token in req.text)
    return UnmaskResponse(text=unmask(req.text, mapping), restored=restored)


@app.post("/v1/inspect-output", response_model=InspectOutputResponse)
def inspect_output(req: InspectOutputRequest) -> InspectOutputResponse:
    """Mask sensitive values a model put in its answer (echoed secrets, identifiers)."""
    findings = find_patterns(normalise(req.text).text)
    if not findings:
        return InspectOutputResponse(text=req.text)
    masked, _ = mask(normalise(req.text).text, findings)
    return InspectOutputResponse(
        text=masked,
        changed=True,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in findings
        ],
    )


@app.get("/v1/policies", response_model=list[PolicyOut])
def list_policies() -> list[PolicyOut]:
    return [PolicyOut(**vars(row)) for row in policy_store.list_rows()]


@app.put("/v1/policies", response_model=PolicyOut)
def update_policy(req: PolicyUpdate) -> PolicyOut:
    try:
        row = policy_store.update(req.scope, req.key, req.action, req.updated_by)
    except PolicyError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    return PolicyOut(**vars(row))


@app.post("/v1/keys", response_model=KeyResponse)
def new_key(req: KeyRequest) -> KeyResponse:
    """Create a personal key. Demo only: there is no login yet, so it is off outside demo mode."""
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Key creation is turned off. Ask your admin.")
    try:
        key = create_key(req.user_id, req.team)
    except KeyError_ as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    return KeyResponse(key=key, user_id=req.user_id, team=req.team, default_model=default_model())


def _read[T](fn: Callable[[sa.Connection], T]) -> T:
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="The database is not connected. Try again soon."
        )
    try:
        with engine.connect() as conn:
            return fn(conn)
    except sa.exc.SQLAlchemyError as err:
        raise HTTPException(
            status_code=503, detail="The data could not be read. Try again soon."
        ) from err


@app.get("/v1/users/{user_id}/seen", response_model=SeenOut)
def user_seen(user_id: str) -> SeenOut:
    """Has the gateway checked at least one request for this user? Drives "Waiting for first
    request" on the Connect page. A user row is created on the first decision."""

    def has_row(conn: sa.Connection) -> bool:
        found = conn.execute(
            sa.select(t.users.c.id).where(t.users.c.pseudonym == user_id).limit(1)
        ).first()
        return found is not None

    return SeenOut(seen=_read(has_row))


@app.get("/v1/metrics", response_model=MetricsOut)
def get_metrics() -> MetricsOut:
    return _read(lambda c: queries.metrics(c, settings.demo_mode))


@app.get("/v1/incidents", response_model=IncidentPage)
def list_incidents(
    decision: str | None = None, team: str | None = None, limit: int = 25, offset: int = 0
) -> IncidentPage:
    limit = max(1, min(limit, 100))
    return _read(lambda c: queries.incidents(c, decision, team, limit, max(offset, 0)))


def _write[T](fn: Callable[[sa.Connection], T]) -> T:
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="The database is not connected. Try again soon."
        )
    try:
        with engine.begin() as conn:
            return fn(conn)
    except reveal.RevealError as err:
        raise HTTPException(status_code=err.status, detail=str(err)) from err
    except sa.exc.SQLAlchemyError as err:
        raise HTTPException(
            status_code=503, detail="The change could not be saved. Nothing was changed."
        ) from err


@app.get("/v1/incidents/{incident_id}", response_model=IncidentDetail)
def incident_detail(incident_id: int) -> IncidentDetail:
    found = _read(lambda c: queries.incident_detail(c, incident_id))
    if found is None:
        raise HTTPException(status_code=404, detail="That incident does not exist.")
    return found


@app.post("/v1/reveal-requests", response_model=RevealOut)
def create_reveal(req: RevealRequest) -> RevealOut:
    return _write(lambda c: reveal.request_reveal(c, req.incident_id, req.requested_by, req.reason))


@app.post("/v1/reveal-requests/{request_id}/approve", response_model=RevealOut)
def approve_reveal(request_id: int, req: RevealDecision) -> RevealOut:
    return _write(lambda c: reveal.decide(c, request_id, req.decided_by, approve=True))


@app.post("/v1/reveal-requests/{request_id}/deny", response_model=RevealOut)
def deny_reveal(request_id: int, req: RevealDecision) -> RevealOut:
    return _write(lambda c: reveal.decide(c, request_id, req.decided_by, approve=False))


@app.get("/v1/incidents/{incident_id}/identity", response_model=IdentityOut)
def incident_identity(incident_id: int, request_id: int, viewer: str = "") -> IdentityOut:
    return _write(lambda c: reveal.reveal_identity(c, incident_id, request_id, viewer))


@app.get("/v1/documents", response_model=list[DocumentOut])
def get_documents() -> list[DocumentOut]:
    return _read(queries.documents)


@app.get("/v1/ask/presets", response_model=list[PresetOut])
def ask_presets() -> list[PresetOut]:
    return [PresetOut(id=p.id, question=p.question) for p in PRESETS]


@app.post("/v1/ask", response_model=AskOut)
def ask(req: AskRequest) -> AskOut:
    preset = BY_ID.get(req.preset)
    if preset is None:
        raise HTTPException(
            status_code=404,
            detail="That question is not on the list. Pick one of the preset questions.",
        )
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="The database is not connected. Try again soon."
        )
    try:
        return AskOut(**run_preset(engine, preset))
    except sa.exc.SQLAlchemyError as err:
        raise HTTPException(
            status_code=503, detail="The data could not be read. Try again soon."
        ) from err


@app.get("/v1/inventory", response_model=list[ToolOut])
def get_inventory() -> list[ToolOut]:
    return _read(queries.inventory)
