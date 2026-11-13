"""Turn an uploaded file into text (PRD 9.1): PDF, DOCX, and plain text or Markdown."""

import io

from docx import Document
from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200


class ExtractError(ValueError):
    """The file cannot be read. The message says what to do and is safe to show."""


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ExtractError("This file is larger than 10 MB. Split it or send the relevant part.")
    name = filename.lower()
    if name.endswith(".pdf"):
        return _pdf(data)
    if name.endswith(".docx"):
        return _docx(data)
    if name.endswith((".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".ts", ".java")):
        return data.decode("utf-8", errors="replace")
    raise ExtractError("This file type is not supported. Use PDF, DOCX, TXT or Markdown.")


def _pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractError("This PDF is password protected. Remove the password and try again.")
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((p.extract_text() or "") for p in pages)
    except ExtractError:
        raise
    except (PyPdfError, ValueError, KeyError, OSError) as err:
        raise ExtractError(
            "This PDF could not be read. Check that the file is not damaged."
        ) from err
    if not text.strip():
        raise ExtractError(
            "No text was found in this PDF. It may be a scan; this version cannot read images."
        )
    return text


def _docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as err:  # python-docx raises several unrelated types on bad files
        raise ExtractError(
            "This DOCX could not be read. Check that the file is not damaged."
        ) from err
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    text = "\n".join(parts)
    if not text.strip():
        raise ExtractError("No text was found in this document.")
    return text
