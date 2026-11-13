import time

from fastapi.testclient import TestClient

from brain.main import app
from brain.sessions import SessionStore

client = TestClient(app)
IBAN = "GR1601101250000000012300695"


def _masked_session(user: str = "u1") -> str:
    r = client.post(
        "/v1/inspect",
        json={"user_id": user, "messages": [{"role": "user", "content": f"Check {IBAN}"}]},
    )
    body = r.json()
    assert body["decision"] == "mask"
    return str(body["session_id"])


def test_unmask_restores_value_for_owner() -> None:
    sid = _masked_session()
    r = client.post(
        "/v1/unmask", json={"session_id": sid, "user_id": "u1", "text": "Looks fine: [IBAN_1]"}
    )
    assert r.json() == {"text": f"Looks fine: {IBAN}", "restored": 1}


def test_unmask_refuses_other_user() -> None:
    sid = _masked_session("u1")
    r = client.post("/v1/unmask", json={"session_id": sid, "user_id": "u2", "text": "[IBAN_1]"})
    assert r.json()["text"] == "[IBAN_1]"
    assert r.json()["restored"] == 0


def test_unmask_unknown_session_is_a_no_op() -> None:
    r = client.post("/v1/unmask", json={"session_id": "nope", "user_id": "u1", "text": "[IBAN_1]"})
    assert r.json()["text"] == "[IBAN_1]"


def test_allow_has_no_session() -> None:
    r = client.post("/v1/inspect", json={"messages": [{"role": "user", "content": "hello"}]})
    assert r.json()["session_id"] is None


def test_session_expires() -> None:
    store = SessionStore(ttl_seconds=0.01)
    sid = store.create("u1", {"[X_1]": "secret"})
    time.sleep(0.03)
    assert store.get(sid, "u1") is None


def test_inspect_output_masks_echoed_secret() -> None:
    r = client.post("/v1/inspect-output", json={"text": "Key: AKIAIOSFODNN7EXAMPLE"})
    body = r.json()
    assert body["changed"] is True
    assert "AKIAIOSFODNN7EXAMPLE" not in body["text"]
    assert body["findings"][0]["category"] == "secret"


def test_inspect_output_leaves_clean_text() -> None:
    r = client.post("/v1/inspect-output", json={"text": "Hello [IBAN_1]"})
    assert r.json() == {"text": "Hello [IBAN_1]", "changed": False, "findings": []}
