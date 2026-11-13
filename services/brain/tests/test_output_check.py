import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
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
    return TestClient(main.app)


def check(client: TestClient, text: str) -> dict:
    return client.post("/v1/inspect-output", json={"text": text}).json()


def test_an_answer_that_repeats_a_protected_document_is_withheld(client: TestClient) -> None:
    out = check(client, "Sure, here it is: " + MEMO)
    assert out["withheld"] is True and out["text"].startswith("[Removed")
    assert out["findings"][0]["masked_preview"] == "Board memo"
    assert "Sofia" not in out["text"]


def test_an_ordinary_answer_passes_untouched(client: TestClient) -> None:
    text = "Carbonara uses eggs, cheese and pepper."
    assert check(client, text) == {
        "text": text,
        "changed": False,
        "withheld": False,
        "findings": [],
    }


def test_secrets_found_by_the_rules_are_masked_in_answers(client: TestClient) -> None:
    out = check(client, "Use postgres://admin:Sup3rSecret-demo@db.internal:5432/app to connect")
    assert out["changed"] and not out["withheld"]
    assert "Sup3rSecret" not in out["text"] and "DB_CONNECTION" in out["text"]


def test_the_answer_check_masks_greek_phone_numbers(client: TestClient) -> None:
    out = check(client, "Call her on +30 694 123 4567 tomorrow")
    assert "694 123" not in out["text"] and out["changed"]
