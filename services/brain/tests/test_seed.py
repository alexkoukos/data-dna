from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

from brain.db import tables as t
from brain.seed import ingest
from brain.seed.generate import generate, is_gateway_tool
from brain.seed.load import run_seed
from brain.seed.logs import write_logs
from brain.seed.spec import SpecError, load, parse_org

ANCHOR = date(2026, 11, 14)


@pytest.fixture(scope="module")
def files():  # type: ignore[no-untyped-def]
    return load()


@pytest.fixture(scope="module")
def org(files):  # type: ignore[no-untyped-def]
    return generate(files.org, files.tools, 42, ANCHOR)


def test_org_matches_the_spec(files, org) -> None:  # type: ignore[no-untyped-def]
    assert len(org.users) == sum(t_.size for t_ in files.org.teams) == 200
    assert len({u.pseudonym for u in org.users}) == 200
    assert len({u.ip for u in org.users}) == 200
    assert org.days[-1] == date(2026, 11, 13)


def test_same_seed_same_company(files, org) -> None:  # type: ignore[no-untyped-def]
    again = generate(files.org, files.tools, 42, ANCHOR)
    assert [u.display_name for u in again.users] == [u.display_name for u in org.users]
    assert [(i.ts, i.decision, i.user_idx) for i in again.incidents] == [
        (i.ts, i.decision, i.user_idx) for i in org.incidents
    ]
    other = generate(files.org, files.tools, 7, ANCHOR)
    assert [u.pseudonym for u in other.users] != [u.pseudonym for u in org.users]


def test_storyline_events_exist(org) -> None:  # type: ignore[no-untyped-def]
    reasons = [r for i in org.incidents for r in i.reasons]
    assert any("rebuilding this document" in r for r in reasons)
    assert any(i.decision == "block" and "rebuilding" in " ".join(i.reasons) for i in org.incidents)
    assert any(
        i.tool == "Claude Code (gateway)" and i.categories == ["secret"] for i in org.incidents
    )


def test_unapproved_tool_spike_shows_in_proxy_traffic(files, org) -> None:  # type: ignore[no-untyped-def]
    index = ingest.build_domain_index(files.tools)
    sales = {u.idx for u in org.users if u.team == "Sales"}
    per_day: dict[date, int] = {}
    for ev in org.proxy_events:
        if ev.user_idx in sales and ingest.match_tool(ev.host, index) == "ChatGPT (personal)":
            per_day[ev.ts.date()] = per_day.get(ev.ts.date(), 0) + 1
    spike_day = org.days[2]  # storyline day 3
    normal = [n for d, n in per_day.items() if d not in (org.days[2], org.days[3])]
    assert per_day[spike_day] > 3 * (sum(normal) / len(normal))


def test_gateway_tools_never_appear_in_proxy_logs(files, org) -> None:  # type: ignore[no-untyped-def]
    gateway = {n for tool in files.tools if is_gateway_tool(tool) for n in tool.domains}
    assert not gateway & {e.host for e in org.proxy_events}


def test_match_tool_uses_parent_domains() -> None:
    index = {"grammarly.com": "Grammarly"}
    assert ingest.match_tool("app.grammarly.com", index) == "Grammarly"
    assert ingest.match_tool("notgrammarly.com", index) is None
    assert ingest.match_tool("com", index) is None


def test_parsers_read_real_formats() -> None:
    squid = [
        "1731502800.123    245 10.1.0.5 TCP_TUNNEL/200 5342 "
        "CONNECT chatgpt.com:443 - HIER_DIRECT/1.2.3.4 -"
    ]
    assert list(ingest.parse_squid(squid)) == [
        (datetime.fromtimestamp(1731502800.123, tz=UTC), "10.1.0.5", "chatgpt.com")
    ]
    assert list(ingest.parse_squid(["garbage", "x y z"])) == []
    zeek = [
        "#separator \\x09",
        "#fields\tts\tuid\tid.orig_h\tquery",
        "1731502800.0\tCabc\t10.1.0.5\tclaude.ai",
        "#close",
    ]
    assert [q for _, _, q in ingest.parse_zeek_dns(zeek)] == ["claude.ai"]


def test_dns_only_use_is_counted_once_per_user_and_day() -> None:
    index = {"claude.ai": "Claude.ai"}
    ts = datetime(2026, 11, 10, 9, tzinfo=UTC)
    leases = {"10.0.0.1": "u-a", "10.0.0.2": "u-b"}
    teams = {"u-a": "Sales", "u-b": "Sales"}
    squid = [(ts, "10.0.0.1", "claude.ai")]
    dns = [
        (ts, "10.0.0.1", "claude.ai"),
        (ts, "10.0.0.2", "claude.ai"),
    ]  # a: duplicate, b: proxy bypass
    rows = ingest.aggregate(squid, dns, leases, teams, index)
    assert [(r.requests, r.users) for r in rows] == [(2, 2)]


def test_logs_roundtrip_through_ingest(files, org, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    paths = write_logs(org, tmp_path)
    index = ingest.build_domain_index(files.tools)
    teams = {u.pseudonym: u.team for u in org.users}
    with paths["squid"].open() as sq, paths["zeek"].open() as zk:
        rows = ingest.aggregate(
            ingest.parse_squid(sq),
            ingest.parse_zeek_dns(zk),
            ingest.read_leases(paths["leases"]),
            teams,
            index,
        )
    assert rows
    assert {r.tool for r in rows} <= {t_.name for t_ in files.tools}
    assert "Company AI" not in {r.tool for r in rows}


def test_spec_errors_are_plain() -> None:
    with pytest.raises(SpecError, match="org.sample.yaml"):
        parse_org({"company": {"name": "x"}})
    bad = {
        "company": {"name": "x"},
        "teams": [{"name": "A", "size": 1, "ai_tools": {"T": "hourly"}}],
    }
    with pytest.raises(SpecError, match="daily"):
        parse_org(bad)


def test_run_seed_fills_an_empty_database_once(tmp_path: Path) -> None:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    assert run_seed(engine, log_dir=tmp_path, anchor=ANCHOR) is True
    with engine.connect() as conn:
        n = lambda table: conn.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()  # noqa: E731
        assert n(t.users) == 200
        assert n(t.ai_tools) == 15
        assert n(t.incidents) > 300
        assert n(t.tool_usage_daily) > 100
        assert n(t.documents) == 3
    assert run_seed(engine, log_dir=tmp_path, anchor=ANCHOR) is False
