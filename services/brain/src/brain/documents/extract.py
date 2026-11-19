"""Turn an uploaded file into text (PRD 9.1): PDF, DOCX, and plain text or Markdown."""

import io
import zipfile

from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader

from brain.documents import ocr

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
MAX_TEXT_CHARS = 200_000
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_GRID_SPAN = 1000
MAX_DOCX_PARTS = 50_000


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
    if name.endswith(ocr.IMAGE_SUFFIXES):
        return _image(data)
    if name.endswith((".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".ts", ".java")):
        return _capped(data.decode("utf-8", errors="replace"))
    raise ExtractError(
        "This file type is not supported. Use PDF, DOCX, TXT, Markdown or an image (PNG, JPG)."
    )


def _capped(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS:
        raise ExtractError(
            f"This file has more than {MAX_TEXT_CHARS:,} characters of text. "
            "Split it or send the relevant part."
        )
    return text


def _pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractError("This PDF is password protected. Remove the password and try again.")
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((p.extract_text() or "") for p in pages)
    except ExtractError:
        raise
    except Exception as err:  # pypdf raises many unrelated types on damaged files
        raise ExtractError(
            "This PDF could not be read. Check that the file is not damaged."
        ) from err
    if not text.strip():
        raise ExtractError(
            "No text was found in this PDF. It may be a scan; this version cannot read images."
        )
    return _capped(text)


def _check_zip(data: bytes) -> None:
    too_big = ExtractError(
        "This DOCX unpacks to too much data. Save it again or send the relevant part."
    )
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
    except zipfile.BadZipFile as err:
        raise ExtractError(
            "This DOCX could not be read. Check that the file is not damaged."
        ) from err
    if sum(i.file_size for i in infos) > MAX_UNPACKED_BYTES:
        raise too_big
    if any(i.file_size / max(i.compress_size, 1) > MAX_COMPRESSION_RATIO for i in infos):
        raise too_big


def _docx(data: bytes) -> str:
    _check_zip(data)
    try:
        doc = Document(io.BytesIO(data))
        for span in doc.element.body.iter(qn("w:gridSpan")):
            if int(span.get(qn("w:val"), "1")) > MAX_GRID_SPAN:
                raise ExtractError(
                    "This DOCX has a table that is too wide to read. "
                    "Save it again or send the relevant part."
                )
        parts: list[str] = []
        for p in doc.paragraphs:
            parts.append(p.text)
        for table in doc.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
                if len(parts) > MAX_DOCX_PARTS:
                    break
        if len(parts) > MAX_DOCX_PARTS:
            raise ExtractError(
                "This DOCX has too many paragraphs or cells. Send the relevant part."
            )
    except ExtractError:
        raise
    except Exception as err:  # python-docx raises several unrelated types on bad files
        raise ExtractError(
            "This DOCX could not be read. Check that the file is not damaged."
        ) from err
    text = "\n".join(parts)
    if not text.strip():
        raise ExtractError("No text was found in this document.")
    return _capped(text)


def _image(data: bytes) -> str:
    try:
        text = ocr.image_text(data)
    except ocr.OcrUnavailable as err:
        raise ExtractError(str(err)) from err
    except ValueError as err:
        raise ExtractError(str(err)) from err
    if not text.strip():
        raise ExtractError("No text was found in this image.")
    return text
