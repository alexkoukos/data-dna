"""Honeytokens (X4): decoy credentials planted inside confidential documents.

Each token is random and exists nowhere else, so when one turns up in a prompt the document it was
planted in has certainly left the company. There are no false alarms: nobody types a 20 character
random key by accident. The tokens look like the real thing (a cloud key, an API key, a mailbox)
so a person who copies a document does not think to remove them.

Planting is manual and visible: `plant_block()` returns lines to paste into the document, and the
registration endpoint stores the same values. The loader also reads a `honeytokens:` list from a
document header, for the demo documents in `data/documents/`.
"""

import logging
import secrets
import string
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.db import tables as t
from brain.detection.patterns import Finding
from brain.policy.store import audit_table

log = logging.getLogger(__name__)

KINDS = ("aws_key", "api_key", "mailbox")
_UPPER = string.ascii_uppercase + string.digits
_ALNUM = string.ascii_letters + string.digits
_WORDS = ("finance", "payroll", "treasury", "legal", "board", "audit", "deals", "reports")


@dataclass(frozen=True)
class Honeytoken:
    kind: str
    value: str


@dataclass(frozen=True)
class Owner:
    document_id: int
    title: str
    kind: str


def _pick(alphabet: str, n: int) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(n))


def generate(count: int) -> list[Honeytoken]:
    """`count` new random tokens, cycling through the kinds."""
    out: list[Honeytoken] = []
    for i in range(count):
        kind = KINDS[i % len(KINDS)]
        if kind == "aws_key":
            value = "AKIA" + _pick(_UPPER, 16)
        elif kind == "api_key":
            value = "sk-live-" + _pick(_ALNUM, 32)
        else:
            name = f"{secrets.choice(_WORDS)}.{_pick(string.ascii_lowercase, 5)}"
            value = f"{name}@vault-{_pick(string.digits, 4)}.corp-internal.example"
        out.append(Honeytoken(kind, value))
    return out


def plant_block(tokens: list[Honeytoken]) -> str:
    """Lines to paste at the end of a document. They read like leftover working notes."""
    labels = {
        "aws_key": "Archive access key (do not share)",
        "api_key": "Reporting API key",
        "mailbox": "Distribution mailbox",
    }
    return "\n".join(f"{labels[k.kind]}: {k.value}" for k in tokens)


class HoneytokenStore:
    def __init__(self, engine: Engine | None, ttl_seconds: float = 5.0) -> None:
        self._engine = engine
        self._ttl = ttl_seconds
        self._cached: dict[str, Owner] = {}
        self._cached_at = -1e9
        self._lock = threading.Lock()

    @property
    def engine(self) -> Engine | None:
        return self._engine

    def invalidate(self) -> None:
        with self._lock:
            self._cached_at = -1e9

    def register(self, document_id: int, tokens: list[Honeytoken]) -> int:
        """Store tokens for a document. A value that is already stored is left as it is."""
        if self._engine is None:
            return 0
        added = 0
        with self._engine.begin() as conn:
            for tok in tokens:
                exists = conn.execute(
                    sa.select(t.honeytokens.c.id).where(t.honeytokens.c.value == tok.value)
                ).first()
                if exists:
                    continue
                conn.execute(
                    sa.insert(t.honeytokens).values(
                        document_id=document_id,
                        kind=tok.kind,
                        value=tok.value,
                        created_at=datetime.now(UTC),
                    )
                )
                added += 1
        self.invalidate()
        return added

    def _owners(self) -> dict[str, Owner]:
        with self._lock:
            if time.monotonic() - self._cached_at < self._ttl:
                return self._cached
        loaded: dict[str, Owner] = {}
        if self._engine is not None:
            try:
                with self._engine.connect() as conn:
                    rows = conn.execute(
                        sa.select(
                            t.honeytokens.c.value,
                            t.honeytokens.c.kind,
                            t.honeytokens.c.document_id,
                            t.documents.c.title,
                        ).join(t.documents, t.documents.c.id == t.honeytokens.c.document_id)
                    ).all()
                loaded = {str(r[0]).lower(): Owner(int(r[2]), str(r[3]), str(r[1])) for r in rows}
            except sa.exc.SQLAlchemyError:
                log.warning("Could not read honeytokens, keeping the last list")
                with self._lock:
                    return self._cached
        with self._lock:
            self._cached, self._cached_at = loaded, time.monotonic()
        return loaded

    def owner(self, value: str) -> Owner | None:
        return self._owners().get(value.lower())

    def find(self, text: str) -> list[Finding]:
        """Every planted token in the text, matched without regard to letter case."""
        owners = self._owners()
        if not owners or not text:
            return []
        low = text.lower()
        found: list[Finding] = []
        for value in owners:
            start = low.find(value)
            while start != -1:
                end = start + len(value)
                found.append(Finding("HONEYTOKEN", "honeytoken", start, end, text[start:end]))
                start = low.find(value, end)
        return sorted(found, key=lambda f: f.start)

    def count(self) -> int:
        return len(self._owners())


def record_alarm(
    engine: Engine | None, owner: Owner, user: str, team: str, tool: str = "Company AI"
) -> None:
    """Write the alarm to the audit log, so it stays even if the incident row is cleaned up."""
    if engine is None:
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.insert(audit_table).values(
                    ts=datetime.now(UTC),
                    actor="honeytoken",
                    action="honeytoken.triggered",
                    target=f"document:{owner.document_id}",
                    details={
                        "title": owner.title,
                        "kind": owner.kind,
                        "user": user,
                        "team": team,
                        "tool": tool,
                    },
                )
            )
    except sa.exc.SQLAlchemyError:
        log.warning("Could not write the honeytoken alarm to the audit log")
