import base64
import io

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

import brain.main as main
from brain.documents.extract import ExtractError, extract_text

IBAN = "GR1601101250000000012300695"


def docx_bytes(*paragraphs: str, table: list[list[str]] | None = None) -> bytes:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table:
        t = doc.add_table(rows=len(table), cols=len(table[0]))
        for i, row in enumerate(table):
            for j, cell in enumerate(row):
                t.cell(i, j).text = cell
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def pdf_with_text(text: str) -> bytes:
    """A one-page PDF that really contains text (built by hand, no extra library)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return bytes(out)


def test_docx_text_and_tables_are_read() -> None:
    data = docx_bytes("First paragraph", "Second", table=[["cell A", "cell B"]])
    text = extract_text("memo.DOCX", data)
    assert "First paragraph" in text and "cell B" in text


def test_pdf_text_is_read() -> None:
    assert "Quarterly budget" in extract_text("a.pdf", pdf_with_text("Quarterly budget"))


def test_plain_text_and_markdown() -> None:
    assert extract_text("n.md", "héllo".encode()) == "héllo"


@pytest.mark.parametrize(
    ("name", "data", "fragment"),
    [
        ("a.exe", b"MZ", "not supported"),
        ("a.pdf", b"not a pdf", "could not be read"),
        ("a.docx", b"not a docx", "could not be read"),
        ("a.pdf", b"x" * (10 * 1024 * 1024 + 1), "larger than 10 MB"),
    ],
)
def test_bad_files_get_a_plain_message(name: str, data: bytes, fragment: str) -> None:
    with pytest.raises(ExtractError, match=fragment):
        extract_text(name, data)


def test_a_pdf_without_text_says_it_may_be_a_scan() -> None:
    w = PdfWriter()
    w.add_blank_page(612, 792)
    buf = io.BytesIO()
    w.write(buf)
    with pytest.raises(ExtractError, match="scan"):
        extract_text("scan.pdf", buf.getvalue())


def _inspect(client: TestClient, content: str, name: str, data: bytes) -> dict:  # type: ignore[type-arg]
    return client.post(
        "/v1/inspect",
        json={
            "user_id": "u-x",
            "team": "Finance",
            "model": "m",
            "messages": [{"role": "user", "content": content}],
            "attachments": [{"filename": name, "content_base64": base64.b64encode(data).decode()}],
        },
    ).json()


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def test_an_iban_inside_an_attached_docx_is_found_and_asks_first(client: TestClient) -> None:
    r = _inspect(client, "Summarise this file", "pay.docx", docx_bytes(f"Pay to {IBAN} today"))
    assert r["decision"] == "warn"
    assert any(f["entity"] == "IBAN" for f in r["findings"])
    assert any("attached file" in reason for reason in r["reasons"])


def test_a_clean_attachment_is_allowed(client: TestClient) -> None:
    r = _inspect(client, "Summarise this", "notes.pdf", pdf_with_text("Team lunch on Friday"))
    assert r["decision"] == "allow"


def test_an_unreadable_attachment_is_a_422_that_names_the_file(client: TestClient) -> None:
    r = client.post(
        "/v1/inspect",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "attachments": [{"filename": "a.exe", "content_base64": "TVo="}],
        },
    )
    assert r.status_code == 422 and r.json()["detail"].startswith("a.exe:")
    bad64 = client.post(
        "/v1/inspect",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "attachments": [{"filename": "a.txt", "content_base64": "***"}],
        },
    )
    assert bad64.status_code == 422 and "could not be decoded" in bad64.json()["detail"]


def test_a_file_can_be_registered_instead_of_pasted_text(client: TestClient) -> None:
    r = client.post(
        "/v1/documents",
        data={"title": "Upload", "sensitivity": "internal"},
        files={"file": ("plan.txt", b"alpha beta gamma delta " * 12, "text/plain")},
    )
    # No database in this fixture: the file was read, then the missing database was reported.
    assert r.status_code == 503
    bad = client.post(
        "/v1/documents",
        data={"title": "Upload", "sensitivity": "internal"},
        files={"file": ("tool.exe", b"MZ", "application/octet-stream")},
    )
    assert bad.status_code in (422, 503)
