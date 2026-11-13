from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.documents.embeddings import HashingEmbedder
from brain.documents.registry import DocMatch
from brain.documents.session import update_coverage
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


@pytest.fixture
def conn() -> sa.Connection:
    e = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(e)
    with e.begin() as c:
        c.execute(sa.insert(t.users).values(pseudonym="u1", team="x", role="employee"))
        c.execute(sa.insert(t.users).values(pseudonym="u2", team="x", role="employee"))
        c.execute(sa.insert(t.documents).values(title="Memo", sensitivity="confidential"))
    return e.connect()


def match(chunks: list[int], sens: str = "confidential", total: int = 10) -> DocMatch:
    return DocMatch(1, "Memo", sens, 0.9, "paraphrase", chunks, total)


def test_coverage_grows_across_prompts_until_it_escalates(conn: sa.Connection) -> None:
    first = update_coverage(conn, 1, [match([0, 1])], NOW)[0]
    assert (first.coverage, first.prompts, first.escalate) == (0.2, 1, False)
    second = update_coverage(conn, 1, [match([1, 2, 3])], NOW + timedelta(minutes=5))[0]
    assert (second.coverage, second.prompts, second.escalate) == (0.4, 2, True)
    assert second.reason == "40% of 'Memo' rebuilt from 2 prompts"


def test_the_same_chunks_again_do_not_add_coverage(conn: sa.Connection) -> None:
    update_coverage(conn, 1, [match([0, 1])], NOW)
    again = update_coverage(conn, 1, [match([0, 1])], NOW + timedelta(minutes=1))[0]
    assert again.coverage == 0.2 and again.prompts == 2


def test_the_window_resets_after_24_hours(conn: sa.Connection) -> None:
    update_coverage(conn, 1, [match([0, 1, 2])], NOW)
    later = update_coverage(conn, 1, [match([5])], NOW + timedelta(hours=25))[0]
    assert (later.coverage, later.prompts, later.escalate) == (0.1, 1, False)


def test_people_are_counted_separately(conn: sa.Connection) -> None:
    update_coverage(conn, 1, [match([0, 1, 2])], NOW)
    other = update_coverage(conn, 2, [match([3])], NOW)[0]
    assert other.coverage == 0.1


def test_a_restricted_document_escalates_on_the_third_prompt(conn: sa.Connection) -> None:
    flags = [
        update_coverage(conn, 1, [match([i], "restricted", 100)], NOW)[0].escalate for i in range(3)
    ]
    assert flags == [False, False, True]


def test_unknown_total_does_not_divide_by_zero(conn: sa.Connection) -> None:
    assert update_coverage(conn, 1, [match([0], total=0)], NOW)[0].coverage == 0.0


def test_rebuilding_a_confidential_document_over_prompts_ends_in_a_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    monkeypatch.setattr(main, "embedder", HashingEmbedder())
    client = TestClient(main.app)
    text = " ".join(f"clause{i} fee{i * 7} term{i * 13}" for i in range(60))
    client.post(
        "/v1/documents", data={"title": "Deal", "sensitivity": "confidential", "text": text}
    )
    words = text.split()

    def ask(part: str) -> dict:  # type: ignore[type-arg]
        return client.post(
            "/v1/inspect",
            json={
                "user_id": "u-rebuild",
                "team": "Exec",
                "model": "m",
                "messages": [{"role": "user", "content": part}],
            },
        ).json()

    decisions = [ask(" ".join(words[i : i + 24])) for i in (0, 24, 48, 72, 96, 120)]
    assert decisions[0]["decision"] == "local"
    assert decisions[-1]["decision"] == "block"
    assert any("rebuilt from" in r for r in decisions[-1]["reasons"])
