from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.policy.store import PolicyStore
from brain.seed.load import run_seed

IBAN = "GR1601101250000000012300695"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    run_seed(engine, log_dir=tmp_path, anchor=datetime.now(UTC).date())
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app)


def test_metrics(client: TestClient) -> None:
    body = client.get("/v1/metrics").json()
    assert body["prompts_checked"] > 1000
    assert 0.8 < body["zero_llm_share"] < 1.0
    assert body["incidents_7d"] > 0
    assert body["unapproved_tools"] >= 3
    assert body["demo_data"] is True


def test_incidents_are_newest_first_and_filterable(client: TestClient) -> None:
    page = client.get("/v1/incidents?limit=10").json()
    assert page["total"] > 300
    stamps = [i["ts"] for i in page["items"]]
    assert stamps == sorted(stamps, reverse=True)
    blocked = client.get("/v1/incidents?decision=block").json()
    assert blocked["total"] > 0
    assert {i["decision"] for i in blocked["items"]} == {"block"}
    legal = client.get("/v1/incidents?team=Legal").json()
    assert {i["team"] for i in legal["items"]} == {"Legal"}


def test_incidents_show_pseudonyms_not_names(client: TestClient) -> None:
    items = client.get("/v1/incidents?limit=50").json()["items"]
    assert all(i["user"].startswith("u-") for i in items)


def test_incident_paging_limits(client: TestClient) -> None:
    assert len(client.get("/v1/incidents?limit=1000").json()["items"]) == 100
    assert len(client.get("/v1/incidents?limit=0").json()["items"]) == 1
    first = client.get("/v1/incidents?limit=5&offset=0").json()["items"]
    second = client.get("/v1/incidents?limit=5&offset=5").json()["items"]
    assert {i["id"] for i in first}.isdisjoint({i["id"] for i in second})


def test_inventory_lists_every_tool_with_usage(client: TestClient) -> None:
    tools = {x["name"]: x for x in client.get("/v1/inventory").json()}
    assert len(tools) == 15
    chatgpt = tools["ChatGPT (personal)"]
    assert chatgpt["approval"] == "unapproved"
    assert chatgpt["requests"] > 0
    assert "Sales" in chatgpt["teams"]
    assert len(chatgpt["trend"]) == 7
    assert chatgpt["alternative"] == "Company AI"
    assert tools["Company AI"]["requests"] > 0  # gateway traffic counts as a tool


def test_inspect_records_incident_and_counter(client: TestClient) -> None:
    before = client.get("/v1/metrics").json()["prompts_checked"]
    body = {
        "user_id": "demo-abc",
        "team": "general",
        "messages": [{"role": "user", "content": f"Pay {IBAN}"}],
    }
    assert client.post("/v1/inspect", json=body).json()["decision"] == "mask"
    clean = {**body, "messages": [{"role": "user", "content": "hello there"}]}
    client.post("/v1/inspect", json=clean)
    assert client.get("/v1/metrics").json()["prompts_checked"] == before + 2
    newest = client.get("/v1/incidents?limit=1").json()["items"][0]
    assert (newest["user"], newest["decision"], newest["categories"]) == (
        "demo-abc",
        "mask",
        ["iban"],
    )
    assert IBAN not in str(newest)  # never the raw value
    assert newest["masked_preview"].startswith("GR")


def test_read_endpoints_say_so_without_a_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "policy_store", PolicyStore(None))
    c = TestClient(main.app)
    for path in ("/v1/metrics", "/v1/incidents", "/v1/inventory"):
        r = c.get(path)
        assert r.status_code == 503
        assert "database" in r.json()["detail"]


def test_documents_register_lists_sensitivity_and_incident_counts(client: TestClient) -> None:
    docs = client.get("/v1/documents").json()
    assert len(docs) == 3
    assert {d["sensitivity"] for d in docs} <= {"internal", "confidential", "restricted"}
    assert all(d["title"] and isinstance(d["incidents"], int) for d in docs)


def test_user_seen_is_false_until_the_gateway_checked_a_request(client: TestClient) -> None:
    assert client.get("/v1/users/demo-newbie/seen").json() == {"seen": False}
    client.post(
        "/v1/inspect",
        json={
            "user_id": "demo-newbie",
            "team": "general",
            "model": "m",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert client.get("/v1/users/demo-newbie/seen").json() == {"seen": True}


def test_inspect_warns_when_a_seeded_client_name_is_in_the_message(client: TestClient) -> None:
    assert main.policy_store.engine is not None
    with main.policy_store.engine.connect() as conn:
        name = conn.execute(sa.text("SELECT name FROM clients LIMIT 1")).scalar_one()
    r = client.post(
        "/v1/inspect",
        json={
            "user_id": "u-x",
            "team": "Sales",
            "model": "m",
            "messages": [{"role": "user", "content": f"Draft a renewal email for {name.upper()}"}],
        },
    ).json()
    assert r["decision"] == "warn"
    assert any(f["category"] == "client_name" for f in r["findings"])
