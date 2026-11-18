"""Stamped (confidential) files are blocked, in the brain and in the gateway's view of a request."""

import base64
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import brain.main as main
from brain.documents.marking import find_marking
from tests.test_extract import docx_bytes, pdf_with_text

_PATH = Path(__file__).resolve().parents[3] / "infra" / "gateway" / "dna_inspect.py"
_SPEC = importlib.util.spec_from_file_location("dna_inspect_pdf", _PATH)
assert _SPEC and _SPEC.loader
dna = importlib.util.module_from_spec(_SPEC)
sys.modules["dna_inspect_pdf"] = dna
_SPEC.loader.exec_module(dna)

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


def test_gateway_pulls_files_out_of_every_request_shape() -> None:
    b64 = base64.b64encode(b"%PDF-1.4").decode()
    openai = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hi"},
                    {
                        "type": "file",
                        "file": {
                            "filename": "a.pdf",
                            "file_data": f"data:application/pdf;base64,{b64}",
                        },
                    },
                ],
            }
        ]
    }
    anthropic = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "title": "b.pdf",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
                    },
                ],
            }
        ]
    }
    responses = {
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": "c.pdf",
                        "file_data": f"data:application/pdf;base64,{b64}",
                    },
                ],
            }
        ]
    }
    assert dna.attached_files(openai, "completion") == [
        {"filename": "a.pdf", "content_base64": b64}
    ]
    assert dna.attached_files(anthropic, "anthropic_messages")[0]["filename"] == "b.pdf"
    assert dna.attached_files(responses, "responses")[0]["filename"] == "c.pdf"


def test_gateway_ignores_plain_text_requests() -> None:
    assert dna.attached_files({"messages": [{"role": "user", "content": "hi"}]}, "completion") == []


def test_check_endpoint_blocks_a_stamped_file(client: TestClient) -> None:
    r = client.post(
        "/v1/check",
        json={
            "text": "",
            "tool": "Claude",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_base64": base64.b64encode(pdf_with_text(STAMPED)).decode(),
                }
            ],
        },
        headers={"x-demo-user": "demo"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["action"] == "block"
