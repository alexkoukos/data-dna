"""X6 (more Greek identifiers) and X7 (the model's answer is checked before the user sees it)."""

from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.detection.entities import EntityDetector
from brain.detection.patterns import find_patterns
from brain.detection.pipeline import inspect_text
from brain.honeytokens import HoneytokenStore, generate
from brain.policy.engine import Decision
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata


@pytest.mark.parametrize(
    ("text", "entity", "value"),
    [
        ("Η ΑΔΤ μου είναι ΑΖ 123456", "ADT", "ΑΖ 123456"),
        ("ταυτότητα: AK-654321", "ADT", "AK-654321"),
        ("identity card AB 123456, issued in Athens", "ADT", "AB 123456"),
        ("πινακίδα ΙΚΑ 1234 του αυτοκινήτου", "PLATE", "ΙΚΑ 1234"),
        ("license plate YBK-4821", "PLATE", "YBK-4821"),
        ("ΓΕΜΗ 123456789012", "GEMI", "123456789012"),
        ("GEMI number 123456789", "GEMI", "123456789"),
        ("My passport number is AK1234567", "PASSPORT", "AK1234567"),
        ("διαβατήριο: ΑΒ 1234567", "PASSPORT", "ΑΒ 1234567"),
    ],
)
def test_identifiers_with_a_word_that_names_them(text: str, entity: str, value: str) -> None:
    found = [f for f in find_patterns(text) if f.entity == entity]
    assert [f.value for f in found] == [value]
    assert inspect_text(text).verdict.decision == Decision.MASK


@pytest.mark.parametrize(
    "text",
    [
        "Order AZ 123456 shipped yesterday",  # same shape, no word that names it
        "Plate of glass ABC 1234 is in stock",
        "the passport photo AK1234567 was bad",
        "passport 1234567",
        "GEMI is a Greek registry",
        "Ο αριθμός 123456789012 είναι τηλέφωνο γραφείου",
    ],
)
def test_the_same_shapes_without_context_are_left_alone(text: str) -> None:
    assert [
        f for f in find_patterns(text) if f.entity in {"ADT", "PLATE", "GEMI", "PASSPORT"}
    ] == []


@pytest.mark.parametrize(
    "text",
    [
        "Call +30 694 123 4567",
        "+30 210 123 4567",
        "0030 6941234567",
        "+306941234567",
        "210 123 4567",
        "210-1234567",
        "tel 6941234567",
    ],
)
def test_greek_phone_formats(text: str) -> None:
    found = EntityDetector().find(text)
    assert any(f.entity == "PHONE" for f in found), text


@pytest.mark.parametrize("text", ["Order 2101234567 shipped", "amount 2.101.234.567 euros"])
def test_long_numbers_are_not_phones(text: str) -> None:
    assert not any(f.entity == "PHONE" for f in EntityDetector().find(text))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.insert(t.documents).values(
                id=1, title="Board memo", sensitivity="restricted", created_at=datetime.now(UTC)
            )
        )
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app)


def test_answer_with_a_key_is_masked_not_withheld(client: TestClient) -> None:
    out = client.post(
        "/v1/inspect-output", json={"text": "Use AKIAIOSFODNN7EXAMPLE and your passport AK1234567"}
    ).json()
    assert out["changed"] and not out["withheld"]
    assert "AKIAIOSFODNN7EXAMPLE" not in out["text"] and "AK1234567" not in out["text"]
    assert out["text"].startswith("Use [")


def test_answer_with_a_decoy_is_withheld_and_recorded(client: TestClient) -> None:
    engine = main.policy_store.engine
    assert engine is not None
    key = next(x for x in generate(3) if x.kind == "aws_key")
    HoneytokenStore(engine).register(1, [key])
    out = client.post(
        "/v1/inspect-output",
        json={"user_id": "u1", "team": "Sales", "text": f"Sure, the key is {key.value}."},
    ).json()
    assert out["withheld"] and key.value not in out["text"]
    assert "held back" in out["text"]
    assert any("Board memo" in r for r in out["reasons"])
    with engine.connect() as conn:
        rows = conn.execute(sa.select(t.incidents.c.tool, t.incidents.c.decision)).all()
        audit = conn.execute(sa.text("select action from audit_log")).all()
    assert rows == [("Company AI (answer)", "block")]
    assert ("honeytoken.triggered",) in audit


def test_answer_may_mention_names_and_source_code(client: TestClient) -> None:
    text = "Delphi Insurance asked Maria Georgiou to run curl https://billing.corp.aegean.gr/api"
    out = client.post("/v1/inspect-output", json={"text": text}).json()
    assert out["changed"] is False and out["text"] == text and not out["withheld"]


def test_clean_answer_is_untouched(client: TestClient) -> None:
    out = client.post("/v1/inspect-output", json={"text": "Bread needs flour and water."}).json()
    assert out["text"] == "Bread needs flour and water." and out["changed"] is False


def test_answer_that_repeats_a_restricted_document_is_withheld(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from brain.documents.embeddings import HashingEmbedder
    from brain.documents.registry import register_document

    memo = (
        "The management team recommends opening offices in Sofia and Belgrade during the second "
        "quarter of 2027. The plan assumes an initial investment of four million euros, financed "
        "from retained earnings, with break even expected after twenty two months. We intend to "
        "acquire a small Sofia firm for one and a half million euros which gives us an existing "
        "client base in banking and telecommunications."
    )
    engine = main.policy_store.engine
    assert engine is not None
    monkeypatch.setattr(main, "embedder", HashingEmbedder())
    register_document(engine, HashingEmbedder(), "Board memo copy", "restricted", memo)
    out = client.post("/v1/inspect-output", json={"text": "Here it is: " + memo}).json()
    assert out["withheld"] and memo[:40] not in out["text"]
