"""X28: the break-it leaderboard and the self-growing attack set.

Attempts are counted in memory and never keep the typed text, only a masked preview, the kind
and an optional nickname. Raw text exists in one place: a candidate row the person chose to
submit as a test case. Approving writes it to the eval file and blanks the row; rejecting
deletes the row. Break-it practice never creates an incident.
"""

import csv
import threading
import uuid
from collections import Counter, deque
from datetime import UTC, date, datetime
from pathlib import Path

import sqlalchemy as sa

from brain.api.schemas import Attempt
from brain.db import tables as t
from brain.policy.store import audit_table

KINDS = {
    "spacing",
    "encoding",
    "look_alike",
    "other_digits",
    "greeklish",
    "injection",
    "secrets",
    "documents",
    "honeytoken",
    "other",
}
EXPECTED = {"mask", "warn", "block"}
MAX_PENDING = 200
CSV_COLUMNS = ["id", "category", "lang", "text", "expected_decision", "notes", "source", "added"]
_csv_lock = threading.Lock()


class BreakitError(ValueError):
    """A refusal the person can act on. `status` is the HTTP status to answer with."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


class AttemptLog:
    """Today's attempts, newest last. In memory only: it resets when the brain restarts."""

    def __init__(self, size: int = 5000) -> None:
        self._items: deque[Attempt] = deque(maxlen=size)

    def add(self, **kw: object) -> Attempt:
        item = Attempt(id=uuid.uuid4().hex[:12], at=datetime.now(UTC), **kw)  # type: ignore[arg-type]
        self._items.append(item)
        return item

    def clear(self) -> None:
        self._items.clear()

    def recent(self, n: int = 50) -> list[Attempt]:
        return list(reversed(self._items))[:n]

    def find(self, attempt_id: str) -> Attempt | None:
        return next((a for a in self._items if a.id == attempt_id), None)

    def today(self, day: date | None = None) -> list[Attempt]:
        day = day or datetime.now(UTC).date()
        return [a for a in self._items if a.at.date() == day]


def board(
    attempts: list[Attempt], breakers: Counter[str], approved: Counter[str]
) -> dict[str, object]:
    """Counters, the list of misses (masked preview and kind only) and the top breakers."""
    stopped = sum(a.decision != "allow" for a in attempts)
    through = len(attempts) - stopped
    return {
        "attempts": len(attempts),
        "stopped": stopped,
        "got_through": through,
        "catch_rate": round(100 * stopped / len(attempts), 1) if attempts else None,
        "misses": [
            {"id": a.id, "kind": a.kind, "preview": a.preview, "nickname": a.nickname, "at": a.at}
            for a in reversed(attempts)
            if a.decision == "allow"
        ][:20],
        "top_breakers": [
            {"nickname": n, "submitted": c, "approved": approved.get(n, 0)}
            for n, c in sorted(
                breakers.items(), key=lambda kv: (-approved.get(kv[0], 0), -kv[1], kv[0])
            )[:5]
        ],
    }


def breaker_counts(conn: sa.Connection) -> tuple[Counter[str], Counter[str]]:
    """Per nickname: candidates submitted (rejected rows are gone) and how many were approved."""
    c = t.breakit_candidates.c
    rows = conn.execute(
        sa.select(c.nickname, c.status).where(c.nickname.is_not(None), c.nickname != "")
    ).all()
    sub: Counter[str] = Counter(str(n) for n, _ in rows)
    ok: Counter[str] = Counter(str(n) for n, s in rows if s == "approved")
    return sub, ok


def submit(
    conn: sa.Connection,
    *,
    text: str,
    preview: str,
    kind: str,
    expected: str,
    got: str,
    nickname: str | None,
) -> int:
    if kind not in KINDS:
        raise BreakitError("Pick one of the attack kinds from the list.")
    if expected not in EXPECTED:
        raise BreakitError("Expected decision must be mask, warn or block.")
    if got != "allow":
        raise BreakitError(
            "The gate already stops this text, so it is not a miss. Nothing was submitted.", 409
        )
    pending = conn.execute(
        sa.select(sa.func.count())
        .select_from(t.breakit_candidates)
        .where(t.breakit_candidates.c.status == "pending")
    ).scalar_one()
    if pending >= MAX_PENDING:
        raise BreakitError("The review queue is full. Try again after the team has caught up.", 429)
    res = conn.execute(
        sa.insert(t.breakit_candidates).values(
            created_at=datetime.now(UTC),
            nickname=(nickname or None),
            kind=kind,
            expected_decision=expected,
            got_decision=got,
            text=text,
            preview=preview,
            status="pending",
        )
    )
    key = res.inserted_primary_key
    if key is None:
        raise sa.exc.SQLAlchemyError("candidate id not returned")
    return int(key[0])


def pending(conn: sa.Connection) -> list[dict[str, object]]:
    c = t.breakit_candidates.c
    rows = (
        conn.execute(
            sa.select(t.breakit_candidates)
            .where(c.status == "pending")
            .order_by(c.created_at, c.id)
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def _audit(
    conn: sa.Connection, actor: str, action: str, target: str, details: dict[str, str]
) -> None:
    conn.execute(
        sa.insert(audit_table).values(
            ts=datetime.now(UTC), actor=actor, action=action, target=target, details=details
        )
    )


def _next_eval_id(path: Path) -> str:
    n = 0
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r["id"].startswith("BI") and r["id"][2:].isdigit():
                    n = max(n, int(r["id"][2:]))
    return f"BI{n + 1:03d}"


def append_to_eval(path: Path, *, category: str, text: str, expected: str, day: date) -> str:
    """Add one row to attacks_scripts.csv with source=breakit and the date. Returns its id."""
    with _csv_lock:
        new_id = _next_eval_id(path)
        fresh = not path.exists() or path.stat().st_size == 0
        if not fresh and not path.read_bytes().endswith(b"\n"):
            with path.open("ab") as f:
                f.write(b"\n")
        with path.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
            if fresh:
                w.writeheader()
            w.writerow(
                {
                    "id": new_id,
                    "category": category,
                    "lang": "en",
                    "text": text,
                    "expected_decision": expected,
                    "notes": "found live on /break-it",
                    "source": "breakit",
                    "added": day.isoformat(),
                }
            )
    return new_id


def _pending_row(conn: sa.Connection, candidate_id: int) -> sa.RowMapping:
    row = (
        conn.execute(
            sa.select(t.breakit_candidates).where(t.breakit_candidates.c.id == candidate_id)
        )
        .mappings()
        .first()
    )
    if row is None or row["status"] != "pending":
        raise BreakitError("That candidate is not waiting for review any more.", 404)
    return row


def approve(conn: sa.Connection, candidate_id: int, reviewer: str, eval_path: Path) -> str:
    row = _pending_row(conn, candidate_id)
    now = datetime.now(UTC)
    new_id = append_to_eval(
        eval_path,
        category=row["kind"],
        text=row["text"] or "",
        expected=row["expected_decision"],
        day=now.date(),
    )
    conn.execute(
        sa.update(t.breakit_candidates)
        .where(t.breakit_candidates.c.id == candidate_id)
        .values(status="approved", text=None, reviewed_by=reviewer, reviewed_at=now, eval_id=new_id)
    )
    _audit(conn, reviewer, "breakit.approve", str(candidate_id), {"eval_id": new_id})
    return new_id


def reject(conn: sa.Connection, candidate_id: int, reviewer: str) -> None:
    _pending_row(conn, candidate_id)
    conn.execute(sa.delete(t.breakit_candidates).where(t.breakit_candidates.c.id == candidate_id))
    _audit(conn, reviewer, "breakit.reject", str(candidate_id), {})
