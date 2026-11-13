"""Sentence embeddings (384 dimensions, multilingual, CPU, ONNX).

`E5Embedder` is the real one: multilingual-e5-small, int8, about 118 MB and 4 ms a chunk. On the
paraphrase set it found more rewrites than the MiniLM and mpnet models it replaced, at a fraction
of the cost of e5-large (see PROGRESS.md for the comparison). `HashingEmbedder` is a deterministic
stand-in for unit tests, so they run without downloading a model; it only knows exact word
overlap, never paraphrase.
"""

import hashlib
import os
import threading
from typing import Any, Protocol

import numpy as np

DIM = 384
MODEL_REPO = "Xenova/multilingual-e5-small"
MODEL_FILE = "onnx/model_quantized.onnx"
MAX_TOKENS = 128


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...


def _unit(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return np.asarray(m / np.where(norms == 0, 1, norms), dtype=np.float32)


def fetch_model_files() -> tuple[str, str]:
    """Paths of the ONNX model and tokenizer, downloaded once into the Hugging Face cache."""
    from huggingface_hub import hf_hub_download

    return (
        hf_hub_download(MODEL_REPO, MODEL_FILE),
        hf_hub_download(MODEL_REPO, "tokenizer.json"),
    )


class E5Embedder:
    def __init__(self) -> None:
        self._state: Any = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        self._load()

    def _load(self) -> Any:
        with self._lock:
            if self._state is None:
                import onnxruntime as ort
                from tokenizers import Tokenizer

                model_path, tokenizer_path = fetch_model_files()
                tokenizer = Tokenizer.from_file(tokenizer_path)
                tokenizer.enable_truncation(max_length=MAX_TOKENS)
                tokenizer.enable_padding()
                options = ort.SessionOptions()
                options.intra_op_num_threads = int(os.environ.get("EMBED_THREADS", "4"))
                session = ort.InferenceSession(
                    model_path, options, providers=["CPUExecutionProvider"]
                )
                self._state = (tokenizer, session, {i.name for i in session.get_inputs()})
            return self._state

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, DIM), dtype=np.float32)
        tokenizer, session, wanted = self._load()
        out = []
        for i in range(0, len(texts), 16):
            # e5 models expect a prefix; "query: " on both sides suits symmetric matching.
            enc = tokenizer.encode_batch(["query: " + t for t in texts[i : i + 16]])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feeds = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in wanted:
                feeds["token_type_ids"] = np.zeros_like(ids)
            hidden = session.run(None, feeds)[0]
            weights = mask[..., None]
            out.append((hidden * weights).sum(axis=1) / weights.sum(axis=1))
        return _unit(np.vstack(out))


class HashingEmbedder:
    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                h = int.from_bytes(hashlib.md5(w.encode()).digest()[:4], "big")  # noqa: S324
                out[i, h % DIM] += 1.0
        return _unit(out)
