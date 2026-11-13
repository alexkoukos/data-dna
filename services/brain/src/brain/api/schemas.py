from datetime import datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class InspectRequest(BaseModel):
    user_id: str = "anonymous"
    team: str = "unknown"
    model: str = "default"
    messages: list[Message]


class FindingOut(BaseModel):
    entity: str
    category: str
    masked_preview: str


class InspectResponse(BaseModel):
    decision: str
    reasons: list[str]
    findings: list[FindingOut] = Field(default_factory=list)
    masked_messages: list[Message] | None = None
    evasion_signals: list[str] = Field(default_factory=list)
    session_id: str | None = None


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
