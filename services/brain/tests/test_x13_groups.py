import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain import settings_store
from brain.db import tables as t
from brain.policy import groups
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

IBAN = "GR1601101250000000012300695"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    settings_store._cache.clear()
    groups._clear()
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    with engine.begin() as c:
        c.execute(sa.insert(t.users).values(pseudonym="u-hr", team="HR", role="hr_manager"))
    return TestClient(main.app)


def send(client: TestClient, team: str, user: str = "u-x") -> str:
    body = {"user_id": user, "team": team, "messages": [{"role": "user", "content": f"Pay {IBAN}"}]}
    return client.post("/v1/inspect", json=body).json()["decision"]


def put(client: TestClient, **over: str):
    body = {
        "kind": "team",
        "group": "HR",
        "scope": "category",
        "key": "iban",
        "action": "allow",
        "updated_by": "alex",
    } | over
    return client.put("/v1/policies/groups", json=body)


def test_a_team_override_changes_only_that_team(client: TestClient) -> None:
    assert send(client, "HR") == "mask" and send(client, "Sales") == "mask"
    assert put(client).status_code == 200
    assert send(client, "HR") == "allow"
    assert send(client, "Sales") == "mask"


def test_a_role_override_wins_over_the_team_one(client: TestClient) -> None:
    put(client, kind="team", group="HR", action="allow")
    put(client, kind="role", group="hr_manager", action="block")
    assert send(client, "HR", user="u-hr") == "block"
    assert send(client, "HR", user="someone-else") == "allow"


def test_putting_twice_replaces_and_delete_restores_the_company_policy(
    client: TestClient,
) -> None:
    put(client, action="allow")
    put(client, action="warn")
    assert len(client.get("/v1/policies/groups").json()) == 1
    assert send(client, "HR") == "warn"
    r = client.delete(
        "/v1/policies/groups",
        params={
            "kind": "team",
            "group": "HR",
            "scope": "category",
            "key": "iban",
            "updated_by": "alex",
        },
    )
    assert r.status_code == 200 and r.json() == []
    assert send(client, "HR") == "mask"


@pytest.mark.parametrize(
    "over",
    [{"kind": "city"}, {"group": " "}, {"scope": "x"}, {"key": "nope"}, {"action": "explode"}],
)
def test_bad_overrides_are_refused_in_plain_words(client: TestClient, over: dict[str, str]) -> None:
    r = put(client, **over)
    assert r.status_code == 422 and r.json()["detail"]


def test_changes_are_audited(client: TestClient) -> None:
    put(client)
    audit = client.get("/v1/policies").status_code  # policies still readable
    assert audit == 200
    with main.policy_store.engine.connect() as c:  # type: ignore[union-attr]
        acts = c.execute(sa.text("select action from audit_log")).scalars().all()
    assert "policy.group.update" in acts


def test_without_a_database_nothing_changes() -> None:
    assert groups.load(None) == []
    assert groups.role_of(None, "x") == "employee"


def test_a_db_blip_keeps_the_last_team_overrides(client: TestClient) -> None:
    engine = main.policy_store.engine
    assert engine is not None
    groups._clear()
    with engine.begin() as c:
        groups.put(
            c,
            main.policy_store.current(),
            groups.Override("team", "HR", "category", "iban", "block"),
            "admin",
        )
    groups._clear()
    assert [o.group for o in groups.load(engine)] == ["HR"]
    assert groups.role_of(engine, "u-hr") == "hr_manager"
    groups._cache[id(engine)] = (0.0, groups._cache[id(engine)][1])  # expired
    with engine.begin() as c:
        c.execute(sa.text("DROP TABLE settings"))
        c.execute(sa.text("DROP TABLE users"))
    assert [o.group for o in groups.load(engine)] == ["HR"]
    assert groups.role_of(engine, "u-hr") == "hr_manager"
