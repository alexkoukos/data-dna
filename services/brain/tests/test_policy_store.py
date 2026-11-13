import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.detection.pipeline import inspect_text
from brain.policy.engine import Decision
from brain.policy.store import PolicyError, PolicyStore, audit_table, load_seed, metadata


def _store() -> PolicyStore:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    metadata.create_all(engine)
    return PolicyStore(engine, ttl_seconds=0)


def test_seed_matches_defaults() -> None:
    seed = load_seed()
    assert seed.categories["iban"] == Decision.MASK
    assert seed.categories["injection"] == Decision.BLOCK
    assert seed.sensitivity["restricted"] == Decision.BLOCK


def test_seed_if_empty_runs_once() -> None:
    store = _store()
    assert store.seed_if_empty() == 12
    assert store.seed_if_empty() == 0


def test_update_changes_current_and_writes_audit() -> None:
    store = _store()
    store.seed_if_empty()
    store.update("category", "iban", "warn", "alice")
    assert store.current().categories["iban"] == Decision.WARN
    with store._engine.connect() as conn:  # type: ignore[union-attr]
        row = conn.execute(sa.select(audit_table)).mappings().one()
    assert row["actor"] == "alice"
    assert row["target"] == "category:iban"
    assert row["details"] == {"from": "mask", "to": "warn"}


@pytest.mark.parametrize(
    ("scope", "key", "action", "actor"),
    [
        ("nope", "iban", "warn", "a"),
        ("category", "nope", "warn", "a"),
        ("category", "iban", "explode", "a"),
        ("category", "iban", "warn", " "),
    ],
)
def test_update_rejects_bad_input(scope: str, key: str, action: str, actor: str) -> None:
    with pytest.raises(PolicyError):
        _store().update(scope, key, action, actor)


def test_without_database_uses_seed_and_refuses_edits() -> None:
    store = PolicyStore(None)
    assert store.current().categories["card"] == Decision.MASK
    with pytest.raises(PolicyError):
        store.update("category", "card", "warn", "a")


def test_unreachable_database_falls_back_to_seed() -> None:
    store = PolicyStore(
        sa.create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        ),
        ttl_seconds=0,
    )
    # tables were never created, so the query fails
    assert store.current().categories["iban"] == Decision.MASK


def test_edited_policy_changes_the_decision(valid_iban: str) -> None:
    store = _store()
    store.seed_if_empty()
    store.update("category", "iban", "block", "alice")
    result = inspect_text(f"Pay {valid_iban}", store.current())
    assert result.verdict.decision == Decision.BLOCK


def test_policy_api_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store()
    store.seed_if_empty()
    monkeypatch.setattr(main, "policy_store", store)
    client = TestClient(main.app)
    rows = client.get("/v1/policies").json()
    assert (rows[0]["scope"], rows[0]["key"]) == ("category", "card")
    ok = client.put(
        "/v1/policies",
        json={"scope": "category", "key": "iban", "action": "warn", "updated_by": "bob"},
    )
    assert ok.status_code == 200
    assert ok.json()["action"] == "warn"
    bad = client.put(
        "/v1/policies",
        json={"scope": "category", "key": "iban", "action": "explode", "updated_by": "bob"},
    )
    assert bad.status_code == 422
    assert "Use one of" in bad.json()["detail"]
