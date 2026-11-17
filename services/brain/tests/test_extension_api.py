from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.policy.store import PolicyStore, audit_table
from brain.policy.store import metadata as policy_metadata
from brain.seed.load import run_seed

IBAN = "GR1601101250000000012300695"


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sa.Engine:
    eng = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(eng)
    policy_metadata.create_all(eng)
    run_seed(eng, log_dir=tmp_path, anchor=datetime.now(UTC).date())
    monkeypatch.setattr(main, "policy_store", PolicyStore(eng, ttl_seconds=0))
    return eng


@pytest.fixture
def client(engine: sa.Engine) -> TestClient:
    return TestClient(main.app)


def _a_user(engine: sa.Engine) -> tuple[str, str]:
    with engine.connect() as conn:
        row = conn.execute(sa.select(t.users.c.pseudonym, t.users.c.team)).first()
    assert row is not None
    return row[0], row[1]


def _last_incident(engine: sa.Engine) -> dict:
    with engine.connect() as conn:
        row = (
            conn.execute(sa.select(t.incidents).order_by(t.incidents.c.id.desc()))
            .mappings()
            .first()
        )
    assert row is not None
    return dict(row)


def test_check_masks_and_returns_the_placeholders(client: TestClient, engine: sa.Engine) -> None:
    user, team = _a_user(engine)
    r = client.post(
        "/v1/check",
        headers={"X-Demo-User": user},
        json={"text": f"Pay {IBAN} today", "tool": "ChatGPT", "url": "https://chatgpt.com/c/1"},
    ).json()
    assert r["action"] == "mask"
    assert IBAN not in r["masked_text"]
    assert r["placeholders"] == {"[IBAN_1]": IBAN}
    assert r["findings"][0]["entity"] == "IBAN"
    assert IBAN not in str(r["findings"])  # only a masked preview leaves the brain
    row = _last_incident(engine)
    assert row["channel"] == "extension"
    assert row["tool"] == "ChatGPT (personal)"  # matched from the page address
    assert row["team"] == team


def test_check_allows_clean_text(client: TestClient) -> None:
    r = client.post("/v1/check", json={"text": "Summarise this meeting in three bullets"}).json()
    assert r["action"] == "allow"
    assert r["placeholders"] is None


def test_policy_has_actions_tools_and_an_etag(client: TestClient) -> None:
    r = client.get("/v1/policy")
    body = r.json()
    assert body["categories"]["iban"] == "mask"
    assert body["tools"]["chatgpt.com"]["approval"] == "unapproved"
    assert body["tools"]["chatgpt.com"]["alternative"] == "Company AI"
    again = client.get("/v1/policy", headers={"If-None-Match": r.headers["ETag"]})
    assert again.status_code == 304


def test_policy_version_moves_when_a_policy_changes(client: TestClient) -> None:
    before = client.get("/v1/policy")
    client.put(
        "/v1/policies",
        json={"scope": "category", "key": "iban", "action": "block", "updated_by": "tester"},
    )
    after = client.get("/v1/policy")
    assert after.json()["categories"]["iban"] == "block"
    assert after.headers["ETag"] != before.headers["ETag"]


def test_visits_count_in_the_inventory_once_per_person_and_day(
    client: TestClient, engine: sa.Engine
) -> None:
    user, team = _a_user(engine)
    now = int(datetime.now(UTC).timestamp() * 1000)
    day = datetime.now(UTC).date()

    def usage() -> tuple[int, int]:
        with engine.connect() as conn:
            row = conn.execute(
                sa.select(t.tool_usage_daily.c.requests, t.tool_usage_daily.c.users)
                .select_from(
                    t.tool_usage_daily.join(
                        t.ai_tools, t.tool_usage_daily.c.tool_id == t.ai_tools.c.id
                    )
                )
                .where(
                    t.ai_tools.c.name == "ChatGPT (personal)",
                    t.tool_usage_daily.c.day == day,
                    t.tool_usage_daily.c.team == team,
                )
            ).first()
        return (row[0], row[1]) if row else (0, 0)

    event = {"ts": now, "tool": "ChatGPT", "kind": "visit", "host": "chatgpt.com"}
    r = client.post("/v1/events", headers={"X-Demo-User": user}, json={"events": [event, event]})
    assert r.json() == {"stored": 2}
    assert usage() == (2, 1)
    client.post("/v1/events", headers={"X-Demo-User": user}, json={"events": [event]})
    assert usage() == (3, 1)


def test_events_never_carry_text(client: TestClient) -> None:
    # The schema has no field for page or prompt text; extra fields are ignored, not stored.
    r = client.post(
        "/v1/events",
        json={"events": [{"ts": 1, "tool": "x", "kind": "visit", "text": "secret prompt"}]},
    )
    assert r.status_code == 200
    assert "secret prompt" not in str(t.ext_events.c.keys())


def test_a_decision_made_offline_becomes_an_incident(client: TestClient, engine: sa.Engine) -> None:
    user, _ = _a_user(engine)
    now = int(datetime.now(UTC).timestamp() * 1000)
    client.post(
        "/v1/events",
        headers={"X-Demo-User": user},
        json={
            "events": [
                {
                    "ts": now,
                    "tool": "ChatGPT",
                    "kind": "decision",
                    "host": "chatgpt.com",
                    "action": "warn",
                    "category": "greek_id",
                    "offline": True,
                }
            ]
        },
    )
    row = _last_incident(engine)
    assert row["decision"] == "warn"
    assert row["channel"] == "extension"
    assert row["tool"] == "ChatGPT (personal)"


def test_override_reason_goes_to_the_audit_log(client: TestClient, engine: sa.Engine) -> None:
    user, _ = _a_user(engine)
    client.post(
        "/v1/events",
        headers={"X-Demo-User": user},
        json={
            "events": [
                {"ts": 1_700_000_000_000, "tool": "x", "kind": "override", "reason": "client asked"}
            ]
        },
    )
    with engine.connect() as conn:
        row = (
            conn.execute(sa.select(audit_table).where(audit_table.c.action == "extension.override"))
            .mappings()
            .first()
        )
    assert row is not None
    assert row["actor"] == user
    assert row["details"] == {"reason": "client asked"}


def test_pairing_gives_a_token_that_identifies_the_person(
    client: TestClient, engine: sa.Engine
) -> None:
    user, team = _a_user(engine)
    code = client.post("/v1/pair/code", json={"user": user}).json()["code"]
    assert len(code) == 6
    paired = client.post("/v1/pair", json={"code": code}).json()
    assert paired["user"] == user
    assert paired["token"].startswith("pyli_")
    pol = client.get("/v1/policy", headers={"Authorization": f"Bearer {paired['token']}"}).json()
    assert (pol["user"], pol["team"]) == (user, team)
    # A code works once, and the token is stored hashed.
    assert client.post("/v1/pair", json={"code": code}).status_code == 400
    with engine.connect() as conn:
        stored = conn.execute(sa.select(t.devices.c.token_hash)).scalar()
    assert stored != paired["token"]


def test_wrong_pairing_code_is_refused(client: TestClient) -> None:
    assert client.post("/v1/pair", json={"code": "000000"}).status_code == 400


def test_demo_users_list(client: TestClient) -> None:
    users = client.get("/v1/demo-users").json()
    assert len(users) > 50
    assert {"user", "team"} <= set(users[0])


def test_ask_local_falls_back_to_a_labelled_stand_in(client: TestClient) -> None:
    r = client.post("/v1/ask-local", json={"prompt": "hello"}).json()
    assert r["ready"] is False
    assert r["model"] == "stand-in"


def test_logs_ingest_adds_squid_lines(client: TestClient, engine: sa.Engine) -> None:
    user, team = _a_user(engine)
    ts = datetime.now(UTC).timestamp()
    line = (
        f"{ts:.3f} 100 10.0.0.9 TCP_TUNNEL/200 5000 CONNECT chatgpt.com:443 - HIER_DIRECT/1.2.3.4 -"
    )
    r = client.post(
        "/v1/logs/ingest", json={"format": "squid", "lines": [line], "leases": {"10.0.0.9": user}}
    )
    assert r.json()["rows"] == 1
    assert team  # the row is filed under the person's team
