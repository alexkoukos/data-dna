"""Unit tests for the gateway glue in infra/gateway/dna_inspect.py (no LiteLLM needed)."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

_PATH = Path(__file__).resolve().parents[3] / "infra" / "gateway" / "dna_inspect.py"
_SPEC = importlib.util.spec_from_file_location("dna_inspect", _PATH)
assert _SPEC and _SPEC.loader
dna = importlib.util.module_from_spec(_SPEC)
sys.modules["dna_inspect"] = dna
_SPEC.loader.exec_module(dna)


def _run(verdict: dict[str, Any] | None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    def handler(request: httpx.Request) -> httpx.Response:
        if verdict is None:
            raise httpx.ConnectError("brain down")
        return httpx.Response(200, json=verdict)

    async def go() -> dict[str, Any]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "raw"}]}
            result: dict[str, Any] = await dna.apply_decision(
                data,
                user_id="u1",
                team="t1",
                headers=headers,
                brain_url="http://brain",
                client=client,
            )
            return result

    return asyncio.run(go())


def test_allow_keeps_request() -> None:
    out = _run({"decision": "allow", "reasons": []})
    assert out["messages"][0]["content"] == "raw"
    assert out["metadata"]["dna_decision"] == "allow"


def test_mask_replaces_messages() -> None:
    masked = [{"role": "user", "content": "[IBAN_1]"}]
    out = _run({"decision": "mask", "reasons": ["Contains iban"], "masked_messages": masked})
    assert out["messages"] == masked


def test_local_reroutes_model() -> None:
    out = _run({"decision": "local", "reasons": ["internal"]})
    assert out["model"] == "local"


def test_warn_returns_409_with_reasons() -> None:
    with pytest.raises(dna.GatewayError) as err:
        _run({"decision": "warn", "reasons": ["Contains card"]})
    assert err.value.status_code == 409
    assert err.value.body["type"] == "warn"
    assert err.value.body["reasons"] == ["Contains card"]


def test_warn_with_ack_header_goes_through() -> None:
    out = _run({"decision": "warn", "reasons": ["x"]}, headers={"X-DNA-Ack": "needed for audit"})
    assert out["metadata"]["dna_decision"] == "warn"


def test_block_returns_403_with_alternative() -> None:
    with pytest.raises(dna.GatewayError) as err:
        _run({"decision": "block", "reasons": ["injection"]})
    assert err.value.status_code == 403
    assert "approved_alternative" in err.value.body


def test_fails_closed_when_brain_is_down() -> None:
    with pytest.raises(dna.GatewayError) as err:
        _run(None)
    assert err.value.status_code == 503
    assert err.value.body["type"] == "unavailable"


def _finalize(handler: Any, session_id: str | None) -> str:
    async def go() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            out: str = await dna.finalize_answer(
                "answer [IBAN_1]",
                user_id="u1",
                team="t1",
                session_id=session_id,
                brain_url="http://brain",
                client=client,
            )
            return out

    return asyncio.run(go())


def test_finalize_filters_then_unmasks() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        text = request.content.decode()
        if request.url.path == "/v1/inspect-output":
            return httpx.Response(200, json={"text": "answer [IBAN_1]"})
        assert "answer [IBAN_1]" in text
        return httpx.Response(200, json={"text": "answer GR16"})

    assert _finalize(handler, "sid") == "answer GR16"
    assert calls == ["/v1/inspect-output", "/v1/unmask"]


def test_finalize_without_session_skips_unmask() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"text": "clean"})

    assert _finalize(handler, None) == "clean"
    assert calls == ["/v1/inspect-output"]


def test_finalize_withholds_answer_when_brain_is_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(dna.GatewayError) as err:
        _finalize(handler, "sid")
    assert err.value.status_code == 503


class _Obj:
    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


def _chunk(content: str | None, finish: str | None = None) -> _Obj:
    return _Obj(choices=[_Obj(delta=_Obj(content=content), finish_reason=finish)])


def _stream(chunks: list[_Obj], transform: Any) -> list[_Obj]:
    async def source() -> Any:
        for c in chunks:
            yield c

    async def go() -> list[_Obj]:
        return [c async for c in dna.rewrite_stream(source(), transform)]

    return asyncio.run(go())


def test_stream_cleans_text_split_across_chunks() -> None:
    seen: list[str] = []

    async def transform(text: str) -> str:
        seen.append(text)
        return text.replace("[IBAN_1]", "GR16")

    out = _stream([_chunk("Check [IB"), _chunk("AN_1] ok"), _chunk(None, "stop")], transform)
    assert seen == ["Check [IBAN_1] ok"]
    assert [c.choices[0].delta.content for c in out] == ["Check GR16 ok", None]
    assert out[-1].choices[0].finish_reason == "stop"


def test_stream_without_text_passes_through() -> None:
    async def transform(text: str) -> str:
        raise AssertionError("should not be called")

    out = _stream([_chunk(None, "stop")], transform)
    assert len(out) == 1


def test_stream_withholds_everything_when_check_fails() -> None:
    async def transform(text: str) -> str:
        raise dna.GatewayError(503, {"type": "unavailable"})

    with pytest.raises(dna.GatewayError):
        _stream([_chunk("secret")], transform)


# --- other ways in: Anthropic messages, responses, embeddings -----------------------------


def _decide(data: dict[str, Any], call_type: str, verdict: dict[str, Any]) -> dict[str, Any]:
    async def go() -> dict[str, Any]:
        handler = lambda request: httpx.Response(200, json=verdict)  # noqa: E731
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            out: dict[str, Any] = await dna.apply_decision(
                data,
                user_id="u1",
                team="t1",
                headers=None,
                brain_url="http://brain",
                client=client,
                call_type=call_type,
            )
            return out

    return asyncio.run(go())


def test_anthropic_text_blocks_are_flattened_and_tool_results_are_included() -> None:
    data = {
        "messages": [
            {"role": "user", "content": "first"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "look at this"},
                    {"type": "tool_result", "tool_use_id": "t", "content": "KEY=abc"},
                ],
            },
        ]
    }
    messages, other = dna.inspection_view(data, "anthropic_messages")
    assert messages[-1]["content"] == "look at this\nKEY=abc"
    assert other is True
    plain, other2 = dna.inspection_view(
        {"messages": [{"role": "user", "content": "hi"}]}, "anthropic_messages"
    )
    assert plain == [{"role": "user", "content": "hi"}] and other2 is False


def test_anthropic_mask_writes_the_masked_text_back_to_the_last_user_message() -> None:
    data = {
        "model": "m",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "pay GR16"}]}],
    }
    out = _decide(
        data,
        "anthropic_messages",
        {
            "decision": "mask",
            "reasons": [],
            "session_id": "s1",
            "masked_messages": [{"role": "user", "content": "pay [IBAN_1]"}],
        },
    )
    assert out["messages"][0]["content"] == "pay [IBAN_1]"
    assert out["metadata"]["dna_session_id"] == "s1"


def test_a_secret_in_a_tool_result_asks_first_because_it_cannot_be_masked_in_place() -> None:
    data = {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t", "content": "KEY=abc"}],
            }
        ]
    }
    with pytest.raises(dna.GatewayError) as err:
        _decide(
            data,
            "anthropic_messages",
            {
                "decision": "mask",
                "reasons": ["Contains secret"],
                "masked_messages": [{"role": "user", "content": "KEY=[S_1]"}],
            },
        )
    assert err.value.status_code == 409
    assert any("cannot be masked" in r for r in err.value.body["reasons"])


def test_responses_input_is_checked_and_masked() -> None:
    out = _decide(
        {"model": "m", "input": "pay GR16"},
        "responses",
        {
            "decision": "mask",
            "reasons": [],
            "masked_messages": [{"role": "user", "content": "pay [IBAN_1]"}],
        },
    )
    assert out["input"] == "pay [IBAN_1]"


def test_embeddings_cannot_go_local_and_unknown_requests_are_refused() -> None:
    with pytest.raises(dna.GatewayError) as err:
        _decide(
            {"input": "secret text"},
            "embeddings",
            {"decision": "local", "reasons": ["Matches a confidential document"]},
        )
    assert err.value.status_code == 403
    with pytest.raises(dna.GatewayError) as err2:
        _decide({"prompt": "draw a cat"}, "image_generation", {"decision": "allow", "reasons": []})
    assert err2.value.status_code == 403 and "not available" in err2.value.body["message"]
