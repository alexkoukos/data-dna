"""X4: decoy credentials planted in documents raise an alarm, and only they do."""

import random
import string
from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.detection.pipeline import inspect_text
from brain.documents.embeddings import HashingEmbedder
from brain.documents.loader import header_honeytokens, load_documents
from brain.honeytokens import HoneytokenStore, generate, plant_block
from brain.policy.engine import Decision
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

DOCS = Path(__file__).parents[3] / "data" / "documents"


@pytest.fixture
def engine() -> sa.Engine:
    e = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(e)
    policy_metadata.create_all(e)
    with e.begin() as conn:
        conn.execute(
            sa.insert(t.documents).values(
                id=1, title="Board memo", sensitivity="restricted", created_at=datetime.now(UTC)
            )
        )
    return e


def test_generated_tokens_look_real_and_are_unique() -> None:
    tokens = generate(60)
    assert len({x.value for x in tokens}) == 60
    assert {x.kind for x in tokens} == {"aws_key", "api_key", "mailbox"}
    for x in tokens:
        if x.kind == "aws_key":
            assert x.value.startswith("AKIA") and len(x.value) == 20
        if x.kind == "api_key":
            assert x.value.startswith("sk-live-") and len(x.value) == 40
        if x.kind == "mailbox":
            assert "@" in x.value and x.value.endswith(".example")


def test_plant_block_holds_every_value() -> None:
    tokens = generate(3)
    block = plant_block(tokens)
    assert all(x.value in block for x in tokens) and len(block.splitlines()) == 3


def test_store_finds_registered_tokens_in_any_letter_case(engine: sa.Engine) -> None:
    store = HoneytokenStore(engine, ttl_seconds=0)
    tokens = generate(3)
    assert store.register(1, tokens) == 3
    assert store.register(1, tokens) == 0  # stored once
    for x in tokens:
        found = store.find(f"please check {x.value.upper()} for me")
        assert [f.category for f in found] == ["honeytoken"]
        owner = store.owner(found[0].value)
        assert owner is not None and owner.title == "Board memo"
    assert store.find("nothing planted here") == []


def test_a_decoy_blocks_even_though_it_looks_like_a_cloud_key(engine: sa.Engine) -> None:
    store = HoneytokenStore(engine, ttl_seconds=0)
    key = next(x for x in generate(3) if x.kind == "aws_key")
    store.register(1, [key])
    res = inspect_text(f"Is {key.value} still valid?", priority_finder=store.find)
    assert res.verdict.decision == Decision.BLOCK
    assert [f.category for f in res.findings] == ["honeytoken"]
    assert "[HONEYTOKEN_1]" in res.masked_text
    # The same shape that is not a decoy is an ordinary secret: masked, not blocked.
    other = inspect_text("Is AKIA" + "A" * 16 + " valid?", priority_finder=store.find)
    assert other.verdict.decision == Decision.MASK


def test_no_false_alarms_on_lookalike_keys_and_ordinary_text(engine: sa.Engine) -> None:
    store = HoneytokenStore(engine, ttl_seconds=0)
    store.register(1, generate(6))
    rng = random.Random(3)
    alnum = string.ascii_letters + string.digits
    texts = (
        [
            "AKIA" + "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(16))
            for _ in range(200)
        ]
        + ["sk-live-" + "".join(rng.choice(alnum) for _ in range(32)) for _ in range(200)]
        + ["Summarise the quarterly numbers for the board", "Πες μου ένα ανέκδοτο", ""]
    )
    for text in texts:
        assert not any(f.category == "honeytoken" for f in store.find(text)), text


def test_header_lists_become_tokens() -> None:
    raw = (
        "---\ntitle: x\nsensitivity: internal\nhoneytokens:\n  - AKIAAAAAAAAAAAAAAAAA\n"
        "  - sk-live-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
        "  - a.b@vault-1.corp-internal.example\n---\ntext"
    )
    kinds = [x.kind for x in header_honeytokens(raw)]
    assert kinds == ["aws_key", "api_key", "mailbox"]
    assert header_honeytokens("no header") == []


def test_every_demo_document_carries_its_decoys_in_the_text(engine: sa.Engine) -> None:
    count = load_documents(engine, HashingEmbedder(), DOCS, keep_text=False)
    assert count == 3
    store = HoneytokenStore(engine, ttl_seconds=0)
    assert store.count() == 6
    for f in DOCS.glob("*.md"):
        body = f.read_text(encoding="utf-8").split("---", 2)[2]
        assert len([x for x in store.find(body)]) == 2, f.name


@pytest.fixture
def client(engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app)


def test_plant_endpoint_then_leak_is_an_alarm(client: TestClient, engine: sa.Engine) -> None:
    r = client.post("/v1/documents/1/honeytokens", json={"count": 2})
    assert r.status_code == 200 and r.json()["tokens"] == 2
    leaked = r.json()["plant_block"].splitlines()[0].split(": ", 1)[1]
    out = client.post(
        "/v1/inspect",
        json={
            "user_id": "u-test",
            "team": "Sales",
            "messages": [{"role": "user", "content": f"What is this? {leaked}"}],
        },
    ).json()
    assert out["decision"] == "block"
    assert any("Board memo" in x and "left the company" in x for x in out["reasons"])
    with engine.connect() as conn:
        audit = conn.execute(
            sa.text("select action, target from audit_log where action = 'honeytoken.triggered'")
        ).all()
        incident = conn.execute(
            sa.select(t.incidents.c.document_id, t.incidents.c.categories)
        ).all()
    assert audit == [("honeytoken.triggered", "document:1")]
    assert incident[0][0] == 1 and "honeytoken" in incident[0][1]


def test_plant_endpoint_rejects_an_unknown_document(client: TestClient) -> None:
    assert client.post("/v1/documents/99/honeytokens", json={}).status_code == 404
