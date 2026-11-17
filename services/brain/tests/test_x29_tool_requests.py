"""X29: request and approve an AI tool. The tool counts as approved in the inventory and in
risk per tool, and every step is in the audit log."""

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.policy.store import PolicyStore, audit_table
from brain.policy.store import metadata as policy_metadata


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, sa.Engine]:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.insert(t.ai_tools).values(
                id=1,
                name="Perplexity",
                vendor="Perplexity AI",
                domains=["perplexity.ai"],
                category="search",
                approval="unapproved",
                risk="high",
                reason="Keeps prompts",
                alternative="Company AI",
            )
        )
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app), engine


def _ask(client: TestClient, tool: str = "Perplexity", user: str = "maria") -> dict[str, object]:
    r = client.post(
        "/v1/tool-requests",
        json={"user_id": user, "team": "Finance", "tool": tool, "reason": "Needs live web search"},
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def _decide(client: TestClient, rid: int, **kw: object) -> object:
    body: dict[str, object] = {
        "reviewer": "sec1",
        "approve": True,
        "risk": "medium",
        "allowed_categories": ["email", "phone"],
        "alternative": "Company AI",
    }
    body.update(kw)
    return client.post(f"/v1/tool-requests/{rid}/decision", json=body)


def _tool(client: TestClient, name: str) -> dict[str, object]:
    return next(x for x in client.get("/v1/inventory").json() if x["name"] == name)


def test_request_approve_updates_inventory_risk_and_audit(
    env: tuple[TestClient, sa.Engine],
) -> None:
    client, engine = env
    before = next(x for x in client.get("/v1/roi").json()["tools"] if x["name"] == "Perplexity")
    assert before["approval"] == "unapproved"

    req = _ask(client)
    assert req["status"] == "pending"
    assert [
        r["id"] for r in client.get("/v1/tool-requests", params={"status": "pending"}).json()
    ] == [req["id"]]

    r = _decide(client, int(req["id"]))  # type: ignore[arg-type]
    assert r.status_code == 200  # type: ignore[attr-defined]
    assert r.json()["status"] == "approved"  # type: ignore[attr-defined]

    tool = _tool(client, "Perplexity")
    assert tool["approval"] == "approved" and tool["risk"] == "medium"
    assert tool["allowed_categories"] == ["email", "phone"] and tool["alternative"] == "Company AI"
    after = next(x for x in client.get("/v1/roi").json()["tools"] if x["name"] == "Perplexity")
    assert after["approval"] == "approved" and after["risk"] == "medium"

    with engine.connect() as conn:
        rows = conn.execute(
            sa.select(audit_table.c.actor, audit_table.c.action).order_by(audit_table.c.id)
        ).all()
    assert [(a, b) for a, b in rows] == [("maria", "tool.request"), ("sec1", "tool.approve")]


def test_approving_an_unknown_tool_adds_it_to_the_inventory(
    env: tuple[TestClient, sa.Engine],
) -> None:
    client, _ = env
    req = _ask(client, "Brand New AI")
    _decide(client, int(req["id"]), risk="low")  # type: ignore[arg-type]
    tool = _tool(client, "Brand New AI")
    assert tool["approval"] == "approved" and tool["risk"] == "low"


def test_reject_leaves_the_tool_unapproved_and_is_audited(
    env: tuple[TestClient, sa.Engine],
) -> None:
    client, engine = env
    req = _ask(client)
    r = _decide(client, int(req["id"]), approve=False, note="Use Company AI")  # type: ignore[arg-type]
    assert r.json()["status"] == "rejected" and r.json()["note"] == "Use Company AI"  # type: ignore[attr-defined]
    assert _tool(client, "Perplexity")["approval"] == "unapproved"
    with engine.connect() as conn:
        actions = [
            a for (a,) in conn.execute(sa.select(audit_table.c.action).order_by(audit_table.c.id))
        ]
    assert actions == ["tool.request", "tool.reject"]


def test_requester_sees_the_outcome_once(env: tuple[TestClient, sa.Engine]) -> None:
    client, _ = env
    req = _ask(client)
    assert client.post("/v1/users/maria/tool-request-outcomes").json() == []  # still pending
    _decide(client, int(req["id"]))  # type: ignore[arg-type]
    first = client.post("/v1/users/maria/tool-request-outcomes").json()
    assert [(o["tool"], o["status"]) for o in first] == [("Perplexity", "approved")]
    assert client.post("/v1/users/maria/tool-request-outcomes").json() == []
    assert client.post("/v1/users/someone-else/tool-request-outcomes").json() == []


def test_approval_needs_a_risk_rating(env: tuple[TestClient, sa.Engine]) -> None:
    client, _ = env
    req = _ask(client)
    assert _decide(client, int(req["id"]), risk=None).status_code == 422  # type: ignore[arg-type,attr-defined]
    assert _tool(client, "Perplexity")["approval"] == "unapproved"
    assert client.get("/v1/tool-requests", params={"status": "pending"}).json()  # still pending


def test_a_request_is_decided_only_once(env: tuple[TestClient, sa.Engine]) -> None:
    client, _ = env
    req = _ask(client)
    assert _decide(client, int(req["id"])).status_code == 200  # type: ignore[arg-type,attr-defined]
    assert _decide(client, int(req["id"]), approve=False).status_code == 409  # type: ignore[arg-type,attr-defined]
    assert _decide(client, 999).status_code == 404  # type: ignore[attr-defined]


def test_an_already_approved_tool_cannot_be_requested(env: tuple[TestClient, sa.Engine]) -> None:
    client, _ = env
    _decide(client, int(_ask(client)["id"]))  # type: ignore[arg-type]
    r = client.post("/v1/tool-requests", json={"user_id": "x", "tool": "perplexity", "reason": "r"})
    assert r.status_code == 409 and "already approved" in r.json()["detail"]


def test_a_person_cannot_flood_the_queue(env: tuple[TestClient, sa.Engine]) -> None:
    client, _ = env
    for n in range(5):
        _ask(client, f"Tool {n}")
    r = client.post(
        "/v1/tool-requests", json={"user_id": "maria", "tool": "One more", "reason": "r"}
    )
    assert r.status_code == 429


@pytest.mark.parametrize("bad", [{"tool": ""}, {"reason": ""}, {"user_id": "a b/c"}])
def test_request_is_validated(env: tuple[TestClient, sa.Engine], bad: dict[str, str]) -> None:
    body = {"user_id": "maria", "tool": "X", "reason": "r"}
    body.update(bad)
    assert env[0].post("/v1/tool-requests", json=body).status_code == 422
