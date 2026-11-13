"""Benchmark small local models (TASKS.md L1): speed and a look at the Greek answers.

Needs an Ollama server with the models pulled:
  docker run -d --name bench-ollama -p 11434:11434 -v bench-ollama:/root/.ollama ollama/ollama
  docker exec bench-ollama ollama pull gemma3:1b      (and the others)
Run:  cd services/brain && uv run python ../../scripts/bench_local_llm.py gemma3:1b qwen2.5:1.5b
Writes eval/local_llm_bench.md. Quality needs a human reading the answers: the script only measures speed.
"""

import statistics
import sys
import time
from pathlib import Path

import httpx

URL = "http://localhost:11434"
PROMPTS = [
    ("el", "Γράψε ένα σύντομο, ευγενικό email σε έναν πελάτη για να μεταθέσουμε τη συνάντηση της Πέμπτης στην Παρασκευή."),
    ("el", "Εξήγησε με απλά λόγια τι είναι ο ΓΚΠΔ και γιατί μας νοιάζει σε μια εταιρεία συμβούλων."),
    ("el", "Συνόψισε σε τρεις προτάσεις: η εταιρεία εξετάζει επέκταση σε δύο νέες αγορές, με επένδυση τεσσάρων εκατομμυρίων ευρώ και αναμενόμενη απόσβεση σε δύο χρόνια."),
    ("en", "Summarise in two sentences: our contract renews automatically for one year unless either side gives ninety days notice, and liability is capped at twelve months of fees."),
    ("en", "Write a two sentence reply declining a meeting invitation politely."),
]


def ask(model: str, prompt: str) -> tuple[str, float, int]:
    start = time.perf_counter()
    r = httpx.post(
        f"{URL}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 160, "temperature": 0.2, "num_ctx": 2048, "num_thread": 4},
        },
        timeout=300,
    )
    r.raise_for_status()
    body = r.json()
    return body["message"]["content"].strip(), time.perf_counter() - start, body["eval_count"]


def main(models: list[str]) -> None:
    lines = ["# Local model benchmark", "", "Speed is measured; quality needs a person to read the answers below.", ""]
    for model in models:
        ask(model, "Say hi in one word.")  # load the model first, so load time is not counted
        rows = [(lang, p, *ask(model, p)) for lang, p in PROMPTS]
        rate = statistics.median(tok / secs for _, _, _, secs, tok in rows)
        secs = statistics.median(s for _, _, _, s, _ in rows)
        lines += [f"## {model}", "", f"Median {rate:.0f} tokens per second, median {secs:.1f} s per answer (up to 160 tokens).", ""]
        for lang, prompt, text, s, tok in rows:
            lines += [f"**[{lang}] {prompt}**", "", text.replace("\n", "\n> "), "", f"_{tok} tokens, {s:.1f} s_", ""]
        print(f"{model}: {rate:.0f} tok/s, {secs:.1f} s per answer")
    out = Path(__file__).resolve().parents[1] / "eval"
    out.mkdir(exist_ok=True)
    (out / "local_llm_bench.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Written to {out}/local_llm_bench.md")


if __name__ == "__main__":
    main(sys.argv[1:] or ["gemma3:1b"])
