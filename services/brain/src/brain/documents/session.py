"""Session memory (PRD 9.4): someone who rebuilds a document piece by piece across prompts.

For each (person, document) we keep the union of matched chunk numbers for 24 hours. When the
share of the document rebuilt reaches the limit, or a restricted document was hit in several
prompts, the decision is raised to block with a plain reason such as
"60% of Board memo rebuilt from 3 prompts".
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from brain.db import tables as t
from brain.documents.registry import DocMatch

WINDOW = timedelta(hours=24)
COVERAGE_BLOCK = 0.4  # policies.yaml: session.rebuild_coverage_block
MAX_PROMPTS_RESTRICTED = 3  # policies.yaml: session.max_prompts_per_restricted_doc


@dataclass(frozen=True)
class Rebuild:
    document_id: int
    title: str
    coverage: float
    prompts: int
    escalate: bool

    @property
    def reason(self) -> str:
        pct = round(self.coverage * 100)
        plural = "prompt" if self.prompts == 1 else "prompts"
        return f"{pct}% of '{self.title}' rebuilt from {self.prompts} {plural}"


def update_coverage(
    conn: sa.Connection, user_id: int, matches: list[DocMatch], now: datetime | None = None
) -> list[Rebuild]:
    now = now or datetime.now(UTC)
    out: list[Rebuild] = []
    for m in matches:
        where = (
            t.session_coverage.c.user_id == user_id,
            t.session_coverage.c.document_id == m.document_id,
        )
        row = conn.execute(sa.select(t.session_coverage).where(*where)).mappings().first()
        started = row["window_start"] if row else None
        if started is not None and started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        fresh = row is None or started is None or now - started > WINDOW
        seen = set() if fresh or row is None else set(row["chunk_idx"] or [])
        seen |= set(m.matched_chunks)
        prompts = 1 if fresh or row is None else int(row["prompts"] or 0) + 1
        values = {
            "chunk_idx": sorted(seen),
            "prompts": prompts,
            "window_start": now if fresh else started,
        }
        if row is None:
            conn.execute(
                sa.insert(t.session_coverage).values(
                    user_id=user_id, document_id=m.document_id, **values
                )
            )
        else:
            conn.execute(sa.update(t.session_coverage).where(*where).values(**values))
        coverage = len(seen) / m.total_chunks if m.total_chunks else 0.0
        escalate = coverage >= COVERAGE_BLOCK or (
            m.sensitivity == "restricted" and prompts >= MAX_PROMPTS_RESTRICTED
        )
        out.append(Rebuild(m.document_id, m.title, round(coverage, 3), prompts, escalate))
    return out
