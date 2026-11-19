from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class Attachment(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    content_base64: str


class InspectRequest(BaseModel):
    user_id: str = "anonymous"
    team: str = "unknown"
    model: str = "default"
    reroute: bool = False  # X31: the person chose "send it to Company AI instead"
    messages: list[Message]
    attachments: list[Attachment] = Field(default_factory=list)
    tool: str | None = None
    channel: str = "gateway"


class FindingOut(BaseModel):
    entity: str
    category: str
    masked_preview: str


class DocumentHit(BaseModel):
    document_id: int
    sensitivity: str
    kind: str
    score: float
    matched_chunks: list[int]
    total_chunks: int


class TraceStep(BaseModel):
    layer: str
    fired: bool = True
    score: float | None = None
    detail: str = ""


class InspectResponse(BaseModel):
    decision: str
    reasons: list[str]
    findings: list[FindingOut] = Field(default_factory=list)
    masked_messages: list[Message] | None = None
    evasion_signals: list[str] = Field(default_factory=list)
    session_id: str | None = None
    documents: list[DocumentHit] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    shadow_decision: str | None = None
    suggested_rewrite: str | None = None
    rerouted: bool = False


class UnmaskRequest(BaseModel):
    session_id: str
    user_id: str
    text: str


class UnmaskResponse(BaseModel):
    text: str
    restored: int = 0


class InspectOutputRequest(BaseModel):
    user_id: str = "anonymous"
    team: str = "unknown"
    text: str


class InspectOutputResponse(BaseModel):
    text: str
    changed: bool = False
    withheld: bool = False
    findings: list[FindingOut] = Field(default_factory=list)


class PolicyOut(BaseModel):
    scope: str
    key: str
    action: str
    updated_by: str | None = None
    updated_at: datetime | None = None


class PolicyUpdate(BaseModel):
    scope: str
    key: str
    action: str
    updated_by: str


class GroupPolicy(BaseModel):
    kind: str
    group: str
    scope: str
    key: str
    action: str


class GroupPolicyUpdate(GroupPolicy):
    updated_by: str


class KeyRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")
    team: str = Field(default="general", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")


class KeyResponse(BaseModel):
    key: str
    user_id: str
    team: str
    default_model: str


class MetricsOut(BaseModel):
    prompts_checked: int
    zero_llm_share: float | None
    incidents_7d: int
    incidents_prev_7d: int
    unapproved_tools: int
    demo_data: bool
    as_of: datetime | None = None


class IncidentOut(BaseModel):
    id: int
    ts: datetime
    user: str
    team: str | None
    tool: str | None
    decision: str
    categories: list[str]
    reasons: list[str]
    masked_preview: str | None = None
    score: float | None = None
    shadow: bool = False
    trace: list[TraceStep] = Field(default_factory=list)


class IncidentPage(BaseModel):
    total: int
    items: list[IncidentOut]


class ToolOut(BaseModel):
    id: int
    name: str
    vendor: str | None
    category: str | None
    approval: str
    risk: str
    reason: str | None
    alternative: str | None
    teams: list[str]
    peak_users: int
    requests: int
    trend: list[int]
    first_seen: str | None
    # Where we saw it: the browser extension, network logs (Squid, Zeek, gateway), or both.
    sources: list[str] = Field(default_factory=list)
    allowed_categories: list[str] = Field(default_factory=list)


class DocumentOut(BaseModel):
    id: int
    title: str
    sensitivity: str
    dna_enabled: bool
    created_at: datetime | None = None
    incidents: int = 0


class SeenOut(BaseModel):
    seen: bool


class PresetOut(BaseModel):
    id: str
    question: str


class AskRequest(BaseModel):
    preset: str | None = None
    question: str | None = Field(default=None, min_length=3, max_length=500)


class AskOut(BaseModel):
    id: str
    question: str
    sql: str
    parameters: dict[str, str]
    columns: list[str]
    rows: list[list[Any]]


class DocumentMatch(BaseModel):
    id: int
    title: str
    sensitivity: str


class RevealOut(BaseModel):
    id: int
    incident_id: int
    requested_by: str
    reason: str
    approved_by: str | None = None
    status: str
    ts: datetime | None = None


class IncidentDetail(BaseModel):
    incident: IncidentOut
    copy_code: str | None = None
    document: DocumentMatch | None = None
    timeline: list[IncidentOut]
    reveals: list[RevealOut]


class RevealRequest(BaseModel):
    incident_id: int
    requested_by: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=10, max_length=500)


class RevealDecision(BaseModel):
    decided_by: str = Field(min_length=1, max_length=80)


class IdentityOut(BaseModel):
    pseudonym: str
    display_name: str | None


class RegisteredDocument(BaseModel):
    id: int
    title: str
    sensitivity: str
    chunks: int


class MarkIn(BaseModel):
    position: int = Field(ge=0)
    variants: list[str] = Field(min_length=4, max_length=4)


class MarkOut(MarkIn):
    preview: str


class ProposeOut(BaseModel):
    marks: list[MarkOut]


class ApproveMarks(BaseModel):
    marks: list[MarkIn]


class CopiesRequest(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=200)


class CopyOut(BaseModel):
    copy_code: str
    recipient: str


class DnaState(BaseModel):
    enabled: bool
    marks: int
    copies: list[str]


class ToolResultRequest(BaseModel):
    text: str
    source: str = Field(default="MCP tool", max_length=100)
    user_id: str = "anonymous"
    team: str = "unknown"


class ToolResultResponse(BaseModel):
    decision: str
    text: str
    reasons: list[str] = Field(default_factory=list)


class TryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    kind: str = Field(default="other", max_length=32, pattern=r"^[a-z_]+$")
    nickname: str | None = Field(default=None, max_length=24, pattern=r"^[\w .\-]{1,24}$")


class LayerOut(BaseModel):
    id: str
    level: int
    label: str
    fired: bool
    detail: str = ""


class TryOut(BaseModel):
    decision: str
    reasons: list[str]
    masked_text: str
    findings: list[FindingOut]
    evasion_signals: list[str]
    layers: list[LayerOut]
    caught_by: str | None = None
    attempt_id: str = ""


class TryExample(BaseModel):
    category: str
    text: str


class HoneytokenRequest(BaseModel):
    count: int = Field(default=2, ge=1, le=6)


class HoneytokenOut(BaseModel):
    document_id: int
    title: str
    plant_block: str
    tokens: int


class ShadowOut(BaseModel):
    enabled: bool
    would_have: dict[str, int]
    total: int


class ShadowIn(BaseModel):
    enabled: bool
    updated_by: str = Field(min_length=1, max_length=80)


class PolicyPreviewRequest(BaseModel):
    scope: str
    key: str
    action: str


class PolicyMove(BaseModel):
    from_: str = Field(alias="from")
    to: str
    count: int


class PolicyPreview(BaseModel):
    days: int
    incidents_checked: int
    changed: int
    stricter: int
    looser: int
    moves: list[PolicyMove]


class PurgeRequest(BaseModel):
    days: int | None = Field(default=None, ge=1, le=3650)


class Attempt(BaseModel):
    id: str = ""
    at: datetime
    decision: str
    caught_by: str | None = None
    preview: str
    length: int
    kind: str = "other"
    nickname: str | None = None


class ExtensionInspect(BaseModel):
    """What the browser extension sends. Who the user is comes from the key, never from here."""

    text: str = Field(max_length=200_000)
    model: str = Field(default="ChatGPT (personal)", max_length=80)


class ExtensionVerdict(BaseModel):
    decision: str
    reasons: list[str]
    entity_types: list[str] = Field(default_factory=list)
    masked_text: str | None = None
    shadow: bool = False
    would_have: str | None = None
    alternative: str = "Company AI"
    alternative_url: str = ""
    user_id: str = ""


class ExtensionAck(BaseModel):
    reason: str = Field(default="", max_length=200)


class ExtensionMe(BaseModel):
    user_id: str
    team: str
    shadow_mode: bool
    incidents_url: str


class CandidateIn(BaseModel):
    """ "It got through": the person chose to submit this raw text as a test case."""

    text: str = Field(min_length=1, max_length=2000)
    expected_decision: str
    kind: str = Field(max_length=32, pattern=r"^[a-z_]+$")
    nickname: str | None = Field(default=None, max_length=24, pattern=r"^[\w .\-]{1,24}$")


class CandidateOut(BaseModel):
    id: int
    created_at: datetime
    nickname: str | None = None
    kind: str
    expected_decision: str
    got_decision: str
    text: str | None = None
    preview: str


class ReviewIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)


class ReviewOut(BaseModel):
    status: str
    eval_id: str | None = None


class BreakerOut(BaseModel):
    nickname: str
    submitted: int
    approved: int


class MissOut(BaseModel):
    id: str
    kind: str
    preview: str
    nickname: str | None = None
    at: datetime


class BoardOut(BaseModel):
    attempts: int
    stopped: int
    got_through: int
    catch_rate: float | None = None
    misses: list[MissOut]
    top_breakers: list[BreakerOut]


_NAME = r"^[A-Za-z0-9_.\-]+$"


class ToolRequestIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=64, pattern=_NAME)
    team: str = Field(default="general", min_length=1, max_length=64, pattern=_NAME)
    tool: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=500)


class ToolRequestOut(BaseModel):
    id: int
    created_at: datetime
    requester: str
    team: str
    tool: str
    reason: str
    status: str
    decided_by: str | None = None
    decided_at: datetime | None = None
    note: str | None = None
    risk: str | None = None
    allowed_categories: list[str] | None = None
    alternative: str | None = None


class ToolDecisionIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)
    approve: bool
    risk: str | None = None
    allowed_categories: list[str] = Field(default_factory=list, max_length=20)
    alternative: str | None = Field(default=None, max_length=80)
    note: str = Field(default="", max_length=300)
