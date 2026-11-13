"""Normalise input before any check, and record evasion signals."""

import base64
import binascii
import codecs
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import unquote

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")
_SPACED_DIGITS = re.compile(r"(?<![\w])(?:\d[ .\-/]{0,2}){8,30}\d(?![\w])")
# An identifier typed one character at a time: "G R 1 6 0 1 ..." (letters and digits).
_SPACED_CHARS = re.compile(r"(?<![\w])(?:[A-Za-z0-9][ .\-/]){11,}[A-Za-z0-9](?![\w])")
# An identifier typed in short groups: "GR 06 01 10 12 ..." (groups of one or two characters).
_SPACED_GROUPS = re.compile(r"(?<![\w])(?:[A-Za-z0-9]{1,2}[ .\-/]){7,}[A-Za-z0-9]{1,3}(?![\w])")
_B64 = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])")
_HEX = re.compile(r"(?<![0-9A-Za-z])(?:[0-9A-Fa-f]{2}){12,}(?![0-9A-Za-z])")
_URL_ESCAPES = re.compile(r"(?:%[0-9A-Fa-f]{2}){6,}")
_LONG_TOKEN = re.compile(r"[A-Za-z0-9]{15,}")
_LETTER_RUN = re.compile(r"(?<!\w)(?:\w ){5,}\w(?!\w)")
_TOKEN = re.compile(r"[^\W_]+(?:[@.][^\W_]+)*", re.UNICODE)
# Letters from other alphabets that look like Latin ones (Cyrillic and Greek).
_LOOKALIKES = str.maketrans(
    "аеорсхуіјѕԁӏАВЕКМНОРСТХ"  # Cyrillic
    "οαεικνυρχΑΒΕΖΗΙΚΜΝΟΡΤΥΧ",  # Greek
    "aeopcxyijsdlABEKMHOPCTXoaeikvupxABEZHIKMNOPTYX",
)
_LEET = str.maketrans("013457@$", "oieastas")
_LATIN = re.compile(r"[A-Za-z]")
_OTHER = re.compile("[" + "".join(chr(c) for c in _LOOKALIKES) + "]")


def _fold_lookalikes(text: str) -> tuple[str, bool]:
    """Swap look-alike letters for Latin ones, but only inside words that mix alphabets."""
    changed = False

    def fix(m: re.Match[str]) -> str:
        nonlocal changed
        word = m.group(0)
        if _LATIN.search(word) and _OTHER.search(word):
            changed = True
            return word.translate(_LOOKALIKES)
        return word

    return _TOKEN.sub(fix, text), changed


def _hex_view(chunk: str) -> str | None:
    try:
        out = bytes.fromhex(chunk).decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return None
    return out if out.isprintable() and len(out) >= 6 else None


_REVERSED_IBAN = re.compile(r"^\d{10,}[A-Za-z]{2}$")


def _loose_views(text: str, signals: list[str]) -> tuple[list[str], list[str]]:
    """Other ways to read the same text.

    Returns (views for every check, views for phrase checks only). ROT13, leetspeak and spaced
    letters are only worth reading for injection phrases and rules: running the identifier
    patterns on them would flag ordinary numbers a second time.
    """
    views: list[str] = []
    phrases: list[str] = []
    for m in _HEX.finditer(text):
        decoded = _hex_view(m.group(0))
        if decoded:
            views.append(decoded)
            signals.append("hex")
    if _URL_ESCAPES.search(text):
        views.append(unquote(text))
        signals.append("url_escapes")
    for m in _LONG_TOKEN.finditer(text):
        if _REVERSED_IBAN.match(m.group(0)):
            views.append(m.group(0)[::-1])
            signals.append("reversed")
    letters = text.replace("  ", "\x00")
    if _LETTER_RUN.search(letters):
        collapsed = re.sub(r"(?<=\w) (?=\w(?!\w))", "", letters).replace("\x00", " ")
        phrases.append(collapsed)
        signals.append("spaced_letters")
    leet = text.translate(_LEET)
    if (
        sum(1 for w in text.split() if re.search(r"[A-Za-z]", w) and re.search(r"[01345@$]", w))
        >= 2
    ):
        phrases.append(leet)
        signals.append("leetspeak")
    if len(text) <= 4000:
        phrases.append(codecs.encode(text, "rot13"))
    return views, phrases


@dataclass
class Normalised:
    text: str
    extra_views: list[str] = field(default_factory=list)
    phrase_views: list[str] = field(default_factory=list)
    evasion_signals: list[str] = field(default_factory=list)


def normalise(raw: str) -> Normalised:
    signals: list[str] = []
    text = unicodedata.normalize("NFKC", raw)
    if _INVISIBLE.search(text):
        signals.append("invisible_characters")
        text = _INVISIBLE.sub("", text)

    text, folded = _fold_lookalikes(text)
    if folded:
        signals.append("mixed_alphabets")

    views: list[str] = []
    loose, phrases = _loose_views(text, signals)
    views.extend(loose)
    for m in _SPACED_DIGITS.finditer(text):
        chunk = m.group(0)
        if re.search(r"[ .\-/]", chunk):
            views.append(re.sub(r"[ .\-/]", "", chunk))
            signals.append("spaced_digits")

    for m in _SPACED_CHARS.finditer(text):
        views.append(re.sub(r"[ .\-/]", "", m.group(0)))
        signals.append("spaced_characters")

    for m in _SPACED_GROUPS.finditer(text):
        views.append(re.sub(r"[ .\-/]", "", m.group(0)))
        signals.append("spaced_characters")

    for m in _B64.finditer(text):
        decoded = _try_b64(m.group(0))
        if decoded:
            views.append(decoded)
            signals.append("base64")

    return Normalised(
        text=text,
        extra_views=views,
        phrase_views=phrases,
        evasion_signals=sorted(set(signals)),
    )


def _try_b64(token: str) -> str | None:
    try:
        data = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
        out = data.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    printable = sum(ch.isprintable() for ch in out) / max(len(out), 1)
    return out if printable > 0.9 and len(out) >= 6 else None
