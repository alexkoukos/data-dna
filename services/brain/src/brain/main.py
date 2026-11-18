"""FastAPI entrypoint for the brain service."""

import asyncio
import base64
import binascii
import csv
import hashlib
import hmac
import html
import json
import logging
import re
import threading
import time
from collections import Counter, OrderedDict
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import sqlalchemy as sa
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse

from brain import (
    alerts,
    breakit,
    coaching,
    compliance,
    digest,
    insights,
    queries,
    reveal,
    settings_store,
    siem,
    toolrequests,
)
from brain.api.schemas import (
    ApproveMarks,
    AskOut,
    AskRequest,
    Attempt,
    BoardOut,
    CandidateIn,
    CandidateOut,
    CopiesRequest,
    CopyOut,
    DnaState,
    DocumentHit,
    DocumentOut,
    ExtensionAck,
    ExtensionInspect,
    ExtensionMe,
    ExtensionVerdict,
    FindingOut,
    GroupPolicy,
    GroupPolicyUpdate,
    HoneytokenOut,
    HoneytokenRequest,
    IdentityOut,
    IncidentDetail,
    IncidentPage,
    InspectOutputRequest,
    InspectOutputResponse,
    InspectRequest,
    InspectResponse,
    KeyRequest,
    KeyResponse,
    LayerOut,
    MarkOut,
    Message,
    MetricsOut,
    PolicyOut,
    PolicyPreview,
    PolicyPreviewRequest,
    PolicyUpdate,
    PresetOut,
    ProposeOut,
    PurgeRequest,
    RegisteredDocument,
    RevealDecision,
    RevealOut,
    RevealRequest,
    ReviewIn,
    ReviewOut,
    SeenOut,
    ShadowIn,
    ShadowOut,
    ToolDecisionIn,
    ToolOut,
    ToolRequestIn,
    ToolRequestOut,
    ToolResultRequest,
    ToolResultResponse,
    TraceStep,
    TryExample,
    TryOut,
    TryRequest,
    UnmaskRequest,
    UnmaskResponse,
)
from brain.ask.free import AskError, ask_free
from brain.ask.presets import BY_ID, PRESETS, match_preset, run_preset
from brain.clients import ClientStore
from brain.config import settings
from brain.db import tables as t
from brain.db.engine import ensure_schema, make_engine
from brain.detection.code_fingerprint import CodeIndex
from brain.detection.entities import EntityDetector
from brain.detection.greeklish import find_greeklish_names
from brain.detection.layers import explain
from brain.detection.normalize import normalise
from brain.detection.patterns import Finding, find_patterns, mask, unmask
from brain.detection.pipeline import (
    HIGH_CONFIDENCE,
    Finder,
    InspectResult,
    _add_without_overlap,
    cap_injection,
    inspect_text,
)
from brain.detection.yara_rules import find_yara
from brain.dna import store as dna_store
from brain.dna.marks import Mark, propose_marks
from brain.documents.embeddings import E5Embedder
from brain.documents.extract import MAX_BYTES, ExtractError, extract_text
from brain.documents.loader import load_documents
from brain.documents.registry import (
    DocMatch,
    DocumentIndex,
    DowngradeRefused,
    register_document,
)
from brain.documents.session import update_coverage
from brain.honeytokens import (
    Honeytoken,
    HoneytokenStore,
    Owner,
    generate,
    plant_block,
    record_alarm,
)
from brain.identity import GatewayUnavailable, Identity, bearer_token, resolve_key
from brain.injection.classifier import InjectionClassifier
from brain.injection.heuristics import injection_finder, injection_finder_instructions
from brain.keys import KeyError_, create_key, default_model
from brain.policy import groups
from brain.policy.engine import PRECEDENCE, Decision
from brain.policy.preview import preview as policy_preview
from brain.policy.store import PolicyError, PolicySet, PolicyStore
from brain.records import record_ack, record_decision, record_reroute, user_row_id
from brain.seed.load import run_seed
from brain.sessions import sessions
from brain.splitstore.routes import router as vault_router
from brain.trace import build_trace

log = logging.getLogger(__name__)
policy_store = PolicyStore(make_engine())
entity_detector = EntityDetector()
injection_classifier = InjectionClassifier()
_client_store: ClientStore | None = None
_honeytoken_store: HoneytokenStore | None = None


embedder = E5Embedder()
_doc_index: DocumentIndex | None = None


def _documents() -> DocumentIndex:
    global _doc_index
    if _doc_index is None or _doc_index.engine is not policy_store.engine:
        _doc_index = DocumentIndex(policy_store.engine, embedder)
    return _doc_index


def _honeytokens() -> HoneytokenStore:
    global _honeytoken_store
    if _honeytoken_store is None or _honeytoken_store.engine is not policy_store.engine:
        _honeytoken_store = HoneytokenStore(policy_store.engine)
    return _honeytoken_store


_code_index: CodeIndex | None = None


def _code() -> CodeIndex:
    """X9: reference code from data/code, loaded once."""
    global _code_index
    if _code_index is None:
        _code_index = CodeIndex()
        if settings.data_dir:
            _code_index.load_dir(Path(settings.data_dir) / "code")
    return _code_index


def _finders() -> list[Finder]:
    """Looser detectors that run after the checksum checks: people, emails, phones, clients."""
    global _client_store
    if _client_store is None or _client_store.engine is not policy_store.engine:
        _client_store = ClientStore(policy_store.engine)
    return [
        find_yara,
        _code().find,
        injection_finder,
        injection_classifier.find,
        find_greeklish_names,
        entity_detector.find,
        _client_store.find,
    ]


async def _recover_loop(store: Any, every_seconds: int = 60) -> None:
    """Settle interrupted split writes now and then. Only entries older than 30 s are touched,
    so a write in flight (here or in another app instance) is never disturbed."""
    while True:
        try:
            n = await asyncio.to_thread(store.recover)
            if n:
                log.warning("Settled %d interrupted split write(s)", n)
        except Exception:
            log.exception("Settling interrupted split writes failed; will retry")
        await asyncio.sleep(every_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if policy_store.engine is not None:
        try:
            ensure_schema(policy_store.engine)
        except sa.exc.SQLAlchemyError:
            log.warning("Could not update the database schema; run make reset if matching fails")
    try:
        added = policy_store.seed_if_empty()
        if added:
            log.info("Seeded %d policies", added)
    except sa.exc.SQLAlchemyError:
        log.warning("Could not seed policies, using the seed file until the database is up")
    recover_task: asyncio.Task[None] | None = None
    if settings.vault_a_url and settings.vault_b_url:
        try:  # settle split writes a crash left half-done, and check the key matches the vaults
            from brain.splitstore import get_store

            store = await asyncio.to_thread(get_store)
            recover_task = asyncio.create_task(_recover_loop(store))
        except Exception:  # the app still serves; vault routes report the problem themselves
            log.exception("Split storage is not ready (vaults down or HMAC key mismatch)")
    try:
        await asyncio.to_thread(embedder.warm_up)
    except Exception:  # without the model only exact copies are caught, not rewrites
        log.exception("Could not load the embedding model; paraphrases are not detected")
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
    if engine is not None and not settings.demo_mode:
        try:
            with engine.begin() as conn:
                gone = insights.purge_expired(conn, settings.retention_days, datetime.now(UTC))
            log.info("Retention purge removed %s", gone)
        except sa.exc.SQLAlchemyError:
            log.warning("The retention purge could not run")
    docs_dir = Path(settings.data_dir) / "documents" if settings.data_dir else None
    if engine is not None and docs_dir is not None and docs_dir.is_dir():
        try:
            n = await asyncio.to_thread(
                load_documents, engine, embedder, docs_dir, settings.demo_mode
            )
            log.info("Registered %d documents from %s", n, docs_dir)
        except Exception:
            log.exception("Registering the documents failed")
    yield
    if recover_task is not None:
        recover_task.cancel()


_attempts = breakit.AttemptLog()

app = FastAPI(title="Data DNA brain", version="0.1.0", lifespan=lifespan)
app.include_router(vault_router)


MAX_BODY_BYTES = 15 * 1024 * 1024
MAX_INSPECT_CHARS = 100_000


class BodyLimit:
    """Refuse a body over MAX_BODY_BYTES. Counts the bytes actually received, so a chunked body
    with no Content-Length cannot get past it; a declared length is refused before any read."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            await _too_large()(scope, receive, send)
            return
        received = 0

        async def limited() -> Any:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise HTTPException(status_code=413, detail=_TOO_LARGE)
            return message

        await self.inner(scope, limited, send)


_TOO_LARGE = "This request is too large (over 15 MB). Send a smaller one."


def _too_large() -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": _TOO_LARGE})


# Added first, so it sits innermost: its 413 reaches the route, not a middleware task group.
app.add_middleware(BodyLimit)


def extension_origin() -> str | None:
    """X27: the only browser origin allowed to call the brain, set by EXTENSION_ID in .env."""
    ident = settings.extension_id.strip()
    return f"chrome-extension://{ident}" if ident else None


@app.middleware("http")
async def extension_cors(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """CORS for the extension endpoints, and only for the extension origin (X27).

    Everything else gets no CORS headers, so no other website can read the brain's answers.
    """
    if not request.url.path.startswith("/v1/extension/"):
        return await call_next(request)  # type: ignore[no-any-return]
    allowed = extension_origin()
    origin = request.headers.get("origin")
    ok = allowed is not None and origin == allowed
    if request.method == "OPTIONS":
        resp = Response(status_code=204 if ok else 403)
    else:
        resp = await call_next(request)
    if ok and allowed is not None:
        resp.headers["Access-Control-Allow-Origin"] = allowed
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Max-Age"] = "600"
        resp.headers["Vary"] = "Origin"
    return resp


def _own_origins() -> set[str]:
    parsed = urlsplit(settings.web_url)
    mine = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
    return {o for o in (mine, "http://localhost:3000", "http://127.0.0.1:3000") if o}


_IDENTITY_PATH = re.compile(r"^/v1/incidents/[^/]+/identity$")


@app.middleware("http")
async def csrf_guard(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """Refuse changes sent from another website (the brain has no login, so the browser is the
    only thing standing between a hostile page and these routes).

    Browsers label cross-site requests with Sec-Fetch-Site or Origin. The gateway, scripts and
    tests send neither and pass. The extension routes have their own CORS rules.
    """
    path = request.url.path
    unsafe = request.method not in ("GET", "HEAD", "OPTIONS") or bool(_IDENTITY_PATH.match(path))
    if not unsafe or path.startswith("/v1/extension/") or path == "/healthz":
        return await call_next(request)  # type: ignore[no-any-return]
    site = request.headers.get("sec-fetch-site")
    origin = request.headers.get("origin")
    if site is not None:
        ok = site in ("same-origin", "none")
    elif origin is not None:
        ok = origin in _own_origins()
    else:
        ok = True
    if not ok:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "This change was sent from another website, so it was refused. "
                "Make it from the Pyli dashboard."
            },
        )
    return await call_next(request)  # type: ignore[no-any-return]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Always 200 while the app runs (compose health). `database` says whether it is reachable."""
    engine = policy_store.engine
    if engine is None:
        return {"status": "ok", "database": "off"}
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except sa.exc.SQLAlchemyError:
        return {"status": "ok", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}


def _attachment_text(req: InspectRequest) -> str:
    """Text of every attached file, appended to the message so one pipeline checks both."""
    parts: list[str] = []
    for a in req.attachments:
        try:
            data = base64.b64decode(a.content_base64, validate=True)
            parts.append(extract_text(a.filename, data))
        except (binascii.Error, ValueError) as err:
            raise HTTPException(
                status_code=422,
                detail=f"{a.filename}: "
                + (
                    str(err)
                    if isinstance(err, ExtractError)
                    else "the file could not be decoded. Attach the file again."
                ),
            ) from err
    return "\n\n" + "\n\n".join(parts) if parts else ""


def _attribute_copy(result: InspectResult, text: str) -> str | None:
    """If the matched document carries DNA marks, name the copy this text came from."""
    engine = policy_store.engine
    if engine is None or not result.doc_matches:
        return None
    try:
        with engine.connect() as conn:
            found = dna_store.attribute_leak(conn, result.doc_matches[0].document_id, text)
    except sa.exc.SQLAlchemyError:
        return None
    if found is None:
        return None
    result.verdict.reasons.append(found.sentence)
    return found.copy_code


def _escalate_rebuilds(req: InspectRequest, result: InspectResult) -> None:
    """Remember which parts of a document this person has sent, and block a rebuild."""
    engine = policy_store.engine
    if engine is None or not result.doc_matches:
        return
    try:
        with engine.begin() as conn:
            uid = user_row_id(conn, req.user_id, req.team)
            rebuilds = update_coverage(conn, uid, result.doc_matches)
    except sa.exc.SQLAlchemyError as err:
        log.warning("Could not update session memory (%s), continuing", type(err).__name__)
        return
    for r in rebuilds:
        if r.escalate:
            result.verdict.reasons.append(r.reason)
            result.verdict.decision = Decision.BLOCK


NEVER_REROUTE = {"injection", "honeytoken"}


def _can_reroute(
    decision: Decision, categories: list[str], memory_reasons: list[str], attached: str
) -> bool:
    """X31: a stopped message may be answered on the company model, with sensitive data masked.

    Not for injection attempts, decoy credentials or a rebuild of a document over several
    messages: those stay blocked. Not for files, which cannot be masked in place.
    """
    return (
        decision in (Decision.BLOCK, Decision.WARN, Decision.LOCAL)
        and not NEVER_REROUTE & set(categories)
        and not memory_reasons
        and not attached
    )


def _decoy_alarm(result: InspectResult) -> list[Owner]:
    """A planted decoy in the prompt means a confidential document left the company (X4)."""
    owners: list[Owner] = []
    for f in result.findings:
        owner = _honeytokens().owner(f.value) if f.category == "honeytoken" else None
        if owner is not None and owner not in owners:
            owners.append(owner)
            result.verdict.reasons.append(
                f"A decoy credential planted in the document '{owner.title}' appeared in this "
                "message, so that document has left the company. This is recorded as an incident."
            )
    return owners


SEGMENT_MARK = "\ue000"
_SEGMENT_JOIN = f"\n\n{SEGMENT_MARK}\n\n"
HISTORY_MAX_EMBEDDED = 8
_TRUSTED_ROLES = {"system", "developer", "assistant"}
# Tool descriptions and other definition text: never new content, but checked like earlier turns.
_DEFINITION_ROLE = "definition"
# Descriptions of tools the client offers: injection wording there warns, it never blocks alone.
_TOOL_DEFINITION_ROLE = "tool_definition"
_DEFINITION_ROLES = {_DEFINITION_ROLE, _TOOL_DEFINITION_ROLE}
_INSTRUCTION_ROLES = {"system", "developer"}
_PREFIX_HISTORY = "Earlier in this conversation: "
_PREFIX_TOOL = "In a tool description: "
_PREFIX_ACCEPTED = "Accepted earlier in this conversation: "
_PREFIX_TRUSTED = "In the instructions, tools or earlier answers: "


@dataclass
class _Pass:
    """One inspection of a group of messages that were checked together."""

    result: InspectResult
    indexes: list[int]
    masked: list[str] | None  # one masked text per message, None if the split went wrong
    normalised: list[str]
    prefix: str = ""


def _group_messages(msgs: list[Message]) -> tuple[list[int], list[int], list[int]]:
    """Split message positions into (new content, earlier user/tool turns, trusted roles).

    Let L be the last message from a user or tool. New content is the unbroken run of user and
    tool messages that ends at L, plus every message after L whatever its role, so a system or
    assistant message a client appends after its question gets the full checks too (a single
    assistant prefill included). System and developer text is trusted (no injection checks)
    only in the leading block before the first user or tool message, which is the normal
    prompt; one that comes later is checked as an earlier turn. Assistant text before the new
    content stays trusted. With no user or tool message at all, everything present is new
    content, so a request never carries text that gets no full check. The other two lists
    are newest first.
    """
    present = [i for i, m in enumerate(msgs) if m.content]
    skip = _TRUSTED_ROLES | _DEFINITION_ROLES
    user_like = [k for k, i in enumerate(present) if msgs[i].role not in skip]
    if not user_like:
        return list(present), [], []
    last = user_like[-1]
    first = last
    while first > 0 and msgs[present[first - 1]].role not in skip:
        first -= 1
    new = [
        present[k]
        for k in range(first, len(present))
        if k <= last or msgs[present[k]].role not in _DEFINITION_ROLES
    ]
    leading = set(present[: user_like[0]])
    older = set(present) - set(new)

    def trusted_role(i: int) -> bool:
        role = msgs[i].role
        return role == "assistant" or (role in _TRUSTED_ROLES and i in leading)

    history = [i for i in reversed(present) if i in older and not trusted_role(i)]
    trusted = [i for i in reversed(present) if i in older and trusted_role(i)]
    return new, history, trusted


@dataclass
class _HistoryGroup:
    """Earlier messages that are checked together, and which checks apply to them."""

    kind: str  # "history", "tool", "instructions" or "trusted"
    indexes: list[int]
    prefix: str
    accepted: bool = False


def _history_groups(
    msgs: list[Message],
    history_idx: list[int],
    trusted_idx: list[int],
    accepted: frozenset[int] = frozenset(),
) -> list[_HistoryGroup]:
    """Split the earlier messages by what kind of text they are. Empty groups are left out, so a
    normal request costs what it did before.

    - earlier user and tool turns, and request text that is not a message: injection phrases block;
    - tool descriptions: injection phrases only warn (`cap_injection`);
    - system and developer text after the first user turn: injection phrases block, unless the
      phrase is negated ("Do not reveal these instructions");
    - the leading prompt and earlier answers: no injection checks.

    Each group is split in two: text the person already accepted comes after the rest, with its
    own prefix, so a warning they answered once is not raised again (see `_lower_accepted`).
    """
    tools = [i for i in history_idx if msgs[i].role == _TOOL_DEFINITION_ROLE]
    instructions = [i for i in history_idx if msgs[i].role in _INSTRUCTION_ROLES]
    rest = [i for i in history_idx if i not in set(tools) | set(instructions)]
    out: list[_HistoryGroup] = []
    for kind, indexes, prefix in (
        ("history", rest, _PREFIX_HISTORY),
        ("tool", tools, _PREFIX_TOOL),
        ("instructions", instructions, _PREFIX_HISTORY),
        ("trusted", trusted_idx, _PREFIX_TRUSTED),
    ):
        fresh = [i for i in indexes if i not in accepted]
        done = [i for i in indexes if i in accepted]
        if fresh:
            out.append(_HistoryGroup(kind, fresh, prefix))
        if done:
            out.append(_HistoryGroup(kind, done, _PREFIX_ACCEPTED, accepted=True))
    return out


def _lower_accepted(p: _Pass) -> None:
    """A warning the person already answered becomes a mask (or nothing) for this earlier text.

    Block and local are never lowered. The text is still masked in place where it differs, so
    an IBAN in an accepted turn does not travel as it is.
    """
    verdict = p.result.verdict
    if verdict.decision != Decision.WARN:
        return
    changed = p.masked is not None and any(
        m != n for m, n in zip(p.masked, p.normalised, strict=True)
    )
    verdict.decision = Decision.MASK if changed else Decision.ALLOW


def _inspect_group(
    texts: list[str],
    tail: str,
    policies: PolicySet,
    placeholders: dict[str, str] | None,
    *,
    finders: list[Finder],
    view_finders: list[Finder],
    doc_match: Callable[..., list[DocMatch]],
    mask_injection: bool = True,
) -> tuple[InspectResult, list[str] | None, list[str]]:
    """Inspect several texts in one call. Returns the result, masked texts and normalised texts.

    The texts are joined with a marker no check treats as a word, so each one can be cut out
    again afterwards. The masked list is None when a finding swallowed a marker.
    """
    segments = [x.replace(SEGMENT_MARK, "") for x in texts] or [""]
    segments[-1] += tail
    result = inspect_text(
        _SEGMENT_JOIN.join(segments),
        policies,
        finders,
        doc_match,
        priority_finder=_honeytokens().find,
        view_finders=view_finders,
        placeholders=placeholders,
        mask_injection=mask_injection,
    )
    masked = result.masked_text.split(_SEGMENT_JOIN)
    normalised = result.text.split(_SEGMENT_JOIN)
    if len(masked) != len(segments) or len(normalised) != len(segments):
        return result, None, normalised
    return result, masked, normalised


class _Remembered[K, V]:
    """A small least-recently-used memory with an expiry, safe to share between requests."""

    def __init__(self, size: int, ttl_seconds: float) -> None:
        self._items: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._size = size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: K) -> V | None:
        with self._lock:
            hit = self._items.get(key)
            if hit is None or time.monotonic() - hit[0] >= self._ttl:
                return None
            self._items.move_to_end(key)
            return hit[1]

    def put(self, key: K, value: V) -> None:
        with self._lock:
            self._items[key] = (time.monotonic(), value)
            while len(self._items) > self._size:
                self._items.popitem(last=False)


# A chat resends the same earlier turns on every request, so only the newest message is new work.
# Answers are kept briefly, so a document registered a moment ago is still found.
_match_memory: _Remembered[tuple[DocumentIndex, int, str, tuple[str, ...]], list[DocMatch]] = (
    _Remembered(256, 60.0)
)
_entity_memory: _Remembered[str, list[Finding]] = _Remembered(512, 600.0)
MAX_REMEMBERED_CHARS = 20_000  # longer messages are worked out each time, never kept


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def _history_matches(
    index: DocumentIndex, text: str, relaxed_for: Sequence[str] = ()
) -> list[DocMatch]:
    """Document matches for earlier turns, worked out and remembered per message."""
    merged: dict[int, DocMatch] = {}
    version = index.current_version()
    for segment in text.split(_SEGMENT_JOIN):
        keep = len(segment) <= MAX_REMEMBERED_CHARS
        key = (index, version, _digest(segment) if keep else "", tuple(relaxed_for))
        found = _match_memory.get(key) if keep else None
        if found is None:
            found = index.match(segment, relaxed_for=relaxed_for, max_embedded=HISTORY_MAX_EMBEDDED)
            if keep:
                _match_memory.put(key, found)
        for m in found:
            old = merged.get(m.document_id)
            if old is None:
                merged[m.document_id] = m
                continue
            best = max((old, m), key=lambda x: (x.kind == "copy", x.score))
            merged[m.document_id] = replace(
                best, matched_chunks=sorted({*old.matched_chunks, *m.matched_chunks})
            )
    return sorted(merged.values(), key=lambda m: (m.kind != "copy", -m.score))


def _history_entities(text: str) -> list[Finding]:
    """The people-and-contact model run per message and remembered, because it is the slow one."""
    out: list[Finding] = []
    offset = 0
    for segment in text.split(_SEGMENT_JOIN):
        keep = len(segment) <= MAX_REMEMBERED_CHARS
        key = _digest(segment) if keep else ""
        found = _entity_memory.get(key) if keep else None
        if found is None:
            found = entity_detector.find(segment)
            if keep:
                _entity_memory.put(key, found)
        out.extend(replace(f, start=f.start + offset, end=f.end + offset) for f in found)
        offset += len(segment) + len(_SEGMENT_JOIN)
    return out


def _for_history(finders: list[Finder]) -> list[Finder]:
    return [_history_entities if f == entity_detector.find else f for f in finders]


def _combine_decisions(passes: list[_Pass]) -> tuple[Decision, list[str]]:
    decision = Decision.ALLOW
    reasons: list[str] = []
    for p in passes:
        if PRECEDENCE[p.result.verdict.decision] > PRECEDENCE[decision]:
            decision = p.result.verdict.decision
        reasons.extend(p.prefix + r for r in p.result.verdict.reasons)
    return decision, reasons


def _combined_documents(passes: list[_Pass]) -> list[DocMatch]:
    seen: dict[int, DocMatch] = {}
    for p in passes:
        for m in p.result.doc_matches:
            seen.setdefault(m.document_id, m)
    return list(seen.values())


def _apply_masks(
    msgs: list[Message], passes: list[_Pass], force: bool = False
) -> list[Message] | None:
    """Masked copy of the conversation. Untouched messages keep their original text.

    Normally only passes whose verdict is mask are rewritten. `force` rewrites every pass that
    found something, whatever its verdict (a reroute answers the whole thing on a company model).
    """
    out = list(msgs)
    for p in passes:
        if force:
            if not p.result.findings:
                continue
        elif p.result.verdict.decision != Decision.MASK:
            continue
        if p.masked is None:
            return None
        for k, i in enumerate(p.indexes):
            if p.masked[k] != p.normalised[k]:
                out[i] = Message(role=msgs[i].role, content=p.masked[k])
    return out


@app.post("/v1/inspect", response_model=InspectResponse)
def inspect(
    req: InspectRequest, background: BackgroundTasks, response: Response
) -> InspectResponse:
    msgs = req.messages
    new_idx, history_idx, trusted_idx = _group_messages(msgs)
    attached = _attachment_text(req)
    if sum(len(m.content) for m in msgs) + len(attached) > MAX_INSPECT_CHARS:
        raise HTTPException(
            status_code=413,
            detail="This request is too long to check (over 100,000 characters). "
            "Shorten it or split it into smaller messages.",
        )
    if not new_idx and not history_idx and not trusted_idx and not attached:
        return InspectResponse(decision=Decision.ALLOW, reasons=[])
    clock = time.perf_counter()
    policies = groups.effective(policy_store.engine, policy_store.current(), req.user_id, req.team)
    finders = _finders()
    documents = _documents()
    passes: list[_Pass] = []
    first: _Pass | None = None
    decoys: list[Owner] = []
    if new_idx or attached:
        texts = [msgs[i].content for i in new_idx]
        r1, m1, n1 = _inspect_group(
            texts,
            attached,
            policies,
            None,
            finders=finders,
            view_finders=[find_yara, injection_finder],
            doc_match=documents.match,
        )
        first = _Pass(r1, new_idx, m1, n1)
        passes.append(first)
        decoys = _decoy_alarm(r1)
    t_checks = time.perf_counter()
    placeholders = dict(first.result.placeholders) if first else None
    earlier = [f for f in finders if f != injection_classifier.find]
    applied: list[int] = []
    accepted = frozenset(i for i in req.accepted_indexes if 0 <= i < len(msgs))
    for group in _history_groups(msgs, history_idx, trusted_idx, accepted):
        mask_injection = True
        view_finders: list[Finder]
        if group.kind == "trusted":
            # System, developer and assistant text: secrets and personal data count, but an
            # injection phrase there is the company's own prompt or a model's answer.
            group_finders = [f for f in earlier if f != injection_finder]
            view_finders = [find_yara]
        elif group.kind == "instructions":
            group_finders = [
                injection_finder_instructions if f == injection_finder else f for f in earlier
            ]
            view_finders = [find_yara, injection_finder_instructions]
        else:
            group_finders = earlier
            view_finders = [find_yara, injection_finder]
            mask_injection = group.kind != "tool"
        # Earlier turns get the same checks as new content, but not the slow injection model.
        rg, mg, ng = _inspect_group(
            [msgs[i].content for i in group.indexes],
            "",
            policies,
            placeholders,
            finders=group_finders if group.kind == "trusted" else _for_history(group_finders),
            view_finders=view_finders,
            doc_match=partial(_history_matches, documents),
            mask_injection=mask_injection,
        )
        if group.kind == "tool":
            cap_injection(rg, policies)
        earlier_pass = _Pass(rg, group.indexes, mg, ng, group.prefix)
        if group.accepted:
            applied.extend(group.indexes)
            _lower_accepted(earlier_pass)
        passes.append(earlier_pass)
        placeholders = rg.placeholders
    t_history = time.perf_counter()
    memory_reasons: list[str] = []
    leaked_copy = None
    if first:
        reasons_before = len(first.result.verdict.reasons)
        _escalate_rebuilds(req, first.result)
        memory_reasons = first.result.verdict.reasons[reasons_before:]
    t_memory = time.perf_counter()
    if first:
        leaked_copy = _attribute_copy(
            first.result, "\n\n".join(msgs[i].content for i in new_idx) + attached
        )
    t_marks = time.perf_counter()
    response.headers["Server-Timing"] = (
        f"checks;dur={(t_checks - clock) * 1000:.1f}, "
        f"history;dur={(t_history - t_checks) * 1000:.1f}, "
        f"memory;dur={(t_memory - t_history) * 1000:.1f}, "
        f"marks;dur={(t_marks - t_memory) * 1000:.1f}"
    )
    would_have_decision, combined_reasons = _combine_decisions(passes)
    masked: list[Message] | None = None
    session_id = None
    extra_reasons: list[str] = []
    if would_have_decision == Decision.MASK and attached:
        # Masking cannot rewrite a file the model will receive, so ask before sending it.
        would_have_decision = Decision.WARN
        extra_reasons.append("An attached file contains sensitive data that cannot be masked")
    elif would_have_decision == Decision.MASK:
        masked = _apply_masks(msgs, passes)
        if masked is None:
            would_have_decision = Decision.WARN
            extra_reasons.append("Part of the conversation could not be masked safely")
    combined_reasons += extra_reasons
    would_have = str(would_have_decision)
    shadow = would_have_decision != Decision.ALLOW and settings_store.get_bool(
        policy_store.engine, settings_store.SHADOW
    )
    top = max(passes, key=lambda p: PRECEDENCE[p.result.verdict.decision])
    steps = build_trace(top.result, memory_reasons if top is first else None)
    findings = [f for p in passes for f in p.result.findings]
    categories = [f.category for f in findings]
    decision = would_have_decision
    reasons = combined_reasons
    rerouted = False
    if req.reroute and not shadow and _can_reroute(decision, categories, memory_reasons, attached):
        # X31: never to the blocked tool. Every pass is masked, not only the ones that said mask.
        reroute_masked = _apply_masks(msgs, passes, force=True)
        if reroute_masked is not None:
            rerouted = True
            masked = reroute_masked
    if rerouted:
        decision = Decision.LOCAL
        reasons = [
            *reasons,
            "Rerouted to Company AI: answered on a company-run model, sensitive data masked.",
        ]
        session_id = sessions.create(req.user_id, placeholders or {})
    elif shadow:
        # Shadow mode: record what the policy would have done, but let the message through.
        decision = Decision.ALLOW
        reasons = [
            f"Shadow mode: the policy would have chosen '{would_have}'. Nothing was changed."
        ]
        masked = None
    elif decision == Decision.MASK and masked is not None:
        session_id = sessions.create(req.user_id, placeholders or {})
    docs = _combined_documents(passes)
    first_docs = first.result.doc_matches if first else []
    # Written after the answer is sent, so the database never adds to the user's wait.
    # A reroute does not create a new incident: it changes the one the person just caused.
    if rerouted:
        background.add_task(record_reroute, policy_store.engine, req.user_id)
    else:
        background.add_task(
            record_decision,
            policy_store.engine,
            user=req.user_id,
            team=req.team,
            decision=would_have,
            categories=categories,
            reasons=combined_reasons,
            masked_preview=findings[0].masked_preview if findings else None,
            document_id=(
                first_docs[0].document_id
                if first_docs
                else decoys[0].document_id
                if decoys
                else docs[0].document_id
                if docs
                else None
            ),
            score=(
                first_docs[0].score
                if first_docs
                else docs[0].score
                if docs and not decoys
                else None
            ),
            copy_code=leaked_copy,
            trace=steps,
            shadow=shadow,
            tool=req.tool,
            channel=req.channel,
        )
    for owner in decoys:
        background.add_task(record_alarm, policy_store.engine, owner, req.user_id, req.team)
    first_categories = [f.category for f in first.result.findings] if first else []
    if not shadow and alerts.is_critical(would_have, first_categories):
        background.add_task(alerts.notify, would_have, first_categories, req.user_id, req.team)
    suggestion = None
    if (
        decision == Decision.WARN
        and first is not None
        and first.masked is not None
        and first.masked[-1] != first.normalised[-1]
    ):
        # X19: a warning also offers a safe rewrite, and we count how often it is shown.
        suggestion = first.masked[-1]
        background.add_task(_count_coaching, coaching.SHOWN)
    warned = sorted(
        {i for p in passes if p.result.verdict.decision == Decision.WARN for i in p.indexes}
    )
    return InspectResponse(
        accepted_applied=sorted(applied),
        warned_indexes=warned,
        session_id=session_id,
        suggested_rewrite=suggestion,
        decision=decision,
        reasons=reasons,
        trace=[TraceStep(**x) for x in steps],
        shadow_decision=would_have if shadow else None,
        rerouted=rerouted,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in findings
        ],
        masked_messages=masked,
        evasion_signals=sorted({s for p in passes for s in p.result.evasion_signals}),
        documents=[
            DocumentHit(
                document_id=m.document_id,
                sensitivity=m.sensitivity,
                kind=m.kind,
                score=m.score,
                matched_chunks=m.matched_chunks,
                total_chunks=m.total_chunks,
            )
            for m in docs
        ],
    )


def _who(authorization: str | None) -> Identity:
    """The user behind a personal gateway key. The client is never trusted to name itself."""
    key = bearer_token(authorization)
    if key is None:
        raise HTTPException(status_code=401, detail="Add your personal key in the extension.")
    try:
        found = resolve_key(key)
    except GatewayUnavailable as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    if found is None:
        raise HTTPException(
            status_code=401, detail="This key is not known to the gate. Copy it again from Connect."
        )
    return found


@app.post("/v1/extension/inspect", response_model=ExtensionVerdict)
def extension_inspect(
    body: ExtensionInspect,
    background: BackgroundTasks,
    response: Response,
    authorization: str | None = Header(default=None),
) -> ExtensionVerdict:
    """X27: check text typed or pasted into a personal AI tool in the browser."""
    who = _who(authorization)
    out = inspect(
        InspectRequest(
            user_id=who.user_id,
            team=who.team,
            model=body.model,
            tool=body.model,
            channel="browser",
            messages=[Message(role="user", content=body.text)],
        ),
        background,
        response,
    )
    masked = out.masked_messages[-1].content if out.masked_messages else None
    types = sorted({f.entity for f in out.findings})
    return ExtensionVerdict(
        decision=out.decision,
        reasons=out.reasons,
        entity_types=types,
        masked_text=masked,
        shadow=out.shadow_decision is not None,
        would_have=out.shadow_decision,
        alternative_url=settings.company_ai_url,
        user_id=who.user_id,
    )


@app.post("/v1/extension/ack")
def extension_ack(
    body: ExtensionAck,
    background: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    """X27: the person chose "Send anyway" on a warning. Recorded like the gateway's X-DNA-Ack."""
    who = _who(authorization)
    background.add_task(record_ack, policy_store.engine, who.user_id, body.reason)
    return {"status": "recorded"}


@app.get("/v1/extension/me", response_model=ExtensionMe)
def extension_me(authorization: str | None = Header(default=None)) -> ExtensionMe:
    """X27: lets the popup show who the key belongs to and whether shadow mode is on."""
    who = _who(authorization)
    return ExtensionMe(
        user_id=who.user_id,
        team=who.team,
        shadow_mode=settings_store.get_bool(policy_store.engine, settings_store.SHADOW),
        incidents_url=f"{settings.web_url}/security/history?user={who.user_id}",
    )


@app.post("/v1/unmask", response_model=UnmaskResponse)
def unmask_answer(req: UnmaskRequest) -> UnmaskResponse:
    """Restore masked values in an answer, only for the user who sent them."""
    mapping = sessions.get(req.session_id, req.user_id)
    if mapping is None:
        return UnmaskResponse(text=req.text, restored=0)
    restored = sum(1 for token in mapping if token in req.text)
    return UnmaskResponse(text=unmask(req.text, mapping), restored=restored)


WITHHELD_NOTICE = "[Removed: this answer repeated text from a protected company document.]"


@app.post("/v1/inspect-output", response_model=InspectOutputResponse)
def inspect_output(req: InspectOutputRequest) -> InspectOutputResponse:
    """Check what a model said before the person sees it (X7).

    Echoed secrets and identifiers are masked. An answer that reproduces a protected document is
    withheld whole, because a masked copy of a board memo is still the board memo.
    """
    text = normalise(req.text).text
    matches = [
        m
        for m in _documents().match(text)
        if m.kind == "copy" or m.score >= HIGH_CONFIDENCE
        if m.sensitivity in ("restricted", "confidential")
    ]
    if matches:
        return InspectOutputResponse(
            text=WITHHELD_NOTICE,
            changed=True,
            withheld=True,
            findings=[
                FindingOut(entity="DOCUMENT", category="document", masked_preview=m.title)
                for m in matches
            ],
        )
    # Mask the answer as written unless the cleaned-up copy (zero-width characters and look-alikes
    # removed) finds something the written text does not: a value hidden on purpose. Only then is
    # the cleaned-up copy masked, and it is scanned once more so a finding that only the written
    # text had is not dropped. The _OUT label keeps these tokens apart from the person's own
    # [IBAN_1].
    raw_found = _add_without_overlap(find_patterns(req.text), find_yara(req.text))
    clean_found = _add_without_overlap(find_patterns(text), find_yara(text))
    hidden = Counter((f.entity, f.value) for f in clean_found) - Counter(
        (f.entity, f.value) for f in raw_found
    )
    if not hidden:
        findings = raw_found
        masked, _ = mask(req.text, findings, label_suffix="_OUT")
    else:
        findings = clean_found
        masked, mapping = mask(text, findings, label_suffix="_OUT")
        more = [
            f
            for f in _add_without_overlap(find_patterns(masked), find_yara(masked))
            if "_OUT_" not in f.value
        ]
        if more:
            masked, _ = mask(masked, more, existing=mapping, label_suffix="_OUT")
            findings = [*findings, *more]
    if not findings:
        return InspectOutputResponse(text=req.text)
    # Fail closed: if anything is still detectable in what is about to be shown, withhold it.
    for view in (masked, normalise(masked).text):
        if any(
            "_OUT_" not in f.value
            for f in _add_without_overlap(find_patterns(view), find_yara(view))
        ):
            return InspectOutputResponse(
                text=WITHHELD_NOTICE,
                changed=True,
                withheld=True,
                findings=[
                    FindingOut(
                        entity=f.entity, category=f.category, masked_preview=f.masked_preview
                    )
                    for f in findings
                ],
            )
    return InspectOutputResponse(
        text=masked,
        changed=True,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in findings
        ],
    )


@app.post("/v1/inspect-tool-result", response_model=ToolResultResponse)
def inspect_tool_result(req: ToolResultRequest, background: BackgroundTasks) -> ToolResultResponse:
    """Text coming back from a tool (MCP server, web page, file) is untrusted: it may carry
    instructions for the model. Injection blocks it; secrets are masked (PRD 9.5)."""
    result = inspect_text(
        req.text,
        policy_store.current(),
        [find_yara, injection_finder, injection_classifier.find],
        doc_matcher=_documents().match,
        priority_finder=_honeytokens().find,
    )
    owners = _decoy_alarm(result)
    for owner in owners:
        background.add_task(record_alarm, policy_store.engine, owner, req.user_id, req.team)
    decision = str(result.verdict.decision)
    reasons = list(result.verdict.reasons)
    # The tool-result answer has three values. A warning is masked when it can be (nobody is
    # there to ask), and confidential company text that would go to the local model is withheld.
    text = result.masked_text
    if decision == "warn":
        decision = "mask" if text != req.text else "block"
    elif decision == "local":
        decision = "block"
        reasons.append("confidential company text in a tool result")
    if decision not in ("block", "mask"):
        return ToolResultResponse(decision="allow", text=req.text)
    background.add_task(
        record_decision,
        policy_store.engine,
        user=req.user_id,
        team=req.team,
        decision=decision,
        categories=[f.category for f in result.findings],
        reasons=reasons,
        masked_preview=result.findings[0].masked_preview if result.findings else None,
        tool=req.source,
    )
    return ToolResultResponse(
        decision=decision, text=text if decision == "mask" else "", reasons=reasons
    )


@app.post("/v1/try", response_model=TryOut)
def try_to_break(req: TryRequest) -> TryOut:
    """The "Try to break it" page: run the whole pipeline on any text and say which level caught
    it. Nothing is stored and no session memory is touched, so nobody's practice shows up as an
    incident."""
    result = inspect_text(
        req.text,
        policy_store.current(),
        _finders(),
        _documents().match,
        view_finders=[find_yara, injection_finder],
        priority_finder=_honeytokens().find,
    )
    _decoy_alarm(result)
    layers = explain(result)
    first = next((x for x in layers if x.fired and x.id != "normalise"), None)
    attempt = _attempts.add(
        decision=str(result.verdict.decision),
        caught_by=first.label if first else None,
        preview=result.masked_text[:120],
        length=len(req.text),
        kind=req.kind,
        nickname=req.nickname,
    )
    return TryOut(
        decision=str(result.verdict.decision),
        reasons=result.verdict.reasons,
        masked_text=result.masked_text,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in result.findings
        ],
        evasion_signals=result.evasion_signals,
        layers=[LayerOut(**x.__dict__) for x in layers],
        caught_by=first.label if first else None,
        attempt_id=attempt.id,
    )


@app.get("/v1/try/attempts", response_model=list[Attempt])
def try_attempts() -> list[Attempt]:
    """X3: the latest attempts to break it, newest first. Kept in memory only (last 50), and
    only the masked preview is shown, so a real secret typed here is never replayed."""
    return _attempts.recent(50)


def _eval_file() -> Path:
    if not settings.data_dir:
        raise HTTPException(status_code=503, detail="The attack file is not available here.")
    return Path(settings.data_dir) / "eval" / "attacks_scripts.csv"


@app.get("/v1/breakit/board", response_model=BoardOut)
def breakit_board() -> BoardOut:
    """X28: today's attempts, how many were stopped, the misses (masked preview and kind only)
    and the top breakers (nicknames only)."""
    try:
        sub, ok = _read(breakit.breaker_counts)
    except HTTPException:
        sub, ok = Counter(), Counter()  # counters still work without the database
    return BoardOut.model_validate(breakit.board(_attempts.today(), sub, ok))


@app.post("/v1/breakit/candidates", response_model=CandidateOut, status_code=201)
def breakit_submit(req: CandidateIn) -> CandidateOut:
    """X28: "It got through". Keeps the raw text because the person chose to submit it as a test
    case; it waits in the review queue. The brain re-checks it, so only real misses are queued."""
    result = inspect_text(
        req.text,
        policy_store.current(),
        _finders(),
        _documents().match,
        view_finders=[find_yara, injection_finder],
        priority_finder=_honeytokens().find,
    )
    try:
        new_id = _write(
            lambda c: breakit.submit(
                c,
                text=req.text,
                preview=result.masked_text[:120],
                kind=req.kind,
                expected=req.expected_decision,
                got=str(result.verdict.decision),
                nickname=req.nickname,
            )
        )
        row = next(r for r in _read(breakit.pending) if r["id"] == new_id)
    except breakit.BreakitError as err:
        raise HTTPException(status_code=err.status, detail=str(err)) from err
    return CandidateOut.model_validate(row)


@app.get("/v1/breakit/candidates", response_model=list[CandidateOut])
def breakit_queue() -> list[CandidateOut]:
    """X28: the review queue for the Security area."""
    return [CandidateOut.model_validate(r) for r in _read(breakit.pending)]


@app.post("/v1/breakit/candidates/{candidate_id}/approve", response_model=ReviewOut)
def breakit_approve(candidate_id: int, req: ReviewIn) -> ReviewOut:
    path = _eval_file()
    try:
        eval_id = _write(lambda c: breakit.approve(c, candidate_id, req.reviewer, path))
    except breakit.BreakitError as err:
        raise HTTPException(status_code=err.status, detail=str(err)) from err
    except OSError as err:
        raise HTTPException(
            status_code=503, detail="The attack file could not be written. Nothing was approved."
        ) from err
    return ReviewOut(status="approved", eval_id=eval_id)


@app.post("/v1/breakit/candidates/{candidate_id}/reject", response_model=ReviewOut)
def breakit_reject(candidate_id: int, req: ReviewIn) -> ReviewOut:
    """Rejecting deletes the row, raw text included, at once."""
    try:
        _write(lambda c: breakit.reject(c, candidate_id, req.reviewer))
    except breakit.BreakitError as err:
        raise HTTPException(status_code=err.status, detail=str(err)) from err
    return ReviewOut(status="rejected")


@app.get("/v1/try/examples", response_model=list[TryExample])
def try_examples() -> list[TryExample]:
    """A few starting attacks, one per kind, taken from data/eval/attacks_scripts.csv."""
    path = Path(settings.data_dir) / "eval" / "attacks_scripts.csv" if settings.data_dir else None
    if path is None or not path.exists():
        return []
    seen: set[str] = set()
    out: list[TryExample] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cat, text = row["category"], row["text"]
            if cat in seen or len(text) > 220 or row["expected_decision"] == "allow":
                continue
            seen.add(cat)
            out.append(TryExample(category=cat, text=text))
    return out


@app.post("/v1/documents/{document_id}/honeytokens", response_model=HoneytokenOut)
def plant_honeytokens(document_id: int, req: HoneytokenRequest) -> HoneytokenOut:
    """Create decoy credentials for a document. The reply holds the lines to paste into it."""
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(status_code=503, detail="The database is not connected.")
    with engine.connect() as conn:
        title = conn.execute(
            sa.select(t.documents.c.title).where(t.documents.c.id == document_id)
        ).scalar_one_or_none()
    if title is None:
        raise HTTPException(
            status_code=404,
            detail="That document is not registered. Pick one from the Documents page.",
        )
    tokens: list[Honeytoken] = generate(req.count)
    _honeytokens().register(document_id, tokens)
    return HoneytokenOut(
        document_id=document_id,
        title=str(title),
        plant_block=plant_block(tokens),
        tokens=len(tokens),
    )


@app.get("/v1/policies", response_model=list[PolicyOut])
def list_policies() -> list[PolicyOut]:
    return [PolicyOut(**vars(row)) for row in policy_store.list_rows()]


@app.post("/v1/policies/preview", response_model=PolicyPreview)
def preview_policy(req: PolicyPreviewRequest) -> PolicyPreview:
    """What a change would have done to the last 14 days, without saving it."""
    try:
        action = Decision(req.action)
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Unknown action. Use one of: allow, mask, warn, local, block."
        ) from None
    if req.scope not in ("category", "sensitivity"):
        raise HTTPException(status_code=422, detail="Unknown scope. Use category or sensitivity.")
    out = _read(lambda c: policy_preview(c, policy_store.current(), req.scope, req.key, action))
    return PolicyPreview(**out)  # type: ignore[arg-type]


@app.put("/v1/policies", response_model=PolicyOut)
def update_policy(req: PolicyUpdate) -> PolicyOut:
    try:
        row = policy_store.update(req.scope, req.key, req.action, req.updated_by)
    except PolicyError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    return PolicyOut(**vars(row))


@app.get("/v1/policies/groups", response_model=list[GroupPolicy])
def list_group_policies() -> list[GroupPolicy]:
    return [GroupPolicy(**o.__dict__) for o in groups.load(policy_store.engine)]


@app.put("/v1/policies/groups", response_model=list[GroupPolicy])
def put_group_policy(req: GroupPolicyUpdate) -> list[GroupPolicy]:
    """Set one action for one team or role. Team first, then role, wins over the company policy."""
    o = groups.Override(req.kind, req.group, req.scope, req.key, req.action)
    try:
        items = _write(lambda c: groups.put(c, policy_store.current(), o, req.updated_by))
    except PolicyError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    return [GroupPolicy(**x.__dict__) for x in items]


@app.delete("/v1/policies/groups", response_model=list[GroupPolicy])
def delete_group_policy(
    kind: str, group: str, scope: str, key: str, updated_by: str
) -> list[GroupPolicy]:
    o = groups.Override(kind, group, scope, key, "")
    try:
        items = _write(lambda c: groups.remove(c, o, updated_by))
    except PolicyError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    return [GroupPolicy(**x.__dict__) for x in items]


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


def _count_coaching(key: str) -> None:
    engine = policy_store.engine
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            coaching.bump(conn, key)
    except sa.exc.SQLAlchemyError:
        log.warning("Could not count a coaching event")


@app.post("/v1/coaching/accepted")
def coaching_accepted(background: BackgroundTasks) -> dict[str, str]:
    """The person chose the safe rewrite. Only a count is kept."""
    background.add_task(_count_coaching, coaching.ACCEPTED)
    return {"status": "counted"}


@app.get("/v1/coaching")
def coaching_stats() -> dict[str, float | int]:
    return _read(coaching.stats)


@app.get("/v1/users/{user_id}/history")
def user_history(user_id: str) -> dict[str, Any]:
    """X24: everything one person triggered, newest first. Masked previews only."""
    return _read(lambda c: insights.history_for_user(c, user_id))


@app.get("/v1/documents/{document_id}/history")
def document_history(document_id: int) -> dict[str, Any]:
    """X24: every incident that matched one document, newest first."""
    out = _read(lambda c: insights.history_for_document(c, document_id))
    if not out["found"] and out["subject"] is None:
        raise HTTPException(
            status_code=404, detail="No such document. Check the id on the Documents page."
        )
    return out


@app.get("/v1/roi")
def roi(days: int = 30) -> dict[str, Any]:
    """X18: leaks stopped, estimated cost avoided (assumptions included) and risk per tool."""
    return _read(lambda c: insights.roi(c, min(max(days, 1), 365)))


@app.get("/v1/weekly-summary")
def weekly_summary() -> dict[str, Any]:
    """X20: plain-language weekly summary for the CISO."""
    return _read(insights.weekly_summary)


@app.post("/v1/admin/purge")
def purge(req: PurgeRequest) -> dict[str, int]:
    """X16: delete incidents older than RETENTION_DAYS (or past their expiry)."""
    days = req.days if req.days is not None else settings.retention_days
    return _write(lambda c: insights.purge_expired(c, days, datetime.now(UTC)))


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


@app.get("/v1/export/incidents")
def export_incidents(
    since: datetime | None = None,
    limit: int = 1000,
    authorization: str | None = Header(default=None),
) -> Response:
    """X30: incidents as JSON lines for a SIEM. No prompt text, no preview, no names."""
    token = settings.siem_export_token
    if token and not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="This export needs the export token.")
    events = _read(lambda c: siem.export(c, since, limit))
    body = "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events)
    return Response(content=body, media_type="application/x-ndjson")


@app.get("/v1/digest/teams", response_model=list[str])
def digest_teams() -> list[str]:
    """X32: the teams that have a digest, one per team lead."""
    return _read(digest.teams)


@app.get("/v1/digest")
def team_digest(team: str) -> dict[str, Any]:
    """X32: the weekly digest for one team, with a Markdown version and an email draft."""
    d = _read(lambda c: digest.build(c, team))
    return {**d, "markdown": digest.to_markdown(d), "email": digest.to_email(d)}


@app.get("/v1/digest.md")
def team_digest_markdown(team: str) -> Response:
    """X32: the same digest as a Markdown file. Nothing is emailed."""
    d = _read(lambda c: digest.build(c, team))
    safe = "".join(ch if ch.isalnum() else "-" for ch in team).strip("-").lower() or "team"
    return Response(
        content=digest.to_markdown(d),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="digest-{safe}.md"'},
    )


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


@app.get("/v1/compliance-report.pdf")
def compliance_report() -> Response:
    evidence = _read(lambda c: compliance.gather_evidence(c, settings.demo_mode))
    return Response(
        content=compliance.render_pdf(evidence),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="data-dna-compliance-report.pdf"'},
    )


@app.get("/v1/shadow-mode", response_model=ShadowOut)
def get_shadow() -> ShadowOut:
    counts = _read(queries.shadow_counts)
    return ShadowOut(
        enabled=settings_store.get_bool(policy_store.engine, settings_store.SHADOW),
        would_have=counts,
        total=sum(counts.values()),
    )


@app.put("/v1/shadow-mode", response_model=ShadowOut)
def put_shadow(req: ShadowIn) -> ShadowOut:
    _write(lambda c: settings_store.set_bool(c, settings_store.SHADOW, req.enabled, req.updated_by))
    return get_shadow()


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


@app.post("/v1/documents", response_model=RegisteredDocument)
def register(
    title: str = Form(min_length=1, max_length=200),
    sensitivity: str = Form(),
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
) -> RegisteredDocument:
    """Register a document so the gateway recognises it, even when it is rewritten."""
    if sensitivity not in ("internal", "confidential", "restricted"):
        raise HTTPException(
            status_code=422,
            detail="Sensitivity must be internal, confidential or restricted.",
        )
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="The database is not connected. Try again soon."
        )
    if file is not None:
        try:
            text = extract_text(file.filename or "upload.txt", file.file.read(MAX_BYTES + 1))
        except ExtractError as err:
            raise HTTPException(status_code=422, detail=str(err)) from err
    try:
        doc_id, chunks = register_document(
            engine,
            embedder,
            title,
            sensitivity,
            text,
            keep_text=settings.demo_mode,
            allow_downgrade=False,
        )
    except DowngradeRefused as err:
        raise HTTPException(status_code=409, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except sa.exc.SQLAlchemyError as err:
        raise HTTPException(
            status_code=503, detail="The document could not be saved. Nothing was changed."
        ) from err
    _documents().invalidate()
    return RegisteredDocument(id=doc_id, title=title, sensitivity=sensitivity, chunks=chunks)


def _dna_write[T](fn: Callable[[sa.Connection], T]) -> T:
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="The database is not connected. Try again soon."
        )
    try:
        with engine.begin() as conn:
            return fn(conn)
    except dna_store.DnaError as err:
        raise HTTPException(status_code=err.status, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except sa.exc.SQLAlchemyError as err:
        raise HTTPException(
            status_code=503, detail="The change could not be saved. Nothing was changed."
        ) from err


@app.post("/v1/documents/{document_id}/dna/propose", response_model=ProposeOut)
def dna_propose(document_id: int, text: str = Form(default="")) -> ProposeOut:
    """Suggest 6 to 8 marks. Nothing is saved until the owner approves them."""

    def run(conn: sa.Connection) -> ProposeOut:
        source = text.strip() or dna_store.stored_text(conn, document_id)
        if not source:
            raise dna_store.DnaError(
                "The text of this document is not stored. Send it in the text field.", 409
            )
        marks = propose_marks(source)
        return ProposeOut(
            marks=[
                MarkOut(position=m.position, variants=m.variants, preview=m.phrase(0))
                for m in marks
            ]
        )

    return _dna_write(run)


@app.post("/v1/documents/{document_id}/dna/approve", response_model=DnaState)
def dna_approve(document_id: int, req: ApproveMarks) -> DnaState:
    def run(conn: sa.Connection) -> DnaState:
        marks = [Mark(m.position, m.variants) for m in req.marks]
        dna_store.save_marks(conn, document_id, marks)
        return DnaState(enabled=True, marks=len(marks), copies=[])

    return _dna_write(run)


@app.post("/v1/documents/{document_id}/copies", response_model=list[CopyOut])
def dna_issue(document_id: int, req: CopiesRequest) -> list[CopyOut]:
    issued = _dna_write(lambda c: dna_store.issue_copies(c, document_id, req.recipients))
    return [CopyOut(copy_code=code, recipient=who) for code, who in issued]


@app.get("/v1/documents/{document_id}/dna", response_model=DnaState)
def dna_state(document_id: int) -> DnaState:
    def run(conn: sa.Connection) -> DnaState:
        marks = dna_store.load_marks(conn, document_id)
        return DnaState(
            enabled=bool(marks),
            marks=len(marks),
            copies=sorted(dna_store.load_copies(conn, document_id)),
        )

    return _read(run)


@app.get("/v1/documents/{document_id}/copies/{code}", response_class=HTMLResponse)
def dna_copy(document_id: int, code: str) -> HTMLResponse:
    title, body = _dna_write(lambda c: dna_store.render_copy_html(c, document_id, code))
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><body style='font-family:sans-serif;max-width:40rem;"
        f"margin:2rem auto;line-height:1.6'><h1>{html.escape(title)}</h1><p>{html.escape(body)}</p>"
        "</body></html>"
    )
    return HTMLResponse(page)


@app.get("/v1/documents", response_model=list[DocumentOut])
def get_documents() -> list[DocumentOut]:
    return _read(queries.documents)


@app.get("/v1/ask/presets", response_model=list[PresetOut])
def ask_presets() -> list[PresetOut]:
    return [PresetOut(id=p.id, question=p.question) for p in PRESETS]


@app.post("/v1/ask", response_model=AskOut)
def ask(req: AskRequest) -> AskOut:
    engine = policy_store.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="The database is not connected. Try again soon."
        )
    if req.question and not req.preset:
        known = match_preset(req.question)
        if known is not None:
            # Same sentence as a reviewed preset: use its fixed SQL, no model call.
            try:
                return AskOut(**run_preset(engine, known))
            except sa.exc.SQLAlchemyError as err:
                raise HTTPException(
                    status_code=503, detail="The data could not be read. Try again soon."
                ) from err
        try:
            answer = ask_free(engine, req.question)
            if answer is None:
                raise HTTPException(
                    status_code=503,
                    detail="Free questions are not available right now. Use a preset question "
                    "or try again in a minute.",
                )
            return AskOut(**answer)
        except AskError as err:
            raise HTTPException(status_code=422, detail=str(err)) from err
    preset = BY_ID.get(req.preset or "")
    if preset is None:
        raise HTTPException(
            status_code=404,
            detail="That question is not on the list. Pick one of the preset questions.",
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


def _tool_error(err: toolrequests.RequestError) -> HTTPException:
    return HTTPException(status_code=err.status, detail=str(err))


@app.post("/v1/tool-requests", response_model=ToolRequestOut, status_code=201)
def request_tool(req: ToolRequestIn) -> ToolRequestOut:
    """X29: an employee asks for an AI tool."""
    try:
        rid = _write(
            lambda c: toolrequests.create(
                c, requester=req.user_id, team=req.team, tool=req.tool, reason=req.reason
            )
        )
        return ToolRequestOut.model_validate(_read(lambda c: toolrequests.get(c, rid)))
    except toolrequests.RequestError as err:
        raise _tool_error(err) from err


@app.get("/v1/tool-requests", response_model=list[ToolRequestOut])
def list_tool_requests(status: str | None = None) -> list[ToolRequestOut]:
    return [
        ToolRequestOut.model_validate(r) for r in _read(lambda c: toolrequests.listing(c, status))
    ]


@app.post("/v1/tool-requests/{request_id}/decision", response_model=ToolRequestOut)
def decide_tool_request(request_id: int, req: ToolDecisionIn) -> ToolRequestOut:
    """X29: security approves (risk, allowed data, optional alternative) or rejects."""
    try:
        row = _write(
            lambda c: toolrequests.decide(
                c,
                request_id,
                reviewer=req.reviewer,
                approve=req.approve,
                risk=req.risk,
                allowed_categories=req.allowed_categories,
                alternative=req.alternative,
                note=req.note,
            )
        )
    except toolrequests.RequestError as err:
        raise _tool_error(err) from err
    return ToolRequestOut.model_validate(row)


@app.post("/v1/users/{user_id}/tool-request-outcomes", response_model=list[ToolRequestOut])
def tool_request_outcomes(
    user_id: str, authorization: str | None = Header(default=None)
) -> list[ToolRequestOut]:
    """X29: decisions the person has not seen yet. Shown once, on their next message."""
    if _who(authorization).user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="These outcomes belong to another person. Open the chat with your own key.",
        )
    rows = _write(lambda c: toolrequests.collect_outcomes(c, user_id))
    return [ToolRequestOut.model_validate(r) for r in rows]
