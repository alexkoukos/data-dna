"""DNA marks (PRD 12): small decoy details that differ per recipient, so a leak names its copy.

Pure functions. A mark sits at a sentence of the document and has 4 variants (a project
codename, an internal reference, or an example name). Each copy takes one variant per mark.
Nothing in the original text is ever changed: a mark only adds a short parenthetical before a
sentence's final punctuation, so dates, amounts, names and legal terms stay as they were.
"""

import hashlib
import math
import random
import re
import unicodedata
from dataclasses import dataclass

VARIANTS = 4
MIN_MARKS, MAX_MARKS = 6, 8

_CODENAMES = [
    "Aurora",
    "Borealis",
    "Cirrus",
    "Dahlia",
    "Ember",
    "Fjord",
    "Garnet",
    "Halcyon",
    "Iris",
    "Juniper",
    "Kestrel",
    "Lumen",
    "Meridian",
    "Nimbus",
    "Orchid",
    "Pinnacle",
    "Quartz",
    "Rowan",
    "Solstice",
    "Tundra",
    "Umber",
    "Vesper",
    "Willow",
    "Zephyr",
]
_SURNAMES = [
    "Kallergi",
    "Vasiliadis",
    "Nikolaidou",
    "Petrakis",
    "Stavrou",
    "Mavridis",
    "Oikonomou",
    "Lazarou",
    "Fotiadis",
    "Karamanli",
    "Dimitriou",
    "Anagnostou",
    "Papazoglou",
    "Siskos",
    "Triantafyllou",
    "Zografos",
]
_TEMPLATES = [
    "internal codename {v}",
    "ref. {v}",
    "as agreed with {v}",
]
_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+")


@dataclass(frozen=True)
class Mark:
    position: int  # index of the sentence the mark is added to
    variants: list[str]

    def phrase(self, variant: int) -> str:
        return _TEMPLATES[self.position % len(_TEMPLATES)].format(v=self.variants[variant])


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_END.split(text.strip()) if s.strip()]


def propose_marks(text: str, count: int = 7, seed: int = 1) -> list[Mark]:
    """6 to 8 marks spread evenly through the text. Raises ValueError if the text is too short."""
    count = max(MIN_MARKS, min(MAX_MARKS, count))
    sents = sentences(text)
    if len(sents) < count:
        raise ValueError(
            f"This document has {len(sents)} sentences. At least {count} are needed to add marks."
        )
    rng = random.Random(seed)
    positions = sorted({round((i + 0.5) * len(sents) / count) for i in range(count)})
    positions = [min(p, len(sents) - 1) for p in positions]
    used: set[str] = set()
    marks: list[Mark] = []
    for pos in positions:
        kind = pos % len(_TEMPLATES)
        options: list[str]
        if kind == 0:
            options = list(_CODENAMES)
        elif kind == 1:
            options = [f"INT-{rng.randint(1000, 9999)}-{rng.choice('ABCDEFGH')}" for _ in range(40)]
        else:
            options = list(_SURNAMES)
        rng.shuffle(options)
        chosen = [v for v in options if v not in used and _fold(v) not in _fold(text)][:VARIANTS]
        if len(chosen) < VARIANTS:
            raise ValueError("Could not find decoy details that are not already in the document.")
        used.update(chosen)
        marks.append(Mark(pos, chosen))
    return marks


def render(text: str, marks: list[Mark], vector: list[int]) -> str:
    """The text with this copy's variant added at every mark."""
    sents = sentences(text)
    by_pos = {m.position: (m, v) for m, v in zip(marks, vector, strict=True)}
    out = []
    for i, s in enumerate(sents):
        if i in by_pos:
            m, v = by_pos[i]
            end = s[-1] if s[-1] in ".!?;" else ""
            body = s[:-1] if end else s
            s = f"{body} ({m.phrase(v)}){end}"
        out.append(s)
    return " ".join(out)


def hamming(a: list[int], b: list[int]) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))


def assign_vectors(
    existing: list[list[int]], count: int, marks: int, seed: int = 7
) -> list[list[int]]:
    """New vectors that differ from every other copy in at least half the marks."""
    need = math.ceil(marks / 2)
    rng = random.Random(seed + len(existing))
    chosen: list[list[int]] = []
    attempts = 0
    while len(chosen) < count:
        attempts += 1
        if attempts > 20000:
            raise ValueError("No more copies can be told apart. Ask for fewer recipients.")
        v = [rng.randrange(VARIANTS) for _ in range(marks)]
        if all(hamming(v, o) >= need for o in existing + chosen):
            chosen.append(v)
    return chosen


def copy_code(document_id: int, vector: list[int]) -> str:
    digest = hashlib.sha256(f"{document_id}:{vector}".encode()).hexdigest()
    return digest[:4].upper()


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@dataclass(frozen=True)
class Attribution:
    copy_code: str
    marks_found: int
    marks_matching: int
    odds: int  # "1 in odds" chance that this many marks agree by coincidence
    runner_up: str | None = None  # a second copy, when marks disagree (collusion)

    @property
    def sentence(self) -> str:
        who = (
            f"all {self.marks_found} match copy {self.copy_code}"
            if self.marks_found == self.marks_matching
            else (f"{self.marks_matching} of {self.marks_found} match copy {self.copy_code}")
        )
        text = f"{self.marks_found} marks found, {who}, 1 in {self.odds:,} chance of coincidence"
        if self.runner_up:
            text += f". The rest match copy {self.runner_up}: the text may be a mix of two copies"
        return text


def attribute(text: str, marks: list[Mark], copies: dict[str, list[int]]) -> Attribution | None:
    """Which issued copy does this text come from? None if no mark variant is present."""
    haystack = _fold(text)
    found: dict[int, int] = {}  # mark index -> variant index seen
    for i, m in enumerate(marks):
        for v, token in enumerate(m.variants):
            if _fold(token) in haystack:
                found[i] = v
                break
    if not found:
        return None
    scores = {code: sum(1 for i, v in found.items() if vec[i] == v) for code, vec in copies.items()}
    if not scores or max(scores.values()) == 0:
        return None
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best, best_n = ranked[0]
    runner = ranked[1][0] if len(ranked) > 1 and ranked[1][1] > 0 and best_n < len(found) else None
    return Attribution(best, len(found), best_n, VARIANTS**best_n, runner)
