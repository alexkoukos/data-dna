"""X27: the browser extension endpoints, the key-to-user lookup and the CORS rule."""

import hashlib

import httpx
import pytest
from fastapi.testclient import TestClient

import brain.identity as identity
import brain.main as main
from brain.identity import GatewayUnavailable, Identity, bearer_token, resolve_key

client = TestClient(main.app)
EXT = "abcdefghijklmnopabcdefghijklmnop"
ORIGIN = f"chrome-extension://{EXT}"


def _gateway(handler):  # type: ignore[no-untyped-def]
    return httpx.Client(base_url="http://gw", transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    identity.forget_all()
    monkeypatch.setattr(main.settings, "extension_id", EXT)


def test_bearer_token_parsing() -> None:
    assert bearer_token("Bearer sk-1") == "sk-1"
    assert bearer_token("bearer  sk-1 ") == "sk-1"
    assert bearer_token("Basic sk-1") is None
    assert bearer_token("Bearer") is None
    assert bearer_token(None) is None


def test_resolve_key_reads_user_and_team_from_the_gateway() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"info": {"user_id": "maria", "team_id": "finance"}})

    assert resolve_key("sk-maria", _gateway(handler)) == Identity("maria", "finance")
    assert seen[0].url.params["key"] != "sk-maria" and len(seen[0].url.params["key"]) == 64
    assert seen[0].headers["authorization"].startswith("Bearer ")  # the admin key, not the user's
    assert seen[0].headers["authorization"] != "Bearer sk-maria"


def test_resolve_key_is_cached_but_unknown_keys_are_not() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.params["key"] == hashlib.sha256(b"sk-ok").hexdigest():
            return httpx.Response(200, json={"info": {"user_id": "u", "team_id": "t"}})
        return httpx.Response(404, json={})

    assert resolve_key("sk-ok", _gateway(handler)) is not None
    assert resolve_key("sk-ok", _gateway(handler)) is not None
    assert calls == 1
    assert resolve_key("sk-bad", _gateway(handler)) is None
    assert resolve_key("sk-bad", _gateway(handler)) is None
    assert calls == 3


def test_resolve_key_rejects_a_key_without_a_user() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"info": {"user_id": None, "team_id": "t"}})

    assert resolve_key("sk-x", _gateway(handler)) is None


def test_resolve_key_says_so_when_the_gateway_is_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(GatewayUnavailable):
        resolve_key("sk-x", _gateway(handler))


def _as(monkeypatch: pytest.MonkeyPatch, user: str = "maria", team: str = "finance") -> None:
    monkeypatch.setattr(main, "resolve_key", lambda key: Identity(user, team))


def test_inspect_needs_a_key() -> None:
    r = client.post("/v1/extension/inspect", json={"text": "hi"})
    assert r.status_code == 401


def test_unknown_key_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "resolve_key", lambda key: None)
    r = client.post(
        "/v1/extension/inspect", json={"text": "hi"}, headers={"Authorization": "Bearer nope"}
    )
    assert r.status_code == 401


def test_gateway_down_is_503_not_401(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(key: str) -> Identity:
        raise GatewayUnavailable("down")

    monkeypatch.setattr(main, "resolve_key", boom)
    r = client.post(
        "/v1/extension/inspect", json={"text": "hi"}, headers={"Authorization": "Bearer k"}
    )
    assert r.status_code == 503


def test_client_cannot_name_the_user(monkeypatch: pytest.MonkeyPatch) -> None:
    _as(monkeypatch, "maria", "finance")
    r = client.post(
        "/v1/extension/inspect",
        json={"text": "hello", "user_id": "ceo", "team": "board"},
        headers={"Authorization": "Bearer k"},
    )
    assert r.status_code == 200
    assert r.json()["user_id"] == "maria"


def test_clean_text_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    _as(monkeypatch)
    r = client.post(
        "/v1/extension/inspect",
        json={"text": "Summarise the history of the Parthenon."},
        headers={"Authorization": "Bearer k"},
    )
    assert r.json()["decision"] == "allow"
    assert r.json()["masked_text"] is None


def test_iban_is_masked_and_names_entity_types_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _as(monkeypatch)
    card = "GR1601101250000000012300695"
    r = client.post(
        "/v1/extension/inspect",
        json={"text": f"Pay into {card} please"},
        headers={"Authorization": "Bearer k"},
    )
    body = r.json()
    assert body["decision"] == "mask"
    assert card not in body["masked_text"]
    assert body["entity_types"]
    assert card not in str(body["reasons"]) + str(body["entity_types"])
    assert body["alternative_url"]


def test_ack_needs_a_key_and_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.post("/v1/extension/ack", json={}).status_code == 401
    _as(monkeypatch)
    r = client.post(
        "/v1/extension/ack", json={"reason": "audit"}, headers={"Authorization": "Bearer k"}
    )
    assert r.status_code == 200


def test_me_returns_identity_and_link(monkeypatch: pytest.MonkeyPatch) -> None:
    _as(monkeypatch)
    r = client.get("/v1/extension/me", headers={"Authorization": "Bearer k"})
    assert r.json()["user_id"] == "maria"
    assert r.json()["incidents_url"].endswith("user=maria")


def test_cors_allows_only_the_extension_origin() -> None:
    pre = client.options(
        "/v1/extension/inspect",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    assert pre.status_code == 204
    assert pre.headers["access-control-allow-origin"] == ORIGIN
    assert "authorization" in pre.headers["access-control-allow-headers"].lower()


@pytest.mark.parametrize("origin", ["https://chatgpt.com", "https://evil.example", "null"])
def test_cors_refuses_other_origins(origin: str) -> None:
    pre = client.options(
        "/v1/extension/inspect",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert pre.status_code == 403
    assert "access-control-allow-origin" not in pre.headers
    got = client.get("/v1/extension/me", headers={"Origin": origin})
    assert "access-control-allow-origin" not in got.headers


def test_cors_is_off_without_an_extension_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.settings, "extension_id", "")
    pre = client.options(
        "/v1/extension/inspect",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in pre.headers


def test_other_routes_get_no_cors_headers() -> None:
    r = client.get("/healthz", headers={"Origin": ORIGIN})
    assert "access-control-allow-origin" not in r.headers


def test_card_number_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    _as(monkeypatch)
    r = client.post(
        "/v1/extension/inspect",
        json={"text": "Charge 4111 1111 1111 1111 please"},
        headers={"Authorization": "Bearer k"},
    )
    assert r.json()["decision"] == "warn"
    assert r.json()["masked_text"] is None


def test_key_lookup_sends_only_the_hash() -> None:
    import hashlib

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"info": {"user_id": "maria", "team_id": "finance"}})

    resolve_key("sk-hash-me", _gateway(handler))
    sent = seen[0].url.params["key"]
    assert sent == hashlib.sha256(b"sk-hash-me").hexdigest() and "sk-hash-me" not in str(
        seen[0].url
    )


def test_expired_identities_are_evicted() -> None:
    import brain.identity as ident

    ident._cache.clear()
    ident._cache["old"] = (0.0, Identity("a", "t"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"info": {"user_id": "u", "team_id": "t"}})

    resolve_key("sk-new", _gateway(handler))
    assert "old" not in ident._cache and len(ident._cache) == 1
