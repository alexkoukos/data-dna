"""FastAPI entrypoint for the brain service."""

from fastapi import FastAPI

from brain.api.schemas import FindingOut, InspectRequest, InspectResponse, Message
from brain.detection.pipeline import inspect_text
from brain.policy.engine import Decision

app = FastAPI(title="Data DNA brain", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/inspect", response_model=InspectResponse)
def inspect(req: InspectRequest) -> InspectResponse:
    # Only the last user message is inspected in this first slice.
    last = next((m for m in reversed(req.messages) if m.role == "user"), None)
    if last is None:
        return InspectResponse(decision=Decision.ALLOW, reasons=[])
    result = inspect_text(last.content)
    masked = None
    if result.verdict.decision == Decision.MASK:
        masked = [
            m if m is not last else Message(role="user", content=result.masked_text)
            for m in req.messages
        ]
    return InspectResponse(
        decision=result.verdict.decision,
        reasons=result.verdict.reasons,
        findings=[
            FindingOut(entity=f.entity, category=f.category, masked_preview=f.masked_preview)
            for f in result.findings
        ],
        masked_messages=masked,
        evasion_signals=result.evasion_signals,
    )
