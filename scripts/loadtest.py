"""Load test for the safety check: how fast does /v1/inspect answer under concurrent load?

Run (stack up):  make loadtest          or   cd services/brain && uv run python ../../scripts/loadtest.py
Options: --users 3 --seconds 15 --url http://localhost:8001 (try --users 10 to see where it saturates)
Sends the prompts of data/eval (clean and risky mixed) as concurrent people and prints requests per
second, error rate and latency p50, p95 and p99. Target (PRD 17): p95 under 100 ms without the LLM
judge. Exit code 1 when the target is missed or any request failed.
"""

import argparse
import asyncio
import csv
import statistics
import sys
import time
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parents[1] / "data" / "eval"
TARGET_P95_MS = 100.0


def prompts() -> list[str]:
    for name in ("prompts.csv", "prompts.sample.csv"):
        p = DATA / name
        if p.exists():
            with p.open(encoding="utf-8", newline="") as f:
                rows = [r["text"] for r in csv.DictReader(f) if r.get("text") and "example row" not in r["notes"]]
            if len(rows) >= 20:
                return rows
    sys.exit("No prompts found. Run scripts/gen_eval_sample.py or fill data/eval/prompts.csv.")


async def worker(client: httpx.AsyncClient, url: str, texts: list[str], stop: float, n: int, out: list[float], errors: list[int]) -> None:
    i = n
    while time.monotonic() < stop:
        body = {"user_id": f"load-{n}", "team": "Load", "model": "m", "messages": [{"role": "user", "content": texts[i % len(texts)]}]}
        i += 1
        start = time.perf_counter()
        try:
            r = await client.post(f"{url}/v1/inspect", json=body)
            ok = r.status_code == 200
        except httpx.HTTPError:
            ok = False
        out.append((time.perf_counter() - start) * 1000)
        if not ok:
            errors.append(1)


async def run(url: str, users: int, seconds: float) -> int:
    texts = prompts()
    latencies: list[float] = []
    errors: list[int] = []
    limits = httpx.Limits(max_connections=users)
    async with httpx.AsyncClient(timeout=30, limits=limits) as client:
        warm = await client.post(f"{url}/v1/inspect", json={"messages": [{"role": "user", "content": "warm up"}]})
        warm.raise_for_status()
        stop = time.monotonic() + seconds
        began = time.monotonic()
        await asyncio.gather(*(worker(client, url, texts, stop, n, latencies, errors) for n in range(users)))
        took = time.monotonic() - began
    s = sorted(latencies)
    pick = lambda q: s[min(len(s) - 1, int(q * len(s)))]  # noqa: E731
    p95 = pick(0.95)
    print(f"{len(s)} requests from {users} people in {took:.0f} s: {len(s) / took:.0f} requests per second")
    print(f"errors: {len(errors)} ({100 * len(errors) / max(len(s), 1):.1f}%)")
    print(f"latency ms: p50 {statistics.median(s):.0f}, p95 {p95:.0f}, p99 {pick(0.99):.0f}, max {s[-1]:.0f}")
    verdict = "PASS" if p95 < TARGET_P95_MS and not errors else "FAIL"
    print(f"target p95 < {TARGET_P95_MS:.0f} ms and no errors: {verdict}")
    return 0 if verdict == "PASS" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://localhost:8001")
    ap.add_argument("--users", type=int, default=3)
    ap.add_argument("--seconds", type=float, default=15)
    a = ap.parse_args()
    try:
        return asyncio.run(run(a.url, a.users, a.seconds))
    except httpx.HTTPError as err:
        sys.exit(f"Could not reach {a.url}. Is the stack running (make up)? {err}")


if __name__ == "__main__":
    sys.exit(main())
