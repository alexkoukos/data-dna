"""X12: try a policy change on the last 14 days before saving it.

Incidents keep the categories that fired and the matched document, not the prompt, and a policy
only maps those to an action. So replaying them under the new policy gives the exact answer for
what the change would have done, without ever storing a raw prompt. Prompts that fired nothing
were allowed and stay allowed.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

import sqlalchemy as sa

from brain.db import tables as t
from brain.policy.engine import PRECEDENCE, Decision, decide
from brain.policy.store import PolicySet
from brain.queries import reference_time


def _with_change(current: PolicySet, scope: str, key: str, action: Decision) -> PolicySet:
    cats, sens = dict(current.categories), dict(current.sensitivity)
    (cats if scope == "category" else sens)[key] = action
    return PolicySet(cats, sens)


def preview(
    conn: sa.Connection,
    current: PolicySet,
    scope: str,
    key: str,
    action: Decision,
    days: int = 14,
) -> dict[str, object]:
    proposed = _with_change(current, scope, key, action)
    ref = reference_time(conn)
    rows: Sequence[Any] = []
    if ref is not None:
        rows = (
            conn.execute(
                sa.select(t.incidents.c.categories, t.documents.c.sensitivity)
                .select_from(
                    t.incidents.outerjoin(
                        t.documents, t.documents.c.id == t.incidents.c.document_id
                    )
                )
                .where(t.incidents.c.ts > ref - timedelta(days=days))
            )
            .mappings()
            .all()
        )
    moves: Counter[tuple[str, str]] = Counter()
    for r in rows:
        cats = list(r["categories"] or [])
        sens = [r["sensitivity"]] if r["sensitivity"] else []
        before = decide(cats, sens, None, current.categories, current.sensitivity).decision
        after = decide(cats, sens, None, proposed.categories, proposed.sensitivity).decision
        if before != after:
            moves[(str(before), str(after))] += 1
    stricter = sum(
        n for (b, a), n in moves.items() if PRECEDENCE[Decision(a)] > PRECEDENCE[Decision(b)]
    )
    looser = sum(
        n for (b, a), n in moves.items() if PRECEDENCE[Decision(a)] < PRECEDENCE[Decision(b)]
    )
    return {
        "days": days,
        "incidents_checked": len(rows),
        "changed": sum(moves.values()),
        "stricter": stricter,
        "looser": looser,
        "moves": [
            {"from": b, "to": a, "count": n}
            for (b, a), n in sorted(moves.items(), key=lambda x: -x[1])
        ],
    }
