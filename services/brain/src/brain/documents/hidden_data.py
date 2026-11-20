"""Data hidden inside an image file: steganography, as a way to carry company data out.

Two kinds of evidence:
- the file itself: bytes after the end of the image, large private PNG chunks, oversized text
  chunks (`container_findings`). Certain, cheap.
- the pixels: sample pair analysis (Dumitrescu, Wu and Wang) estimates which share of the lowest
  bits carries a message (`lsb_payload`). Only for lossless formats; a JPEG cannot keep such a
  message. Clean pictures estimate near 0; a message in 10% of the pixels estimates about 0.1.

Detection is the first line. The second is that the gateway redraws every picture before a model
sees it (`purify.py`), which wipes pixel-level messages and appended data whether found or not.
"""

import struct
from typing import Any

APPENDED_LIMIT = 16  # some encoders leave a few padding bytes
PRIVATE_CHUNK_LIMIT = 1024
TEXT_CHUNKS_LIMIT = 64 * 1024
LSB_LIMIT = 0.25  # estimated share of pixels carrying a message
LSB_MIN_PIXELS = 40_000

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_KNOWN = {
    b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB",
    b"cICP", b"mDCv", b"cLLi", b"tEXt", b"zTXt", b"iTXt", b"bKGD", b"hIST", b"pHYs", b"sPLT",
    b"eXIf", b"tIME", b"acTL", b"fcTL", b"fdAT", b"oFFs", b"pCAL", b"sCAL", b"sTER", b"gIFg",
    b"gIFx", b"dSIG", b"vpAg", b"caBX",
}  # fmt: skip


def _png(data: bytes) -> list[str]:
    out: list[str] = []
    pos, text_bytes = 8, 0
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        end = pos + 12 + length
        if end > len(data):
            return out  # a damaged file: the image reader says so
        if kind in (b"tEXt", b"zTXt", b"iTXt"):
            text_bytes += length
        elif kind not in _PNG_KNOWN and length > PRIVATE_CHUNK_LIMIT:
            out.append(f"a private block of {length:,} bytes ({kind.decode('latin-1')!r})")
        pos = end
        if kind == b"IEND":
            break
    if len(data) - pos > APPENDED_LIMIT:
        out.append(f"{len(data) - pos:,} bytes after the end of the image")
    if text_bytes > TEXT_CHUNKS_LIMIT:
        out.append(f"{text_bytes:,} bytes of text blocks")
    return out


def _jpeg_end(data: bytes) -> int | None:
    """Where the JPEG really ends (after its EOI marker), following its segments."""
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            return None
        marker = data[pos + 1]
        if marker == 0xD9:
            return pos + 2
        if marker in (0x01, *range(0xD0, 0xD8)) or marker == 0xFF:
            pos += 1 if marker == 0xFF else 2
            continue
        (length,) = struct.unpack(">H", data[pos + 2 : pos + 4])
        pos += 2 + length
        if marker == 0xDA:  # entropy-coded data until the next real marker
            while pos + 1 < len(data):
                if data[pos] == 0xFF and data[pos + 1] not in (0x00, *range(0xD0, 0xD8)):
                    break
                pos += 1
    return None


def _jpeg(data: bytes) -> list[str]:
    end = _jpeg_end(data)
    if end is None or len(data) - end <= APPENDED_LIMIT:
        return []
    tail = data[end : end + 16]
    if tail[4:8] == b"ftyp":  # a phone's motion photo: a short video after the picture
        return []
    return [f"{len(data) - end:,} bytes after the end of the image"]


def _riff(data: bytes) -> list[str]:
    (size,) = struct.unpack("<I", data[4:8])
    extra = len(data) - (8 + size + (size & 1))
    return [f"{extra:,} bytes after the end of the image"] if extra > APPENDED_LIMIT else []


def _bmp(data: bytes) -> list[str]:
    (size,) = struct.unpack("<I", data[2:6])
    extra = len(data) - size
    return [f"{extra:,} bytes after the end of the image"] if extra > APPENDED_LIMIT else []


def container_findings(data: bytes) -> list[str]:
    """What the image file carries besides the picture, in words. Empty for a plain image."""
    try:
        if data.startswith(_PNG_SIGNATURE):
            return _png(data)
        if data.startswith(b"\xff\xd8"):
            return _jpeg(data)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return _riff(data)
        if data.startswith(b"BM") and len(data) > 6:
            return _bmp(data)
    except struct.error:
        return []
    return []


def _pair_estimate(channel: Any) -> float:
    """Sample pair analysis on one colour channel: the estimated share of pixels with a message
    in their lowest bit (0 for a clean picture)."""
    import numpy as np

    c = channel.astype(np.int64)
    u, v = c[:, :-1].ravel(), c[:, 1:].ravel()
    total = u.size
    even, odd = v % 2 == 0, v % 2 == 1
    x = int(np.sum((even & (u < v)) | (odd & (u > v))))
    y = int(np.sum((even & (u > v)) | (odd & (u < v))))
    z = int(np.sum(u == v))
    w = int(np.sum((u // 2 == v // 2) & (u != v)))
    a, b, k = (w + z) / 2, 2 * x - total, y - x
    if a == 0:
        return 0.0
    disc = b * b - 4 * a * k
    if disc < 0:
        return 0.0
    root = disc**0.5
    return float(min(abs((-b - root) / (2 * a)), abs((-b + root) / (2 * a))))


def lsb_payload(img: Any) -> float:
    """The largest estimated message share over the colour channels, for the whole picture and
    for its top quarter (simple tools write the message from the first row on)."""
    import numpy as np

    arr = np.array(img.convert("RGB"))
    if arr.shape[0] * arr.shape[1] < LSB_MIN_PIXELS:
        return 0.0
    top = arr[: max(arr.shape[0] // 4, 1)]
    regions = [arr] + ([top] if top.shape[0] * top.shape[1] >= LSB_MIN_PIXELS else [])
    return max(_pair_estimate(r[..., ch]) for r in regions for ch in range(3))


def lossless(data: bytes) -> bool:
    """PNG, BMP, TIFF or lossless WebP: formats whose lowest pixel bits survive saving."""
    return data.startswith((_PNG_SIGNATURE, b"BM", b"II*\x00", b"MM\x00*")) or (
        data[:4] == b"RIFF" and data[8:12] == b"WEBP" and data[12:16] == b"VP8L"
    )
