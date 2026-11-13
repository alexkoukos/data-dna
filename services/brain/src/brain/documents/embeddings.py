"""Sentence embeddings (384 dimensions, multilingual, runs on CPU through ONNX).

`FastEmbedder` is the real one. `HashingEmbedder` is a deterministic stand-in for unit tests, so
they run without downloading a model. It only knows exact word overlap, never paraphrase.
"""

import hashlib
import threading
from typing import Any, Protocol

import numpy as np

DIM = 384
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...


def _unit(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return np.asarray(m / np.where(norms == 0, 1, norms), dtype=np.float32)


class FastEmbedder:
    def __init__(self) -> None:
        self._model: Any = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        self._load()

    def _load(self) -> Any:
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(MODEL)
            return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, DIM), dtype=np.float32)
        return _unit(np.array(list(self._load().embed(texts)), dtype=np.float32))


class HashingEmbedder:
    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                h = int.from_bytes(hashlib.md5(w.encode()).digest()[:4], "big")  # noqa: S324
                out[i, h % DIM] += 1.0
        return _unit(out)
