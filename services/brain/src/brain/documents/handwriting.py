"""Read handwriting in images: TrOCR-small-handwritten (MIT), quantized ONNX, about 63 MB.

The printed-text reader (RapidOCR) neither finds nor reads handwriting. This pass looks at the ink
the printed reader left unread, cuts it into lines and words, and reads each word with TrOCR. It
runs only on document-like pictures (a light page with some ink), and words it is unsure about are
dropped, because on shapes that are not writing the model invents words.

The model is baked into the brain image at build time (`fetch_model_files`, pinned revision). If it
is missing (a local install that did not download it), the pass is skipped.
"""

import threading
from typing import Any

MODEL_REPO = "Xenova/trocr-small-handwritten"
MODEL_REVISION = "02bea33ca09a70e2e2d91140a7e6e1a729606a5b"
FILES = ("onnx/encoder_model_quantized.onnx", "onnx/decoder_model_quantized.onnx", "tokenizer.json")
START_ID = 2  # decoder start and end of text
MAX_TOKENS = 24  # one word, or one run of digits
MAX_WORDS = 150  # per image: about 30 ms a word on a CPU
MIN_CONFIDENCE = 0.6  # mean top probability of the tokens of a word
MAX_INK_SHARE = 0.25  # more ink than this is a photo or a drawing, not a page with writing
MIN_LINE, MAX_LINE = 12, 220  # line heights in pixels that can be writing

_state: Any = None
_lock = threading.Lock()


def fetch_model_files(local_only: bool = False) -> list[str]:
    from huggingface_hub import hf_hub_download

    return [
        hf_hub_download(MODEL_REPO, f, revision=MODEL_REVISION, local_files_only=local_only)
        for f in FILES
    ]


def available() -> bool:
    try:
        return _load() is not None
    except Exception:  # noqa: BLE001 - no model files or no runtime: the pass is skipped
        return False


def _load() -> Any:
    global _state
    with _lock:
        if _state is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            enc, dec, tok = fetch_model_files(local_only=True)
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            _state = (
                ort.InferenceSession(enc, opts, providers=["CPUExecutionProvider"]),
                ort.InferenceSession(dec, opts, providers=["CPUExecutionProvider"]),
                Tokenizer.from_file(tok),
            )
    return _state


def _read_word(crop: Any) -> tuple[str, float]:
    """One word image to (text, confidence)."""
    import numpy as np
    from PIL import Image

    enc, dec, tok = _load()
    x = np.asarray(
        crop.convert("RGB").resize((384, 384), Image.Resampling.BICUBIC), dtype=np.float32
    )
    x = ((x / 255.0 - 0.5) / 0.5).transpose(2, 0, 1)[None]
    hidden = enc.run(None, {"pixel_values": x})[0]
    ids, probs = [START_ID], []
    for _ in range(MAX_TOKENS):
        logits = dec.run(
            ["logits"],
            {"input_ids": np.array([ids], dtype=np.int64), "encoder_hidden_states": hidden},
        )[0][0, -1]
        e = np.exp(logits - logits.max())
        nxt = int(e.argmax())
        probs.append(float(e[nxt] / e.sum()))
        if nxt == START_ID:
            break
        ids.append(nxt)
    text = tok.decode(ids[1:], skip_special_tokens=True).strip()
    return text, (sum(probs) / len(probs) if probs else 0.0)


def _runs(mask: Any, axis: int, min_gap: int) -> list[tuple[int, int]]:
    """Start and end of the stretches with ink along one axis, joining gaps up to `min_gap`."""
    filled = mask.any(axis=axis)
    out: list[tuple[int, int]] = []
    start, gap = -1, 0
    for i, v in enumerate(filled):
        if v:
            start = i if start < 0 else start
            gap = 0
        elif start >= 0:
            gap += 1
            if gap > min_gap:
                out.append((start, i - gap + 1))
                start, gap = -1, 0
    if start >= 0:
        out.append((start, len(filled)))
    return out


def read_handwriting(img: Any, printed_boxes: list[Any]) -> list[str]:
    """Lines of handwriting in `img` outside the boxes the printed reader already read."""
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    gray = np.array(img.convert("L"))
    if np.median(gray) < 150:  # a dark or busy picture: not a page with writing
        return []
    ink = gray < min(170, int(np.median(gray)) - 40)
    for box in printed_boxes:
        pts = np.array(box, dtype=int)
        x0, y0 = np.maximum(pts.min(0) - 4, 0)
        x1, y1 = pts.max(0) + 4
        ink[y0:y1, x0:x1] = False
    if not ink.any() or ink.mean() > MAX_INK_SHARE:
        return []
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)) > 0
    page = Image.fromarray(gray)
    lines: list[str] = []
    words_read = 0
    for y0, y1 in _runs(ink, 1, 4):
        h = y1 - y0
        if not MIN_LINE <= h <= MAX_LINE:
            continue
        words: list[str] = []
        for x0, x1 in _runs(ink[y0:y1], 0, max(5, h // 4)):
            if words_read >= MAX_WORDS:
                break
            if x1 - x0 < 4:
                continue
            pad = max(6, h // 5)
            crop = page.crop((max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad))
            text, confidence = _read_word(ImageOps.autocontrast(crop))
            words_read += 1
            if text and confidence >= MIN_CONFIDENCE:
                words.append(text)
        if words:
            lines.append(" ".join(words))
    return lines
