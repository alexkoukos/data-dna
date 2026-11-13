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


# Every way into the gateway that carries text we understand. Anything else (images, audio,
# pass-through routes) is refused: an unchecked door would let people around the safety check.
CHAT_CALLS = {"completion", "acompletion", "text_completion", "atext_completion"}
ANTHROPIC_CALLS = {"anthropic_messages", "aanthropic_messages"}
RESPONSES_CALLS = {"responses", "aresponses"}
EMBEDDING_CALLS = {"embeddings", "aembedding"}
SUPPORTED_CALLS = CHAT_CALLS | ANTHROPIC_CALLS | RESPONSES_CALLS | EMBEDDING_CALLS


def _blocks_text(content: Any) -> tuple[str, bool]:
    """Text of a message that is a string or a list of blocks, and whether it has other blocks.

    Tool results (a file Claude Code read, for example) count as text because secrets live there.
    Images and tool calls are "other": they cannot be masked in place.
    """
    if isinstance(content, str):
        return content, False
    parts: list[str] = []
    other = False
    for block in content or []:
        if not isinstance(block, dict):
            other = True
            continue
        kind = block.get("type")
        if kind in ("text", "input_text", "output_text"):
            parts.append(str(block.get("text", "")))
        elif kind == "tool_result":
            inner, _ = _blocks_text(block.get("content"))
            parts.append(inner)
            other = True
        else:
            other = True
    return "\n".join(p for p in parts if p), other


def inspection_view(data: dict[str, Any], call_type: str) -> tuple[list[dict[str, str]], bool]:
    """The request as plain chat messages for the brain, and whether it has parts that cannot
    be masked in place."""
    if call_type in EMBEDDING_CALLS:
        raw = data.get("input")
        texts = [raw] if isinstance(raw, str) else [t for t in (raw or []) if isinstance(t, str)]
        return [{"role": "user", "content": "\n".join(texts)}], isinstance(raw, list) and len(raw) > 1
    if call_type in RESPONSES_CALLS:
        raw = data.get("input")
        if isinstance(raw, str):
            return [{"role": "user", "content": raw}], False
        out, other = [], False
        for item in raw or []:
            if isinstance(item, dict):
                text, o = _blocks_text(item.get("content"))
                out.append({"role": str(item.get("role", "user")), "content": text})
                other = other or o
        return out, other
    out, other = [], False
    for m in data.get("messages", []):
        text, o = _blocks_text(m.get("content") or "")
        out.append({"role": m.get("role", "user"), "content": text})
        other = other or (o and m is data["messages"][-1])
    return out, other


def _write_masked(data: dict[str, Any], call_type: str, masked_text: str) -> None:
    """Put the masked text of the last user message back where it came from."""
    if call_type in EMBEDDING_CALLS or (call_type in RESPONSES_CALLS and isinstance(data.get("input"), str)):
        data["input"] = masked_text
        return
    key = "input" if call_type in RESPONSES_CALLS else "messages"
    items = data[key]
    last = next(i for i in range(len(items) - 1, -1, -1) if items[i].get("role", "user") == "user")
    items[last]["content"] = masked_text


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
    call_type: str = "completion",
) -> dict[str, Any]:
    """Ask the brain about this request and return the (possibly changed) request.

    Raises GatewayError for warn, block and brain failures. Fails closed: if the brain
    cannot be reached the request is not forwarded. Works for chat, Anthropic messages,
    responses and embeddings; other kinds of request are refused.
    """
    if call_type not in SUPPORTED_CALLS:
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "This kind of request is not available through the company gateway.",
                "reasons": [f"Unsupported request type: {call_type}"],
                "approved_alternative": "Use the chat or messages interface of the gateway.",
            },
        )
    messages, unmaskable = inspection_view(data, call_type)
    payload = {
        "user_id": user_id,
        "team": team,
        "model": str(data.get("model", "default")),
        "messages": messages,
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

    if decision == "mask" and unmaskable:
        # A file, tool result or list of inputs cannot be rewritten in place: ask first instead.
        decision = "warn"
        reasons = [*reasons, "Sensitive data in a file or tool output cannot be masked automatically"]
    if decision == "mask" and verdict.get("masked_messages"):
        if call_type in CHAT_CALLS:
            data["messages"] = verdict["masked_messages"]
        else:
            _write_masked(data, call_type, verdict["masked_messages"][-1]["content"])
        data.setdefault("metadata", {})["dna_session_id"] = verdict.get("session_id")
    elif decision == "local" and call_type in EMBEDDING_CALLS:
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "This text is confidential and cannot be sent to an embedding service.",
                "reasons": reasons,
                "approved_alternative": "Use the company chat, which keeps data inside.",
            },
        )
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
