"""X13: policies per team and per role (HR may see salaries, Sales may not).

An override changes one category or sensitivity action for one group. Overrides are kept as JSON
in the `settings` table, so no database change is needed. The effective policy for a person is
the company policy, then the overrides for their team, then the overrides for their role (role
wins). A person's role is read from `users` and defaults to "employee".
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.db import tables as t
from brain.policy.engine import PRECEDENCE, Decision
from brain.policy.store import SCOPES, PolicyError, PolicySet, audit_table

log = logging.getLogger(__name__)

KEY = "group_policies"
KINDS = ("team", "role")
_TTL = 3.0
_cache: dict[int, tuple[float, list["Override"]]] = {}


@dataclass(frozen=True)
class Override:
    kind: str  # "team" or "role"
    group: str
    scope: str  # "category" or "sensitivity"
    key: str
    action: str


def _clear() -> None:
    _cache.clear()
    _roles.clear()


def load(engine: Engine | None) -> list[Override]:
    if engine is None:
        return []
    hit = _cache.get(id(engine))
    if hit is not None and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    try:
        with engine.connect() as conn:
            raw = conn.execute(
                sa.select(t.settings.c.value).where(t.settings.c.key == KEY)
            ).scalar()
    except sa.exc.SQLAlchemyError:
        log.warning("Could not read group policies, keeping the last list")
        return hit[1] if hit is not None else []
    items: list[Override] = []
    try:
        for r in json.loads(raw) if raw else []:
            items.append(Override(**r))
    except (ValueError, TypeError):
        log.warning("Group policies are not valid JSON, ignoring them")
        items = []
    _cache[id(engine)] = (time.monotonic(), items)
    return items


_roles: dict[str, tuple[float, str]] = {}
_MAX_ROLES = 10_000
ROLE_FALLBACK_SECONDS = 300.0


def _lookup_role(engine: Engine | None, user_id: str) -> str | None:
    """A person's role, or None when the database cannot be read and the last answer is too old."""
    if engine is None:
        return "employee"
    try:
        with engine.connect() as conn:
            role = conn.execute(
                sa.select(t.users.c.role).where(t.users.c.pseudonym == user_id)
            ).scalar()
    except sa.exc.SQLAlchemyError:
        hit = _roles.get(user_id)
        if hit is not None and time.monotonic() - hit[0] < ROLE_FALLBACK_SECONDS:
            return hit[1]
        _roles.pop(user_id, None)
        return None
    found = str(role or "employee")
    if len(_roles) >= _MAX_ROLES:
        _roles.clear()
    _roles[user_id] = (time.monotonic(), found)
    return found


def role_of(engine: Engine | None, user_id: str) -> str:
    return _lookup_role(engine, user_id) or "employee"


def apply(base: PolicySet, overrides: list[Override], team: str, role: str) -> PolicySet:
    """The policy one person is held to. Team overrides first, then role overrides."""
    cats, sens = dict(base.categories), dict(base.sensitivity)
    for kind, group in (("team", team), ("role", role)):
        for o in overrides:
            if o.kind == kind and o.group.lower() == group.lower():
                (cats if o.scope == "category" else sens)[o.key] = Decision(o.action)
    return PolicySet(cats, sens)


def strictest(base: PolicySet, overrides: list[Override], team: str) -> PolicySet:
    """The most severe action any of the person's possible roles, or their team, would give."""
    cats, sens = dict(base.categories), dict(base.sensitivity)
    for o in overrides:
        if o.kind == "team" and o.group.lower() != team.lower():
            continue
        target = cats if o.scope == "category" else sens
        action = Decision(o.action)
        if o.key not in target or PRECEDENCE[action] > PRECEDENCE[target[o.key]]:
            target[o.key] = action
    return PolicySet(cats, sens, degraded=True)


def effective(engine: Engine | None, base: PolicySet, user_id: str, team: str) -> PolicySet:
    overrides = load(engine)
    if not overrides:
        return base
    role = _lookup_role(engine, user_id)
    if role is None:
        return strictest(base, overrides, team)
    return apply(base, overrides, team, role)


def _validate(seed: PolicySet, o: Override) -> None:
    if o.kind not in KINDS:
        raise PolicyError(f"Unknown group type '{o.kind}'. Use one of: {', '.join(KINDS)}.")
    if not o.group.strip():
        raise PolicyError("Say which team or role this applies to.")
    if o.scope not in SCOPES:
        raise PolicyError(f"Unknown scope '{o.scope}'. Use one of: {', '.join(SCOPES)}.")
    known = seed.categories if o.scope == "category" else seed.sensitivity
    if o.key not in known:
        raise PolicyError(f"Unknown {o.scope} '{o.key}'. Use one of: {', '.join(sorted(known))}.")
    try:
        Decision(o.action)
    except ValueError:
        raise PolicyError(
            f"Unknown action '{o.action}'. Use one of: {', '.join(d.value for d in Decision)}."
        ) from None


def _save(conn: sa.Connection, items: list[Override], actor: str, what: str, target: str) -> None:
    now = datetime.now(UTC)
    value = json.dumps([o.__dict__ for o in items])
    updated = conn.execute(
        sa.update(t.settings)
        .where(t.settings.c.key == KEY)
        .values(value=value, updated_by=actor, updated_at=now)
    )
    if updated.rowcount == 0:
        conn.execute(
            sa.insert(t.settings).values(key=KEY, value=value, updated_by=actor, updated_at=now)
        )
    conn.execute(
        sa.insert(audit_table).values(
            ts=now, actor=actor, action=what, target=target, details={"count": len(items)}
        )
    )
    _clear()


def _read_all(conn: sa.Connection) -> list[Override]:
    raw = conn.execute(sa.select(t.settings.c.value).where(t.settings.c.key == KEY)).scalar()
    return [Override(**r) for r in json.loads(raw)] if raw else []


def put(conn: sa.Connection, seed: PolicySet, o: Override, actor: str) -> list[Override]:
    _validate(seed, o)
    if not actor.strip():
        raise PolicyError("Say who is making the change (updated_by).")
    items = [
        x
        for x in _read_all(conn)
        if (x.kind, x.group.lower(), x.scope, x.key) != (o.kind, o.group.lower(), o.scope, o.key)
    ] + [o]
    _save(conn, items, actor, "policy.group.update", f"{o.kind}:{o.group}:{o.scope}:{o.key}")
    return items


def remove(conn: sa.Connection, o: Override, actor: str) -> list[Override]:
    if not actor.strip():
        raise PolicyError("Say who is making the change (updated_by).")
    items = [
        x
        for x in _read_all(conn)
        if (x.kind, x.group.lower(), x.scope, x.key) != (o.kind, o.group.lower(), o.scope, o.key)
    ]
    _save(conn, items, actor, "policy.group.delete", f"{o.kind}:{o.group}:{o.scope}:{o.key}")
    return items
