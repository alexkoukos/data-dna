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
