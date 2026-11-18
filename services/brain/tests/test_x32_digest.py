"""X32: weekly team digest. Numbers match the incidents of the seeded company, and no employee
name, pseudonym or message text appears anywhere in it."""

import json
from collections import Counter
from datetime import date, timedelta

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain import digest
from brain.ask.free import create_views
from brain.db import tables as t
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata
from brain.queries import reference_time
from brain.seed.load import run_seed

ANCHOR = date(2026, 11, 14)


@pytest.fixture(scope="module")
def engine(tmp_path_factory: pytest.TempPathFactory) -> sa.Engine:
    e = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(e)
    policy_metadata.create_all(e)
    assert run_seed(e, log_dir=tmp_path_factory.mktemp("logs"), anchor=ANCHOR)
    create_views(e)
    return e


@pytest.fixture
def client(engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app)


def _direct(engine: sa.Engine, team: str) -> tuple[Counter[str], int, Counter[str]]:
    """The same numbers straight from the incidents table, written independently of digest.py."""
    with engine.connect() as conn:
        ref = reference_time(conn)
        assert ref is not None
        rows = conn.execute(
            sa.select(t.incidents.c.decision, t.incidents.c.categories, t.incidents.c.ts).where(
                t.incidents.c.team == team
            )
        ).all()
    start = ref - timedelta(days=7)
    prev_start = ref - timedelta(days=14)

    def aware(ts):  # type: ignore[no-untyped-def]
        return ts if ts.tzinfo else ts.replace(tzinfo=ref.tzinfo)

    this = [r for r in rows if start < aware(r[2]) <= ref]
    prev = [r for r in rows if prev_start < aware(r[2]) <= start]
    cats: Counter[str] = Counter()
    for r in this:
        cats.update(set(r[1] or []))
    return Counter(r[0] for r in this), len(prev), cats


def test_every_team_matches_the_incidents_table(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        names = digest.teams(conn)
        assert len(names) >= 3
        checked = 0
        for team in names:
            d = digest.build(conn, team)
            outcomes, prev, cats = _direct(engine, team)
            assert d["outcomes"] == dict(outcomes), team
            assert d["incidents"] == sum(outcomes.values()), team
            assert d["previous"] == prev, team
            assert d["change"] == d["incidents"] - prev
            assert {c["category"]: c["count"] for c in d["categories"]} == dict(cats.most_common(5))
            checked += d["incidents"]
    assert checked > 50  # the seeded company has real numbers, so this is not trivially empty


def test_tools_carry_their_approval_from_the_inventory(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        team = max(digest.teams(conn), key=lambda x: digest.build(conn, x)["incidents"])
        d = digest.build(conn, team)
        inv = dict(conn.execute(sa.text("SELECT name, approval FROM v_inventory")).all())
    assert d["tools"]
    assert all(t_["approval"] == inv.get(t_["name"], "unknown") for t_ in d["tools"])
    assert sum(t_["count"] for t_ in d["tools"]) <= d["incidents"]


def test_two_or_three_tips_chosen_from_the_categories_that_fired(engine: sa.Engine) -> None:
    with engine.connect() as conn:
        for team in digest.teams(conn):
            d = digest.build(conn, team)
            assert 2 <= len(d["tips"]) <= 3
            fired = [c["category"] for c in d["categories"]]
            expected = [digest.TIPS[c] for c in fired if c in digest.TIPS][:2]
            assert d["tips"][: len(expected)] == expected


def test_no_names_pseudonyms_or_message_text_anywhere(
    engine: sa.Engine, client: TestClient
) -> None:
    with engine.connect() as conn:
        pseudonyms = [r[0] for r in conn.execute(sa.text("SELECT pseudonym FROM users"))]
        names = [r[0] for r in conn.execute(sa.text("SELECT display_name FROM users")) if r[0]]
        previews = [
            r[0] for r in conn.execute(sa.text("SELECT masked_preview FROM incidents")) if r[0]
        ]
        team = digest.teams(conn)[0]
    out = client.get("/v1/digest", params={"team": team}).json()
    blob = json.dumps(out) + client.get("/v1/digest.md", params={"team": team}).text
    assert len(pseudonyms) > 100 and names
    for who in pseudonyms + names:
        assert who not in blob
    for preview in previews[:200]:
        assert preview not in blob
    assert "no employee names" in out["note"] and out["note"] in out["markdown"]
    assert out["note"] in out["email"]["body"]


def test_digest_reads_only_the_views_and_never_the_person_column(engine: sa.Engine) -> None:
    seen: list[str] = []

    def spy(conn, cursor, statement, *_):  # type: ignore[no-untyped-def]
        seen.append(statement.lower())

    sa.event.listen(engine, "before_cursor_execute", spy)
    try:
        with engine.connect() as conn:
            digest.build(conn, digest.teams(conn)[0])
    finally:
        sa.event.remove(engine, "before_cursor_execute", spy)
    assert len(seen) >= 4
    for sql in seen:
        assert "v_incidents" in sql or "v_inventory" in sql  # the views, never the tables
        assert "person" not in sql and "pseudonym" not in sql and "display_name" not in sql
        assert "masked_preview" not in sql
        assert " users" not in sql


def test_endpoints_return_markdown_and_an_email_draft(
    client: TestClient, engine: sa.Engine
) -> None:
    with engine.connect() as conn:
        team = digest.teams(conn)[0]
    assert team in client.get("/v1/digest/teams").json()
    out = client.get("/v1/digest", params={"team": team}).json()
    assert out["markdown"].startswith(f"# Weekly AI digest: {team}")
    assert "## Do this instead" in out["markdown"]
    assert out["email"]["subject"] == f"Weekly AI digest for {team}"
    assert "Do this instead:" in out["email"]["body"]
    md = client.get("/v1/digest.md", params={"team": team})
    assert md.headers["content-type"].startswith("text/markdown")
    assert "attachment" in md.headers["content-disposition"]
    assert md.text == out["markdown"]


def test_a_team_with_no_incidents_gets_an_honest_digest(client: TestClient) -> None:
    out = client.get("/v1/digest", params={"team": "Nobody"}).json()
    assert out["incidents"] == 0 and out["outcomes"] == {}
    assert len(out["tips"]) >= 2
    assert "0 this week" in out["markdown"] or "none the week before" in out["markdown"]


def test_trend_wording() -> None:
    base = {"incidents": 12, "previous": 10, "change": 2, "change_pct": 20}
    assert digest._trend(base) == "12 this week, up by 2 (20%) on last week (10)."
    assert digest._trend({**base, "incidents": 8, "change": -2, "change_pct": -20}) == (
        "8 this week, down by 2 (20%) on last week (10)."
    )
    assert digest._trend({**base, "incidents": 10, "change": 0, "change_pct": 0}) == (
        "10 this week, unchanged on last week (10)."
    )
    assert digest._trend({**base, "previous": 0, "change": 12, "change_pct": None}) == (
        "12 this week, none the week before."
    )


def test_an_unapproved_tool_adds_a_company_ai_tip() -> None:
    tips = digest._tips(["iban"], [{"name": "Perplexity", "approval": "unapproved", "count": 3}])
    assert len(tips) == 2 and "Use Company AI instead of Perplexity" in tips[1]
