"""Inline files sent straight to the gateway (OpenAI file and image parts, Responses input files,
Anthropic documents and images) are read by the brain, not passed through unread."""

import asyncio
import base64
import copy
from typing import Any

import httpx
import pytest

import brain.main as main
from brain.documents import ocr
from tests.test_extract import IBAN, docx_bytes, pdf_with_text
from tests.test_gateway_logic import _decide, dna

STAMPED = pdf_with_text("Q4 report. Classification: RESTRICTED.")


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def chat(*parts: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": "m",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "summarise"}, *parts]}],
    }


def file_part(data: bytes, filename: str = "q4.pdf", media: str = "application/pdf") -> dict:  # type: ignore[type-arg]
    return {
        "type": "file",
        "file": {"filename": filename, "file_data": f"data:{media};base64,{b64(data)}"},
    }


def sent_attachments(data: dict[str, Any], call_type: str = "completion") -> list[dict[str, str]]:
    seen: list[dict[str, Any]] = []
    _decide(copy.deepcopy(data), call_type, {"decision": "allow", "reasons": []}, seen)
    return seen[0].get("attachments", [])  # type: ignore[no-any-return]


# --- what the gateway hands to the brain -------------------------------------------------------


def test_an_openai_pdf_file_part_goes_to_the_brain() -> None:
    [a] = sent_attachments(chat(file_part(STAMPED)))
    assert a["filename"] == "q4.pdf"
    assert base64.b64decode(a["content_base64"]) == STAMPED


def test_images_and_files_in_every_format_go_to_the_brain() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
    url = f"data:image/png;base64,{b64(png)}"
    openai = chat(
        {"type": "image_url", "image_url": {"url": url}},
        {"type": "image_url", "image_url": url},
        {"type": "input_audio", "input_audio": {"data": b64(b"RIFF....WAVE"), "format": "wav"}},
    )
    names = [a["filename"] for a in sent_attachments(openai)]
    assert names == ["attachment.png", "attachment.png", "attachment.bin"]

    responses = {
        "model": "m",
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": url},
                    {"type": "input_file", "filename": "memo", "file_data": b64(STAMPED)},
                ],
            }
        ],
    }
    assert [a["filename"] for a in sent_attachments(responses, "responses")] == [
        "attachment.png",
        "memo",
    ]

    anthropic = {
        "model": "m",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": b64(STAMPED),
                        },
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "t",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": b64(png),
                                },
                            }
                        ],
                    },
                ],
            }
        ],
    }
    assert [a["filename"] for a in sent_attachments(anthropic, "anthropic_messages")] == [
        "attachment.pdf",
        "attachment.png",
    ]


def test_text_that_is_already_checked_and_web_addresses_are_not_attachments() -> None:
    text_file = file_part(f"key {IBAN}".encode(), "a.txt", "text/plain")
    remote = {"type": "image_url", "image_url": {"url": "https://example.test/cat.png"}}
    assert sent_attachments(chat(text_file, remote)) == []
    anthropic_text = {
        "model": "m",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "text/plain",
                            "data": b64(b"plain words"),
                        },
                    }
                ],
            }
        ],
    }
    assert sent_attachments(anthropic_text, "anthropic_messages") == []


def test_the_same_field_names_elsewhere_are_not_attachments() -> None:
    url = f"data:application/pdf;base64,{b64(STAMPED)}"
    data = {
        "model": "m",
        "user": url,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "hi", "file_data": url}]}
        ],
    }
    assert sent_attachments(data) == []


def test_a_file_name_is_made_safe_and_kept_short() -> None:
    part = file_part(STAMPED, filename="../../etc/\x00passwd" + "x" * 300)
    [a] = sent_attachments(chat(part))
    assert "/" not in a["filename"] and "\x00" not in a["filename"]
    assert len(a["filename"]) <= 104


def test_too_many_or_too_large_files_are_refused_before_the_brain_is_asked() -> None:
    seen: list[dict[str, Any]] = []
    many = chat(*[file_part(STAMPED) for _ in range(dna.MAX_ATTACHMENTS + 1)])
    with pytest.raises(dna.GatewayError) as err:
        _decide(many, "completion", {"decision": "allow"}, seen)
    assert err.value.status_code == 403 and seen == []


def test_a_binary_file_that_is_not_exact_base64_is_refused() -> None:
    bad = {"type": "file", "file": {"file_data": "data:application/pdf;base64,AAA!AAAA"}}
    with pytest.raises(dna.GatewayError) as err:
        sent_attachments(chat(bad))
    assert err.value.status_code == 403


def test_a_file_the_brain_cannot_read_is_blocked_not_passed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "a.wav: This file type is not supported."})

    async def go() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await dna.apply_decision(
                chat(file_part(b"RIFF....WAVE", "a.wav", "audio/wav")),
                user_id="u1",
                team="t",
                headers=None,
                brain_url="http://brain",
                client=client,
            )

    with pytest.raises(dna.GatewayError) as err:
        asyncio.run(go())
    assert err.value.status_code == 403
    assert "a.wav" in err.value.body["message"]


# --- the gateway with the real brain behind it (in process, no Docker) -------------------------


def through_brain(data: dict[str, Any], call_type: str = "completion") -> dict[str, Any]:
    async def go() -> dict[str, Any]:
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport) as client:
            out: dict[str, Any] = await dna.apply_decision(
                data,
                user_id="u-gw-files",
                team="Finance",
                headers=None,
                brain_url="http://brain",
                client=client,
                call_type=call_type,
            )
            return out

    return asyncio.run(go())


def test_a_restricted_pdf_sent_as_a_file_part_is_blocked() -> None:
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat(file_part(STAMPED)))
    assert err.value.status_code == 403
    assert "q4.pdf is marked RESTRICTED" in str(err.value.body)


def test_a_pdf_with_an_iban_asks_first_because_a_file_cannot_be_masked() -> None:
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat(file_part(pdf_with_text(f"Pay {IBAN} today"), "pay.pdf")))
    assert err.value.status_code == 409


def test_a_word_file_with_an_iban_asks_first() -> None:
    docx = docx_bytes(f"Pay {IBAN} today")
    media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat(file_part(docx, "pay.docx", media)))
    assert err.value.status_code == 409


def test_a_clean_pdf_is_allowed_through() -> None:
    out = through_brain(chat(file_part(pdf_with_text("Team lunch on Friday"), "lunch.pdf")))
    assert out["metadata"]["dna_decision"] == "allow"


def test_a_pdf_with_a_text_name_is_still_read_as_a_pdf() -> None:
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat(file_part(STAMPED, "notes.txt", "application/octet-stream")))
    assert err.value.status_code == 403


def test_audio_cannot_be_read_so_it_is_refused() -> None:
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat(file_part(b"RIFF\x00\x00\x00\x00WAVEfmt ", "a.wav", "audio/wav")))
    assert err.value.status_code == 403


@pytest.mark.skipif(not ocr.available(), reason="OCR extra not installed")
def test_a_screenshot_of_a_stamped_page_is_blocked() -> None:
    from tests.test_chat_files import png_bytes

    shot = png_bytes("Board pack", "Classification: RESTRICTED")
    url = f"data:image/png;base64,{b64(shot)}"
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat({"type": "image_url", "image_url": {"url": url}}))
    assert err.value.status_code == 403


def test_an_image_with_no_text_passes_because_nothing_in_it_can_leak() -> None:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(buf, "PNG")
    url = f"data:image/png;base64,{b64(buf.getvalue())}"
    if ocr.available():
        out = through_brain(chat({"type": "image_url", "image_url": {"url": url}}))
        assert out["metadata"]["dna_decision"] == "allow"
    else:  # without OCR the image cannot be read, so it is refused
        with pytest.raises(dna.GatewayError):
            through_brain(chat({"type": "image_url", "image_url": {"url": url}}))


def test_bytes_that_are_not_a_readable_image_are_refused() -> None:
    url = f"data:image/png;base64,{b64(bytes(range(256)) * 2)}"
    with pytest.raises(dna.GatewayError) as err:
        through_brain(chat({"type": "image_url", "image_url": {"url": url}}))
    assert err.value.status_code == 403
