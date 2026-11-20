"""Employee simulator: people with the browser extension use AI sites, so the dashboard moves.

Local:   cd services/brain && uv run python ../../scripts/simulate.py --count 40
Compose: docker compose --profile sim run --rm sim      (or: make simulate)

Each step is what the extension does: report a visit to an AI site, send the prompt to
`/v1/check` as one of the seeded demo people, and on a warning let half the people send anyway
with a reason. Prompts come from data/eval/prompts.csv (or prompts.sample.csv): about 70% are
clean, the rest are leaks, injections and evasion attempts. Everything is invented.
Needs the stack running (make up).
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
DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
# (host the person visits, name the extension reports, weight)
SITES = [
    ("chatgpt.com", "ChatGPT", 50),
    ("claude.ai", "Claude.ai", 20),
    ("gemini.google.com", "Gemini", 15),
    ("perplexity.ai", "Perplexity", 10),
    ("chat.deepseek.com", "DeepSeek", 5),
]


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
    sys.exit("No prompts found. Run scripts/gen_eval_sample.py or fill data/eval/prompts.csv.")


def now_ms() -> int:
    return int(time.time() * 1000)


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
    with httpx.Client(timeout=60, base_url=BRAIN) as http:
        try:
            everyone = http.get("/v1/demo-users").raise_for_status().json()
        except httpx.HTTPError as err:
            sys.exit(f"Could not reach the brain at {BRAIN}. Is the stack running (make up)? {err}")
        if not everyone:
            sys.exit("The brain lists no demo people. Is DEMO_MODE on?")
        people = [p["user"] for p in rng.sample(everyone, min(args.people, len(everyone)))]
        sites = [(s[0], s[1]) for s in SITES]
        weights = [s[2] for s in SITES]
        for _ in range(args.count):
            who = {"X-Demo-User": rng.choice(people)}
            host, tool = rng.choices(sites, weights)[0]
            http.post(
                "/v1/events",
                headers=who,
                json={"events": [{"ts": now_ms(), "tool": tool, "kind": "visit", "host": host}]},
            )
            text = rng.choice(risky if rng.random() < args.risky else clean)
            r = http.post(
                "/v1/check",
                headers=who,
                json={"text": text, "tool": tool, "url": f"https://{host}/"},
            ).json()
            action = r["action"]
            if action == "warn":
                outcomes["warned"] += 1
                if rng.random() < 0.5:
                    http.post(
                        "/v1/events",
                        headers=who,
                        json={
                            "events": [
                                {
                                    "ts": now_ms(),
                                    "tool": tool,
                                    "kind": "override",
                                    "host": host,
                                    "reason": "simulated: needed for work",
                                }
                            ]
                        },
                    )
                    outcomes["sent anyway"] += 1
                else:
                    outcomes["cancelled"] += 1
            else:
                outcomes[{"local": "company AI"}.get(action, action)] += 1
            time.sleep(args.delay)
    print(f"Sent {args.count} prompts as {len(people)} people:")
    for k, v in outcomes.most_common():
        print(f"  {k:<12} {v}")
    print("Open http://localhost:3000/security to see them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
