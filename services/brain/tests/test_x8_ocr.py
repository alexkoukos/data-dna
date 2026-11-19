import pytest

from brain.documents import ocr
from brain.documents.extract import ExtractError, extract_text


def _png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, "PNG")
    return buf.getvalue()


def test_an_image_without_ocr_installed_is_refused_with_a_next_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ocr, "_engine", None)
    monkeypatch.setattr(
        ocr, "_load", lambda: (_ for _ in ()).throw(ocr.OcrUnavailable("Enable OCR"))
    )
    with pytest.raises(ExtractError, match="Enable OCR"):
        extract_text("screenshot.png", _png())


def test_text_found_in_an_image_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "image_text", lambda data: "IBAN GR1601101250000000012300695")
    assert "IBAN" in extract_text("shot.JPG", b"x")


def test_an_image_with_no_text_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ocr, "image_text", lambda data: "  ")
    with pytest.raises(ExtractError, match="No text"):
        extract_text("blank.png", b"x")


def test_a_damaged_image_is_refused_in_plain_words(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(data: bytes) -> str:
        raise ValueError("This image could not be read. Check that the file is not damaged.")

    monkeypatch.setattr(ocr, "image_text", bad)
    with pytest.raises(ExtractError, match="could not be read"):
        extract_text("x.png", b"x")


def test_unsupported_types_still_refused() -> None:
    with pytest.raises(ExtractError, match="not supported"):
        extract_text("x.exe", b"x")


def test_decompression_bomb_is_refused_before_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    from PIL import Image

    monkeypatch.setattr(ocr, "MAX_PIXELS", 100)
    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, "PNG")
    monkeypatch.setattr(
        ocr, "_load", lambda: (_ for _ in ()).throw(AssertionError("OCR must not start"))
    )
    with pytest.raises(ExtractError, match="too many pixels"):
        extract_text("big.png", buf.getvalue())
