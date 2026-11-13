"""Greek names typed in Latin letters, "greeklish" (X5).

The English language model misses a lower-case "giorgos papadopoulos", and the Greek one does not
read Latin letters. Greek surnames follow a few endings (-opoulos, -idis, -akis, -oglou) and a list
of very common ones, so a plain word match is reliable and has no model cost. It only runs on text
written in Latin letters, because Greek-script names are the Greek model's job.
"""

import re

from brain.detection.patterns import Finding

_SUFFIXES = (
    "opoulos",
    "opoulou",
    "poulos",
    "poulou",
    "idis",
    "idou",
    "iadis",
    "iadou",
    "akis",
    "akou",
    "akos",
    "oglou",
    "ianos",
    "ianou",
)


def _words(block: str) -> list[str]:
    return block.split()


_COMMON = _words(
    """
    georgiou ioannou nikolaou dimitriou christou petrou pavlou antoniou konstantinou vasileiou
    papanikolaou papadimitriou karagiannis alexiou stavrou theodorou markou andreou kyriakou
    papadakis oikonomou economou voulgaris mavridis karras
    """
)
_FIRST = _words(
    """
    giorgos giannis yiannis nikos dimitris kostas konstantinos maria eleni katerina sofia
    christos panagiotis stelios vasilis vasilios alexandros thanasis manolis michalis petros
    pavlos stavros antonis lefteris dimos spyros thodoris ioanna anna georgia despina evangelia
    """
)
_SUFFIX_RE = "|".join(_SUFFIXES)
_SURNAME = re.compile(rf"\b(?:[a-z]{{2,}}(?:{_SUFFIX_RE})|{'|'.join(_COMMON)})\b", re.IGNORECASE)
_FIRST_RE = re.compile(rf"\b(?:{'|'.join(_FIRST)})\b", re.IGNORECASE)
_LATIN = re.compile(r"[A-Za-z]")
_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")


def find_greeklish_names(text: str) -> list[Finding]:
    """A Greek surname in Latin letters, with the first name before it when there is one."""
    if not _LATIN.search(text):
        return []
    found: list[Finding] = []
    for m in _SURNAME.finditer(text):
        if _GREEK.search(text[max(m.start() - 1, 0) : m.end() + 1]):
            continue  # part of a word that is partly Greek: not a greeklish name
        start = m.start()
        before = text[:start].rstrip(" ")
        prev = _FIRST_RE.search(before[-16:]) if before else None
        if prev and prev.end() == len(before[-16:]):
            start = len(before) - len(before[-16:]) + prev.start()
        found.append(Finding("PERSON", "person_email_phone", start, m.end(), text[start : m.end()]))
    return found
