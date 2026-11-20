"""X8: read text from images and screenshots, then run the same checks as for any text.

Uses RapidOCR (ONNX, CPU) when it is installed: `uv sync --extra ocr`. It is optional so the
default image stays small. Without it, an image is refused with a message that says what to do,
never silently let through unread.
"""

import difflib
import hashlib
import io
import re
import threading
import time
import warnings
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from brain.documents import hidden_data

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif")
MAX_PIXELS = 40_000_000
# The recogniser sometimes drops the space between a label and its value ("IBANGR16...",
# "AFM123456789"). The checks look for whole tokens, so the space is put back.
_GLUED_IBAN = re.compile(r"(?<=[A-Za-z])(?=[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b)")
_GLUED_NUMBER = re.compile(r"(?<=[A-Za-z]{3})(?=\d{6,})")
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


def respace(line: str) -> str:
    """Put back a space the recogniser dropped between a label and an IBAN or a long number."""
    return _GLUED_NUMBER.sub(" ", _GLUED_IBAN.sub(" ", line))


# Labels the reader puts in front of text a person would not see as plain writing. The brain's
# checks read all of it; `HIDDEN_LABEL` itself is a finding (category `hidden_text`), because text
# drawn so a person cannot see it but a model can is how instructions are slipped to an AI.
HIDDEN_LABEL = "[Text hard to see in this image]"
HIDDEN_DATA_LABEL = "[Hidden data in this image]"  # a finding of its own: `hidden_data`
CODE_LABEL = "[QR or barcode in this image]"
META_LABEL = "[Image metadata: {}]"
MAX_SIDE = 3000  # larger images are shrunk before reading: tiny text survives, time stays bounded
MIN_HIDDEN_LETTERS = 6
_META_CHARS = 4000
# EXIF fields that hold free text: description, artist, copyright, user comment, Windows fields.
_EXIF_TEXT = {
    270: "Description",
    315: "Artist",
    33432: "Copyright",
    37510: "UserComment",
    40091: "Title",
    40092: "Comment",
    40094: "Keywords",
    40095: "Subject",
}


@dataclass
class ImageReading:
    """What an image says: the text a person sees, text drawn to be hard to see, the payload of
    QR codes and barcodes, and free-text metadata. A model can read every one of these."""

    visible: list[str] = field(default_factory=list)
    hidden: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    metadata: list[tuple[str, str]] = field(default_factory=list)
    hidden_data: list[str] = field(default_factory=list)  # what the file carries besides pixels

    def text(self) -> str:
        parts = list(self.visible)
        if self.hidden:
            parts += [HIDDEN_LABEL, *self.hidden]
        if self.hidden_data:
            parts += [HIDDEN_DATA_LABEL, *self.hidden_data]
        if self.codes:
            parts += [CODE_LABEL, *self.codes]
        for key, value in self.metadata:
            parts += [META_LABEL.format(key), value]
        return "\n".join(parts)


def _key(line: str) -> str:
    return re.sub(r"[^0-9a-z]", "", line.lower())


def _new_lines(found: list[str], known: list[str]) -> list[str]:
    """Lines in `found` that are not (nearly) a line already in `known`."""
    seen = [_key(k) for k in known]
    joined = "".join(seen)
    out: list[str] = []
    for line in found:
        k = _key(line)
        if len(re.sub(r"[^a-z]", "", k)) < MIN_HIDDEN_LETTERS or k in joined:
            continue
        if any(difflib.SequenceMatcher(None, k, s).ratio() >= 0.75 for s in seen):
            continue
        out.append(line)
        seen.append(k)
    return out


def _read(engine: Callable[..., Any], arr: Any) -> tuple[list[str], list[Any]]:
    """Lines of printed text and the boxes they were read from."""
    result, _ = engine(arr)
    rows = [row for row in (result or []) if str(row[1]).strip()]
    return [respace(str(row[1])) for row in rows], [row[0] for row in rows]


def _lines(engine: Callable[..., Any], arr: Any) -> list[str]:
    return _read(engine, arr)[0]


def _has_vertical_text(engine: Callable[..., Any], arr: Any) -> bool:
    import numpy as np

    boxes, _ = engine(arr, use_rec=False)
    for box in boxes or []:
        pts = np.array(box, dtype=float)
        width = np.linalg.norm(pts[1] - pts[0])
        height = np.linalg.norm(pts[3] - pts[0])
        if height > 40 and height > 1.5 * width:
            return True
    return False


def _codes(rgb: Any) -> list[str]:
    """Text inside QR codes and barcodes. A model can read a QR code; a person cannot."""
    import cv2

    out: list[str] = []
    try:
        ok, decoded, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(rgb)
        if ok:
            out += [d for d in decoded if d]
    except cv2.error:
        pass
    if hasattr(cv2, "barcode"):
        try:
            ok, decoded, _, _ = cv2.barcode.BarcodeDetector().detectAndDecodeMulti(rgb)
            if ok:
                out += [d for d in decoded if d and d not in out]
        except cv2.error:
            pass
    return out


def _metadata(opened: Any) -> list[tuple[str, str]]:
    """Free text stored in the file: PNG text chunks, XMP, EXIF comments and descriptions."""
    out: list[tuple[str, str]] = []

    def add(key: str, value: Any) -> None:
        if isinstance(value, bytes):
            raw = value
            if raw[:8] in (b"ASCII\x00\x00\x00", b"UNICODE\x00", b"JIS\x00\x00\x00\x00\x00"):
                raw = raw[8:]
            try:
                value = (
                    raw.decode("utf-16-le")
                    if key in ("Title", "Comment", "Keywords", "Subject")
                    else raw.decode("utf-8")
                )
            except UnicodeDecodeError:
                value = raw.decode("latin-1")
        if not isinstance(value, str):
            return
        value = re.sub(r"<[^>]{0,400}>", " ", value) if key == "XMP" else value
        value = re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()[:_META_CHARS]
        if len(re.sub(r"[^A-Za-z\u0370-\u03ff]", "", value)) >= 3:
            out.append((key, value))

    for key, value in (opened.info or {}).items():
        if key in ("xmp", "XML:com.adobe.xmp"):
            add("XMP", value)
        elif isinstance(key, str) and key not in ("icc_profile", "exif", "transparency"):
            add(key, value)
    try:
        exif = opened.getexif()
    except Exception:  # noqa: BLE001 - a broken EXIF block must not stop the image check
        exif = {}
    for tag, name in _EXIF_TEXT.items():
        if tag in exif:
            add(name, exif[tag])
    try:
        sub = exif.get_ifd(0x8769) if hasattr(exif, "get_ifd") else {}
    except Exception:  # noqa: BLE001
        sub = {}
    if 37510 in sub:
        add("UserComment", sub[37510])
    return out


def read_pil(img: Any, metadata: list[tuple[str, str]] | None = None) -> ImageReading:
    """Read a Pillow image the way a model would see it, and look for what a person would not.

    Passes: the image as shown on white (and on black when it has transparency); a local-contrast
    copy that brings out near-invisible text; the colour channels with transparency removed (text
    hidden under transparent pixels); turned copies when the text runs vertically. Text found
    only by the extra passes is reported as hidden.
    """
    import cv2
    import numpy as np
    from PIL import Image

    engine = _load()
    if img.width * img.height > MAX_PIXELS:
        raise ValueError("An image is too large to read. Shrink it or send fewer pages.")
    if max(img.size) > MAX_SIDE:
        img = img.copy()
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    raw = None
    if has_alpha:
        rgba = img.convert("RGBA")
        if np.array(rgba.getchannel("A")).min() < 255:
            on_white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            on_black = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
            base = np.array(Image.alpha_composite(on_white, rgba).convert("RGB"))
            dark = np.array(Image.alpha_composite(on_black, rgba).convert("RGB"))
            raw = np.array(rgba.convert("RGB"))  # what a reader that drops transparency sees
        else:
            has_alpha = False
    if not has_alpha:
        base = np.array(img.convert("RGB"))
    visible, boxes = _read(engine, base)
    from brain.documents import handwriting

    if handwriting.available():  # writing the printed reader neither found nor read
        visible += _new_lines(handwriting.read_handwriting(Image.fromarray(base), boxes), visible)
    if has_alpha:
        visible += _new_lines(_lines(engine, dark), visible)
    if _has_vertical_text(engine, base):
        for turn in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE):
            visible += _new_lines(_lines(engine, cv2.rotate(base, turn)), visible)
    gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
    boosted = cv2.createCLAHE(clipLimit=8.0, tileGridSize=(8, 8)).apply(gray)
    hidden = _new_lines(_lines(engine, cv2.cvtColor(boosted, cv2.COLOR_GRAY2RGB)), visible)
    if raw is not None:
        hidden += _new_lines(_lines(engine, raw), visible + hidden)
    return ImageReading(visible, hidden, _codes(base), metadata or [])


def pil_text(img: Any) -> str:
    """The text in a Pillow image (used for the page images of a scanned PDF)."""
    return read_pil(img).text()


# Company Chat reads a picture when it is attached and the gateway reads the same bytes again when
# it is sent. A short memory of recent readings (by content hash, in this process only, never on
# disk) answers the second time at once.
_CACHE_SIZE = 64
_CACHE_SECONDS = 600.0
_cache: OrderedDict[str, tuple[float, ImageReading]] = OrderedDict()
_cache_lock = threading.Lock()


def read_image(data: bytes) -> ImageReading:
    """Open an image file safely and read it (see `read_pil`). Recent readings are remembered."""
    key = hashlib.sha256(data).hexdigest()
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None and now - hit[0] < _CACHE_SECONDS:
            _cache.move_to_end(key)
            return hit[1]
    reading = _read_image(data)
    with _cache_lock:
        _cache[key] = (now, reading)
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return reading


def _read_image(data: bytes) -> ImageReading:
    from PIL import Image, ImageOps

    too_big = ValueError(
        "This image has too many pixels to read. Shrink it or crop the part you need."
    )
    damaged = ValueError("This image could not be read. Check that the file is not damaged.")
    animated = ValueError(
        "Animated images cannot be checked frame by frame. Send a still image (PNG or JPG)."
    )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            opened = Image.open(io.BytesIO(data))
            if opened.width * opened.height > MAX_PIXELS:
                raise too_big
            if getattr(opened, "n_frames", 1) > 1:
                raise animated
            meta = _metadata(opened)
            opened.load()
            carried = hidden_data.container_findings(data)
            if hidden_data.lossless(data):
                share = hidden_data.lsb_payload(opened)
                if share >= hidden_data.LSB_LIMIT:
                    carried.append(
                        f"the lowest bits of about {share:.0%} of the pixels look like a hidden "
                        "message (steganography)"
                    )
            img = ImageOps.exif_transpose(opened) or opened  # turned the way it is shown
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as err:
        raise too_big from err
    except ValueError as err:
        if err is too_big or err is animated:
            raise
        raise damaged from err
    except Exception as err:  # Pillow raises several unrelated types on bad files
        raise damaged from err
    reading = read_pil(img, meta)
    reading.hidden_data = carried
    return reading


def image_text(data: bytes) -> str:
    """Everything an image says, with labels for hidden text, codes and metadata."""
    return read_image(data).text()
