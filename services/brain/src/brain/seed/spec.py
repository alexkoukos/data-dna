"""Load the organisation spec (data/org/org.yaml) and the AI tool catalogue (data/ai_tools.csv).

While the team's real files are still templates (they say "TBD" or are very small) the complete
samples next to them are used, so the demo always has a full company.
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

FREQUENCIES = {"daily": 5.0, "weekly": 1.0 / 5, "rare": 1.0 / 15}  # requests per working day
KINDS = {"tool_spike", "api_key_paste", "contract_paste", "salary_questions", "memo_rebuild"}


class SpecError(ValueError):
    """The spec is wrong. The message says what to fix."""


@dataclass
class TeamSpec:
    name: str
    size: int
    roles: list[str]
    ai_tools: dict[str, str]


@dataclass
class OrgSpec:
    company: str
    teams: list[TeamSpec]
    clients: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    storyline: list[dict[str, Any]]
    source: str = ""


@dataclass
class ToolSpec:
    name: str
    vendor: str
    domains: list[str]
    category: str
    approval: str
    risk: str
    reason: str
    alternative: str


@dataclass
class DataFiles:
    org: OrgSpec
    tools: list[ToolSpec] = field(default_factory=list)


def default_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "org").is_dir():
            return parent / "data"
    return Path("/data")


def parse_org(raw: dict[str, Any], source: str = "") -> OrgSpec:
    try:
        teams = [
            TeamSpec(
                name=str(t["name"]),
                size=int(t["size"]),
                roles=list(t.get("roles") or ["employee"]),
                ai_tools=dict(t.get("ai_tools") or {}),
            )
            for t in raw["teams"]
        ]
        spec = OrgSpec(
            company=str(raw["company"]["name"]),
            teams=teams,
            clients=list(raw.get("clients") or []),
            documents=list(raw.get("documents") or []),
            storyline=list(raw.get("storyline") or []),
            source=source,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SpecError(
            f"org spec is incomplete: {exc!r}. Compare it with org.sample.yaml."
        ) from exc
    for team in spec.teams:
        if team.size < 1:
            raise SpecError(f"Team {team.name}: size must be at least 1.")
        for tool, freq in team.ai_tools.items():
            if freq not in FREQUENCIES:
                raise SpecError(
                    f"Team {team.name}, tool {tool}: '{freq}' must be one of {sorted(FREQUENCIES)}."
                )
    for ev in spec.storyline:
        if ev.get("kind") not in KINDS:
            raise SpecError(f"Storyline day {ev.get('day')}: kind must be one of {sorted(KINDS)}.")
        if not 1 <= int(ev.get("day", 0)) <= 14:
            raise SpecError("Storyline day must be between 1 and 14.")
    return spec


def parse_tools(path: Path) -> list[ToolSpec]:
    with path.open(encoding="utf-8", newline="") as f:
        return [
            ToolSpec(
                name=row["name"].strip(),
                vendor=row["vendor"].strip(),
                domains=[d.strip().lower() for d in row["domains"].split(";") if d.strip()],
                category=row["category"].strip(),
                approval=row["approval"].strip(),
                risk=row["risk"].strip(),
                reason=row["reason"].strip(),
                alternative=row["alternative"].strip(),
            )
            for row in csv.DictReader(f)
        ]


def _is_template(raw: dict[str, Any]) -> bool:
    name = str(raw.get("company", {}).get("name", ""))
    return "TBD" in name or len(raw.get("teams", [])) < 3


def load(data_dir: Path | None = None) -> DataFiles:
    root = data_dir or default_data_dir()
    raw = yaml.safe_load((root / "org" / "org.yaml").read_text(encoding="utf-8"))
    source = "org.yaml"
    if _is_template(raw):
        log.warning("org.yaml is still a template, using org.sample.yaml")
        raw = yaml.safe_load((root / "org" / "org.sample.yaml").read_text(encoding="utf-8"))
        source = "org.sample.yaml"
    tools = parse_tools(root / "ai_tools.csv")
    if len(tools) < 5:
        log.warning("ai_tools.csv has fewer than 5 tools, using ai_tools.sample.csv")
        tools = parse_tools(root / "ai_tools.sample.csv")
    return DataFiles(org=parse_org(raw, source), tools=tools)
