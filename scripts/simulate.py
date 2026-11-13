"""Employee simulator: people with personal keys chat through the gateway, so the dashboard moves.

Local:   cd services/brain && uv run python ../../scripts/simulate.py --count 40
Compose: docker compose --profile sim run --rm sim      (or: make simulate)

Prompts come from data/eval/prompts.csv (or prompts.sample.csv). About 70% are clean, the rest are
leaks, injections and evasion attempts. On a warning, half the people send anyway with a reason.
Everything is invented. Needs the stack running (make up).
"""

import argparse
import csv
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

BRAIN = os.environ.get("BRAIN_URL", "http://localhost:8001")
GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:4000")
TEAMS = ["Engineering", "Sales", "Legal", "HR", "Finance", "Marketing", "Operations"]
DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))


def load_prompts() -> tuple[list[str], list[str]]:
    for name in ("prompts.csv", "prompts.sample.csv"):
        path = DATA / "eval" / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("text") and "example row" not in r["notes"]]
        if len(rows) >= 20:
            clean = [r["text"] for r in rows if r["label"] == "clean"]
            risky = [r["text"] for r in rows if r["label"] != "clean"]
            return clean, risky
    sys.exit("No prompts found. See TASKS.md T3, or run scripts/gen_eval_sample.py.")


def new_person(client: httpx.Client, n: int, rng: random.Random) -> tuple[str, str, str]:
    """(pseudonym, key, model). Creates the key through the brain, like the Connect page does."""
    user = f"sim-{n:03d}-{rng.randrange(16**4):04x}"
    resp = client.post(f"{BRAIN}/v1/keys", json={"user_id": user, "team": rng.choice(TEAMS)})
    resp.raise_for_status()
    body = resp.json()
    return user, body["key"], body["default_model"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--count", type=int, default=60, help="number of prompts to send")
    ap.add_argument("--people", type=int, default=8, help="how many simulated people")
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between prompts")
    ap.add_argument("--risky", type=float, default=0.3, help="share of risky prompts (0 to 1)")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    clean, risky = load_prompts()
    outcomes: Counter[str] = Counter()
    with httpx.Client(timeout=60) as http:
        try:
            people = [new_person(http, i, rng) for i in range(args.people)]
        except httpx.HTTPError as err:
            sys.exit(f"Could not reach the brain at {BRAIN}. Is the stack running (make up)? {err}")
        for i in range(args.count):
            _, key, model = rng.choice(people)
            text = rng.choice(risky if rng.random() < args.risky else clean)
            headers = {"Authorization": f"Bearer {key}"}
            body = {"model": model, "messages": [{"role": "user", "content": text}]}
            r = http.post(f"{GATEWAY}/v1/chat/completions", headers=headers, json=body)
            if r.status_code == 409:
                outcomes["warned"] += 1
                if rng.random() < 0.5:
                    r = http.post(
                        f"{GATEWAY}/v1/chat/completions",
                        headers={**headers, "X-DNA-Ack": "simulated: needed for work"},
                        json=body,
                    )
                    outcomes["sent anyway"] += 1
                else:
                    outcomes["cancelled"] += 1
            elif r.status_code == 403:
                outcomes["blocked"] += 1
            elif r.status_code == 200:
                outcomes[r.headers.get("x-dna-decision", "allow")] += 1
            else:
                outcomes[f"error {r.status_code}"] += 1
            time.sleep(args.delay)
    print(f"Sent {args.count} prompts as {args.people} people:")
    for k, v in outcomes.most_common():
        print(f"  {k:<12} {v}")
    print("Open http://localhost:3000/security to see them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
