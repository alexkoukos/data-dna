"""Turn an uploaded file into text: PDF (with OCR for scanned pages), DOCX, images, plain text.

What a file is comes from its content, not its name, for every format that has a signature: a PDF
named `notes.txt` is read as a PDF, so a wrong name cannot hide what a model would read.
"""

import io
import zipfile
from typing import Literal

from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader

from brain.documents import ocr

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
MAX_OCR_PAGES = 10  # scanned pages read with OCR per file: about 1 to 3 seconds each on a CPU
MIN_PAGE_TEXT = 20  # a page with less text than this is treated as a scan
MAX_TEXT_CHARS = 200_000
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_GRID_SPAN = 1000
MAX_DOCX_PARTS = 50_000
TEXT_SUFFIXES = (".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".ts", ".java")

Kind = Literal["pdf", "docx", "image", "text"]


class ExtractError(ValueError):
    """The file cannot be read. The message says what to do and is safe to show."""


def sniff(data: bytes) -> Kind | None:
    """What the bytes really are, from their content. None for a binary format we cannot read."""
    if data[:1024].lstrip(b"\x00\t\n\r\f ").startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = set(z.namelist())
        except zipfile.BadZipFile:
            return None
        return "docx" if "word/document.xml" in names else None
    if data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"BM")) or (
        data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    ):
        return "image"
    if b"\x00" in data:
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return "text"


def _claimed(name: str) -> Kind | None:
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".docx"):
        return "docx"
    if name.endswith(ocr.IMAGE_SUFFIXES):
        return "image"
    if name.endswith(TEXT_SUFFIXES):
        return "text"
    return None


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ExtractError("This file is larger than 10 MB. Split it or send the relevant part.")
    claimed = _claimed(filename.lower())
    if claimed is None:
        raise ExtractError(
            "This file type is not supported. Use PDF, DOCX, TXT, Markdown or an image (PNG, JPG)."
        )
    actual = sniff(data)
    # A PDF, Word file or image is read as what it is, whatever its name says. Text-like content
    # under a binary name is read as that format, so a damaged file says it is damaged.
    kind = actual if actual in ("pdf", "docx", "image") else claimed
    if kind == "text" and actual is None:
        raise ExtractError(
            "This file is named as text but holds data that is not text. Check that it is the "
            "right file, or save it again as plain text."
        )
    if kind == "pdf":
        return _pdf(data)
    if kind == "docx":
        return _docx(data)
    if kind == "image":
        return _image(data)
    return _capped(data.decode("utf-8", errors="replace"))


def _capped(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS:
        raise ExtractError(
            f"This file has more than {MAX_TEXT_CHARS:,} characters of text. "
            "Split it or send the relevant part."
        )
    return text


def _pdf(data: bytes) -> str:
    return _capped(_pdf_text(data))


def _pdf_text(data: bytes, max_pages: int = MAX_PAGES) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractError("This PDF is password protected. Remove the password and try again.")
        texts = [(p.extract_text() or "") for p in reader.pages[:max_pages]]
    except ExtractError:
        raise
    except Exception as err:  # pypdf raises many unrelated types on damaged files
        raise ExtractError(
            "This PDF could not be read. Check that the file is not damaged."
        ) from err
    scanned = [i for i, t in enumerate(texts) if len(t.strip()) < MIN_PAGE_TEXT]
    if scanned and ocr.available():
        for i in scanned[:MAX_OCR_PAGES]:
            texts[i] = "\n".join(filter(None, [texts[i], _page_ocr(reader, i)]))
    text = "\n".join(texts)
    if not text.strip():
        raise ExtractError(
            "No text was found in this PDF, even with OCR. Check that the scan is readable, or "
            "copy the text into the message."
            if ocr.available()
            else "No text was found in this PDF. It may be a scan; this install cannot read "
            "images. Copy the text into the message, or save the PDF again with selectable text."
        )
    return text


def _page_ocr(reader: PdfReader, index: int) -> str:
    """The text in the images of one scanned page."""
    try:
        images = reader.pages[index].images
        return "\n".join(ocr.pil_text(img.image) for img in images if img.image is not None)
    except ocr.OcrUnavailable:
        return ""
    except ValueError as err:
        raise ExtractError(str(err)) from err
    except Exception as err:  # pypdf and Pillow raise many unrelated types on damaged images
        raise ExtractError(
            "A scanned page in this PDF could not be read. Check that the file is not damaged."
        ) from err


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
    return _capped(_docx_text(data))


def _docx_text(data: bytes) -> str:
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
        raise ExtractError(
            "No text was found in this document. Check that it is the right file, or paste the "
            "text into the message."
        )
    return text


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
