"""Stamped (confidential) files are blocked, in the brain and in the gateway's view of a request."""

import base64

import pytest
from fastapi.testclient import TestClient

import brain.main as main
from brain.documents.marking import find_marking
from tests.test_extract import docx_bytes, pdf_with_text

STAMPED = "Q4 report. Classification: RESTRICTED. Only for internal use."


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def _post(client: TestClient, name: str, data: bytes) -> dict:  # type: ignore[type-arg]
    return client.post(
        "/v1/inspect",
        json={
            "user_id": "u-pdf",
            "team": "Finance",
            "model": "m",
            "messages": [{"role": "user", "content": "analyze this report"}],
            "attachments": [{"filename": name, "content_base64": base64.b64encode(data).decode()}],
        },
    ).json()


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("Ταξινόμηση: RESTRICTED", "RESTRICTED"),
        ("ΕΜΠΙΣΤΕΥΤΙΚΟ", "ΕΜΠΙΣΤΕΥΤΙΚΟ"),
        ("Εμπιστευτικό έγγραφο", "ΕΜΠΙΣΤΕΥΤΙΚΟ"),
        ("Μόνο για εσωτερική χρήση", "ΕΣΩΤΕΡΙΚΗ ΧΡΗΣΗ"),
        ("STRICTLY CONFIDENTIAL", "STRICTLY CONFIDENTIAL"),
        ("Internal use only", "INTERNAL USE ONLY"),
    ],
)
def test_stamps_are_found(text: str, label: str) -> None:
    assert find_marking(text) == label


def test_plain_text_has_no_stamp() -> None:
    assert find_marking("Team lunch on Friday, the budget is on track.") is None


def test_a_stamped_pdf_is_blocked(client: TestClient) -> None:
    r = _post(client, "Akryon_Report_Q4.pdf", pdf_with_text(STAMPED))
    assert r["decision"] == "block"
    assert any("Akryon_Report_Q4.pdf is marked RESTRICTED" in x for x in r["reasons"])


def test_a_stamped_docx_is_blocked(client: TestClient) -> None:
    assert _post(client, "memo.docx", docx_bytes(STAMPED))["decision"] == "block"


def test_an_unstamped_pdf_still_goes_through(client: TestClient) -> None:
    assert _post(client, "lunch.pdf", pdf_with_text("Team lunch on Friday"))["decision"] == "allow"


def test_extension_check_blocks_a_stamped_file(client: TestClient) -> None:
    """The browser extension sends the file to /v1/check; a stamped one comes back as block."""
    data = pdf_with_text(STAMPED)
    out = client.post(
        "/v1/check",
        json={
            "text": "",
            "tool": "Claude.ai",
            "url": "https://claude.ai/chat/1",
            "attachments": [
                {"filename": "report.pdf", "content_base64": base64.b64encode(data).decode()}
            ],
        },
        headers={"X-Demo-User": "u-pdf"},
    ).json()
    assert out["action"] == "block"
    assert any("RESTRICTED" in r for r in out["reasons"])
