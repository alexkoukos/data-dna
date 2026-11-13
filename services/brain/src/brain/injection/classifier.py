"""Prompt-injection classifier (PRD 9.5): protectai/deberta-v3-base-prompt-injection-v2 on ONNX.

Optional: the model is about 740 MB, so it is not baked into the image. `make injection-model`
downloads it into the `models` volume. Without it the phrase heuristics still run. It reads long
text only (uploaded files, pasted pages), where a hidden instruction is most likely, because it
costs about 0.6 s for every 400 tokens, so it only reads text of 250 words or more.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from brain.detection.patterns import Finding

log = logging.getLogger(__name__)

MODEL_REPO = "protectai/deberta-v3-base-prompt-injection-v2"
MODEL_DIR = Path(os.environ.get("INJECTION_MODEL_DIR", "/models/injection"))
THRESHOLD = 0.9
MAX_TOKENS = 512
MIN_WORDS = 250  # below this the phrase heuristics are enough, and the model costs ~0.6 s a window
MAX_WINDOWS = 4


class _Scorer(Protocol):
    def __call__(self, texts: list[str]) -> list[float]: ...


class InjectionClassifier:
    def __init__(self, model_dir: Path = MODEL_DIR, scorer: _Scorer | None = None) -> None:
        self._dir = model_dir
        self._scorer = scorer
        self._checked_at = float("-inf")
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self._load() is not None

    def _load(self) -> _Scorer | None:
        with self._lock:
            if self._scorer is not None:
                return self._scorer
            if time.monotonic() - self._checked_at < 30:
                return None
            self._checked_at = time.monotonic()
            onnx = self._dir / "onnx" / "model.onnx"
            tok = self._dir / "onnx" / "tokenizer.json"
            if not (onnx.exists() and tok.exists()):
                return None
            try:
                self._scorer = _onnx_scorer(onnx, tok)
                log.info("Injection classifier loaded from %s", self._dir)
            except Exception:
                log.exception("Could not load the injection classifier")
            return self._scorer

    def find(self, text: str) -> list[Finding]:
        words = text.split()
        scorer = self._load()
        if scorer is None or len(words) < MIN_WORDS:
            return []
        step = 300  # words per window: about 400 tokens, safely under the limit
        windows = [" ".join(words[i : i + step]) for i in range(0, len(words), step)][:MAX_WINDOWS]
        scores = scorer(windows)
        hits = [(w, s) for w, s in zip(windows, scores, strict=True) if s >= THRESHOLD]
        if not hits:
            return []
        start = text.find(hits[0][0][:40])
        start = max(start, 0)
        end = min(len(text), start + len(hits[0][0]))
        return [Finding("INJECTION_MODEL", "injection", start, end, text[start:end])]


def _onnx_scorer(onnx_path: Path, tokenizer_path: Path) -> _Scorer:
    import onnxruntime as ort
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.enable_truncation(max_length=MAX_TOKENS)
    tokenizer.enable_padding()
    options = ort.SessionOptions()
    options.intra_op_num_threads = int(os.environ.get("EMBED_THREADS", "4"))
    session: Any = ort.InferenceSession(str(onnx_path), options, providers=["CPUExecutionProvider"])
    wanted = {i.name for i in session.get_inputs()}

    def score(texts: list[str]) -> list[float]:
        enc = tokenizer.encode_batch(texts)
        feeds = {
            "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
        }
        logits = session.run(None, {k: v for k, v in feeds.items() if k in wanted})[0]
        e = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = e / e.sum(axis=1, keepdims=True)
        return [float(p[1]) for p in probs]  # label 1 is "injection"

    return score
