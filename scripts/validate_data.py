"""Check the team's data files before they reach the app. Run: make validate."""

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "data"
errors: list[str] = []


def check_csv(path: Path, required: list[str], enums: dict[str, set[str]]) -> int:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            errors.append(f"{path.name}: missing columns {missing}")
            return 0
        n = 0
        ids: set[str] = set()
        for i, row in enumerate(reader, start=2):
            n += 1
            for col, allowed in enums.items():
                v = (row.get(col) or "").strip()
                if v and v not in allowed:
                    errors.append(f"{path.name} line {i}: {col}='{v}' must be one of {sorted(allowed)}")
            rid = row.get(required[0], "")
            if rid in ids:
                errors.append(f"{path.name} line {i}: duplicate {required[0]} '{rid}'")
            ids.add(rid)
        return n


n_prompts = check_csv(
    ROOT / "eval" / "prompts.csv",
    ["id", "lang", "text", "label", "leak_type", "document_id", "entity_types", "expected_decision"],
    {
        "lang": {"el", "en"},
        "label": {"leak", "clean", "injection", "evasion"},
        "leak_type": {"copy", "edit", "paraphrase", "split", "pattern"},
        "expected_decision": {"allow", "warn", "mask", "local", "block"},
    },
)
n_attacks = check_csv(
    ROOT / "eval" / "attacks.csv",
    ["id", "lang", "technique", "text", "expected"],
    {"lang": {"el", "en"}},
)
n_tools = check_csv(
    ROOT / "ai_tools.csv",
    ["name", "vendor", "domains", "category", "approval", "risk", "reason", "alternative"],
    {"approval": {"approved", "tolerated", "unapproved"}, "risk": {"low", "medium", "high"}},
)
org = yaml.safe_load((ROOT / "org" / "org.yaml").read_text(encoding="utf-8"))
for key in ("company", "teams", "clients", "storyline"):
    if key not in org:
        errors.append(f"org.yaml: missing '{key}'")

if errors:
    print("Data problems found:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"Data OK: {n_prompts} prompts, {n_attacks} attacks, {n_tools} AI tools, {len(org.get('teams', []))} teams")
