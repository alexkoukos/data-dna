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
