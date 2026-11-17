"""Split storage. Pure tests always run; vault tests need VAULT_A_URL / VAULT_B_URL (set in the
`splitstore-tests` compose service, which also sets REQUIRE_VAULTS=1 so they cannot be skipped)."""

import os
import random
import uuid

import psycopg
import pytest

from brain.splitstore import AccessDenied, Actor, IntegrityError, SplitStore
from brain.splitstore import integrity as ig
from brain.splitstore import shares as sh

KEY = b"k" * 64
ADMIN = Actor("tester", "admin")
NUMBERS = [0, 1, -1, 4_250_00, -99_999, 2**100, -(2**100), sh.MAX_ABS, -sh.MAX_ABS]
STRINGS = ["", "plain", "Γιώργος Παπαδόπουλος", "Ελληνικά, με τόνους: ά έ ή ί ό ύ ώ ΐ ΰ", "日本 🙂"]


# ---- pure ----------------------------------------------------------------------------------
@pytest.mark.parametrize("v", NUMBERS)
def test_int_split_roundtrip(v: int) -> None:
    a, b = sh.split_int(v)
    assert 0 <= a < sh.P and 0 <= b < sh.P
    assert sh.join_int(a, b) == v


def test_int_out_of_range_and_types() -> None:
    for bad in (sh.MAX_ABS + 1, -sh.MAX_ABS - 1):
        with pytest.raises(ValueError):
            sh.split_int(bad)
    for bad in (1.5, True, "1"):  # type: ignore[assignment]
        with pytest.raises(TypeError):
            sh.split_int(bad)  # type: ignore[arg-type]


def test_shares_look_random() -> None:
    assert len({sh.split_int(42)[0] for _ in range(50)}) == 50
    assert sh.split_int(42)[0] != 42


@pytest.mark.parametrize("s", STRINGS)
def test_bytes_split_roundtrip(s: str) -> None:
    a, b = sh.split_bytes(s.encode())
    assert len(a) == len(b) == len(s.encode())
    assert sh.join_bytes(a, b).decode() == s


def test_tags_are_keyed_and_bound_to_position() -> None:
    t = ig.tag(KEY, "A", "r1", "f", "n", b"x")
    assert t != ig.tag(b"z" * 64, "A", "r1", "f", "n", b"x")
    assert t != ig.tag(KEY, "B", "r1", "f", "n", b"x")
    assert t != ig.tag(KEY, "A", "r2", "f", "n", b"x")
    assert t != ig.tag(KEY, "A", "r1", "g", "n", b"x")
    with pytest.raises(ValueError):
        ig.check_names("a|b", "f")


def test_load_key_prefers_secret_and_falls_back_when_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    secret = tmp_path / "hmac_key"
    secret.write_text("a" * 64)
    assert ig.load_key(str(secret), str(tmp_path / "fb")) == b"a" * 64
    assert not (tmp_path / "fb").exists()
    secret.unlink()
    secret.mkdir()  # what compose mounts when the secret file does not exist
    k1 = ig.load_key(str(secret), str(tmp_path / "fb"))
    assert len(k1) == 64 and k1 == ig.load_key(str(secret), str(tmp_path / "fb"))  # stable


# ---- against the vaults ---------------------------------------------------------------------
URL_A, URL_B = os.environ.get("VAULT_A_URL", ""), os.environ.get("VAULT_B_URL", "")


@pytest.fixture
def audit() -> list[tuple[str, str, str, dict]]:  # type: ignore[type-arg]
    return []


@pytest.fixture
def store(audit: list) -> SplitStore:  # type: ignore[type-arg]
    if not (URL_A and URL_B):
        if os.environ.get("REQUIRE_VAULTS"):
            pytest.fail("vault URLs not set")
        pytest.skip("vaults not available (run: docker compose run --rm splitstore-tests)")
    return SplitStore(URL_A, URL_B, KEY, lambda *e: audit.append(e))


@pytest.fixture
def ns() -> str:
    """Unique namespace per test, so tests never see each other's rows."""
    return "t" + uuid.uuid4().hex[:10]


def _exec(url: str, sql: str, *args: object) -> list:  # type: ignore[type-arg]
    with psycopg.connect(url) as c:
        cur = c.execute(sql, args)
        return cur.fetchall() if cur.description else []


@pytest.mark.parametrize("v", NUMBERS + STRINGS + [b"\x00\xff\x10", b""])
def test_roundtrip(store: SplitStore, ns: str, v: int | str | bytes) -> None:
    store.store(ns, "f", v)
    out = store.reveal(ns, "f", ADMIN)
    assert out == v and type(out) is type(v)


def test_overwrite(store: SplitStore, ns: str) -> None:
    store.store(ns, "f", 1)
    store.store(ns, "f", "now text")
    assert store.reveal(ns, "f", ADMIN) == "now text"


def test_tamper_share_in_vault_a_fails(store: SplitStore, ns: str, audit: list) -> None:  # type: ignore[type-arg]
    store.store(ns, "salary", 5_000_00)
    _exec(URL_A, f"UPDATE shares SET num = (num + 1) %% {sh.P} WHERE record_id = %s", ns)
    with pytest.raises(IntegrityError):
        store.reveal(ns, "salary", ADMIN)
    assert [a[1] for a in audit] == ["splitstore.integrity_error"]


def test_tamper_text_share_fails(store: SplitStore, ns: str) -> None:
    store.store(ns, "name", "Μαρία")
    _exec(
        URL_A,
        "UPDATE shares SET data = set_byte(data, 0, get_byte(data, 0) # 1) WHERE record_id = %s",
        ns,
    )
    with pytest.raises(IntegrityError):
        store.reveal(ns, "name", ADMIN)


def test_tamper_share_and_its_tag_still_fails_value_tag(store: SplitStore, ns: str) -> None:
    """An attacker with vault-a but no key cannot forge tag_a, so this is caught by tag_a anyway;
    here we check the value tag too by replacing the value tag in vault-b."""
    store.store(ns, "f", 7)
    _exec(URL_B, "UPDATE shares SET value_tag = %s WHERE record_id = %s", b"\x00" * 32, ns)
    with pytest.raises(IntegrityError):
        store.reveal(ns, "f", ADMIN)


@pytest.mark.parametrize("with_tags", [False, True])
def test_swapping_shares_between_records_fails(store: SplitStore, ns: str, with_tags: bool) -> None:
    r1, r2 = ns + "-1", ns + "-2"
    store.store(r1, "salary", 1_000_00)
    store.store(r2, "salary", 9_000_00)
    cols = "num, tag" if with_tags else "num"
    rows = {
        r: _exec(URL_A, f"SELECT {cols} FROM shares WHERE record_id = %s", r)[0] for r in (r1, r2)
    }
    sets = "num = %s, tag = %s" if with_tags else "num = %s"
    for rid, other in ((r1, r2), (r2, r1)):
        _exec(URL_A, f"UPDATE shares SET {sets} WHERE record_id = %s", *rows[other], rid)
    for rid in (r1, r2):
        with pytest.raises(IntegrityError):
            store.reveal(rid, "salary", ADMIN)


def test_missing_share_is_integrity_error(store: SplitStore, ns: str) -> None:
    store.store(ns, "f", 1)
    _exec(URL_A, "DELETE FROM shares WHERE record_id = %s", ns)
    with pytest.raises(IntegrityError):
        store.reveal(ns, "f", ADMIN)
    with pytest.raises(KeyError):
        store.reveal(ns + "-nope", "f", ADMIN)


def test_reveal_requires_role_and_is_audited(store: SplitStore, ns: str, audit: list) -> None:  # type: ignore[type-arg]
    store.store(ns, "f", 1)
    with pytest.raises(AccessDenied):
        store.reveal(ns, "f", Actor("eve", "intern"))
    store.reveal(ns, "f", Actor("ann", "dpo"))
    assert [(a[0], a[1]) for a in audit] == [
        ("eve", "splitstore.reveal.denied"),
        ("ann", "splitstore.reveal"),
    ]
    assert "1" not in str(audit).replace(ns, "")  # no value in the audit trail


def test_aggregate_sum_matches_plaintext(store: SplitStore, ns: str) -> None:
    rng = random.Random(1)
    vals = {f"{ns}-{i}": rng.randint(-50_000_00, 90_000_00) for i in range(40)}
    for rid, v in vals.items():
        store.store(rid, "pay", v)
    store.store(ns + "-x", "other", 999)  # different field is not summed
    assert store.aggregate_sum("pay", list(vals)) == sum(vals.values())
    subset = list(vals)[:10]
    assert store.aggregate_sum("pay", subset) == sum(vals[r] for r in subset)
    with pytest.raises(IntegrityError):
        store.aggregate_sum("pay", [*subset, ns + "-ghost"])


def test_aggregate_all_records_of_field(store: SplitStore, ns: str) -> None:
    field = "pay-" + ns  # unique field so "all" means only ours
    for i, v in enumerate([100, -30, 5]):
        store.store(f"{ns}-{i}", field, v)
    assert store.aggregate_sum(field) == 75
    assert store.aggregate_sum(field + "-empty") == 0
    store.store(ns + "-t", field, "text")
    with pytest.raises(ValueError):
        store.aggregate_sum(field)


def test_vault_a_dump_has_no_plaintext(store: SplitStore, ns: str) -> None:
    secrets_ = {"name": "Γιώργος Παπαδόπουλος", "city": "Θεσσαλονίκη", "salary": 4_250_00}
    for f, v in secrets_.items():
        store.store(ns, f, v)
    rows = _exec(
        URL_A,
        "SELECT record_id, field, kind, num, data, tag, value_tag FROM shares WHERE record_id = %s",
        ns,
    )
    assert len(rows) == 3
    dump = repr(rows)
    dump_bytes = b"".join(bytes(c) for r in rows for c in r if isinstance(c, (bytes, memoryview)))
    for v in secrets_.values():
        assert str(v) not in dump
        if isinstance(v, str):
            assert v.encode() not in dump_bytes and v not in dump
    # vault-b alone is just as blind
    rows_b = _exec(URL_B, "SELECT num, data FROM shares WHERE record_id = %s", ns)
    assert all(r[0] != 4_250_00 for r in rows_b)
    assert not any(r[1] is not None and "Γιώργος".encode() in bytes(r[1]) for r in rows_b)


# ---- atomic writes, recovery, tag-checked aggregate, key canary ------------------------------
def _count(url: str, ns: str) -> int:
    return _exec(url, "SELECT count(*) FROM shares WHERE record_id = %s", ns)[0][0]


def _fail_nth(monkeypatch: pytest.MonkeyPatch, name: str, nth: int) -> None:
    real = getattr(psycopg.Connection, name)
    calls = {"n": 0}

    def wrapper(self, *a, **k):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == nth:
            raise OSError("simulated crash")
        return real(self, *a, **k)

    monkeypatch.setattr(psycopg.Connection, name, wrapper)


def test_failed_prepare_leaves_nothing_in_either_vault(
    store: SplitStore, ns: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fail_nth(monkeypatch, "tpc_prepare", 2)  # vault-b cannot prepare
    with pytest.raises(OSError):
        store.store(ns, "f", 5)
    monkeypatch.undo()
    assert _count(URL_A, ns) == _count(URL_B, ns) == 0
    store.store(ns, "f", 5)
    assert store.reveal(ns, "f", ADMIN) == 5


@pytest.mark.parametrize("fail_commit", [1, 2])  # 1: before A commits, 2: A done, B not
def test_crash_between_prepare_and_commit_is_recovered(
    store: SplitStore, ns: str, monkeypatch: pytest.MonkeyPatch, fail_commit: int
) -> None:
    _fail_nth(monkeypatch, "tpc_commit", fail_commit)
    with pytest.raises(OSError):
        store.store(ns, "f", 123_00)
    monkeypatch.undo()
    # the write finished (rolled forward), never half-way
    assert _count(URL_A, ns) == _count(URL_B, ns) == 1
    assert store.reveal(ns, "f", ADMIN) == 123_00


def test_recover_rolls_back_a_prepare_that_only_vault_a_has(store: SplitStore, ns: str) -> None:
    gid = "split-" + uuid.uuid4().hex
    with psycopg.connect(URL_A, autocommit=True) as c:
        c.execute("BEGIN")
        c.execute(
            "INSERT INTO shares (record_id, field, kind, num, tag) VALUES (%s, 'f', 'n', 1, %s)",
            (ns, b"x"),
        )
        c.execute(f"PREPARE TRANSACTION '{gid}'")
    assert store.recover(60) == 0  # too young: left alone (it could still be in flight)
    assert store.recover(0) >= 1
    assert _count(URL_A, ns) == 0
    assert _exec(URL_A, "SELECT count(*) FROM pg_prepared_xacts WHERE gid = %s", gid)[0][0] == 0


def test_aggregate_checks_share_tags(store: SplitStore, ns: str) -> None:
    field = "pay-" + ns
    for i, v in enumerate([100, 200, 300]):
        store.store(f"{ns}-{i}", field, v)
    assert store.aggregate_sum(field) == 600
    _exec(URL_A, f"UPDATE shares SET num = (num + 1) %% {sh.P} WHERE record_id = %s", ns + "-1")
    with pytest.raises(IntegrityError):
        store.aggregate_sum(field)  # tampering caught
    assert store.aggregate_sum(field, verify_tags=False) == 601  # fast path trusts the vaults


def test_aggregate_detects_moved_and_missing_shares(store: SplitStore, ns: str) -> None:
    field = "pay-" + ns
    store.store(ns + "-1", field, 1_000)
    store.store(ns + "-2", field, 9_000)
    _exec(URL_B, "UPDATE shares SET record_id = %s WHERE record_id = %s", ns + "-tmp", ns + "-1")
    _exec(URL_B, "UPDATE shares SET record_id = %s WHERE record_id = %s", ns + "-1", ns + "-2")
    _exec(URL_B, "UPDATE shares SET record_id = %s WHERE record_id = %s", ns + "-2", ns + "-tmp")
    with pytest.raises(IntegrityError):  # shares swapped between records
        store.aggregate_sum(field)
    _exec(URL_A, "DELETE FROM shares WHERE record_id = %s", ns + "-1")
    with pytest.raises(IntegrityError):
        store.aggregate_sum(field)


def test_wrong_key_is_reported_as_key_mismatch(store: SplitStore) -> None:
    from brain.splitstore import KeyMismatchError

    saved = _exec(URL_B, "SELECT value FROM meta WHERE name = 'key_canary'")
    _exec(URL_B, "DELETE FROM meta WHERE name = 'key_canary'")
    try:
        store.check_key()  # first use writes the canary
        store.check_key()  # and the same key passes again
        with pytest.raises(KeyMismatchError):
            SplitStore(URL_A, URL_B, b"other-key" * 8).check_key()
    finally:
        _exec(URL_B, "DELETE FROM meta WHERE name = 'key_canary'")
        if saved:  # put back what the running app had written
            _exec(URL_B, "INSERT INTO meta VALUES ('key_canary', %s)", bytes(saved[0][0]))


# ---- HTTP routes -----------------------------------------------------------------------------
@pytest.fixture
def client(store: SplitStore, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from brain.splitstore import routes

    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes.settings, "vault_api_token", "tok-123")
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


AUTH = {"Authorization": "Bearer tok-123"}


def test_http_needs_a_token(client, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    body = {"record_id": "r", "field": "f", "actor": "a", "role": "admin"}
    assert client.post("/v1/vault/reveal", json=body).status_code == 401
    assert (
        client.post("/v1/vault/reveal", json=body, headers={"Authorization": "x"}).status_code
        == 401
    )
    from brain.splitstore import routes

    monkeypatch.setattr(routes.settings, "vault_api_token", "")
    assert client.post("/v1/vault/reveal", json=body, headers=AUTH).status_code == 503  # off


def test_http_store_reveal_aggregate(client, ns: str) -> None:  # type: ignore[no-untyped-def]
    field = "pay-" + ns
    for i, v in enumerate([1_00, 2_50]):
        r = client.post(
            "/v1/vault/store",
            json={"record_id": f"{ns}-{i}", "field": field, "value": v},
            headers=AUTH,
        )
        assert r.status_code == 204
    client.post(
        "/v1/vault/store", json={"record_id": ns, "field": "name", "value": "Μαρία"}, headers=AUTH
    )
    ask = {"record_id": ns, "field": "name", "actor": "ann", "role": "dpo"}
    r = client.post("/v1/vault/reveal", json=ask, headers=AUTH)
    assert r.status_code == 200 and r.json()["value"] == "Μαρία"
    r = client.post("/v1/vault/reveal", json={**ask, "role": "intern"}, headers=AUTH)
    assert r.status_code == 403
    assert (
        client.post(
            "/v1/vault/reveal", json={**ask, "record_id": ns + "-no"}, headers=AUTH
        ).status_code
        == 404
    )
    r = client.post("/v1/vault/aggregate", json={"field": field}, headers=AUTH)
    assert r.json()["sum"] == 3_50
    _exec(URL_A, f"UPDATE shares SET num = (num + 1) %% {sh.P} WHERE record_id = %s", ns + "-0")
    assert (
        client.post("/v1/vault/aggregate", json={"field": field}, headers=AUTH).status_code == 409
    )
    for bad in (True, 1.5, None, ["x"]):
        r = client.post(
            "/v1/vault/store", json={"record_id": "r", "field": "f", "value": bad}, headers=AUTH
        )
        assert r.status_code == 422


def test_app_role_is_not_a_superuser(store: SplitStore) -> None:
    for url in (URL_A, URL_B):
        sup, create_role, create_db = _exec(
            url,
            "SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles "
            "WHERE rolname = current_user",
        )[0]
        assert not (sup or create_role or create_db)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            _exec(url, "CREATE TABLE evil (x int)")
