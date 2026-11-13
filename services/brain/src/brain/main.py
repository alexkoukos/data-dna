"""FastAPI entrypoint for the brain service."""

import asyncio
import base64
import binascii
import html
import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import sqlalchemy as sa
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse

from brain import compliance, queries, reveal, settings_store
from brain.api.schemas import (
    ApproveMarks,
    AskOut,
    AskRequest,
    CopiesRequest,
    CopyOut,
    DnaState,
    DocumentHit,
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
    MarkOut,
    Message,
    MetricsOut,
    PolicyOut,
    PolicyPreview,
    PolicyPreviewRequest,
    PolicyUpdate,
    PresetOut,
    ProposeOut,
    RegisteredDocument,
    RevealDecision,
    RevealOut,
    RevealRequest,
    SeenOut,
    ShadowIn,
    ShadowOut,
    ToolOut,
    ToolResultRequest,
    ToolResultResponse,
    TraceStep,
    UnmaskRequest,
    UnmaskResponse,
)
from brain.ask.free import AskError, run_free
from brain.ask.presets import BY_ID, PRESETS, run_preset
from brain.clients import ClientStore
from brain.config import settings
from brain.db import tables as t
from brain.db.engine import ensure_schema, make_engine
from brain.detection.entities import EntityDetector
from brain.detection.normalize import normalise
from brain.detection.patterns import find_patterns, mask, unmask
from brain.detection.pipeline import (
    HIGH_CONFIDENCE,
    Finder,
    InspectResult,
    _add_without_overlap,
    inspect_text,
)
from brain.detection.yara_rules import find_yara
from brain.dna import store as dna_store
from brain.dna.marks import Mark, propose_marks
from brain.documents.embeddings import E5Embedder
from brain.documents.extract import MAX_BYTES, ExtractError, extract_text
from brain.documents.loader import load_documents
from brain.documents.registry import DocumentIndex, register_document
from brain.documents.session import update_coverage
from brain.injection.classifier import InjectionClassifier
from brain.injection.heuristics import injection_finder
from brain.keys import KeyError_, create_key, default_model
from brain.policy.engine import Decision
from brain.policy.preview import preview as policy_preview
from brain.policy.store import PolicyError, PolicyStore
from brain.records import record_decision, user_row_id
from brain.seed.load import run_seed
from brain.sessions import sessions
from brain.trace import build_trace

log = logging.getLogger(__name__)
policy_store = PolicyStore(make_engine())
entity_detector = EntityDetector()
injection_classifier = InjectionClassifier()
_client_store: ClientStore | None = None


embedder = E5Embedder()
_doc_index: DocumentIndex | None = None


def _documents() -> DocumentIndex:
    global _doc_index
    if _doc_index is None or _doc_index.engine is not policy_store.engine:
        _doc_index = DocumentIndex(policy_store.engine, embedder)
    return _doc_index


def _finders() -> list[Finder]:
    """Looser detectors that run after the checksum checks: people, emails, phones, clients."""
    global _client_store
    if _client_store is None or _client_store.engine is not policy_store.engine:
        _client_store = ClientStore(policy_store.engine)
    return [
        find_yara,
        injection_finder,
        injection_classifier.find,
        entity_detector.find,
        _client_store.find,
    ]


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


app = FastAPI(title="Data DNA brain", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


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
                + (str(err) if isinstance(err, ExtractError) else "the file could not be decoded."),
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
    except sa.exc.SQLAlchemyError:
        log.warning("Could not update session memory, continuing")
        return
    for r in rebuilds:
        if r.escalate:
            result.verdict.reasons.append(r.reason)
            result.verdict.decision = Decision.BLOCK


@app.post("/v1/inspect", response_model=InspectResponse)
def inspect(
    req: InspectRequest, background: BackgroundTasks, response: Response
) -> InspectResponse:
    # Only the last user message is inspected in this first slice.
    last = next((m for m in reversed(req.messages) if m.role == "user"), None)
    if last is None:
        return InspectResponse(decision=Decision.ALLOW, reasons=[])
    clock = time.perf_counter()
    attached = _attachment_text(req)
    result = inspect_text(
        last.content + attached,
        policy_store.current(),
        _finders(),
        _documents().match,
        view_finders=[find_yara, injection_finder],
    )
    t_checks = time.perf_counter()
    reasons_before = len(result.verdict.reasons)
    _escalate_rebuilds(req, result)
    memory_reasons = result.verdict.reasons[reasons_before:]
    t_memory = time.perf_counter()
    leaked_copy = _attribute_copy(result, last.content + attached)
    t_marks = time.perf_counter()
    response.headers["Server-Timing"] = (
        f"checks;dur={(t_checks - clock) * 1000:.1f}, "
        f"memory;dur={(t_memory - t_checks) * 1000:.1f}, "
        f"marks;dur={(t_marks - t_memory) * 1000:.1f}"
    )
    masked = None
    session_id = None
    if result.verdict.decision == Decision.MASK and attached:
        # Masking cannot rewrite a file the model will receive, so ask before sending it.
        result.verdict.decision = Decision.WARN
        result.verdict.reasons.append(
            "An attached file contains sensitive data that cannot be masked"
        )
    would_have = str(result.verdict.decision)
    shadow = result.verdict.decision != Decision.ALLOW and settings_store.get_bool(
        policy_store.engine, settings_store.SHADOW
    )
    steps = build_trace(result, memory_reasons)
    reasons = list(result.verdict.reasons)
    decision = result.verdict.decision
    if shadow:
        # Shadow mode: record what the policy would have done, but let the message through.
        decision = Decision.ALLOW
        reasons = [
            f"Shadow mode: the policy would have chosen '{would_have}'. Nothing was changed."
        ]
    elif decision == Decision.MASK:
        masked = [
            m if m is not last else Message(role="user", content=result.masked_text)
            for m in req.messages
        ]
        session_id = sessions.create(req.user_id, result.placeholders)
    # Written after the answer is sent, so the database never adds to the user's wait.
    background.add_task(
        record_decision,
        policy_store.engine,
        user=req.user_id,
        team=req.team,
        decision=would_have,
        categories=[f.category for f in result.findings],
        reasons=result.verdict.reasons,
        masked_preview=result.findings[0].masked_preview if result.findings else None,
        document_id=result.doc_matches[0].document_id if result.doc_matches else None,
        score=result.doc_matches[0].score if result.doc_matches else None,
        copy_code=leaked_copy,
        trace=steps,
        shadow=shadow,
    )
    return InspectResponse(
        session_id=session_id,
        decision=decision,
        reasons=reasons,
        trace=[TraceStep(**x) for x in steps],
        shadow_decision=would_have if shadow else None,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in result.findings
        ],
        masked_messages=masked,
        evasion_signals=result.evasion_signals,
        documents=[
            DocumentHit(
                document_id=m.document_id,
                sensitivity=m.sensitivity,
                kind=m.kind,
                score=m.score,
                matched_chunks=m.matched_chunks,
                total_chunks=m.total_chunks,
            )
            for m in result.doc_matches
        ],
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
    findings = _add_without_overlap(find_patterns(text), find_yara(text))
    if not findings:
        return InspectOutputResponse(text=req.text)
    masked, _ = mask(text, findings)
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
    )
    decision = str(result.verdict.decision)
    if decision not in ("block", "mask"):
        return ToolResultResponse(decision="allow", text=req.text)
    background.add_task(
        record_decision,
        policy_store.engine,
        user=req.user_id,
        team=req.team,
        decision=decision,
        categories=[f.category for f in result.findings],
        reasons=result.verdict.reasons,
        masked_preview=result.findings[0].masked_preview if result.findings else None,
        tool=req.source,
    )
    text = result.masked_text if decision == "mask" else ""
    return ToolResultResponse(decision=decision, text=text, reasons=result.verdict.reasons)


@app.get("/v1/policies", response_model=list[PolicyOut])
def list_policies() -> list[PolicyOut]:
    return [PolicyOut(**vars(row)) for row in policy_store.list_rows()]


@app.post("/v1/policies/preview", response_model=PolicyPreview)
def preview_policy(req: PolicyPreviewRequest) -> PolicyPreview:
    """What a change would have done to the last 14 days, without saving it."""
    try:
        action = Decision(req.action)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown action.") from None
    if req.scope not in ("category", "sensitivity"):
        raise HTTPException(status_code=422, detail="Unknown scope.")
    out = _read(lambda c: policy_preview(c, policy_store.current(), req.scope, req.key, action))
    return PolicyPreview(**out)  # type: ignore[arg-type]


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
            engine, embedder, title, sensitivity, text, keep_text=settings.demo_mode
        )
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
        try:
            return AskOut(**run_free(engine, req.question))
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
