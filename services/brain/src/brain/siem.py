"""X30: send incidents to a SOC. A JSON-lines export, an optional syslog sender (CEF) and an
optional HMAC-signed webhook.

An exported event holds only: time, a pseudonymous user key ID (never the name; the two-person
reveal still applies), team, tool, decision, categories, matched document ID and rule IDs.
It never holds prompt text, a masked preview or the free-text reasons.
"""

import hashlib
import hmac
import json
import logging
import re
import socket
from datetime import UTC, datetime
from typing import Any

import httpx
import sqlalchemy as sa

from brain.config import settings
from brain.db import tables as t

log = logging.getLogger(__name__)

SEVERITY = {"block": 8, "local": 6, "warn": 5, "rerouted": 4, "mask": 3}
FIELDS = (
    "id",
    "time",
    "user_key_id",
    "team",
    "tool",
    "decision",
    "categories",
    "document_id",
    "rule_ids",
    "shadow",
)


def slug(label: str) -> str:
    """A stable rule ID from a layer name: "Patterns and checksums" -> "patterns-and-checksums"."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def rule_ids(trace: list[dict[str, Any]] | None) -> list[str]:
    return sorted({slug(str(s.get("layer", ""))) for s in trace or [] if s.get("fired")} - {""})


def event(
    *,
    incident_id: int | None,
    ts: datetime,
    user_key_id: str,
    team: str | None,
    tool: str | None,
    decision: str,
    categories: list[str] | None,
    document_id: int | None,
    trace: list[dict[str, Any]] | None,
    shadow: bool = False,
) -> dict[str, Any]:
    """Build an event from named fields only, so nothing else can leak in by accident."""
    return {
        "id": incident_id,
        "time": ts.astimezone(UTC).isoformat(timespec="seconds"),
        "user_key_id": user_key_id,
        "team": team or "",
        "tool": tool or "",
        "decision": decision,
        "categories": sorted(set(categories or [])),
        "document_id": document_id,
        "rule_ids": rule_ids(trace),
        "shadow": bool(shadow),
    }


def _hdr(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _ext(value: str) -> str:
    return value.replace("\\", "\\\\").replace("=", "\\=").replace("\r", "\\n").replace("\n", "\\n")


def to_cef(ev: dict[str, Any]) -> str:
    """A CEF:0 line. The header escapes backslash and pipe; values also escape = and newlines."""
    when = datetime.fromisoformat(ev["time"])
    parts = {
        "rt": str(int(when.timestamp() * 1000)),
        "externalId": str(ev["id"]) if ev["id"] is not None else "",
        "suser": ev["user_key_id"],
        "act": ev["decision"],
        "cs1Label": "team",
        "cs1": ev["team"],
        "cs2Label": "tool",
        "cs2": ev["tool"],
        "cs3Label": "categories",
        "cs3": ",".join(ev["categories"]),
        "cs4Label": "ruleIds",
        "cs4": ",".join(ev["rule_ids"]),
        "cn1Label": "documentId",
        "cn1": "" if ev["document_id"] is None else str(ev["document_id"]),
        "cn2Label": "shadow",
        "cn2": "1" if ev["shadow"] else "0",
    }
    keys = list(parts)
    ext = " ".join(
        f"{k}={_ext(parts[k])}"
        for n, k in enumerate(keys)
        if parts[k] != ""
        and not (k.endswith("Label") and parts[keys[n + 1]] == "")  # no label for an empty value
    )
    name = f"Sentry {ev['decision']}: {ev['tool'] or 'AI tool'}"
    sev = SEVERITY.get(ev["decision"], 1)
    return f"CEF:0|Sentry|Gate|1.0|{_hdr(ev['decision'])}|{_hdr(name)}|{sev}|{ext}"


def sign(body: bytes, secret: str) -> str:
    """HMAC-SHA256 of the exact body, as a hex string."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, secret: str, signature: str) -> bool:
    return hmac.compare_digest(sign(body, secret), signature.removeprefix("sha256="))


def syslog_message(cef: str, host: str = "sentry", now: datetime | None = None) -> bytes:
    """RFC 3164 frame at facility local0, severity info (<134>), with the CEF line as the text."""
    stamp = (now or datetime.now(UTC)).strftime("%b %e %H:%M:%S")
    return f"<134>{stamp} {host} sentry: {cef}".encode()


def send_syslog(cef: str, host: str, port: int, proto: str) -> None:
    data = syslog_message(cef)
    if proto.lower() == "tcp":
        with socket.create_connection((host, port), timeout=3) as s:
            s.sendall(data + b"\n")
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(data, (host, port))


def send_webhook(ev: dict[str, Any], url: str, secret: str) -> None:
    body = json.dumps(ev, separators=(",", ":"), sort_keys=True).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Sentry-Signature"] = "sha256=" + sign(body, secret)
    httpx.post(url, content=body, headers=headers, timeout=5.0).raise_for_status()


def push(ev: dict[str, Any]) -> None:
    """Send one new incident to every configured destination. Never raises: a down SIEM must not
    slow or fail the person's request."""
    if settings.siem_syslog_host:
        try:
            send_syslog(
                to_cef(ev),
                settings.siem_syslog_host,
                settings.siem_syslog_port,
                settings.siem_syslog_proto,
            )
        except OSError:
            log.warning("SIEM: the syslog receiver could not be reached")
    if settings.siem_webhook_url:
        try:
            send_webhook(ev, settings.siem_webhook_url, settings.siem_webhook_secret)
        except httpx.HTTPError:
            log.warning("SIEM: the webhook could not be reached")


def export(conn: sa.Connection, since: datetime | None, limit: int = 1000) -> list[dict[str, Any]]:
    """Incidents after `since`, oldest first, as events."""
    i, u = t.incidents.c, t.users.c
    q = (
        sa.select(
            i.id,
            i.ts,
            u.pseudonym,
            i.team,
            i.tool,
            i.decision,
            i.categories,
            i.document_id,
            i.trace,
            i.shadow,
        )
        .select_from(t.incidents.join(t.users, t.users.c.id == i.user_id))
        .order_by(i.ts, i.id)
        .limit(max(1, min(limit, 5000)))
    )
    if since is not None:
        q = q.where(i.ts > since)
    return [
        event(
            incident_id=r.id,
            ts=r.ts if r.ts.tzinfo else r.ts.replace(tzinfo=UTC),
            user_key_id=r.pseudonym,
            team=r.team,
            tool=r.tool,
            decision=r.decision,
            categories=list(r.categories or []),
            document_id=r.document_id,
            trace=r.trace,
            shadow=bool(r.shadow),
        )
        for r in conn.execute(q)
    ]
