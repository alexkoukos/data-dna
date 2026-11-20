"""Company Chat files end to end: brain reads the file, the gateway checks the message, a mock
model answers. Needs `make up`; skipped otherwise. Run with: make test-gateway

This is the path the chat page takes: POST /v1/files/extract, then the text inside the message to
/v1/chat/completions. The model is LiteLLM's mock, so no key and no network are needed.
"""

import httpx
import pytest
from openai import OpenAI, PermissionDeniedError

from tests.test_chat_files import AWS_KEY, as_message
from tests.test_extract import IBAN, docx_bytes, pdf_with_text
from tests.test_gateway_live import BRAIN, _gateway_up, client  # noqa: F401 - the fixture

pytestmark = pytest.mark.skipif(not _gateway_up(), reason="gateway not running (make up)")

# A line of the confidential sample document "Salary bands 2027" (data/documents, synthetic).
SALARY_LINE = (
    "Το μπόνους απόδοσης δεν μπορεί να ξεπερνά το δέκα πέντε τοις εκατό του βασικού μισθού, "
    "και οι αυξήσεις εγκρίνονται μία φορά τον χρόνο, τον Ιανουάριο, μετά από αξιολόγηση."
)


def _extract(name: str, data: bytes) -> str:
    r = httpx.post(f"{BRAIN}/v1/files/extract", files={"file": (name, data)}, timeout=60)
    r.raise_for_status()
    return str(r.json()["text"])


def _send(client: OpenAI, content: str, model: str = "demo-mock") -> tuple[str, str]:  # noqa: F811
    raw = client.chat.completions.with_raw_response.create(
        model=model, messages=[{"role": "user", "content": content}]
    )
    return raw.headers.get("x-dna-decision", ""), raw.parse().choices[0].message.content or ""


def test_a_file_with_an_iban_and_a_key_is_masked_and_answered(client: OpenAI) -> None:  # noqa: F811
    # Worded like an invoice on purpose: "access key: AKIA..." alone reads like the last lines of
    # the restricted board memo, and the document matcher then (rightly) answers locally.
    text = _extract(
        "invoice.docx",
        docx_bytes(
            f"Invoice 42 for office chairs. Please pay {IBAN} by Friday.",
            f"The supplier portal login uses {AWS_KEY} for the upload script.",
        ),
    )
    decision, answer = _send(client, as_message("invoice.docx", text), model="demo-echo")
    assert decision == "mask"
    # demo-echo answers "I checked [IBAN_1]": the gate puts the real value back for the person.
    assert IBAN in answer and "[IBAN_1]" not in answer


def test_a_masked_file_still_streams(client: OpenAI) -> None:  # noqa: F811
    text = _extract("pay.txt", f"Pay {IBAN} today.".encode())
    stream = client.chat.completions.create(
        model="demo-echo",
        messages=[{"role": "user", "content": as_message("pay.txt", text)}],
        stream=True,
    )
    answer = "".join(c.choices[0].delta.content or "" for c in stream if c.choices)
    assert IBAN in answer and "[IBAN_1]" not in answer


def test_a_confidential_paragraph_in_a_file_stays_inside(client: OpenAI) -> None:  # noqa: F811
    text = _extract("notes.docx", docx_bytes("Meeting notes", SALARY_LINE))
    try:
        decision, answer = _send(client, as_message("notes.docx", text))
    except PermissionDeniedError:
        decision, answer = "block", ""
    assert decision in ("local", "block")
    if decision == "local":
        assert answer.strip()


def test_a_stamped_file_is_blocked_with_its_name(client: OpenAI) -> None:  # noqa: F811
    text = _extract("q4.pdf", pdf_with_text("Q4 report. Classification: RESTRICTED."))
    try:
        decision, _ = _send(client, as_message("q4.pdf", text))
    except PermissionDeniedError as err:
        assert "q4.pdf" in str(err.body)
        return
    assert decision == "local"


def test_a_clean_file_is_allowed(client: OpenAI) -> None:  # noqa: F811
    text = _extract("lunch.pdf", pdf_with_text("Team lunch on Friday at noon"))
    decision, answer = _send(client, as_message("lunch.pdf", text))
    assert decision == "allow" and "safety check" in answer
