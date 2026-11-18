"""X8: read text from images and screenshots, then run the same checks as for any text.

Uses RapidOCR (ONNX, CPU) when it is installed: `uv sync --extra ocr`. It is optional so the
default image stays small. Without it, an image is refused with a message that says what to do,
never silently let through unread.
"""

import io
import warnings
from collections.abc import Callable
from typing import Any

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
MAX_PIXELS = 40_000_000
_engine: Callable[..., Any] | None = None


class OcrUnavailable(RuntimeError):
    """OCR is not installed. The message is safe to show."""


def available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def _load() -> Callable[..., Any]:
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as err:
            raise OcrUnavailable(
                "Reading text in images is not switched on in this install. "
                "Paste the text instead, or ask the admin to enable OCR (uv sync --extra ocr)."
            ) from err
        _engine = RapidOCR()
    return _engine


def image_text(data: bytes) -> str:
    """The text found in an image, one line per detected line. Empty if there is none."""
    import numpy as np
    from PIL import Image

    too_big = ValueError(
        "This image has too many pixels to read. Shrink it or crop the part you need."
    )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            opened = Image.open(io.BytesIO(data))
            if opened.width * opened.height > MAX_PIXELS:
                raise too_big
            img = np.array(opened.convert("RGB"))
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as err:
        raise too_big from err
    except ValueError as err:
        if err is too_big:
            raise
        raise ValueError(
            "This image could not be read. Check that the file is not damaged."
        ) from err
    except Exception as err:  # Pillow raises several unrelated types on bad files
        raise ValueError(
            "This image could not be read. Check that the file is not damaged."
        ) from err
    engine = _load()
    result, _ = engine(img)
    return "\n".join(str(row[1]) for row in (result or []))
