"""X30: SIEM export. CEF line, HMAC signature, syslog and webhook senders, and no prompt text."""

import json
import socket
import threading
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain import records, siem
from brain.db import tables as t
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

TRACE = [
    {"layer": "Patterns and checksums", "fired": True, "score": None, "detail": "IBAN (iban)"},
    {"layer": "Document matching", "fired": True, "score": 0.91, "detail": "copy of a memo"},
    {"layer": "Client list", "fired": False, "score": None, "detail": ""},
]
WHEN = datetime(2026, 11, 17, 10, 30, tzinfo=UTC)
SECRET_TEXT = "GR1601101250000000012300695 salary of Maria Papadopoulou"


def _ev(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "incident_id": 42,
        "ts": WHEN,
        "user_key_id": "u-de036ece",
        "team": "Finance",
        "tool": "ChatGPT (personal)",
        "decision": "block",
        "categories": ["iban", "document", "iban"],
        "document_id": 3,
        "trace": TRACE,
    }
    base.update(kw)
    return siem.event(**base)  # type: ignore[arg-type]


def test_event_has_only_the_agreed_fields_and_rule_ids_from_fired_layers() -> None:
    ev = _ev()
    assert tuple(ev) == siem.FIELDS
    assert ev["rule_ids"] == ["document-matching", "patterns-and-checksums"]
    assert ev["categories"] == ["document", "iban"]
    assert ev["time"] == "2026-11-17T10:30:00+00:00"


def test_cef_line_format() -> None:
    line = siem.to_cef(_ev())
    parts = line.split("|", 7)
    assert parts[:7] == [
        "CEF:0",
        "Pyli",
        "Gate",
        "1.0",
        "block",
        "Pyli block: ChatGPT (personal)",
        "8",
    ]
    ext = parts[7]
    assert f"rt={int(WHEN.timestamp() * 1000)}" in ext  # epoch milliseconds
    assert "externalId=42" in ext and "suser=u-de036ece" in ext and "act=block" in ext
    assert "cs1Label=team cs1=Finance" in ext
    assert "cs3=document,iban" in ext and "cs4=document-matching,patterns-and-checksums" in ext
    assert "cn1Label=documentId cn1=3" in ext


def test_cef_severity_follows_the_decision() -> None:
    sev = {
        d: siem.to_cef(_ev(decision=d)).split("|")[6] for d in ("block", "local", "warn", "mask")
    }
    assert sev == {"block": "8", "local": "6", "warn": "5", "mask": "3"}


def test_cef_escapes_pipes_equals_backslashes_and_newlines() -> None:
    line = siem.to_cef(_ev(tool="A|B", team="x=y\\z\nw"))
    assert "Pyli block: A\\|B" in line.split("|8|")[0] + ""
    ext = line.split("|8|", 1)[1]
    assert "cs1=x\\=y\\\\z\\nw" in ext
    assert "\n" not in line


def test_cef_leaves_out_empty_values() -> None:
    line = siem.to_cef(_ev(document_id=None, categories=[]))
    assert "cn1" not in line and "cs3" not in line  # neither the value nor its label


def test_hmac_signature_matches_and_detects_tampering() -> None:
    body = b'{"a":1}'
    sig = siem.sign(body, "s3cret")
    assert len(sig) == 64
    assert siem.verify(body, "s3cret", sig) and siem.verify(body, "s3cret", "sha256=" + sig)
    assert not siem.verify(b'{"a":2}', "s3cret", sig)
    assert not siem.verify(body, "other", sig)


def test_webhook_body_is_signed_with_the_exact_bytes_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_post(url: str, **kw: object) -> httpx.Response:
        seen.update(kw, url=url)
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(siem.httpx, "post", fake_post)
    siem.send_webhook(_ev(), "http://siem.example/hook", "s3cret")
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert siem.verify(seen["content"], "s3cret", headers["X-Pyli-Signature"])  # type: ignore[arg-type]
    assert json.loads(seen["content"])["user_key_id"] == "u-de036ece"  # type: ignore[arg-type]


def test_syslog_udp_delivers_the_cef_line() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(("127.0.0.1", 0))
    srv.settimeout(3)
    siem.send_syslog(siem.to_cef(_ev()), "127.0.0.1", srv.getsockname()[1], "udp")
    data = srv.recv(4096).decode()
    srv.close()
    assert data.startswith("<134>") and " pyli: CEF:0|Pyli|Gate|1.0|block|" in data


def test_syslog_tcp_delivers_a_newline_terminated_line() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    srv.settimeout(3)
    got: list[bytes] = []

    def accept() -> None:
        conn, _ = srv.accept()
        got.append(conn.recv(4096))
        conn.close()

    th = threading.Thread(target=accept)
    th.start()
    siem.send_syslog(siem.to_cef(_ev()), "127.0.0.1", srv.getsockname()[1], "tcp")
    th.join(3)
    srv.close()
    assert got[0].endswith(b"\n") and b"CEF:0|Pyli" in got[0]


def test_push_never_raises_when_the_siem_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(siem.settings, "siem_syslog_host", "127.0.0.1")
    monkeypatch.setattr(siem.settings, "siem_syslog_port", 9)
    monkeypatch.setattr(siem.settings, "siem_syslog_proto", "tcp")
    monkeypatch.setattr(siem.settings, "siem_webhook_url", "http://127.0.0.1:9/x")
    siem.push(_ev())  # must not raise


def test_push_does_nothing_when_nothing_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(siem, "send_syslog", lambda *a: called.append("s"))
    monkeypatch.setattr(siem, "send_webhook", lambda *a: called.append("w"))
    siem.push(_ev())
    assert called == []


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> sa.Engine:
    e = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(e)
    policy_metadata.create_all(e)
    monkeypatch.setattr(main, "policy_store", PolicyStore(e, ttl_seconds=0))
    return e


def _record(engine: sa.Engine, decision: str = "block") -> None:
    records.record_decision(
        engine,
        user="u-de036ece",
        team="Finance",
        decision=decision,
        categories=["iban"],
        reasons=[f"Contains the text {SECRET_TEXT}"],
        masked_preview=f"masked: {SECRET_TEXT}",
        tool="ChatGPT (personal)",
        document_id=None,
        trace=TRACE,
    )


def test_no_prompt_text_in_any_exported_field(engine: sa.Engine) -> None:
    _record(engine)
    client = TestClient(main.app)
    r = client.get("/v1/export/incidents")
    assert r.headers["content-type"].startswith("application/x-ndjson")
    lines = r.text.strip().split("\n")
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert tuple(row) == siem.FIELDS
    blob = r.text + siem.to_cef(row)
    for leak in ("GR1601101250000000012300695", "Papadopoulou", "salary", "masked", "Contains"):
        assert leak not in blob
    assert row["user_key_id"] == "u-de036ece" and row["tool"] == "ChatGPT (personal)"
    assert "display_name" not in blob


def test_export_since_returns_only_newer_incidents(engine: sa.Engine) -> None:
    _record(engine)
    client = TestClient(main.app)
    later = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    assert client.get("/v1/export/incidents", params={"since": later}).text == ""
    earlier = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    assert len(client.get("/v1/export/incidents", params={"since": earlier}).text.splitlines()) == 1


def test_allowed_prompts_are_not_exported(engine: sa.Engine) -> None:
    _record(engine, "allow")
    assert TestClient(main.app).get("/v1/export/incidents").text == ""


def test_export_token_is_enforced_when_set(
    engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main.settings, "siem_export_token", "tok")
    client = TestClient(main.app)
    assert client.get("/v1/export/incidents").status_code == 401
    assert (
        client.get("/v1/export/incidents", headers={"Authorization": "Bearer no"}).status_code
        == 401
    )
    assert (
        client.get("/v1/export/incidents", headers={"Authorization": "Bearer tok"}).status_code
        == 200
    )


def test_recording_an_incident_pushes_it(
    engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    pushed: list[dict[str, object]] = []
    monkeypatch.setattr(siem, "push", pushed.append)
    _record(engine)
    assert len(pushed) == 1 and pushed[0]["decision"] == "block" and pushed[0]["id"] == 1
    assert "Papadopoulou" not in json.dumps(pushed)
