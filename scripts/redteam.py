"""Red team (TASKS.md E2): attack the safety check with known attack prompts and report what passes.

  make redteam        (needs `make up`; Node for promptfoo; uv for garak's prompt library)

1. promptfoo (eval/promptfoo/promptfooconfig.yaml): 25 curated cases, pass or fail each.
2. garak (NVIDIA's open source LLM scanner): about 190 known attack prompts (jailbreaks, prompt
   injection, encoded payloads, instructions hidden in documents) are sent to /v1/inspect. We count
   how many the gateway flags. Most of these attack the MODEL, not company data, so a low catch
   rate here is expected and is reported as it is.
Writes eval/redteam/report.md and report.json. Telemetry of both tools is switched off.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "redteam"
BRAIN = os.environ.get("BRAIN_URL", "http://localhost:8001")


def run_promptfoo() -> dict[str, dict[str, int]]:
    env = {**os.environ, "PROMPTFOO_DISABLE_TELEMETRY": "1", "PROMPTFOO_DISABLE_UPDATE": "1", "PROMPTFOO_DISABLE_SHARING": "1"}
    subprocess.run(
        ["npx", "--yes", "promptfoo@0.125.1", "eval", "-c", "eval/promptfoo/promptfooconfig.yaml",
         "-o", "eval/redteam/promptfoo.json", "--no-cache", "--no-progress-bar"],
        cwd=ROOT, env=env, check=False, capture_output=True, text=True,
    )
    data = json.loads((OUT / "promptfoo.json").read_text(encoding="utf-8"))
    by_cat: dict[str, dict[str, int]] = {}
    failures: list[str] = []
    for r in data["results"]["results"]:
        cat = (r["testCase"].get("metadata") or {}).get("category", "other")
        row = by_cat.setdefault(cat, {"passed": 0, "failed": 0})
        row["passed" if r["success"] else "failed"] += 1
        if not r["success"]:
            failures.append(r["testCase"]["description"])
    by_cat["_failures"] = {f: 1 for f in failures}  # type: ignore[dict-item]
    return by_cat


def run_garak() -> dict[str, dict[str, int]]:
    path = OUT / "garak_prompts.json"
    if not path.exists():
        subprocess.run(
            ["uvx", "--python", "3.12", "--from", "garak", "python", "scripts/garak_dump.py", str(path), "40"],
            cwd=ROOT, check=True, capture_output=True,
        )
    prompts = json.loads(path.read_text(encoding="utf-8"))["prompts"]
    result: dict[str, dict[str, int]] = {}
    with httpx.Client(timeout=60) as http:
        for module, texts in prompts.items():
            row = {"flagged": 0, "allowed": 0, "errors": 0}
            for text in texts:
                body = {"user_id": "garak", "team": "Redteam", "model": "m", "messages": [{"role": "user", "content": text}]}
                try:
                    r = http.post(f"{BRAIN}/v1/inspect", json=body)
                    r.raise_for_status()
                    row["flagged" if r.json()["decision"] != "allow" else "allowed"] += 1
                except httpx.HTTPError:
                    row["errors"] += 1
            result[module] = row
    return result


def main() -> int:
    try:
        httpx.get(f"{BRAIN}/healthz", timeout=3).raise_for_status()
    except httpx.HTTPError:
        sys.exit(f"The brain is not reachable at {BRAIN}. Start the stack first: make up")
    OUT.mkdir(parents=True, exist_ok=True)
    pf = run_promptfoo()
    failures = list(pf.pop("_failures", {}))
    gk = run_garak()

    lines = ["# Red team report", "", "## promptfoo: curated cases (decision must match)", "",
             "| Category | Passed | Failed |", "| --- | --- | --- |"]
    for cat, v in sorted(pf.items()):
        lines.append(f"| {cat} | {v['passed']} | {v['failed']} |")
    if failures:
        lines += ["", "Failing cases:", *[f"- {f}" for f in failures]]
    lines += ["", "## garak: known attack prompts sent to the safety check", "",
              "| Prompt family | Prompts | Flagged by the gateway | Share |", "| --- | --- | --- | --- |"]
    for mod, v in gk.items():
        n = v["flagged"] + v["allowed"] + v["errors"]
        lines.append(f"| {mod} | {n} | {v['flagged']} | {round(100 * v['flagged'] / n)}% |")
    lines += ["", "Most garak prompts attack the model's behaviour (jailbreaks, hidden instructions) rather than"
              " carry company data, so the gateway is only expected to catch the ones with recognisable"
              " injection phrases, secrets or identifiers. The rest reach the model, which is why the"
              " approved model should be hardened separately."]
    report = "\n".join(lines) + "\n"
    (OUT / "report.md").write_text(report, encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps({"promptfoo": pf, "promptfoo_failures": failures, "garak": gk}, indent=1), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
