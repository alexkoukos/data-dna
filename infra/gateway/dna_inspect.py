"""Gateway-side glue between LiteLLM and the brain (PRD section 8).

Pure logic, no LiteLLM imports, so it can be unit tested without the gateway image.
`dna_guardrail.py` is the thin LiteLLM wrapper around it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

ACK_HEADER = "x-dna-ack"
LOCAL_MODEL = "local"


@dataclass
class GatewayError(Exception):
    """An answer the gateway returns instead of forwarding the request."""

    status_code: int
    body: dict[str, Any] = field(default_factory=dict)


def _ack_given(headers: dict[str, str] | None) -> bool:
    lowered = {k.lower(): v for k, v in (headers or {}).items()}
    return bool(lowered.get(ACK_HEADER, "").strip())


async def apply_decision(
    data: dict[str, Any],
    *,
    user_id: str,
    team: str,
    headers: dict[str, str] | None,
    brain_url: str,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    """Ask the brain about this request and return the (possibly changed) request.

    Raises GatewayError for warn, block and brain failures. Fails closed: if the brain
    cannot be reached the request is not forwarded.
    """
    payload = {
        "user_id": user_id,
        "team": team,
        "model": str(data.get("model", "default")),
        "messages": [
            {"role": m.get("role", "user"), "content": m.get("content") or ""}
            for m in data.get("messages", [])
            if isinstance(m.get("content") or "", str)
        ],
    }
    try:
        resp = await client.post(f"{brain_url}/v1/inspect", json=payload, timeout=10.0)
        resp.raise_for_status()
        verdict = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GatewayError(
            503,
            {
                "type": "unavailable",
                "message": "The safety check is not available, so your message was not sent.",
                "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
                "detail": type(exc).__name__,
            },
        ) from exc

    decision = verdict.get("decision", "allow")
    reasons = verdict.get("reasons", [])

    if decision == "mask" and verdict.get("masked_messages"):
        data["messages"] = verdict["masked_messages"]
        data.setdefault("metadata", {})["dna_session_id"] = verdict.get("session_id")
    elif decision == "local":
        data["model"] = LOCAL_MODEL
    elif decision == "warn" and not _ack_given(headers):
        raise GatewayError(
            409,
            {
                "type": "warn",
                "message": "This message may contain sensitive data.",
                "reasons": reasons,
                "options": ["Send anyway (add the X-DNA-Ack header with your reason)", "Edit it"],
            },
        )
    elif decision == "block":
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "This message was not sent because it contains protected data.",
                "reasons": reasons,
                "approved_alternative": "Use the company chat, which keeps data inside.",
            },
        )

    metadata = data.setdefault("metadata", {})
    metadata["dna_decision"] = decision
    metadata["dna_reasons"] = reasons
    return data


async def finalize_answer(
    text: str,
    *,
    user_id: str,
    team: str,
    session_id: str | None,
    brain_url: str,
    client: httpx.AsyncClient,
) -> str:
    """Filter a model answer, then restore the user's own masked values.

    Order matters: filter first, so only values the model invented or echoed are masked,
    then unmask, so the user's own values come back. If the brain cannot be reached the
    answer is withheld rather than returned unfiltered.
    """
    try:
        out = await client.post(
            f"{brain_url}/v1/inspect-output",
            json={"user_id": user_id, "team": team, "text": text},
            timeout=10.0,
        )
        out.raise_for_status()
        text = out.json()["text"]
        if session_id:
            back = await client.post(
                f"{brain_url}/v1/unmask",
                json={"session_id": session_id, "user_id": user_id, "text": text},
                timeout=10.0,
            )
            back.raise_for_status()
            text = back.json()["text"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise GatewayError(
            503,
            {
                "type": "unavailable",
                "message": "The answer could not be checked, so it was not shown.",
                "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
                "detail": type(exc).__name__,
            },
        ) from exc
    return text


def _delta(chunk: Any) -> Any:
    choices = getattr(chunk, "choices", None)
    return getattr(choices[0], "delta", None) if choices else None


async def rewrite_stream(
    chunks: AsyncIterator[Any], transform: Callable[[str], Awaitable[str]]
) -> AsyncIterator[Any]:
    """Check a streamed answer before the client sees any of it.

    The whole answer is collected first, because a secret or a placeholder can be split across
    chunks and a half-seen value cannot be filtered. The cleaned text is then sent in the first
    content chunk; chunks without text (role, finish reason, usage) pass through in order. The
    client still gets a normal stream, only the text arrives together.
    """
    buffered: list[Any] = []
    parts: list[str] = []
    async for chunk in chunks:
        buffered.append(chunk)
        delta = _delta(chunk)
        if delta is not None and isinstance(getattr(delta, "content", None), str):
            parts.append(delta.content)
    cleaned = await transform("".join(parts)) if parts else ""
    placed = False
    for chunk in buffered:
        delta = _delta(chunk)
        has_text = delta is not None and isinstance(getattr(delta, "content", None), str)
        if not has_text:
            yield chunk
        elif not placed:
            delta.content = cleaned
            placed = True
            yield chunk
