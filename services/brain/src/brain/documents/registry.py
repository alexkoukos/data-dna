"""Document registry and matching (PRD 9.3).

Register: split into chunks, store a MinHash signature and an embedding per chunk. The text is kept
only when `keep_text` is on (demo mode, for the puzzle view). Match: chunk the prompt the same way;
a chunk is a copy when MinHash Jaccard >= 0.5, a paraphrase when embedding cosine >= 0.88
(tuned on tests/data/paraphrases.json).
Vectors live in Postgres (pgvector); matching runs over a small in-process cache of them.
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import numpy as np
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.db import tables as t
from brain.documents.chunking import chunk_text, language, words
from brain.documents.embeddings import Embedder
from brain.documents.fingerprint import PERMS, jaccard, signature

log = logging.getLogger(__name__)

COPY_JACCARD = 0.5
PARAPHRASE_COSINE = 0.88  # e5 scores are compressed: same-topic text sits near 0.85
# A rewrite in the other language (Greek text against an English document or the reverse) scores
# lower for true and false matches alike, so it gets its own, lower cutoff.
CROSS_LANGUAGE_COSINE = 0.86
MIN_WORDS_TO_EMBED = 10
MAX_QUERY_CHUNKS = 64  # chunks compared by MinHash (cheap)
MAX_EMBEDDED_CHUNKS = 16  # windows sent through the embedding model (about 4 ms each)

# A document can carry translations of itself (data/documents/<name>.<lang>.md). Their chunks are
# stored under the same document with index (n + 1) * TRANSLATION_BASE + position, so an English
# rewrite of a Greek document is compared with English text, at the stricter same-language cutoff.
TRANSLATION_BASE = 10_000
# A translation is a second, shorter route to the same document, so it gets a stricter cutoff:
# the highest ordinary question scored 0.882 against it, the rewrites it is there to catch 0.906
# or more (small sample, see docs/calibration.md). Re-measure before changing.
TRANSLATION_COSINE = 0.90

Kind = Literal["copy", "paraphrase"]


@dataclass(frozen=True)
class DocMatch:
    document_id: int
    title: str
    sensitivity: str
    score: float
    kind: Kind
    matched_chunks: list[int]
    total_chunks: int


@dataclass
class _Chunk:
    document_id: int
    idx: int
    sig: bytes
    vec: np.ndarray
    lang: str = "en"


class DocumentIndex:
    def __init__(
        self, engine: Engine | None, embedder: Embedder, ttl_seconds: float = 10.0
    ) -> None:
        self.engine = engine
        self._embedder = embedder
        self._ttl = ttl_seconds
        self._chunks: list[_Chunk] = []
        self._matrix = np.zeros((0, 384), dtype=np.float32)
        self._docs: dict[int, tuple[str, str]] = {}
        self._totals: dict[int, int] = {}
        self._tsizes: dict[tuple[int, int], int] = {}
        self._loaded_at = float("-inf")
        self._lock = threading.Lock()

    def invalidate(self) -> None:
        self._loaded_at = float("-inf")

    def _refresh(self) -> None:
        if time.monotonic() - self._loaded_at < self._ttl or self.engine is None:
            return
        try:
            with self.engine.connect() as conn:
                docs = {
                    r.id: (r.title, r.sensitivity)
                    for r in conn.execute(
                        sa.select(t.documents.c.id, t.documents.c.title, t.documents.c.sensitivity)
                    )
                }
                rows = conn.execute(
                    sa.select(
                        t.doc_chunks.c.document_id,
                        t.doc_chunks.c.idx,
                        t.doc_chunks.c.minhash,
                        t.doc_chunks.c.embedding,
                        t.doc_chunks.c.lang,
                    ).order_by(t.doc_chunks.c.document_id, t.doc_chunks.c.idx)
                ).all()
        except sa.exc.SQLAlchemyError:
            log.warning("Could not read the document index, keeping the last one")
            self._loaded_at = time.monotonic()
            return
        chunks = [
            _Chunk(
                r.document_id,
                r.idx,
                bytes(r.minhash),
                np.asarray(r.embedding, dtype=np.float32),
                r.lang or "en",
            )
            for r in rows
            if r.minhash is not None and r.embedding is not None
        ]
        self._docs = docs
        self._chunks = chunks
        self._matrix = (
            np.stack([c.vec for c in chunks]) if chunks else np.zeros((0, 384), dtype=np.float32)
        )
        totals: dict[int, int] = {}
        tsizes: dict[tuple[int, int], int] = {}
        for c in chunks:
            if c.idx < TRANSLATION_BASE:
                totals[c.document_id] = totals.get(c.document_id, 0) + 1
            else:
                key = (c.document_id, c.idx // TRANSLATION_BASE)
                tsizes[key] = tsizes.get(key, 0) + 1
        self._totals = totals
        self._tsizes = tsizes
        self._loaded_at = time.monotonic()

    def _source_idx(self, c: _Chunk) -> int:
        """The position in the original document that a chunk stands for.

        A translation chunk maps to the same relative place, so coverage across prompts and the
        "n of m parts" line count the original document, not its translations.
        """
        if c.idx < TRANSLATION_BASE:
            return c.idx
        n = self._totals.get(c.document_id, 0)
        size = self._tsizes.get((c.document_id, c.idx // TRANSLATION_BASE), 0)
        if n == 0 or size == 0:
            return 0
        return min(n - 1, (c.idx % TRANSLATION_BASE) * n // size)

    def match(self, text: str) -> list[DocMatch]:
        """Documents this text copies or paraphrases, best first. Empty if none are registered."""
        with self._lock:
            self._refresh()
            chunks, matrix = self._chunks, self._matrix
        if not chunks:
            return []
        pieces = chunk_text(text)[:MAX_QUERY_CHUNKS]
        if not pieces:
            return []
        query_sigs = [signature(p) for p in pieces]
        best: dict[int, tuple[float, Kind]] = {}
        hit: dict[int, set[int]] = {}

        def note(c: _Chunk, score: float, kind: Kind) -> None:
            hit.setdefault(c.document_id, set()).add(self._source_idx(c))
            old = best.get(c.document_id)
            if (
                old is None
                or (kind == "copy" and old[1] != "copy")
                or (kind == old[1] and score > old[0])
            ):
                best[c.document_id] = (score, kind)

        copied: set[int] = set()
        copied_query: set[int] = set()
        for qi, qs in enumerate(query_sigs):
            for i, c in enumerate(chunks):
                j = jaccard(qs, c.sig)
                if j >= COPY_JACCARD:
                    note(c, j, "copy")
                    copied.add(i)
                    copied_query.add(qi)
        if len(words(text)) >= MIN_WORDS_TO_EMBED:
            # The model is the slow part, so: skip everything when MinHash already explained the
            # prompt, and cap how many windows are embedded (spread evenly over long prompts).
            wanted = [p for p in chunk_text(text) if len(p.split()) >= 6]
            if copied_query and len(copied_query) >= len(pieces) - 1:
                wanted = []
            if len(wanted) > MAX_EMBEDDED_CHUNKS:
                step = len(wanted) / MAX_EMBEDDED_CHUNKS
                wanted = [wanted[int(k * step)] for k in range(MAX_EMBEDDED_CHUNKS)]
            if wanted:
                sims = self._embedder.embed(wanted) @ matrix.T
                query_lang = np.array([language(p) for p in wanted])
                chunk_lang = np.array([c.lang for c in chunks])
                cutoff = np.where(
                    query_lang[:, None] == chunk_lang[None, :],
                    PARAPHRASE_COSINE,
                    CROSS_LANGUAGE_COSINE,
                )
                is_translation = np.array([c.idx >= TRANSLATION_BASE for c in chunks])
                cutoff = np.where(
                    is_translation[None, :], np.maximum(cutoff, TRANSLATION_COSINE), cutoff
                )
                for qi, i in zip(*np.nonzero(sims >= cutoff), strict=True):
                    if int(i) not in copied:
                        note(chunks[int(i)], float(sims[qi, i]), "paraphrase")
        out = [
            DocMatch(
                document_id=d,
                title=self._docs.get(d, ("", ""))[0],
                sensitivity=self._docs.get(d, ("", "internal"))[1],
                score=round(score, 3),
                kind=kind,
                matched_chunks=sorted(hit[d]),
                total_chunks=self._totals.get(d, 0),
            )
            for d, (score, kind) in best.items()
        ]
        return sorted(out, key=lambda m: (m.kind != "copy", -m.score))


def register_document(
    engine: Engine,
    embedder: Embedder,
    title: str,
    sensitivity: str,
    text: str,
    keep_text: bool = False,
    translations: list[str] | None = None,
) -> tuple[int, int]:
    """Create (or refill) a document and its chunks. Returns (document id, chunk count).

    `translations` are other-language versions of the same text. They are matched like the
    original but never stored as readable text and not counted in the chunk count.
    """
    pieces = chunk_text(text)
    if not pieces:
        raise ValueError("The document has no text to protect.")
    vectors = embedder.embed(pieces)
    extra: list[dict[str, object]] = []
    for n, translated in enumerate(translations or [], start=1):
        tp = chunk_text(translated)
        if not tp:
            continue
        tv = embedder.embed(tp)
        extra += [
            {
                "idx": n * TRANSLATION_BASE + i,
                "minhash": signature(p),
                "embedding": tv[i].tolist(),
                "text_demo": None,
                "lang": language(p),
            }
            for i, p in enumerate(tp)
        ]
    with engine.begin() as conn:
        found = conn.execute(
            sa.select(t.documents.c.id).where(t.documents.c.title == title)
        ).scalar_one_or_none()
        if found is None:
            res = conn.execute(
                sa.insert(t.documents).values(
                    title=title, sensitivity=sensitivity, created_at=datetime.now(UTC)
                )
            )
            key = res.inserted_primary_key
            if key is None:
                raise sa.exc.SQLAlchemyError("document id not returned")
            doc_id = int(key[0])
        else:
            doc_id = int(found)
            conn.execute(
                sa.update(t.documents)
                .where(t.documents.c.id == doc_id)
                .values(sensitivity=sensitivity)
            )
            conn.execute(sa.delete(t.doc_chunks).where(t.doc_chunks.c.document_id == doc_id))
        conn.execute(
            sa.insert(t.doc_chunks),
            [
                {
                    "document_id": doc_id,
                    "idx": i,
                    "minhash": signature(p),
                    "embedding": vectors[i].tolist(),
                    "text_demo": p if keep_text else None,
                    "lang": language(p),
                }
                for i, p in enumerate(pieces)
            ],
        )
        if extra:
            conn.execute(sa.insert(t.doc_chunks), [{"document_id": doc_id, **row} for row in extra])
    return doc_id, len(pieces)


__all__ = ["DocMatch", "DocumentIndex", "register_document", "PERMS"]
