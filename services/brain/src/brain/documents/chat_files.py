"""Files attached in Company Chat: check what a file really is, then turn it into text.

The text goes back to the chat, which sends it inside the message. The gateway checks it like any
typed text before a model sees it, so a file can never reach a model unchecked. Nothing here is
stored or logged: the bytes and the text live only for the length of the request.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from typing import Literal

from brain.documents.extract import ExtractError, _docx_text, _pdf_text

Kind = Literal["pdf", "docx", "text"]

# What the composer accepts, and which kind of content each name must hold.
SUFFIX_KIND: dict[str, Kind] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "text",
    ".md": "text",
    ".csv": "text",
}
# A chat file is shorter than a registered document: fewer pages keeps a huge PDF cheap.
MAX_CHAT_PAGES = 50
UNSUPPORTED = (
    "This file type is not supported here. Attach a PDF, Word (.docx), text, Markdown or CSV file."
)


@dataclass(frozen=True)
class ChatFile:
    filename: str
    kind: Kind
    text: str
    chars: int  # characters in the whole file
    truncated: bool  # only the first `max_chars` are in `text`


def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot > 0 else ""


def sniff(data: bytes) -> Kind | None:
    """What the bytes really are, from their content and not their name."""
    if data[:1024].lstrip(b"\x00\t\n\r\f ").startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = set(z.namelist())
        except zipfile.BadZipFile:
            return None
        return "docx" if "word/document.xml" in names else None
    if b"\x00" in data:
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return "text"


def read_chat_file(filename: str, data: bytes, *, max_bytes: int, max_chars: int) -> ChatFile:
    """Check and read one attached file. Raises ExtractError with a message safe to show."""
    claimed = SUFFIX_KIND.get(_suffix(filename))
    if claimed is None:
        raise ExtractError(UNSUPPORTED)
    if len(data) > max_bytes:
        raise ExtractError(
            f"This file is larger than {max_bytes // (1024 * 1024)} MB. "
            "Split it or attach only the part you need."
        )
    if not data:
        raise ExtractError("This file is empty. Check that it is the right file.")
    actual = sniff(data)
    if actual != claimed:
        raise ExtractError(
            f"This file is named .{_suffix(filename)[1:]} but its content is not "
            f"{'a ' + claimed.upper() if claimed != 'text' else 'plain text'}. "
            "It may be damaged or renamed. Save it again in the right format and attach it."
        )
    if claimed == "pdf":
        text = _pdf_text(data, max_pages=MAX_CHAT_PAGES)
    elif claimed == "docx":
        text = _docx_text(data)
    else:
        text = data.decode("utf-8").removeprefix("﻿")
        if not text.strip():
            raise ExtractError("This file has no text in it. Check that it is the right file.")
    return ChatFile(
        filename=filename,
        kind=claimed,
        text=text[:max_chars],
        chars=len(text),
        truncated=len(text) > max_chars,
    )


# How the chat puts a file inside a message. The brain reads the name back to give a stamped file
# a reason with its name. Typing the same header by hand only makes the check stricter.
_FILE_HEADER = re.compile(r"^\[File: ([^\]\n]{1,200})\]$", re.M)


def file_blocks(text: str) -> list[tuple[str, str]]:
    """(name, body) for every file the chat placed in `text`. Linear in the length of the text."""
    heads = list(_FILE_HEADER.finditer(text))
    out: list[tuple[str, str]] = []
    for n, h in enumerate(heads):
        end = heads[n + 1].start() if n + 1 < len(heads) else len(text)
        body = text[h.end() : end].removeprefix("\n")
        close = body.find(f"\n[End of file: {h.group(1)}]")
        out.append((h.group(1), body if close < 0 else body[:close]))
    return out
