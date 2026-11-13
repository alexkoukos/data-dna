"""Normalise input before any check, and record evasion signals."""

import base64
import binascii
import html
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field

from brain.detection.confusables import ascii_digits, digit_lookalike_view, fold_mixed_tokens

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")
_SPACED_DIGITS = re.compile(r"(?<![\w])(?:\d[ .\-/\t\r\n]?){8,30}\d(?![\w])")
# An identifier typed one character at a time: "G R 1 6 0 1 ..." (letters and digits).
_SPACED_CHARS = re.compile(r"(?<![\w])(?:[A-Za-z0-9][ .\-/\t\r\n]){11,}[A-Za-z0-9](?![\w])")
# An identifier typed in short groups: "GR 06 01 10 12 ..." (groups of one or two characters).
_SPACED_GROUPS = re.compile(
    r"(?<![\w])(?:[A-Za-z0-9]{1,4}[ .\-/\t\r\n]{1,3}){5,}[A-Za-z0-9]{1,4}(?![\w])"
)
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

    # Digits from other scripts and look-alike letters (X5). Both keep the length, so a finding
    # is masked in the original place.
    ascii_text = ascii_digits(text)
    if ascii_text != text:
        signals.append("unicode_digits")
        text = ascii_text
    text, disguised = fold_mixed_tokens(text)
    if disguised:
        signals.append("mixed_script")

    views: list[str] = []
    lookalike = digit_lookalike_view(text)
    if lookalike:
        views.append(lookalike)
        signals.append("digit_lookalikes")
    for m in _SPACED_DIGITS.finditer(text):
        chunk = m.group(0)
        if re.search(r"[ .\-/\t\r\n]", chunk):
            views.append(re.sub(r"[ .\-/\t\r\n]", "", chunk))
            signals.append("spaced_digits")

    for m in _SPACED_CHARS.finditer(text):
        views.append(re.sub(r"[ .\-/\t\r\n]", "", m.group(0)))
        signals.append("spaced_characters")

    for m in _SPACED_GROUPS.finditer(text):
        joined = _identifier_run(m.group(0))
        if joined:
            views.append(joined)
            signals.append("spaced_characters")

    for hidden_text, signal in _decoded_views(text):
        views.append(hidden_text)
        signals.append(signal)

    for m in _B64.finditer(text):
        decoded = _try_b64(m.group(0))
        if decoded:
            views.append(decoded)
            signals.append("base64")

    return Normalised(text=text, extra_views=views, evasion_signals=sorted(set(signals)))


def _identifier_run(chunk: str) -> str | None:
    """Join the groups of a spaced run, minus the plain words around it ("Pay to GR92 0110 ...").
    A run of short words is not an identifier: it needs six digits, or sixteen capitals and digits
    with at least three digits."""
    groups = re.split(r"[ .\-/\t\r\n]+", chunk)

    def word(g: str) -> bool:
        return not any(c.isdigit() for c in g) and any(c.islower() for c in g)

    while groups and word(groups[0]):
        groups.pop(0)
    while groups and word(groups[-1]):
        groups.pop()
    joined = "".join(groups)
    digits = sum(c.isdigit() for c in joined)
    if digits >= 6 or (digits >= 3 and len(joined) >= 16 and joined == joined.upper()):
        return joined
    return None


_HEX = re.compile(r"(?<![0-9A-Za-z])(?:[0-9A-Fa-f]{2}){12,}(?![0-9A-Za-z])")
_PERCENT = re.compile(r"(?:%[0-9A-Fa-f]{2}){6,}")
_ENTITIES = re.compile(r"(?:&#(?:\d{2,3}|x[0-9A-Fa-f]{2});){6,}")


def _decoded_views(text: str) -> list[tuple[str, str]]:
    """Text hidden as hex, percent-encoding or HTML entities, decoded so the checks can read it."""
    out: list[tuple[str, str]] = []
    for m in _HEX.finditer(text):
        try:
            decoded = bytes.fromhex(m.group(0)).decode("ascii")
        except (ValueError, UnicodeDecodeError):
            continue
        if decoded.isprintable():
            out.append((decoded, "hex"))
    for m in _PERCENT.finditer(text):
        decoded = urllib.parse.unquote(m.group(0))
        if decoded.isprintable():
            out.append((decoded, "percent_encoding"))
    for m in _ENTITIES.finditer(text):
        decoded = html.unescape(m.group(0))
        if decoded.isprintable():
            out.append((decoded, "html_entities"))
    return out


def _try_b64(token: str) -> str | None:
    try:
        data = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
        out = data.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    printable = sum(ch.isprintable() for ch in out) / max(len(out), 1)
    return out if printable > 0.9 and len(out) >= 6 else None
