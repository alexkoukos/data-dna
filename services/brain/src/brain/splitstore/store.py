"""Split storage: every sensitive value becomes two shares in two independent Postgres vaults.

The app is the only thing that can reach both. Never logs or audits values or shares.
"""

import contextlib
import functools
import logging
import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import sql as psql

from brain.splitstore import integrity as ig
from brain.splitstore import shares as sh
from brain.splitstore.integrity import IntegrityError

log = logging.getLogger(__name__)

REVEAL_ROLES = frozenset({"admin", "dpo", "payroll"})
AuditSink = Callable[[str, str, str, dict[str, Any]], None]  # actor, action, target, details


class AccessDenied(PermissionError):
    pass


class KeyMismatchError(RuntimeError):
    """The HMAC key is not the one the vaults were written with (not tampering: wrong key)."""


@dataclass(frozen=True)
class Actor:
    name: str
    role: str


def log_audit(actor: str, action: str, target: str, details: dict[str, Any]) -> None:
    """Fallback audit sink (the app wires the audit_log table in). Holds names only."""
    log.warning("audit %s %s %s %s", actor, action, target, details)


Value = int | str | bytes
_GID_PREFIX = "split-"
_GID_RE = re.compile(r"split-[0-9a-f]{32}")


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
        self._write_both(
            sql,
            (record_id, field, kind, num_a, data_a, tag_a, None),
            (record_id, field, kind, num_b, data_b, tag_b, vtag),
        )

    def _write_both(self, sql: str, args_a: tuple[Any, ...], args_b: tuple[Any, ...]) -> None:
        """Two-phase commit (PREPARE TRANSACTION) across both vaults: either both rows land or
        neither does. Order: prepare A, prepare B, commit A, commit B. A crash in between leaves
        prepared transactions that recover() settles (see there)."""
        gid = _GID_PREFIX + uuid.uuid4().hex
        with psycopg.connect(self._dsn_a) as ca, psycopg.connect(self._dsn_b) as cb:
            try:
                ca.tpc_begin(gid)
                cb.tpc_begin(gid)
                ca.execute(sql, args_a)
                cb.execute(sql, args_b)
                ca.tpc_prepare()
                cb.tpc_prepare()
            except BaseException:
                for c in (ca, cb):  # nothing is committed yet: undo whatever stage each is in
                    with contextlib.suppress(psycopg.Error):
                        c.tpc_rollback()
                raise
            try:
                ca.tpc_commit()
                cb.tpc_commit()
            except BaseException:
                log.error("split write %s died between prepare and commit; recovering", gid)
                try:
                    self.recover(0, only=gid)
                finally:
                    raise

    def recover(self, min_age_seconds: int = 30, only: str | None = None) -> int:
        """Settle split writes that were interrupted between prepare and commit. Returns how many.

        Commit order is A then B, so for a prepared gid: in both vaults -> commit both; only in B
        (A already committed) -> commit B; only in A (B never prepared) -> roll A back. Only
        entries older than `min_age_seconds` are touched, so a write still in flight is left
        alone; pass 0 at startup, when this process has none. `only` settles a single gid.
        Prepared entries lock their rows: until settled, writes to the same record wait.
        """
        pa, pb = (
            self._prepared(self._dsn_a, min_age_seconds),
            self._prepared(self._dsn_b, min_age_seconds),
        )
        done = 0
        for gid in sorted(pa | pb):
            if only is not None and gid != only:
                continue
            if gid in pa and gid in pb:
                self._finish(self._dsn_a, gid, "COMMIT")
                self._finish(self._dsn_b, gid, "COMMIT")
            elif gid in pb:
                self._finish(self._dsn_b, gid, "COMMIT")
            else:
                self._finish(self._dsn_a, gid, "ROLLBACK")
            done += 1
        return done

    @staticmethod
    def _prepared(dsn: str, min_age_seconds: int) -> set[str]:
        with psycopg.connect(dsn, autocommit=True) as c:
            rows = c.execute(
                "SELECT gid FROM pg_prepared_xacts WHERE gid LIKE %s AND database = "
                "current_database() AND prepared < now() - make_interval(secs => %s)",
                (_GID_PREFIX + "%", min_age_seconds),
            ).fetchall()
        return {r[0] for r in rows if _GID_RE.fullmatch(r[0])}

    @staticmethod
    def _finish(dsn: str, gid: str, verb: str) -> None:
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(psql.SQL(verb + " PREPARED {}").format(psql.Literal(gid)))

    def check_key(self) -> None:
        """Fail early, and clearly, if the HMAC key differs from the one used for stored data.

        vault-b keeps a canary, HMAC(key, "canary"), written the first time. It reveals nothing
        about the key. Without it a wrong key looks exactly like tampering on every reveal.
        """
        canary = ig.tag(self._key, "K", "-", "canary", "k", b"")
        with psycopg.connect(self._dsn_b) as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value BYTEA NOT NULL)"
            )
            c.execute(
                "INSERT INTO meta (name, value) VALUES ('key_canary', %s) ON CONFLICT DO NOTHING",
                (canary,),
            )
            (stored,) = c.execute("SELECT value FROM meta WHERE name = 'key_canary'").fetchone()  # type: ignore[misc]
        if not ig.same(stored, canary):
            raise KeyMismatchError(
                "HMAC key does not match the one the vaults were written with "
                "(restore the original secrets/hmac_key, or reset the vault volumes)"
            )

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
    def aggregate_sum(
        self, field: str, record_ids: Sequence[str] | None = None, *, verify_tags: bool = True
    ) -> int:
        """Each vault sums its own shares mod P; only the two sums meet. No value is rebuilt.

        verify_tags (default): each vault's shares are also checked against their own tag
        (tag_a / tag_b) before summing, so a tampered, moved or missing share is caught here too.
        That moves shares (never values) into the app, one vault at a time; nothing is combined
        per record. value_tag needs the whole value, so it is only checked by reveal().
        verify_tags=False sums inside each vault instead (fast, no tag check).
        Row counts must match in both vaults and the result must fit in [-(P//2), P//2].
        """
        ids = sorted(set(record_ids)) if record_ids is not None else None
        if verify_tags:
            sa_, ids_a = self._verified_sum(self._dsn_a, "A", field, ids)
            sb_, ids_b = self._verified_sum(self._dsn_b, "B", field, ids)
            if ids_a != ids_b:
                raise IntegrityError("vaults disagree about which records exist")
            na = nb = len(ids_a)
        else:
            sa_, na = self._vault_sum(self._dsn_a, field, ids)
            sb_, nb = self._vault_sum(self._dsn_b, field, ids)
        if na != nb or (ids is not None and na != len(ids)):
            raise IntegrityError("vaults disagree about which records exist")
        return sh.join_int(sa_, sb_)

    def _verified_sum(
        self, dsn: str, role: str, field: str, ids: list[str] | None
    ) -> tuple[int, set[str]]:
        sql = "SELECT record_id, kind, num, tag FROM shares WHERE field = %s"
        args: list[Any] = [field]
        if ids is not None:
            sql += " AND record_id = ANY(%s)"
            args.append(ids)
        with psycopg.connect(dsn) as c:
            rows = c.execute(sql, args).fetchall()
        if any(r[1] != "n" for r in rows):
            raise ValueError(f"field {field!r} holds non-numeric values")
        bad = 0
        for rid, _, num, tg in rows:
            expect = ig.tag(self._key, role, rid, field, "n", sh.int_to_bytes(int(num)))
            bad += not ig.same(tg, expect)
        if bad:
            raise IntegrityError(f"share tag mismatch in vault-{role.lower()} ({bad} record(s))")
        return sum(int(r[2]) for r in rows) % sh.P, {r[0] for r in rows}

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
    """The store wired from the environment (VAULT_A_URL, VAULT_B_URL, HMAC_KEY_FILE).

    The first call per process checks the key against the vault canary (KeyMismatchError).
    """
    from brain.config import settings

    if not settings.vault_a_url or not settings.vault_b_url:
        raise RuntimeError("VAULT_A_URL and VAULT_B_URL are not set")
    s = SplitStore(
        settings.vault_a_url,
        settings.vault_b_url,
        ig.load_key(settings.hmac_key_file),
        audit or db_audit,
    )
    _checked(s)
    return s


_ok_keys: set[bytes] = set()


def _checked(s: SplitStore) -> None:
    fp = ig.tag(s._key, "K", "-", "fp", "k", b"")
    if fp not in _ok_keys:
        s.check_key()
        _ok_keys.add(fp)


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
