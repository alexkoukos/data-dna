"""Split storage: every sensitive value becomes two shares in two independent Postgres vaults.

The app is the only thing that can reach both. Never logs or audits values or shares.
"""

import functools
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import psycopg

from brain.splitstore import integrity as ig
from brain.splitstore import shares as sh
from brain.splitstore.integrity import IntegrityError

log = logging.getLogger(__name__)

REVEAL_ROLES = frozenset({"admin", "dpo", "payroll"})
AuditSink = Callable[[str, str, str, dict[str, Any]], None]  # actor, action, target, details


class AccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Actor:
    name: str
    role: str


def log_audit(actor: str, action: str, target: str, details: dict[str, Any]) -> None:
    """Fallback audit sink (the app wires the audit_log table in). Holds names only."""
    log.warning("audit %s %s %s %s", actor, action, target, details)


Value = int | str | bytes


def _kind(value: Value) -> str:
    if isinstance(value, bool):
        raise TypeError("booleans are not supported")
    if isinstance(value, int):
        return "n"
    if isinstance(value, str):
        return "s"
    if isinstance(value, bytes):
        return "b"
    raise TypeError("value must be int, str or bytes")


def _value_payload(kind: str, value: Value) -> bytes:
    if kind == "n":
        return str(value).encode()
    return value.encode("utf-8") if isinstance(value, str) else bytes(value)


class SplitStore:
    def __init__(self, dsn_a: str, dsn_b: str, key: bytes, audit: AuditSink = log_audit) -> None:
        self._dsn_a, self._dsn_b, self._key, self._audit = dsn_a, dsn_b, key, audit

    # -- write -----------------------------------------------------------------------------
    def store(self, record_id: str, field: str, value: Value) -> None:
        ig.check_names(record_id, field)
        kind = _kind(value)
        num_a = num_b = data_a = data_b = None
        if kind == "n":
            num_a, num_b = sh.split_int(value)  # type: ignore[arg-type]
            pa, pb = sh.int_to_bytes(num_a), sh.int_to_bytes(num_b)
        else:
            raw = _value_payload(kind, value)
            data_a, data_b = sh.split_bytes(raw)
            pa, pb = data_a, data_b
        tag_a = ig.tag(self._key, "A", record_id, field, kind, pa)
        tag_b = ig.tag(self._key, "B", record_id, field, kind, pb)
        vtag = ig.tag(self._key, "V", record_id, field, kind, _value_payload(kind, value))
        sql = (
            "INSERT INTO shares (record_id, field, kind, num, data, tag, value_tag) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (record_id, field) DO UPDATE SET "
            "kind = EXCLUDED.kind, num = EXCLUDED.num, data = EXCLUDED.data, "
            "tag = EXCLUDED.tag, value_tag = EXCLUDED.value_tag"
        )
        # Two databases, no distributed transaction: commit B only after A succeeded, and drop
        # A's row again if B fails, so a half-written value is not left behind.
        with psycopg.connect(self._dsn_a) as ca, psycopg.connect(self._dsn_b) as cb:
            ca.execute(sql, (record_id, field, kind, num_a, data_a, tag_a, None))
            cb.execute(sql, (record_id, field, kind, num_b, data_b, tag_b, vtag))
            cb.commit()
            ca.commit()

    # -- read ------------------------------------------------------------------------------
    def reveal(self, record_id: str, field: str, actor: Actor) -> Value:
        target = f"{record_id}/{field}"
        if actor.role not in REVEAL_ROLES:
            self._audit(actor.name, "splitstore.reveal.denied", target, {"role": actor.role})
            raise AccessDenied("this role may not reveal split values")
        try:
            value = self._reveal(record_id, field)
        except IntegrityError as e:
            self._audit(actor.name, "splitstore.integrity_error", target, {"reason": str(e)})
            raise
        self._audit(actor.name, "splitstore.reveal", target, {"role": actor.role})
        return value

    def _row(self, dsn: str, record_id: str, field: str) -> Any:
        with psycopg.connect(dsn) as c:
            return c.execute(
                "SELECT kind, num, data, tag, value_tag FROM shares "
                "WHERE record_id = %s AND field = %s",
                (record_id, field),
            ).fetchone()

    def _reveal(self, record_id: str, field: str) -> Value:
        ig.check_names(record_id, field)
        ra, rb = self._row(self._dsn_a, record_id, field), self._row(self._dsn_b, record_id, field)
        if ra is None or rb is None:
            if ra is None and rb is None:
                raise KeyError(f"no value stored for {record_id}/{field}")
            raise IntegrityError("share missing in one vault")
        (kind_a, num_a, data_a, tag_a, _), (kind_b, num_b, data_b, tag_b, vtag) = ra, rb
        if kind_a != kind_b or kind_a not in ("n", "s", "b"):
            raise IntegrityError("share types disagree")
        kind = kind_a
        try:
            if kind == "n":
                pa, pb = sh.int_to_bytes(int(num_a)), sh.int_to_bytes(int(num_b))
            else:
                pa, pb = bytes(data_a), bytes(data_b)
        except (TypeError, OverflowError, ValueError):
            raise IntegrityError("malformed share") from None
        # Check both tags before combining anything; `&` so neither check short-circuits.
        ok_a = ig.same(tag_a, ig.tag(self._key, "A", record_id, field, kind, pa))
        ok_b = ig.same(tag_b, ig.tag(self._key, "B", record_id, field, kind, pb))
        if not (ok_a & ok_b):
            raise IntegrityError("share tag mismatch")
        try:
            if kind == "n":
                value: Value = sh.join_int(int(num_a), int(num_b))
            else:
                raw = sh.join_bytes(pa, pb)
                value = raw.decode("utf-8") if kind == "s" else raw
        except ValueError:
            raise IntegrityError("shares do not combine") from None
        if not ig.same(
            vtag, ig.tag(self._key, "V", record_id, field, kind, _value_payload(kind, value))
        ):
            raise IntegrityError("value tag mismatch")
        return value

    # -- aggregate -------------------------------------------------------------------------
    def aggregate_sum(self, field: str, record_ids: Sequence[str] | None = None) -> int:
        """Each vault sums its own shares mod P; only the two sums meet. No value is rebuilt.

        Trade-off: share tags are not checked here (that would pull every share into the app).
        Row counts must match in both vaults and the result must fit in [-(P//2), P//2].
        """
        ids = sorted(set(record_ids)) if record_ids is not None else None
        sa_, na = self._vault_sum(self._dsn_a, field, ids)
        sb_, nb = self._vault_sum(self._dsn_b, field, ids)
        if na != nb or (ids is not None and na != len(ids)):
            raise IntegrityError("vaults disagree about which records exist")
        return sh.join_int(sa_, sb_)

    @staticmethod
    def _vault_sum(dsn: str, field: str, ids: list[str] | None) -> tuple[int, int]:
        sql = (
            f"SELECT COALESCE(SUM(num), 0) %% {sh.P}, COUNT(*) FILTER (WHERE kind = 'n'), "
            "COUNT(*) FILTER (WHERE kind <> 'n') FROM shares WHERE field = %s"
        )
        args: list[Any] = [field]
        if ids is not None:
            sql += " AND record_id = ANY(%s)"
            args.append(ids)
        with psycopg.connect(dsn) as c:
            total, n_num, n_other = c.execute(sql, args).fetchone()  # type: ignore[misc]
        if n_other:
            raise ValueError(f"field {field!r} holds non-numeric values")
        return int(total), int(n_num)


def get_store(audit: AuditSink | None = None) -> SplitStore:
    """The store wired from the environment (VAULT_A_URL, VAULT_B_URL, HMAC_KEY_FILE)."""
    from brain.config import settings

    if not settings.vault_a_url or not settings.vault_b_url:
        raise RuntimeError("VAULT_A_URL and VAULT_B_URL are not set")
    return SplitStore(
        settings.vault_a_url,
        settings.vault_b_url,
        ig.load_key(settings.hmac_key_file),
        audit or db_audit,
    )


@functools.cache
def _engine() -> Any:
    from brain.db.engine import make_engine

    return make_engine()


def db_audit(actor: str, action: str, target: str, details: dict[str, Any]) -> None:
    """Write to the app's audit_log table (same table the policy and reveal features use)."""
    from datetime import UTC, datetime

    import sqlalchemy as sa

    from brain.policy.store import audit_table

    engine = _engine()
    if engine is None:
        log_audit(actor, action, target, details)
        return
    with engine.begin() as conn:
        conn.execute(
            sa.insert(audit_table).values(
                ts=datetime.now(UTC), actor=actor, action=action, target=target, details=details
            )
        )
