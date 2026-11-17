from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.ask.free as free
import brain.main as main
from brain.ask.free import AskError, clean_sql, create_views, run_free
from brain.db import tables as t
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata
from brain.seed.load import run_seed


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    run_seed(engine, log_dir=tmp_path, anchor=datetime.now(UTC).date())
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    return TestClient(main.app)


GOOD = [
    "SELECT team, COUNT(*) AS n FROM v_incidents WHERE decision = 'block' GROUP BY team",
    "```sql\nSELECT name FROM v_inventory WHERE approval = 'unapproved';\n```",
    "WITH recent AS (SELECT * FROM v_incidents) SELECT tool, COUNT(*) FROM recent GROUP BY tool",
    "select u.tool from v_tool_usage u join v_inventory i on i.name = u.tool",
]


@pytest.mark.parametrize("sql", GOOD)
def test_a_plain_select_over_the_views_is_accepted(sql: str) -> None:
    out = clean_sql(sql)
    assert out.lower().startswith(("select", "with")) and ";" not in out and "```" not in out


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE incidents",
        "SELECT * FROM v_incidents; DROP TABLE users",
        "SELECT * FROM users",
        "SELECT * FROM incidents",
        "SELECT * FROM v_incidents UNION SELECT pseudonym, display_name, 3 FROM users",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT * FROM v_incidents -- hide",
        "SELECT * FROM information_schema.tables",
        "UPDATE ai_tools SET approval = 'approved'",
        "SELECT * FROM v_incidents /* x */",
        "SELECT current_setting('server_version')",
        "",
        "I think the answer is five teams.",
        "SELECT * FROM sqlite_master",
        "WITH x AS (DELETE FROM incidents RETURNING *) SELECT * FROM x",
    ],
)
def test_anything_else_is_refused_with_a_plain_message(sql: str) -> None:
    with pytest.raises(AskError):
        clean_sql(sql)


def test_views_answer_real_questions_and_never_expose_real_names(client: TestClient) -> None:
    engine = main.policy_store.engine
    assert engine is not None
    create_views(engine)
    out = run_free(engine, "blocked by team", lambda _q: GOOD[0])
    assert out["columns"] == ["team", "n"] and out["rows"]
    assert out["sql"].startswith("SELECT team")
    with engine.connect() as conn:
        cols = {r[1] for r in conn.execute(sa.text("PRAGMA table_info(v_incidents)"))}
    assert "display_name" not in cols and "person" in cols


def test_results_are_capped_and_a_bad_query_is_a_plain_error(client: TestClient) -> None:
    engine = main.policy_store.engine
    assert engine is not None
    create_views(engine)
    many = run_free(engine, "all incidents", lambda _q: "SELECT id FROM v_incidents")
    assert 0 < len(many["rows"]) <= 500
    with pytest.raises(AskError, match="did not run"):
        run_free(engine, "x", lambda _q: "SELECT nosuchcolumn FROM v_incidents")


def test_the_endpoint_uses_a_model_and_shows_the_sql(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = main.policy_store.engine
    assert engine is not None
    create_views(engine)
    monkeypatch.setattr(free, "write_sql", lambda q: GOOD[1])
    r = client.post("/v1/ask", json={"question": "which tools are unapproved?"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "free" and "v_inventory" in body["sql"] and body["rows"]


def test_a_refused_query_is_a_422_and_no_model_says_what_to_do(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(free, "write_sql", lambda q: "DROP TABLE incidents")
    bad = client.post("/v1/ask", json={"question": "please clean up"})
    assert bad.status_code == 422 and "read data" in bad.json()["detail"]

    def none(_q: str) -> str:
        raise AskError("No model is available to write the query. Use one of the preset questions.")

    monkeypatch.setattr(free, "write_sql", none)
    r = client.post("/v1/ask", json={"question": "anything at all"})
    assert r.status_code == 422 and "preset" in r.json()["detail"]
    assert client.post("/v1/ask", json={"question": "x"}).status_code == 422  # too short


BRIEF_QUESTION = "Which teams sent client data to unapproved AI tools this week?"


def test_the_brief_question_is_the_first_preset_and_returns_the_expected_teams(
    client: TestClient,
) -> None:
    presets = client.get("/v1/ask/presets").json()
    assert presets[0]["question"] == BRIEF_QUESTION
    out = client.post("/v1/ask", json={"preset": presets[0]["id"]}).json()
    assert out["id"] == "client_data_unapproved" and out["columns"][0] == "team"
    # Seed 42 (the demo data): these teams, most client-data incidents first.
    assert [r[0] for r in out["rows"]] == ["Engineering", "Operations", "HR", "Legal"]
    # Every team listed really has client data caught and unapproved-tool requests.
    engine = main.policy_store.engine
    assert engine is not None
    with engine.connect() as conn:
        with_client = {
            r[0]
            for r in conn.execute(
                sa.text(
                    "SELECT team FROM incidents WHERE CAST(categories AS TEXT) LIKE '%client_name%'"
                )
            )
        }
    assert {r[0] for r in out["rows"]} <= with_client
    assert all(r[1] > 0 for r in out["rows"])


@pytest.mark.parametrize(
    "typed",
    [
        BRIEF_QUESTION,
        "which teams sent client data to unapproved ai tools this week",
        "  WHICH teams sent client data to unapproved AI tools this week??  ",
    ],
)
def test_the_same_sentence_typed_in_free_text_uses_the_preset_without_a_model(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, typed: str
) -> None:
    def no_model(_q: str) -> str:
        raise AssertionError("the model must not be called for a preset question")

    monkeypatch.setattr(free, "write_sql", no_model)
    body = client.post("/v1/ask", json={"question": typed}).json()
    assert body["id"] == "client_data_unapproved"


def test_a_different_question_still_goes_to_the_model(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = main.policy_store.engine
    assert engine is not None
    create_views(engine)
    monkeypatch.setattr(free, "write_sql", lambda q: GOOD[1])
    body = client.post("/v1/ask", json={"question": "which tools are unapproved?"}).json()
    assert body["id"] == "free"
