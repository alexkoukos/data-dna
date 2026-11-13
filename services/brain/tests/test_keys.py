import httpx
import pytest
from fastapi.testclient import TestClient

import brain.main as main
from brain.keys import KeyError_, create_key

client = TestClient(main.app)


def _gateway(handler):  # type: ignore[no-untyped-def]
    return httpx.Client(base_url="http://gw", transport=httpx.MockTransport(handler))


def test_create_key_makes_team_then_key() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"key": "sk-abc"})

    assert create_key("u1", "finance", _gateway(handler)) == "sk-abc"
    assert calls == ["/team/new", "/key/generate"]


def test_create_key_reports_gateway_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(KeyError_):
        create_key("u1", "finance", _gateway(handler))


def test_keys_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "create_key", lambda user, team: "sk-xyz")
    r = client.post("/v1/keys", json={"user_id": "maria", "team": "finance"})
    assert r.status_code == 200
    assert r.json()["key"] == "sk-xyz"
    assert r.json()["default_model"] in ("demo-mock", "gpt-4o-mini")


def test_keys_endpoint_rejects_odd_user_id() -> None:
    assert client.post("/v1/keys", json={"user_id": "a b/c"}).status_code == 422


def test_keys_endpoint_off_outside_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.settings, "demo_mode", False)
    assert client.post("/v1/keys", json={"user_id": "maria"}).status_code == 403
