"""Policies in the database, seeded from policies.yaml, editable at runtime (PRD section 10).

If the database cannot be reached the engine falls back to the seed file, so detection keeps
working. Every change is written to audit_log.
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa
import yaml
from sqlalchemy.engine import Engine

from brain.policy.engine import Decision

log = logging.getLogger(__name__)

SEED_PATH = Path(__file__).with_name("policies.yaml")
SCOPES = ("category", "sensitivity")

metadata = sa.MetaData()
policies_table = sa.Table(
    "policies",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("scope", sa.Text, nullable=False),
    sa.Column("key", sa.Text, nullable=False),
    sa.Column("action", sa.Text, nullable=False),
    sa.Column("updated_by", sa.Text),
    sa.Column("updated_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint("scope", "key"),
)
audit_table = sa.Table(
    "audit_log",
    metadata,
    sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
    sa.Column("ts", sa.DateTime(timezone=True)),
    sa.Column("actor", sa.Text, nullable=False),
    sa.Column("action", sa.Text, nullable=False),
    sa.Column("target", sa.Text),
    sa.Column("details", sa.JSON),
)


class PolicyError(ValueError):
    """A change the editor asked for that is not allowed. The message is shown to the user."""


@dataclass
class PolicySet:
    categories: dict[str, Decision]
    sensitivity: dict[str, Decision]


@dataclass
class PolicyRow:
    scope: str
    key: str
    action: str
    updated_by: str | None
    updated_at: datetime | None


def load_seed() -> PolicySet:
    raw = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))
    return PolicySet(
        categories={k: Decision(v) for k, v in raw["categories"].items()},
        sensitivity={k: Decision(v) for k, v in raw["documents"]["sensitivity"].items()},
    )


class PolicyStore:
    def __init__(self, engine: Engine | None, ttl_seconds: float = 5.0) -> None:
        self._engine = engine
        self._ttl = ttl_seconds
        self._cached: PolicySet | None = None
        self._cached_at = 0.0
        self._lock = threading.Lock()
        self._seed = load_seed()

    @property
    def engine(self) -> Engine | None:
        return self._engine

    def invalidate(self) -> None:
        with self._lock:
            self._cached = None

    def current(self) -> PolicySet:
        """Policies to apply now. Cached briefly so a request does not hit the database."""
        with self._lock:
            if self._cached is not None and time.monotonic() - self._cached_at < self._ttl:
                return self._cached
        loaded = self._load()
        with self._lock:
            self._cached, self._cached_at = loaded, time.monotonic()
        return loaded

    def _load(self) -> PolicySet:
        if self._engine is None:
            return self._seed
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(sa.select(policies_table)).mappings().all()
        except sa.exc.SQLAlchemyError:
            log.warning("Policy table unreachable, using the seed file")
            return self._seed
        merged = PolicySet(dict(self._seed.categories), dict(self._seed.sensitivity))
        for row in rows:
            try:
                action = Decision(row["action"])
            except ValueError:
                continue
            target = merged.categories if row["scope"] == "category" else merged.sensitivity
            target[row["key"]] = action
        return merged

    def seed_if_empty(self) -> int:
        """Insert the seed rows when the table is empty. Returns how many rows were added."""
        if self._engine is None:
            return 0
        with self._engine.begin() as conn:
            if conn.execute(sa.select(sa.func.count()).select_from(policies_table)).scalar_one():
                return 0
            now = datetime.now(UTC)
            rows = [
                {"scope": "category", "key": k, "action": v.value, "updated_by": "seed"}
                for k, v in self._seed.categories.items()
            ] + [
                {"scope": "sensitivity", "key": k, "action": v.value, "updated_by": "seed"}
                for k, v in self._seed.sensitivity.items()
            ]
            conn.execute(sa.insert(policies_table), [{**r, "updated_at": now} for r in rows])
            return len(rows)

    def list_rows(self) -> list[PolicyRow]:
        current = self.current()
        rows: dict[tuple[str, str], PolicyRow] = {}
        for scope, mapping in (
            ("category", current.categories),
            ("sensitivity", current.sensitivity),
        ):
            for key, action in mapping.items():
                rows[(scope, key)] = PolicyRow(scope, key, action.value, "seed", None)
        if self._engine is not None:
            try:
                with self._engine.connect() as conn:
                    for r in conn.execute(sa.select(policies_table)).mappings():
                        rows[(r["scope"], r["key"])] = PolicyRow(
                            r["scope"], r["key"], r["action"], r["updated_by"], r["updated_at"]
                        )
            except sa.exc.SQLAlchemyError:
                log.warning("Policy table unreachable while listing")
        return sorted(rows.values(), key=lambda p: (p.scope, p.key))

    def update(self, scope: str, key: str, action: str, actor: str) -> PolicyRow:
        if self._engine is None:
            raise PolicyError("Policies cannot be changed because the database is not connected.")
        if scope not in SCOPES:
            raise PolicyError(f"Unknown scope '{scope}'. Use one of: {', '.join(SCOPES)}.")
        known = self._seed.categories if scope == "category" else self._seed.sensitivity
        if key not in known:
            raise PolicyError(f"Unknown {scope} '{key}'. Use one of: {', '.join(sorted(known))}.")
        try:
            decision = Decision(action)
        except ValueError:
            allowed = ", ".join(d.value for d in Decision)
            raise PolicyError(f"Unknown action '{action}'. Use one of: {allowed}.") from None
        if not actor.strip():
            raise PolicyError("Say who is making the change (updated_by).")

        now = datetime.now(UTC)
        with self._engine.begin() as conn:
            old = conn.execute(
                sa.select(policies_table.c.action).where(
                    policies_table.c.scope == scope, policies_table.c.key == key
                )
            ).scalar_one_or_none()
            if old is None:
                conn.execute(
                    sa.insert(policies_table).values(
                        scope=scope,
                        key=key,
                        action=decision.value,
                        updated_by=actor,
                        updated_at=now,
                    )
                )
            else:
                conn.execute(
                    sa.update(policies_table)
                    .where(policies_table.c.scope == scope, policies_table.c.key == key)
                    .values(action=decision.value, updated_by=actor, updated_at=now)
                )
            details: dict[str, Any] = {"from": old, "to": decision.value}
            conn.execute(
                sa.insert(audit_table).values(
                    ts=now,
                    actor=actor,
                    action="policy.update",
                    target=f"{scope}:{key}",
                    details=details,
                )
            )
        self.invalidate()
        return PolicyRow(scope, key, decision.value, actor, now)
