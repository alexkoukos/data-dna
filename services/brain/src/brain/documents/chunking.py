"""Split text into overlapping word windows with 50% overlap (PRD 9.3).

The PRD said about 60 words. On the paraphrase check (tests/data/paraphrases.json) 60-word windows
missed most rewrites of a single sentence, because a short rewrite is diluted by the rest of the
window. 20-word windows separate rewrites from same-topic questions much better.
"""

import re

CHUNK_WORDS = 20
STEP_WORDS = 10
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
