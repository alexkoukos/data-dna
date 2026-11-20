"""Redraw a picture before a model sees it, so what reaches the model is only what a person sees.

The gateway sends the redrawn copy instead of the original (see `apply_decision`). Redrawing:
- puts the picture on a white page: nothing hidden under transparent pixels survives;
- scales it to at most 2048 pixels, then by a further 0.97 and back to JPEG at quality 85, with a
  very light blur: a message in the lowest pixel bits, bytes appended to the file and all metadata
  are gone, and pixel patterns tuned against one model lose most of their effect (the same
  input transformations used as a defence in the research on adversarial images);
- keeps text readable for the model.

This is a transformation defence, not a proof: an attacker who knows the exact transformation can
try to survive it. Hidden and instruction text found by the checks are still blocked or asked
about first.
"""

import io
from typing import Any

MAX_SIDE = 2048
EXTRA_SCALE = 0.97
QUALITY = 85
BLUR_RADIUS = 0.6


def purify_image(img: Any) -> bytes:
    from PIL import Image, ImageFilter

    rgba = img.convert("RGBA")
    page = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(page, rgba).convert("RGB")
    scale = min(1.0, MAX_SIDE / max(flat.size)) * EXTRA_SCALE
    size = (max(1, round(flat.width * scale)), max(1, round(flat.height * scale)))
    flat = flat.resize(size, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    out = io.BytesIO()
    flat.save(out, "JPEG", quality=QUALITY, optimize=True)  # no EXIF, no ICC, no comments
    return out.getvalue()


def purify(data: bytes) -> bytes:
    """The redrawn JPEG of an image file. Raises ValueError for a file that is not an image."""
    from PIL import Image, ImageOps

    try:
        opened = Image.open(io.BytesIO(data))
        opened.load()
        img = ImageOps.exif_transpose(opened) or opened
    except Exception as err:  # Pillow raises several unrelated types on bad files
        raise ValueError(
            "This image could not be read. Check that the file is not damaged."
        ) from err
    return purify_image(img)
