"""Files attached in Company Chat: check what a file really is, then turn it into text.

The text goes back to the chat, which sends it inside the message. The gateway checks it like any
typed text before a model sees it, so a file can never reach a model unchecked. Nothing here is
stored or logged: the bytes and the text live only for the length of the request.
"""

import re
from dataclasses import dataclass

from brain.documents import ocr
from brain.documents.extract import ExtractError, Kind, _docx_text, _image, _pdf_text, sniff

__all__ = ["SUFFIX_KIND", "ChatFile", "file_blocks", "read_chat_file", "sniff", "suffixes"]

# What the composer accepts, and which kind of content each name must hold.
SUFFIX_KIND: dict[str, Kind] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "text",
    ".md": "text",
    ".csv": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
}


def suffixes() -> list[str]:
    """The names the chat accepts. Images only when OCR is installed, so the picker never offers
    a file the server would refuse."""
    return sorted(k for k, v in SUFFIX_KIND.items() if v != "image" or ocr.available())


# A chat file is shorter than a registered document: fewer pages keeps a huge PDF cheap.
MAX_CHAT_PAGES = 50
UNSUPPORTED = (
    "This file type is not supported here. Attach a PDF, Word (.docx), text, Markdown, CSV or "
    "image (PNG, JPG) file."
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


def read_chat_file(filename: str, data: bytes, *, max_bytes: int, max_chars: int) -> ChatFile:
    """Check and read one attached file. Raises ExtractError with a message safe to show."""
    claimed = SUFFIX_KIND.get(_suffix(filename))
    if claimed is None or _suffix(filename) not in suffixes():
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
        what = {"text": "plain text", "image": "an image"}.get(claimed, f"a {claimed.upper()}")
        raise ExtractError(
            f"This file is named .{_suffix(filename)[1:]} but its content is not {what}. "
            "It may be damaged or renamed. Save it again in the right format and attach it."
        )
    if claimed == "pdf":
        text = _pdf_text(data, max_pages=MAX_CHAT_PAGES)
    elif claimed == "docx":
        text = _docx_text(data)
    elif claimed == "image":
        text = _image(data)
    else:
        text = data.decode("utf-8").removeprefix("﻿")
        if not text.strip():
            raise ExtractError("This file has no text in it. Check that it is the right file.")
    from brain.injection.directives import LABEL, directive_sentences

    orders = directive_sentences(text)  # read in full, also past the cut
    return ChatFile(
        filename=filename,
        kind=claimed,
        text=text[:max_chars] + (f"\n{LABEL}\n" + "\n".join(orders) if orders else ""),
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
        # The last closing line, not the first: a file can hold a fake "[End of file: ...]" to
        # push a stamp or an instruction outside its own block.
        close = body.rfind(f"\n[End of file: {h.group(1)}]")
        out.append((h.group(1), body if close < 0 else body[:close]))
    return out
