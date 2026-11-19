"""Classification stamps on a file ("RESTRICTED", "ΕΜΠΙΣΤΕΥΤΙΚΟ", "Internal use only").

A company marks its confidential files on the page. A file that carries such a stamp must not go
to an AI tool outside the company, whether or not it was registered with the gate first. The check
is for stamps only; the document matcher still handles registered files that were reworded.
"""

import re
import unicodedata

# Compared after accents are removed and case is folded, so "ΕΜΠΙΣΤΕΥΤΙΚΌ" and "εμπιστευτικο" match.
_STAMPS: list[tuple[str, re.Pattern[str]]] = [
    ("RESTRICTED", re.compile(r"\brestricted\b")),
    ("STRICTLY CONFIDENTIAL", re.compile(r"\bstrictly\s+confidential\b")),
    (
        "CONFIDENTIAL",
        re.compile(r"\b(?:classification|classified|marking)\W{0,3}\s*confidential\b"),
    ),
    (
        "CONFIDENTIAL",
        re.compile(r"\bconfidential\s*[-–—:|]\s*(?:do not|not for|internal|restricted)"),
    ),
    ("INTERNAL USE ONLY", re.compile(r"\binternal\s+use\s+only\b")),
    ("ΕΜΠΙΣΤΕΥΤΙΚΟ", re.compile(r"\bεμπιστευτικ[οαη]\w*")),
    ("ΑΠΟΡΡΗΤΟ", re.compile(r"\bαπορρητ[οα]\w*")),
    ("ΕΣΩΤΕΡΙΚΗ ΧΡΗΣΗ", re.compile(r"μονο\s+για\s+εσωτερικη\s+χρηση")),
]


def _fold(text: str) -> str:
    plain = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return plain.casefold()


def find_marking(text: str) -> str | None:
    """The first classification stamp found in the text, or None."""
    folded = _fold(text)
    for label, pattern in _STAMPS:
        if pattern.search(folded):
            return label
    return None
