"""Split text into overlapping word windows with 50% overlap (PRD 9.3).

The PRD said about 60 words. On the paraphrase sets (tests/data/paraphrases.json and
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
