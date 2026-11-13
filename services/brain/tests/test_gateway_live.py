"""Live integration test through the gateway. Needs `make up`; skipped otherwise.

Run with: make test-gateway
"""

import os

import httpx
import pytest
from openai import OpenAI, PermissionDeniedError

GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:4000")
MASTER = os.environ.get("LITELLM_MASTER_KEY", "sk-admin-change-me")


def _gateway_up() -> bool:
    try:
        return httpx.get(f"{GATEWAY}/health/liveliness", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _gateway_up(), reason="gateway not running (make up)")


@pytest.fixture(scope="module")
def client() -> OpenAI:
    admin = {"Authorization": f"Bearer {MASTER}"}
    httpx.post(f"{GATEWAY}/team/new", headers=admin, json={"team_id": "itest"})
    resp = httpx.post(
        f"{GATEWAY}/key/generate",
        headers=admin,
        json={
            "user_id": "u-itest",
            "team_id": "itest",
            "models": ["demo-mock", "demo-echo", "demo-leaky"],
        },
    )
    resp.raise_for_status()
    return OpenAI(base_url=f"{GATEWAY}/v1", api_key=resp.json()["key"], max_retries=0)


def _ask(client: OpenAI, text: str, model: str = "demo-mock", **kwargs: object) -> str:
    out = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": text}],
        **kwargs,  # type: ignore[arg-type]
    )
    return out.choices[0].message.content or ""


def test_clean_prompt_is_answered(client: OpenAI) -> None:
    assert "safety check" in _ask(client, "Summarize our meeting notes")


def test_masked_prompt_is_answered(client: OpenAI) -> None:
    assert "safety check" in _ask(client, "Check IBAN GR1601101250000000012300695")


def test_warn_returns_409_and_ack_proceeds(client: OpenAI) -> None:
    risky = "AMKA 01011990123 card 4111 1111 1111 1111 IBAN GR1601101250000000012300695"
    with pytest.raises(Exception) as err:
        _ask(client, risky)
    assert getattr(err.value, "status_code", None) == 409
    assert "safety check" in _ask(client, risky, extra_headers={"X-DNA-Ack": "audit"})


def test_unknown_key_is_rejected() -> None:
    bad = OpenAI(base_url=f"{GATEWAY}/v1", api_key="sk-nope", max_retries=0)
    with pytest.raises((PermissionDeniedError, Exception)):
        _ask(bad, "hi")


def test_masked_value_is_restored_in_the_answer(client: OpenAI) -> None:
    answer = _ask(client, "Check IBAN GR1601101250000000012300695", model="demo-echo")
    assert "GR1601101250000000012300695" in answer
    assert "[IBAN_1]" not in answer


def test_secret_in_a_model_answer_is_masked(client: OpenAI) -> None:
    answer = _ask(client, "How do I deploy?", model="demo-leaky")
    assert "AKIAIOSFODNN7EXAMPLE" not in answer


def _stream(client: OpenAI, text: str, model: str) -> str:
    stream = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": text}], stream=True
    )
    return "".join(c.choices[0].delta.content or "" for c in stream if c.choices)


def test_streamed_answer_gets_masked_value_back(client: OpenAI) -> None:
    answer = _stream(client, "Check IBAN GR1601101250000000012300695", "demo-echo")
    assert "GR1601101250000000012300695" in answer
    assert "[IBAN_1]" not in answer


def test_streamed_answer_is_filtered(client: OpenAI) -> None:
    answer = _stream(client, "How do I deploy?", "demo-leaky")
    assert "AKIAIOSFODNN7EXAMPLE" not in answer
