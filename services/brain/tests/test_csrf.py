"""H4: changes sent from another website are refused; the gateway, scripts and tests pass."""

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

EVIL = {"Origin": "https://evil.example"}
DOC = {"title": "Plan", "sensitivity": "internal", "text": "alpha beta gamma delta " * 10}


def _client(monkeypatch) -> tuple[TestClient, sa.Engine]:  # type: ignore[no-untyped-def]
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app), engine


def _docs(engine: sa.Engine) -> int:
    with engine.connect() as c:
        return len(c.execute(sa.select(t.documents.c.id)).all())


def test_cross_site_form_post_is_refused(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, engine = _client(monkeypatch)
    r = client.post("/v1/documents", data=DOC, headers=EVIL)
    assert r.status_code == 403 and "another website" in r.json()["detail"]
    assert _docs(engine) == 0


def test_same_origin_and_headerless_posts_pass(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, engine = _client(monkeypatch)
    assert client.post("/v1/documents", data=DOC).status_code == 200
    ok = client.post(
        "/v1/documents",
        data={**DOC, "title": "Plan 2"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert ok.status_code == 200
    same = client.post(
        "/v1/documents",
        data={**DOC, "title": "Plan 3"},
        headers={"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost:3000"},
    )
    assert same.status_code == 200 and _docs(engine) == 3


def test_sec_fetch_site_cross_site_is_refused_even_with_good_origin(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, engine = _client(monkeypatch)
    r = client.post(
        "/v1/documents",
        data=DOC,
        headers={"Sec-Fetch-Site": "cross-site", "Origin": "http://localhost:3000"},
    )
    assert r.status_code == 403 and _docs(engine) == 0


def test_extension_routes_are_left_to_their_cors(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, _ = _client(monkeypatch)
    r = client.post("/v1/extension/inspect", json={}, headers=EVIL)
    assert r.status_code != 403 or "another website" not in r.text


def test_get_requests_are_not_checked(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, _ = _client(monkeypatch)
    assert client.get("/healthz", headers=EVIL).status_code == 200
    assert client.get("/v1/ask/presets", headers=EVIL).status_code == 200


def test_identity_get_cross_site_refused(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, _ = _client(monkeypatch)
    r = client.get("/v1/incidents/1/identity?request_id=1&viewer=x", headers=EVIL)
    assert r.status_code == 403 and "another website" in r.json()["detail"]
    other = client.get("/v1/incidents/1/identity?request_id=1&viewer=x")
    assert "another website" not in other.text


def test_an_unknown_host_is_refused_for_every_route(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, _ = _client(monkeypatch)
    r = client.get("/v1/ask/presets", headers={"Host": "attacker.example:8001"})
    assert r.status_code == 403 and "not one the Pyli gate answers on" in r.json()["detail"]
    for ok in ("localhost:8001", "127.0.0.1:8001", "brain:8001", "gateway:4000"):
        assert client.get("/v1/ask/presets", headers={"Host": ok}).status_code == 200
    assert client.get("/healthz", headers={"Host": "attacker.example"}).status_code == 200


def test_a_foreign_origin_is_refused_even_when_the_browser_says_same_origin(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, engine = _client(monkeypatch)
    r = client.post(
        "/v1/documents",
        data=DOC,
        headers={"Sec-Fetch-Site": "same-origin", "Origin": "https://evil.example"},
    )
    assert r.status_code == 403 and _docs(engine) == 0


def test_the_copy_link_is_guarded_like_a_change(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, _ = _client(monkeypatch)
    r = client.get("/v1/documents/1/copies/ABC", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403 and "another website" in r.json()["detail"]


def test_more_host_spellings(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client, _ = _client(monkeypatch)
    for ok in ("localhost.:8001", "0.0.0.0:8001", "host.docker.internal:8001", "[::1]:8001"):
        assert client.get("/v1/ask/presets", headers={"Host": ok}).status_code == 200, ok
    assert (
        client.get("/v1/ask/presets", headers={"Host": "evil.localhost.example"}).status_code == 403
    )
