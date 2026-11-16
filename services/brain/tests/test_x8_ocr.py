import pytest

from brain.documents import ocr
from brain.documents.extract import ExtractError, extract_text


def test_an_image_without_ocr_installed_is_refused_with_a_next_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ocr, "_engine", None)
    monkeypatch.setattr(
        ocr, "_load", lambda: (_ for _ in ()).throw(ocr.OcrUnavailable("Enable OCR"))
    )
    with pytest.raises(ExtractError, match="Enable OCR"):
        extract_text("screenshot.png", b"\x89PNG....")


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
