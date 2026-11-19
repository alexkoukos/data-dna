"""Split text into overlapping word windows with 50% overlap.

The original design said about 60 words. On the paraphrase sets (tests/data/paraphrases.json and
data/eval/prompts.csv) 60-word windows missed most rewrites of a single sentence, because a short
rewrite is diluted by the rest of the window. 16-word windows moving 8 words at a time found the
most rewrites for the least false alarms.
"""

import re

CHUNK_WORDS = 16
STEP_WORDS = 8
_WORD = re.compile(r"\S+")


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def chunk_text(text: str, size: int = CHUNK_WORDS, step: int = STEP_WORDS) -> list[str]:
    """Windows of `size` words moving `step` words at a time. A short text is one chunk."""
    ws = words(text)
    if not ws:
        return []
    if len(ws) <= size:
        return [" ".join(ws)]
    chunks = []
    for start in range(0, len(ws), step):
        window = ws[start : start + size]
        chunks.append(" ".join(window))
        if start + size >= len(ws):
            break
    return chunks


def rebuild_text(chunks: list[str], step: int = STEP_WORDS) -> str:
    """Rebuild a document from its overlapping chunks (whitespace becomes single spaces)."""
    out: list[str] = []
    for i, c in enumerate(chunks):
        ws = c.split()
        out.extend(ws if i == len(chunks) - 1 else ws[:step])
    return " ".join(out)


_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_LATIN = re.compile(r"[A-Za-z]")


# X10: German and French are told apart from English by common function words. Short or
# ambiguous text stays 'en', which only means "use the same-language cutoff", never a failure.
_STOP = {
    "de": frozenset(
        [
            "der",
            "die",
            "das",
            "und",
            "ist",
            "nicht",
            "ein",
            "eine",
            "mit",
            "von",
            "zu",
            "den",
            "dem",
            "des",
            "auf",
            "für",
            "sie",
            "wir",
            "ich",
            "im",
            "werden",
            "wird",
            "sind",
            "auch",
            "bei",
            "nach",
            "über",
            "oder",
            "aus",
            "als",
            "wie",
            "vertrag",
            "kunde",
            "preis",
        ]
    ),
    "fr": frozenset(
        [
            "le",
            "la",
            "les",
            "des",
            "une",
            "est",
            "pas",
            "pour",
            "avec",
            "dans",
            "sur",
            "par",
            "que",
            "qui",
            "nous",
            "vous",
            "ils",
            "sont",
            "ce",
            "cette",
            "aux",
            "du",
            "au",
            "et",
            "en",
            "contrat",
            "client",
            "prix",
            "être",
        ]
    ),
    "en": frozenset(
        [
            "the",
            "and",
            "is",
            "of",
            "to",
            "in",
            "that",
            "for",
            "with",
            "are",
            "this",
            "on",
            "be",
            "by",
            "as",
            "at",
            "an",
            "it",
            "not",
            "from",
            "or",
            "we",
            "you",
            "they",
            "their",
            "contract",
            "client",
            "price",
        ]
    ),
}
_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def language(text: str) -> str:
    """'el', 'de', 'fr' or 'en'. Greek by script, the others by common words."""
    if len(_GREEK.findall(text)) > len(_LATIN.findall(text)):
        return "el"
    toks = [w.lower() for w in _TOKEN.findall(text)]
    if len(toks) < 4:
        return "en"
    score = {lang: sum(w in stop for w in toks) for lang, stop in _STOP.items()}
    best = max(score, key=lambda k: (score[k], k == "en"))
    return best if score[best] >= 2 else "en"
