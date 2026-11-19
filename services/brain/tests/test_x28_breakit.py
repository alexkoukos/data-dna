"""X28: leaderboard counters, the candidate -> approve -> CSV flow, reject deletes, no raw text."""

import csv
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.eval.run import (
    Attack,
    AttackResult,
    Result,
    Row,
    load_attacks,
    summarise,
    summarise_attacks,
    summarise_breakit,
    to_markdown,
)
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

HEADER = "id,category,lang,text,expected_decision,notes,source,added\n"
# Passes every level today: a name in Latin letters with no Greek ending or common surname.
MISS = "please summarise the minutes of the quarterly review for me"


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[TestClient, sa.Engine, Path]:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    (tmp_path / "eval").mkdir()
    csv_path = tmp_path / "eval" / "attacks_scripts.csv"
    csv_path.write_text(HEADER + "A1,spacing,en,G R 1 6,warn,,seed,\n", encoding="utf-8")
    monkeypatch.setattr(main.settings, "data_dir", str(tmp_path))
    main._attempts.clear()
    return TestClient(main.app), engine, csv_path


def _try(client: TestClient, text: str, **kw: str) -> dict[str, object]:
    return client.post("/v1/try", json={"text": text, **kw}).json()  # type: ignore[no-any-return]


def test_board_counts_attempts_stopped_and_got_through(
    env: tuple[TestClient, sa.Engine, Path], valid_iban: str
) -> None:
    client, _, _ = env
    _try(client, f"Pay {valid_iban}", kind="encoding")
    _try(client, "How do I make carbonara?", kind="spacing")
    _try(client, "Tell me a joke", kind="spacing")
    b = client.get("/v1/breakit/board").json()
    assert (b["attempts"], b["stopped"], b["got_through"]) == (3, 1, 2)
    assert b["catch_rate"] == 33.3
    assert {m["kind"] for m in b["misses"]} == {"spacing"}


def test_board_with_no_attempts_has_no_rate(env: tuple[TestClient, sa.Engine, Path]) -> None:
    b = env[0].get("/v1/breakit/board").json()
    assert b["attempts"] == 0 and b["catch_rate"] is None and b["misses"] == []


def test_misses_show_only_a_masked_preview_never_the_raw_text(
    env: tuple[TestClient, sa.Engine, Path], valid_iban: str
) -> None:
    client, engine, _ = env
    secret = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789"
    out = _try(client, f"remember {secret}", kind="secrets", nickname="Eleni")
    assert secret not in str(client.get("/v1/breakit/board").json())
    assert secret not in str(client.get("/v1/try/attempts").json())
    # an attempt that was not submitted leaves no raw text anywhere in the database
    with engine.connect() as conn:
        assert (
            conn.execute(sa.select(sa.func.count()).select_from(t.breakit_candidates)).scalar() == 0
        )
        assert conn.execute(sa.select(sa.func.count()).select_from(t.incidents)).scalar() == 0
    assert out["attempt_id"]


def test_practice_creates_no_incident(
    env: tuple[TestClient, sa.Engine, Path], valid_iban: str
) -> None:
    client, engine, _ = env
    _try(client, f"Pay {valid_iban}")
    _try(client, MISS)
    with engine.connect() as conn:
        assert conn.execute(sa.select(sa.func.count()).select_from(t.incidents)).scalar() == 0


def _submit(client: TestClient, text: str = MISS, **kw: str) -> object:
    body = {"text": text, "expected_decision": "warn", "kind": "spacing", "nickname": "Eleni"}
    body.update(kw)
    return client.post("/v1/breakit/candidates", json=body)


def test_candidate_approve_appends_a_breakit_row_and_blanks_the_raw_text(
    env: tuple[TestClient, sa.Engine, Path],
) -> None:
    client, engine, csv_path = env
    r = _submit(client)
    assert r.status_code == 201  # type: ignore[attr-defined]
    cid = r.json()["id"]  # type: ignore[attr-defined]
    queue = client.get("/v1/breakit/candidates").json()
    assert [q["id"] for q in queue] == [cid] and queue[0]["text"] == MISS

    ok = client.post(f"/v1/breakit/candidates/{cid}/approve", json={"reviewer": "sec1"})
    assert ok.status_code == 200 and ok.json()["eval_id"] == "BI001"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    assert [r["id"] for r in rows] == ["A1", "BI001"]
    last = rows[-1]
    assert last["source"] == "breakit" and last["added"] and last["text"] == MISS
    assert (last["category"], last["expected_decision"]) == ("spacing", "warn")
    assert load_attacks(csv_path.parents[1])[-1].source == "breakit"

    assert client.get("/v1/breakit/candidates").json() == []
    with engine.connect() as conn:
        row = conn.execute(sa.select(t.breakit_candidates)).mappings().one()
        assert row["status"] == "approved" and row["text"] is None
    # approving twice is refused and adds nothing
    assert (
        client.post(f"/v1/breakit/candidates/{cid}/approve", json={"reviewer": "x"}).status_code
        == 404
    )
    assert len(list(csv.DictReader(csv_path.open(encoding="utf-8")))) == 2


def test_second_approval_gets_the_next_id(env: tuple[TestClient, sa.Engine, Path]) -> None:
    client, _, csv_path = env
    for text in (MISS, MISS + " again"):
        cid = _submit(client, text).json()["id"]  # type: ignore[attr-defined]
        client.post(f"/v1/breakit/candidates/{cid}/approve", json={"reviewer": "sec1"})
    assert [r["id"] for r in csv.DictReader(csv_path.open(encoding="utf-8"))] == [
        "A1",
        "BI001",
        "BI002",
    ]


def test_text_with_commas_quotes_and_newlines_survives_the_csv(
    env: tuple[TestClient, sa.Engine, Path],
) -> None:
    client, _, csv_path = env
    text = 'say "hi", then\nnew line, ok'
    cid = _submit(client, text).json()["id"]  # type: ignore[attr-defined]
    client.post(f"/v1/breakit/candidates/{cid}/approve", json={"reviewer": "sec1"})
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    assert rows[-1]["text"] == text


def test_reject_deletes_the_row_and_its_raw_text_at_once(
    env: tuple[TestClient, sa.Engine, Path],
) -> None:
    client, engine, csv_path = env
    cid = _submit(client).json()["id"]  # type: ignore[attr-defined]
    r = client.post(f"/v1/breakit/candidates/{cid}/reject", json={"reviewer": "sec1"})
    assert r.json()["status"] == "rejected"
    with engine.connect() as conn:
        assert (
            conn.execute(sa.select(sa.func.count()).select_from(t.breakit_candidates)).scalar() == 0
        )
        actions = [a for (a,) in conn.execute(sa.text("select action from audit_log"))]
    assert "breakit.reject" in actions
    assert len(list(csv.DictReader(csv_path.open(encoding="utf-8")))) == 1


def test_a_text_the_gate_already_stops_is_not_a_miss(
    env: tuple[TestClient, sa.Engine, Path], valid_iban: str
) -> None:
    client, engine, _ = env
    r = _submit(client, f"Pay {valid_iban}")
    assert r.status_code == 409  # type: ignore[attr-defined]
    with engine.connect() as conn:
        assert (
            conn.execute(sa.select(sa.func.count()).select_from(t.breakit_candidates)).scalar() == 0
        )


@pytest.mark.parametrize(
    "bad", [{"expected_decision": "allow"}, {"kind": "bogus"}, {"kind": "Bad Kind"}, {"text": ""}]
)
def test_submission_is_validated(
    env: tuple[TestClient, sa.Engine, Path], bad: dict[str, str]
) -> None:
    assert _submit(env[0], **bad).status_code == 422  # type: ignore[attr-defined]


def test_queue_is_capped_so_it_cannot_be_flooded(
    env: tuple[TestClient, sa.Engine, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("brain.breakit.MAX_PENDING", 2)
    client = env[0]
    assert _submit(client, MISS + " 1").status_code == 201  # type: ignore[attr-defined]
    assert _submit(client, MISS + " 2").status_code == 201  # type: ignore[attr-defined]
    assert _submit(client, MISS + " 3").status_code == 429  # type: ignore[attr-defined]


def test_top_breakers_list_nicknames_only(env: tuple[TestClient, sa.Engine, Path]) -> None:
    client, _, _ = env
    a = _submit(client, MISS + " a", nickname="Eleni").json()["id"]  # type: ignore[attr-defined]
    _submit(client, MISS + " b", nickname="Eleni")
    _submit(client, MISS + " c", nickname="Nikos")
    client.post(f"/v1/breakit/candidates/{a}/approve", json={"reviewer": "sec1"})
    top = client.get("/v1/breakit/board").json()["top_breakers"]
    assert top[0] == {"nickname": "Eleni", "submitted": 2, "approved": 1}
    assert top[1]["nickname"] == "Nikos"
    assert set(top[0]) == {"nickname", "submitted", "approved"}


def test_nickname_must_be_a_plain_display_name(env: tuple[TestClient, sa.Engine, Path]) -> None:
    r = _submit(env[0], nickname="a@b.com")
    assert r.status_code == 422  # type: ignore[attr-defined]


def test_eval_reports_breakit_rows_on_their_own_line() -> None:
    def r(src: str, got: str) -> AttackResult:
        return AttackResult(Attack("X", "spacing", "t", "warn", "", src, "2026-11-17"), got)

    results = [r("seed", "warn"), r("breakit", "allow"), r("breakit", "warn")]
    old = summarise_attacks([x for x in results if x.attack.source != "breakit"])
    bi = summarise_breakit(results)
    assert old is not None and old["n"] == 1  # old numbers do not include the new rows
    assert bi is not None and (bi["n"], bi["still_missed"], bi["now_caught"]) == (2, 1, 1)
    assert summarise_breakit([r("seed", "warn")]) is None
    md = to_markdown(_minimal_report(bi))
    assert "Found live, still missed: 1" in md


def _minimal_report(bi: dict[str, object]) -> dict[str, object]:
    row = Row("X", "en", "some text", "clean", "", "", "allow")
    rep = summarise([Result(row, "allow", False, 5.0, False, "")], "prompts.sample.csv")
    rep["breakit"] = bi
    return rep


def test_approve_falls_back_when_data_eval_is_read_only(
    env: tuple[TestClient, sa.Engine, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, csv_path = env
    fallback = tmp_path / "volume" / "attacks_scripts.csv"
    fallback.parent.mkdir()
    fallback.write_text(HEADER + "A1,spacing,en,x,warn,,seed,\n", encoding="utf-8")
    monkeypatch.setattr(main, "BREAKIT_FALLBACK", fallback)
    real = main.breakit.append_to_eval

    def deny(path: Path, **kw: object) -> str:
        if path == csv_path:
            raise PermissionError("read-only")
        return real(path, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(main.breakit, "append_to_eval", deny)
    cid = _submit(client).json()["id"]  # type: ignore[attr-defined]
    ok = client.post(f"/v1/breakit/candidates/{cid}/approve", json={"reviewer": "sec1"})
    assert ok.status_code == 200 and "docker compose cp" in ok.json()["note"]
    assert "BI001" in fallback.read_text(encoding="utf-8")
    assert "BI001" not in csv_path.read_text(encoding="utf-8")
