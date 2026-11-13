"""Run inside garak's own environment: write a sample of its attack prompts to a JSON file.

  uvx --python 3.12 --from garak python scripts/garak_dump.py eval/redteam/garak_prompts.json 40

garak is NVIDIA's open source LLM scanner. Its probe modules hold thousands of known attack
prompts (jailbreaks, prompt injection, encoded payloads, instructions hidden in documents). We do not
use garak to scan a model; we use its prompt library to ask: does the gateway notice these?
"""

import importlib
import json
import random
import sys

import garak.probes.base as base

MODULES = ["promptinject", "dan", "encoding", "latentinjection", "goodside"]


def main(out: str, per_module: int) -> None:
    rng = random.Random(1)
    sample: dict[str, list[str]] = {}
    for name in MODULES:
        mod = importlib.import_module(f"garak.probes.{name}")
        prompts: list[str] = []
        for cls in vars(mod).values():
            if isinstance(cls, type) and issubclass(cls, base.Probe) and cls is not base.Probe and cls.__module__ == mod.__name__:
                try:
                    prompts.extend(str(p) if isinstance(p, str) else str(p.get("text", p)) for p in cls().prompts)
                except Exception:
                    continue
        prompts = sorted(set(prompts))
        rng.shuffle(prompts)
        sample[name] = prompts[:per_module]
        print(f"{name}: {len(prompts)} prompts, kept {len(sample[name])}", file=sys.stderr)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"source": "garak " + __import__("garak").__version__, "prompts": sample}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
