"""Match proxy and DNS logs against the AI tool catalogue and aggregate usage (PRD section 11).

`aggregate` is pure (lines in, rows out). Tools served through the gateway never appear in these
logs; their usage comes from the gateway counters instead.
"""

import csv
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from brain.seed.spec import ToolSpec


@dataclass(frozen=True)
class UsageRow:
    day: date
    tool: str
    team: str
    users: int
    requests: int


def build_domain_index(tools: Iterable[ToolSpec]) -> dict[str, str]:
    index: dict[str, str] = {}
    for tool in tools:
        for domain in tool.domains:
            index[domain.lower()] = tool.name
    return index


def match_tool(host: str, index: dict[str, str]) -> str | None:
    """Exact host first, then each parent domain (app.grammarly.com matches grammarly.com)."""
    parts = host.lower().rstrip(".").split(".")
    for i in range(len(parts) - 1):
        hit = index.get(".".join(parts[i:]))
        if hit:
            return hit
    return None


def parse_squid(lines: Iterable[str]) -> Iterable[tuple[datetime, str, str]]:
    """Yield (time, client ip, host) from Squid native format."""
    for line in lines:
        parts = line.split()
        if len(parts) < 7:
            continue
        try:
            ts = datetime.fromtimestamp(float(parts[0]), tz=UTC)
        except ValueError:
            continue
        target = parts[6]
        host = target.split("://", 1)[-1].split("/", 1)[0].rsplit(":", 1)[0]
        yield ts, parts[2], host


def parse_zeek_dns(lines: Iterable[str]) -> Iterable[tuple[datetime, str, str]]:
    """Yield (time, client ip, query) from a Zeek dns.log, using its #fields header."""
    fields: list[str] = []
    for line in lines:
        if line.startswith("#fields"):
            fields = line.rstrip("\n").split("\t")[1:]
            continue
        if line.startswith("#") or not fields:
            continue
        row = dict(zip(fields, line.rstrip("\n").split("\t"), strict=False))
        try:
            ts = datetime.fromtimestamp(float(row["ts"]), tz=UTC)
        except (KeyError, ValueError):
            continue
        if row.get("query"):
            yield ts, row.get("id.orig_h", ""), row["query"]


def aggregate(
    squid: Iterable[tuple[datetime, str, str]],
    dns: Iterable[tuple[datetime, str, str]],
    leases: dict[str, str],
    user_team: dict[str, str],
    index: dict[str, str],
) -> list[UsageRow]:
    """Requests and distinct users per day, tool and team.

    A DNS lookup counts as a request only when that user had no proxy request for the tool that
    day, so people who go around the proxy still show up without being counted twice.
    """
    requests: dict[tuple[date, str, str], int] = defaultdict(int)
    people: dict[tuple[date, str, str], set[str]] = defaultdict(set)
    proxied: set[tuple[date, str, str]] = set()  # (day, tool, pseudonym)

    for ts, ip, host in squid:
        tool, who = match_tool(host, index), leases.get(ip)
        if tool is None or who is None or who not in user_team:
            continue
        key = (ts.date(), tool, user_team[who])
        requests[key] += 1
        people[key].add(who)
        proxied.add((ts.date(), tool, who))

    for ts, ip, host in dns:
        tool, who = match_tool(host, index), leases.get(ip)
        if tool is None or who is None or who not in user_team:
            continue
        if (ts.date(), tool, who) in proxied:
            continue
        key = (ts.date(), tool, user_team[who])
        requests[key] += 1
        people[key].add(who)

    return [
        UsageRow(day, tool, team, len(people[(day, tool, team)]), n)
        for (day, tool, team), n in sorted(requests.items())
    ]


def read_leases(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as f:
        return {row["ip"]: row["pseudonym"] for row in csv.DictReader(f)}
