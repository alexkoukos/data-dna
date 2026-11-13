"""Document registry and matching (PRD 9.3).

Register: split into chunks, store a MinHash signature and an embedding per chunk. The text is kept
only when `keep_text` is on (demo mode, for the puzzle view). Match: chunk the prompt the same way;
a chunk is a copy when MinHash Jaccard >= 0.5, a paraphrase when embedding cosine >= 0.70
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
from brain.documents.chunking import chunk_text, words
from brain.documents.embeddings import Embedder
from brain.documents.fingerprint import PERMS, jaccard, signature

log = logging.getLogger(__name__)

COPY_JACCARD = 0.5
PARAPHRASE_COSINE = 0.70
MIN_WORDS_TO_EMBED = 12
MAX_QUERY_CHUNKS = 64

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
                    ).order_by(t.doc_chunks.c.document_id, t.doc_chunks.c.idx)
                ).all()
        except sa.exc.SQLAlchemyError:
            log.warning("Could not read the document index, keeping the last one")
            self._loaded_at = time.monotonic()
            return
        chunks = [
            _Chunk(
                r.document_id, r.idx, bytes(r.minhash), np.asarray(r.embedding, dtype=np.float32)
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
        for c in chunks:
            totals[c.document_id] = totals.get(c.document_id, 0) + 1
        self._totals = totals
        self._loaded_at = time.monotonic()

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
            hit.setdefault(c.document_id, set()).add(c.idx)
            old = best.get(c.document_id)
            if (
                old is None
                or (kind == "copy" and old[1] != "copy")
                or (kind == old[1] and score > old[0])
            ):
                best[c.document_id] = (score, kind)

        copied: set[int] = set()
        for qs in query_sigs:
            for i, c in enumerate(chunks):
                j = jaccard(qs, c.sig)
                if j >= COPY_JACCARD:
                    note(c, j, "copy")
                    copied.add(i)
        if len(words(text)) >= MIN_WORDS_TO_EMBED:
            sims = self._embedder.embed(pieces) @ matrix.T
            for qi in range(sims.shape[0]):
                for i in np.nonzero(sims[qi] >= PARAPHRASE_COSINE)[0]:
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
) -> tuple[int, int]:
    """Create (or refill) a document and its chunks. Returns (document id, chunk count)."""
    pieces = chunk_text(text)
    if not pieces:
        raise ValueError("The document has no text to protect.")
    vectors = embedder.embed(pieces)
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
                }
                for i, p in enumerate(pieces)
            ],
        )
    return doc_id, len(pieces)


__all__ = ["DocMatch", "DocumentIndex", "register_document", "PERMS"]
