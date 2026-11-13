"""MinHash signatures (128 permutations, 5-word shingles) for near-copy detection."""

import unicodedata

import numpy as np
from datasketch import MinHash

from brain.documents.chunking import words

PERMS = 128
SHINGLE = 5


def _norm(word: str) -> str:
    """Lower case, no accents, no punctuation at the edges, so formatting changes do not matter."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    return base.strip(".,;:!?\"'()[]{}«»“”‘’—–-").replace("ς", "σ")


def signature(text: str) -> bytes:
    ws = [w for w in (_norm(x) for x in words(text)) if w]
    m = MinHash(num_perm=PERMS, seed=1)
    if len(ws) < SHINGLE:
        shingles = [" ".join(ws)] if ws else []
    else:
        shingles = [" ".join(ws[i : i + SHINGLE]) for i in range(len(ws) - SHINGLE + 1)]
    for s in shingles:
        m.update(s.encode("utf-8"))
    return bytes(m.hashvalues.astype(np.uint64).tobytes())


def jaccard(a: bytes, b: bytes) -> float:
    """Estimated Jaccard similarity of two signatures."""
    x = np.frombuffer(a, dtype=np.uint64)
    y = np.frombuffer(b, dtype=np.uint64)
    return float(np.mean(x == y))
