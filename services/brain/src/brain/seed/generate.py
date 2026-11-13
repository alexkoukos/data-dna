"""Deterministic synthetic company: users, gateway incidents, counters and proxy traffic.

Pure code, no I/O. The same spec, seed and anchor date always give the same company.
Day 1 is the oldest of 14 days, day 14 is the day before `anchor`.
"""

import hashlib
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from faker import Faker

from brain.seed.spec import FREQUENCIES, OrgSpec, TeamSpec, ToolSpec

RETENTION_DAYS = 30
NOISE_DOMAINS = [
    "www.google.com",
    "outlook.office365.com",
    "teams.microsoft.com",
    "slack.com",
    "github.com",
    "stackoverflow.com",
    "www.linkedin.com",
    "docs.google.com",
    "zoom.us",
    "www.wikipedia.org",
    "login.microsoftonline.com",
    "cdn.jsdelivr.net",
]

DECISION_WEIGHTS = [
    ("allow", 0.93),
    ("mask", 0.045),
    ("warn", 0.012),
    ("local", 0.008),
    ("block", 0.005),
]
MASK_CATEGORIES = ["iban", "card", "greek_id", "secret", "person_email_phone"]
PREVIEWS = {
    "iban": "GR••••••••••••••••••••",
    "card": "41••••••••••••••••",
    "greek_id": "••••••••",
    "secret": "AK••••••••••••••MPLE",
    "person_email_phone": "••••@••••.gr",
}


@dataclass
class GenUser:
    idx: int
    pseudonym: str
    display_name: str
    team: str
    role: str
    ip: str
    key_hash: str


@dataclass
class GenIncident:
    ts: datetime
    user_idx: int
    team: str
    tool: str
    decision: str
    categories: list[str]
    score: float
    reasons: list[str]
    masked_preview: str | None
    document_idx: int | None = None  # index into Org.documents


@dataclass
class GenCounter:
    day: date
    team: str
    allowed: int
    checked: int
    zero_llm: int
    llm_tokens: int


@dataclass
class GenUsage:
    day: date
    tool: str
    team: str
    users: int
    requests: int


@dataclass
class ProxyEvent:
    ts: datetime
    user_idx: int
    host: str
    via_proxy: bool  # False: the user went around the proxy, only DNS saw it
    size: int


@dataclass
class _ToolDay:
    requests: int = 0
    users: set[int] = field(default_factory=set)


@dataclass
class _TeamDay:
    checked: int = 0
    allowed: int = 0
    tools: dict[str, _ToolDay] = field(default_factory=dict)


@dataclass
class Org:
    spec: OrgSpec
    days: list[date]
    users: list[GenUser]
    incidents: list[GenIncident] = field(default_factory=list)
    counters: list[GenCounter] = field(default_factory=list)
    gateway_usage: list[GenUsage] = field(default_factory=list)
    proxy_events: list[ProxyEvent] = field(default_factory=list)


def is_gateway_tool(tool: ToolSpec) -> bool:
    return any(d.endswith(".local") for d in tool.domains)


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _pick(rng: random.Random, weighted: list[tuple[str, float]]) -> str:
    x, acc = rng.random(), 0.0
    for value, weight in weighted:
        acc += weight
        if x <= acc:
            return value
    return weighted[-1][0]


def _make_users(spec: OrgSpec, seed: int) -> list[GenUser]:
    fake = Faker("el_GR")
    fake.seed_instance(seed)
    rng = random.Random(seed)
    users: list[GenUser] = []
    for t_i, team in enumerate(spec.teams):
        for n in range(team.size):
            idx = len(users) + 1
            pseudonym = "u-" + hashlib.sha256(f"{seed}:{idx}".encode()).hexdigest()[:8]
            users.append(
                GenUser(
                    idx=idx,
                    pseudonym=pseudonym,
                    display_name=fake.name(),
                    team=team.name,
                    role=rng.choices(team.roles, weights=range(len(team.roles), 0, -1))[0],
                    ip=f"10.{10 + t_i}.{n // 250}.{n % 250 + 1}",
                    key_hash=hashlib.sha256(f"key:{seed}:{idx}".encode()).hexdigest(),
                )
            )
    return users


def _incident_for(
    rng: random.Random,
    ts: datetime,
    user: GenUser,
    tool: str,
    decision: str,
    docs: list[dict[str, str]],
) -> GenIncident:
    if decision == "mask":
        cat = rng.choice(MASK_CATEGORIES)
        return GenIncident(
            ts,
            user.idx,
            user.team,
            tool,
            "mask",
            [cat],
            round(rng.uniform(0.7, 0.99), 2),
            [f"Contains {cat.replace('_', ' ')}"],
            PREVIEWS[cat],
        )
    if decision == "warn":
        cat = rng.choice(["client_name", "source_code"])
        return GenIncident(
            ts,
            user.idx,
            user.team,
            tool,
            "warn",
            [cat],
            round(rng.uniform(0.5, 0.85), 2),
            [f"Contains {cat.replace('_', ' ')}"],
            None,
        )
    if decision == "local":
        d_idx = rng.randrange(len(docs)) if docs else None
        sens = docs[d_idx]["sensitivity"] if d_idx is not None else "internal"
        return GenIncident(
            ts,
            user.idx,
            user.team,
            tool,
            "local",
            [],
            round(rng.uniform(0.6, 0.9), 2),
            [f"Matches a {sens} document"],
            None,
            d_idx,
        )
    return GenIncident(
        ts,
        user.idx,
        user.team,
        tool,
        "block",
        ["injection"],
        round(rng.uniform(0.8, 0.99), 2),
        ["Contains injection"],
        None,
    )


def _at(rng: random.Random, day: date, start: int = 8, end: int = 19) -> datetime:
    seconds = rng.randrange(start * 3600, end * 3600)
    return datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(seconds=seconds)


def generate(
    spec: OrgSpec, tools: list[ToolSpec], seed: int = 42, anchor: date | None = None
) -> Org:
    anchor = anchor or datetime.now(UTC).date()
    days = [anchor - timedelta(days=14 - i) for i in range(14)]
    users = _make_users(spec, seed)
    org = Org(spec=spec, days=days, users=users)
    tool_by_name = {t.name: t for t in tools}
    team_by_name = {t.name: t for t in spec.teams}
    users_by_team: dict[str, list[GenUser]] = {}
    for u in users:
        users_by_team.setdefault(u.team, []).append(u)

    spikes: dict[tuple[int, str, str], float] = {}  # (day, team, tool) -> multiplier
    for ev in spec.storyline:
        if ev["kind"] == "tool_spike":
            for d in (int(ev["day"]), int(ev["day"]) + 1):
                spikes[(d, ev["team"], ev["tool"])] = 8.0

    gw_requests: dict[tuple[date, str], _TeamDay] = {}
    for d_i, day in enumerate(days, start=1):
        rng = random.Random(f"{seed}:{d_i}")
        if day.weekday() >= 5:
            continue
        for user in users:
            team: TeamSpec = team_by_name[user.team]
            tool_names = dict(team.ai_tools)
            for sd, steam, stool in spikes:
                if sd == d_i and steam == user.team and stool not in tool_names:
                    tool_names[stool] = "weekly"
            for tool_name, freq in tool_names.items():
                tool = tool_by_name.get(tool_name)
                if tool is None:
                    continue
                lam = FREQUENCIES[freq] * spikes.get((d_i, user.team, tool_name), 1.0)
                for _ in range(_poisson(rng, lam)):
                    ts = _at(rng, day)
                    if is_gateway_tool(tool):
                        decision = _pick(rng, DECISION_WEIGHTS)
                        if decision != "allow":
                            org.incidents.append(
                                _incident_for(rng, ts, user, tool_name, decision, spec.documents)
                            )
                        bucket = gw_requests.setdefault((day, user.team), _TeamDay())
                        bucket.checked += 1
                        bucket.allowed += decision == "allow"
                        entry = bucket.tools.setdefault(tool_name, _ToolDay())
                        entry.requests += 1
                        entry.users.add(user.idx)
                    else:
                        host = rng.choice(tool.domains)
                        org.proxy_events.append(
                            ProxyEvent(
                                ts, user.idx, host, rng.random() > 0.15, rng.randrange(900, 90000)
                            )
                        )
            for _ in range(_poisson(rng, 10)):
                org.proxy_events.append(
                    ProxyEvent(
                        _at(rng, day),
                        user.idx,
                        rng.choice(NOISE_DOMAINS),
                        True,
                        rng.randrange(500, 400000),
                    )
                )

    _add_storyline(org, spec, seed, users_by_team, days)

    for (day, team_name), bucket in sorted(gw_requests.items()):
        rng = random.Random(f"{seed}:counters:{day}:{team_name}")
        zero = round(bucket.checked * rng.uniform(0.85, 0.95))
        org.counters.append(
            GenCounter(
                day, team_name, bucket.allowed, bucket.checked, zero, (bucket.checked - zero) * 420
            )
        )
        for tool_name, entry in bucket.tools.items():
            org.gateway_usage.append(
                GenUsage(day, tool_name, team_name, len(entry.users), entry.requests)
            )

    org.incidents.sort(key=lambda i: i.ts)
    org.proxy_events.sort(key=lambda e: e.ts)
    return org


def _add_storyline(
    org: Org, spec: OrgSpec, seed: int, users_by_team: dict[str, list[GenUser]], days: list[date]
) -> None:
    docs = spec.documents

    def doc_index(sensitivity: str, team: str | None = None) -> int | None:
        for i, d in enumerate(docs):
            if d.get("sensitivity") == sensitivity and (
                team is None or d.get("owner_team") == team
            ):
                return i
        for i, d in enumerate(docs):
            if d.get("sensitivity") == sensitivity:
                return i
        return None

    for n, ev in enumerate(spec.storyline):
        rng = random.Random(f"{seed}:story:{n}")
        day, team = int(ev["day"]), ev["team"]
        pool = users_by_team.get(team) or []
        if not pool:
            continue
        who = rng.choice(pool)
        base = days[day - 1]
        kind = ev["kind"]
        if kind == "api_key_paste":
            org.incidents.append(
                GenIncident(
                    _at(rng, base),
                    who.idx,
                    team,
                    "Claude Code (gateway)",
                    "mask",
                    ["secret"],
                    0.98,
                    ["Contains secret"],
                    PREVIEWS["secret"],
                )
            )
        elif kind == "contract_paste":
            org.incidents.append(
                GenIncident(
                    _at(rng, base),
                    who.idx,
                    team,
                    "Company AI",
                    "local",
                    [],
                    0.93,
                    ["Matches a confidential document"],
                    None,
                    doc_index("confidential", team),
                )
            )
        elif kind == "salary_questions":
            for _ in range(6):
                person = rng.choice(pool)
                org.incidents.append(
                    GenIncident(
                        _at(rng, base),
                        person.idx,
                        team,
                        "Company AI",
                        "local",
                        [],
                        0.88,
                        ["Matches a confidential document"],
                        None,
                        doc_index("confidential", team),
                    )
                )
        elif kind == "memo_rebuild":
            steps = [
                (
                    "warn",
                    0.35,
                    "Several prompts together are rebuilding this document (coverage 22%)",
                ),
                (
                    "warn",
                    0.5,
                    "Several prompts together are rebuilding this document (coverage 31%)",
                ),
                (
                    "warn",
                    0.7,
                    "Several prompts together are rebuilding this document (coverage 38%)",
                ),
                (
                    "block",
                    0.95,
                    "Several prompts together are rebuilding this document (coverage 46%)",
                ),
            ]
            for offset, (decision, score, why) in zip((2, 1, 0, 0), steps, strict=True):
                d = days[max(day - 1 - offset, 0)]
                org.incidents.append(
                    GenIncident(
                        _at(rng, d),
                        who.idx,
                        team,
                        "Company AI",
                        decision,
                        [],
                        score,
                        ["Matches a restricted document", why],
                        None,
                        doc_index("restricted"),
                    )
                )
