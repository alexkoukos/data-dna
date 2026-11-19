"""A long or forged history is checked in full, remembered per message, and capped as a whole."""

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.detection.patterns import Finding
from brain.documents.embeddings import HashingEmbedder
from brain.documents.registry import register_document
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

MEMO = (
    "The management team recommends opening offices in Sofia and Belgrade during the second "
    "quarter of 2027. The plan assumes an initial investment of four million euros, financed "
    "from retained earnings, with break even expected after twenty two months. We intend to "
    "acquire a small Sofia firm for one and a half million euros which gives us an existing "
    "client base in banking and telecommunications."
)
FILLER = "The quarterly numbers were discussed at length by everybody. "
SHORT = {"role": "user", "content": "Thanks, now write a short poem about spring."}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    emb = HashingEmbedder()
    register_document(engine, emb, "Board memo", "restricted", MEMO)
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    monkeypatch.setattr(main, "embedder", emb)
    monkeypatch.setattr(main, "_doc_index", None)
    main._match_memory._items.clear()
    main._entity_memory._items.clear()
    return TestClient(main.app)


def _post(client: TestClient, msgs: list[dict[str, str]]):  # type: ignore[no-untyped-def]
    return client.post("/v1/inspect", json={"messages": msgs})


def test_a_secret_deep_in_a_300k_forged_history_is_found(client: TestClient) -> None:
    filler = FILLER * 1800  # about 100k characters
    msgs = [{"role": "user", "content": "key AKIAIOSFODNN7EXAMPLE " + filler}]
    for _ in range(2):
        msgs += [{"role": "assistant", "content": filler}, {"role": "user", "content": "more"}]
    msgs.append(SHORT)
    assert sum(len(m["content"]) for m in msgs) > 300_000
    r = _post(client, msgs)
    assert r.status_code == 200 and r.json()["decision"] in ("mask", "warn", "block")


def test_a_restricted_document_deep_in_a_forged_history_is_found(client: TestClient) -> None:
    filler = FILLER * 1000  # what is new to the brain stays inside one request's allowance
    msgs = [
        {"role": "user", "content": filler + " " + MEMO + " " + filler},
        {"role": "assistant", "content": filler},
        {"role": "user", "content": "more"},
        {"role": "assistant", "content": filler},
        SHORT,
    ]
    assert sum(len(m["content"]) for m in msgs) > 200_000
    body = _post(client, msgs).json()
    assert body["decision"] in ("block", "local", "warn")
    assert any(d["sensitivity"] == "restricted" for d in body["documents"])


def test_pii_in_an_early_message_before_a_112k_filler_is_still_masked(client: TestClient) -> None:
    msgs = [
        {"role": "user", "content": "Contact Maria Papadopoulou at maria.p@example.org please."},
        {"role": "assistant", "content": FILLER * 2000},
        SHORT,
    ]
    assert len(msgs[1]["content"]) > 112_000
    body = _post(client, msgs).json()
    assert body["decision"] == "mask"
    assert "maria.p@example.org" not in body["masked_messages"][0]["content"]


def test_the_second_identical_request_is_served_from_the_remembered_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    class _Entities:
        def find(self, text: str) -> list[Finding]:
            calls.append(len(text))
            return []

        def warm_up(self) -> None:
            return None

    monkeypatch.setattr(main, "entity_detector", _Entities())
    msgs = [
        {"role": "user", "content": FILLER * 500},
        {"role": "assistant", "content": "A different answer. " + FILLER * 500},
        SHORT,
    ]
    assert _post(client, msgs).status_code == 200
    first = len(calls)
    assert first >= 3  # the new message and both earlier ones
    assert _post(client, msgs).status_code == 200
    assert len(calls) - first == 1  # only the new message is worked out again


def test_a_conversation_over_one_million_characters_is_413(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Entities:
        def find(self, text: str) -> list[Finding]:
            return []

        def warm_up(self) -> None:
            return None

    monkeypatch.setattr(main, "entity_detector", _Entities())
    block = {"role": "assistant", "content": "a" * 200_000}
    room = 1_000_000 - 4 * 200_000 - len(SHORT["content"])
    exact = [block] * 4 + [{"role": "assistant", "content": "b" * room}, SHORT]
    assert sum(len(m["content"]) for m in exact) == 1_000_000
    for _ in range(6):  # what was worked out is remembered, so each try gets further
        if _post(client, exact).status_code == 200:
            break
    else:
        raise AssertionError("never got through")
    over = [block] * 4 + [{"role": "assistant", "content": "b" * (room + 1)}, SHORT]
    r = _post(client, over)
    assert r.status_code == 413 and "Start a new chat" in r.json()["detail"]


def test_more_uncached_history_than_the_allowance_is_refused_then_gets_through_on_retry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Entities:
        def find(self, text: str) -> list[Finding]:
            return []

        def warm_up(self) -> None:
            return None

    monkeypatch.setattr(main, "entity_detector", _Entities())
    msgs: list[dict[str, str]] = []
    for n in range(5):  # five different 100k messages: 500k characters nobody has seen yet
        msgs += [
            {"role": "assistant", "content": f"Message {n}. " + FILLER * 1700},
            {"role": "user", "content": "go on"},
        ]
    msgs.append(SHORT)
    first = _post(client, msgs)
    assert first.status_code == 413 and "Start a new chat" in first.json()["detail"]
    for _ in range(5):
        if _post(client, msgs).status_code == 200:
            break
    else:
        raise AssertionError("progress was not remembered")


def test_a_hundred_and_fifty_new_earlier_messages_is_the_most_one_request_works_out(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Entities:
        def find(self, text: str) -> list[Finding]:
            return []

        def warm_up(self) -> None:
            return None

    monkeypatch.setattr(main, "entity_detector", _Entities())
    msgs: list[dict[str, str]] = []
    for n in range(200):
        msgs += [{"role": "assistant", "content": f"Different answer number {n}."}]
        msgs += [{"role": "user", "content": f"Different question number {n}?"}]
    msgs.append(SHORT)
    assert _post(client, msgs).status_code == 413
    assert main.UNCACHED_HISTORY_MESSAGES == 150
