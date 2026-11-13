"""Normalise input before any check, and record evasion signals."""

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass, field

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")
_SPACED_DIGITS = re.compile(r"(?<![\w])(?:\d[ .\-/]?){8,30}\d(?![\w])")
# An identifier typed one character at a time: "G R 1 6 0 1 ..." (letters and digits).
_SPACED_CHARS = re.compile(r"(?<![\w])(?:[A-Za-z0-9][ .\-/]){11,}[A-Za-z0-9](?![\w])")
_B64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])")


@dataclass
class Normalised:
    text: str
    extra_views: list[str] = field(default_factory=list)
    evasion_signals: list[str] = field(default_factory=list)


def normalise(raw: str) -> Normalised:
    signals: list[str] = []
    text = unicodedata.normalize("NFKC", raw)
    if _INVISIBLE.search(text):
        signals.append("invisible_characters")
        text = _INVISIBLE.sub("", text)

    views: list[str] = []
    for m in _SPACED_DIGITS.finditer(text):
        chunk = m.group(0)
        if re.search(r"[ .\-/]", chunk):
            views.append(re.sub(r"[ .\-/]", "", chunk))
            signals.append("spaced_digits")

    for m in _SPACED_CHARS.finditer(text):
        views.append(re.sub(r"[ .\-/]", "", m.group(0)))
        signals.append("spaced_characters")

    for m in _B64.finditer(text):
        decoded = _try_b64(m.group(0))
        if decoded:
            views.append(decoded)
            signals.append("base64")

    return Normalised(text=text, extra_views=views, evasion_signals=sorted(set(signals)))


def _try_b64(token: str) -> str | None:
    try:
        data = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
        out = data.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    printable = sum(ch.isprintable() for ch in out) / max(len(out), 1)
    return out if printable > 0.9 and len(out) >= 6 else None
