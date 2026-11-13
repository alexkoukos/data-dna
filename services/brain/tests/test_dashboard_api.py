from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata
from brain.seed.load import run_seed

IBAN = "GR1601101250000000012300695"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
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


def test_preset_questions_are_listed(client: TestClient) -> None:
    presets = client.get("/v1/ask/presets").json()
    assert len(presets) == 5
    assert any("unapproved AI tools and also had client data" in p["question"] for p in presets)


def test_every_preset_runs_and_shows_its_sql(client: TestClient) -> None:
    for p in client.get("/v1/ask/presets").json():
        out = client.post("/v1/ask", json={"preset": p["id"]}).json()
        assert out["sql"].lstrip().startswith("SELECT")
        assert out["columns"] and out["parameters"]["since"]
        assert all(len(row) == len(out["columns"]) for row in out["rows"])


def test_client_data_question_finds_the_storyline(client: TestClient) -> None:
    out = client.post("/v1/ask", json={"preset": "top_tools"}).json()
    assert out["rows"], "the demo company has tool usage in the last 7 days"
    assert out["columns"] == ["tool", "approval", "requests"]
    requests = [row[2] for row in out["rows"]]
    assert requests == sorted(requests, reverse=True)


def test_unknown_preset_gets_a_plain_404(client: TestClient) -> None:
    r = client.post("/v1/ask", json={"preset": "drop_tables"})
    assert r.status_code == 404
    assert "preset" in r.json()["detail"]


def test_ask_says_so_without_a_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "policy_store", PolicyStore(None))
    r = TestClient(main.app).post("/v1/ask", json={"preset": "top_tools"})
    assert r.status_code == 503


def _an_incident_id(client: TestClient) -> int:
    return int(client.get("/v1/incidents?limit=1").json()["items"][0]["id"])


def test_incident_detail_shows_a_pseudonym_and_the_same_persons_timeline(
    client: TestClient,
) -> None:
    detail = client.get(f"/v1/incidents/{_an_incident_id(client)}").json()
    assert detail["incident"]["user"].startswith("u-")
    assert "display_name" not in str(detail)
    assert all(i["user"] == detail["incident"]["user"] for i in detail["timeline"])
    assert detail["reveals"] == []


def test_unknown_incident_is_a_plain_404(client: TestClient) -> None:
    r = client.get("/v1/incidents/99999999")
    assert r.status_code == 404
    assert "does not exist" in r.json()["detail"]


def test_identity_stays_sealed_until_a_second_person_approves(client: TestClient) -> None:
    inc = _an_incident_id(client)
    asked = client.post(
        "/v1/reveal-requests",
        json={"incident_id": inc, "requested_by": "Anna", "reason": "Pasted a client contract"},
    ).json()
    assert asked["status"] == "pending"
    # Sealed while pending.
    sealed = client.get(f"/v1/incidents/{inc}/identity?request_id={asked['id']}&viewer=Anna")
    assert sealed.status_code == 403
    # The requester cannot approve their own request.
    own = client.post(f"/v1/reveal-requests/{asked['id']}/approve", json={"decided_by": " anna "})
    assert own.status_code == 422
    assert "second person" in own.json()["detail"]
    # A different person can.
    ok = client.post(f"/v1/reveal-requests/{asked['id']}/approve", json={"decided_by": "Nikos"})
    assert ok.json()["status"] == "approved"
    seen = client.get(f"/v1/incidents/{inc}/identity?request_id={asked['id']}&viewer=Anna").json()
    assert seen["pseudonym"].startswith("u-")
    assert seen["display_name"]
    # Every step is in the audit log.
    assert main.policy_store.engine is not None
    with main.policy_store.engine.connect() as conn:
        actions = [
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT action FROM audit_log WHERE action LIKE 'reveal.%' "
                    "OR action LIKE 'identity.%' ORDER BY id"
                )
            )
        ]
    assert actions == ["reveal.requested", "reveal.approved", "identity.revealed"]


def test_denied_request_never_reveals_and_cannot_be_decided_twice(client: TestClient) -> None:
    inc = _an_incident_id(client)
    asked = client.post(
        "/v1/reveal-requests",
        json={"incident_id": inc, "requested_by": "Anna", "reason": "Just curious about this"},
    ).json()
    denied = client.post(f"/v1/reveal-requests/{asked['id']}/deny", json={"decided_by": "Nikos"})
    assert denied.json()["status"] == "denied"
    again = client.post(f"/v1/reveal-requests/{asked['id']}/approve", json={"decided_by": "Eva"})
    assert again.status_code == 422
    sealed = client.get(f"/v1/incidents/{inc}/identity?request_id={asked['id']}")
    assert sealed.status_code == 403


def test_reveal_needs_a_real_reason_and_only_one_pending_request(client: TestClient) -> None:
    inc = _an_incident_id(client)
    short = client.post(
        "/v1/reveal-requests", json={"incident_id": inc, "requested_by": "Anna", "reason": "hi"}
    )
    assert short.status_code == 422
    body = {"incident_id": inc, "requested_by": "Anna", "reason": "Pasted a client contract"}
    assert client.post("/v1/reveal-requests", json=body).status_code == 200
    dup = client.post("/v1/reveal-requests", json=body)
    assert dup.status_code == 422
    assert "already waiting" in dup.json()["detail"]


def test_an_approval_for_one_incident_does_not_open_another(client: TestClient) -> None:
    items = client.get("/v1/incidents?limit=2").json()["items"]
    a, b = items[0]["id"], items[1]["id"]
    asked = client.post(
        "/v1/reveal-requests",
        json={"incident_id": a, "requested_by": "Anna", "reason": "Pasted a client contract"},
    ).json()
    client.post(f"/v1/reveal-requests/{asked['id']}/approve", json={"decided_by": "Nikos"})
    r = client.get(f"/v1/incidents/{b}/identity?request_id={asked['id']}")
    assert r.status_code == 403


def test_register_a_document_then_a_copy_of_it_is_blocked(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from brain.documents.embeddings import HashingEmbedder

    monkeypatch.setattr(main, "embedder", HashingEmbedder())
    text = " ".join(f"secret{i} budget{i % 7} plan{i % 5}" for i in range(40))
    made = client.post(
        "/v1/documents",
        data={"title": "Roadmap", "sensitivity": "restricted", "text": text},
    ).json()
    assert made["chunks"] >= 5
    r = client.post(
        "/v1/inspect",
        json={
            "user_id": "u-x",
            "team": "Sales",
            "model": "m",
            "messages": [{"role": "user", "content": "Improve this: " + text[:300]}],
        },
    ).json()
    assert r["decision"] == "block"
    assert r["documents"][0]["kind"] == "copy"
    listed = client.get("/v1/documents").json()
    assert any(d["title"] == "Roadmap" and d["incidents"] >= 1 for d in listed)


def test_register_rejects_a_bad_sensitivity_and_empty_text(client: TestClient) -> None:
    bad = client.post("/v1/documents", data={"title": "X", "sensitivity": "top", "text": "a b c"})
    assert bad.status_code == 422 and "restricted" in bad.json()["detail"]
    empty = client.post(
        "/v1/documents", data={"title": "X", "sensitivity": "internal", "text": " "}
    )
    assert empty.status_code == 422


def test_a_docx_upload_is_registered_and_then_recognised(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from brain.documents.embeddings import HashingEmbedder
    from tests.test_extract import docx_bytes

    monkeypatch.setattr(main, "embedder", HashingEmbedder())
    body = " ".join(f"tender{i} price{i % 9} lot{i % 4}" for i in range(40))
    made = client.post(
        "/v1/documents",
        data={"title": "Tender", "sensitivity": "confidential"},
        files={"file": ("tender.docx", docx_bytes(body), "application/octet-stream")},
    )
    assert made.status_code == 200 and made.json()["chunks"] >= 5
    r = client.post(
        "/v1/inspect",
        json={
            "user_id": "u-x",
            "team": "Sales",
            "model": "m",
            "messages": [{"role": "user", "content": body[:300]}],
        },
    ).json()
    assert r["decision"] == "local"
