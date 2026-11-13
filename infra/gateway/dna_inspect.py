"""Gateway-side glue between LiteLLM and the brain (PRD section 8).

Pure logic, no LiteLLM imports, so it can be unit tested without the gateway image.
`dna_guardrail.py` is the thin LiteLLM wrapper around it.
"""

from __future__ import annotations

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
    return data
