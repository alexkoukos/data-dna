"""Run any Ollama model as the D7 borderline judge on the TEST set and report how good it is.

  python3 scripts/eval_judge.py gemma3:1b                 one model
  python3 scripts/eval_judge.py gemma3:1b dna-judge       compare models side by side
  python3 scripts/eval_judge.py gemma3:1b --dry-run       describe the test set, no model calls
  python3 scripts/eval_judge.py dna-judge --out eval/judge_eval.md
  python3 scripts/eval_judge.py gemma3:1b --legacy        the old, smaller set built straight from data/eval

Standard library only. Needs an Ollama server (default http://localhost:11434) for a real run.

Default test file: data/finetune/test.jsonl, made by scripts/gen_judge_test.py. It is never trained on (the generator
refuses any overlap with the training data) and holds 600+ rows from two test companies (Akryon, Aegean Meridian):
the teammates' labelled prompts, about 90 new hand-written gold cases, entity cases, public-document copies, and
label-preserving rewrites (Greeklish, capitals, no accents, typos). The `d7_neg60` rows are the original 60 negatives
(48 clean prompts + 12 same-topic questions) the untuned gemma3:1b was measured on (42 false positives).

The report gives, per model: precision, recall, precision at a 30% base rate, the false positives on the 60, recall
and false positive rate per candidate type, and a per-slice table. An answer that is not valid JSON counts as NO.
--legacy builds the older set (Aegean only, character-overlap candidates, fixed stand-in score --score).
"""

import argparse
import csv
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services" / "brain" / "src"))

from brain.documents.chunking import chunk_text, language  # noqa: E402
from judge_format import build_input, doc_candidate, entity_candidate, parse_verdict, reason_ok  # noqa: E402

DOC_DIR = ROOT / "data" / "documents"
PROMPTS = ROOT / "data" / "eval" / "prompts.csv"
ATTACKS = ROOT / "data" / "eval" / "attacks.csv"
HOLDOUT = ROOT / "services" / "brain" / "tests" / "data" / "holdout.json"
BASE_RATE = 0.30  # share of leaks among borderline messages (PROGRESS.md)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?:\+30[ .-]?)?69\d{2}[ .-]?\d{6}")
NAME = re.compile(r"\b[A-ZΑ-Ω][a-zα-ωά-ώ]+(?:\s+[A-ZΑ-Ω][a-zα-ωά-ώ]+)+\b")


def _grams(s: str) -> Counter:
    s = re.sub(r"\s+", " ", s.lower())
    return Counter(s[i : i + 3] for i in range(max(0, len(s) - 2)))


def _cos(a: Counter, b: Counter) -> float:
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _words(s: str) -> set:
    return set(re.findall(r"\w+", s.lower()))


def load_docs() -> dict[str, dict]:
    docs = {}
    for f in sorted(DOC_DIR.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        title = re.search(r'title:\s*"?(.*?)"?\s*$', front, re.M).group(1)
        sens = re.search(r"sensitivity:\s*(\w+)", front).group(1)
        chunks = chunk_text(body.strip())
        docs[f.stem] = {"title": title, "sens": sens, "chunks": chunks, "grams": [_grams(c) for c in chunks]}
    return docs


def doc_case(docs: dict, text: str, doc_id: str | None, score: float) -> dict:
    """Nearest chunk (inside doc_id when known, else in all documents) as a doc_chunk candidate."""
    best = (-1.0, "", 0)
    g = _grams(text)
    for d, info in docs.items():
        if doc_id and d != doc_id:
            continue
        for i, cg in enumerate(info["grams"]):
            c = _cos(g, cg)
            if c > best[0]:
                best = (c, d, i)
    _, d, i = best
    info = docs[d]
    chunk = info["chunks"][i]
    shared = len(_words(text) & _words(chunk)) / max(1, len(_words(text) | _words(chunk)))
    kind = "copy" if shared >= 0.5 else "paraphrase"
    shown = round(shared, 3) if kind == "copy" else score
    cand = doc_candidate(info["title"], info["sens"], kind, shown, language(text), language(chunk), chunk)
    return {"prompt": text, "candidate": cand}


def entity_case(text: str) -> dict | None:
    m = EMAIL.search(text) or PHONE.search(text) or NAME.search(text)
    if not m:
        return None
    cat = "EMAIL" if EMAIL.fullmatch(m.group(0)) else "PHONE" if PHONE.fullmatch(m.group(0)) else "PERSON"
    w = text.split()
    pos = next((i for i, x in enumerate(w) if m.group(0).split()[0] in x), 0)
    ctx = " ".join(w[max(0, pos - 7) : pos + 8])
    return {"prompt": text, "candidate": entity_candidate(cat, m.group(0), ctx), "gold": "YES"}


def read_negatives_file(path: Path) -> list[str]:
    if path.suffix == ".csv":
        return [r["text"] for r in csv.DictReader(path.open(encoding="utf-8"))]
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return [x["text"] if isinstance(x, dict) else x for x in (data["negatives"] if isinstance(data, dict) else data)]
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def build_sets(score: float, negatives_file: Path | None) -> dict[str, list[dict]]:
    docs = load_docs()
    rows = list(csv.DictReader(PROMPTS.open(encoding="utf-8")))
    holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    title_to_id = {d["title"]: k for k, d in docs.items()}

    pos: list[dict] = []
    for r in rows:
        if r["label"] == "leak" and r["document_id"] in docs and r["leak_type"] in {"paraphrase", "edit", "copy", "split"}:
            c = doc_case(docs, r["text"], r["document_id"], score)
            c["gold"], c["source"] = "YES", "prompts.csv:" + r["leak_type"]
            pos.append(c)
    for p in holdout["positives"]:
        c = doc_case(docs, p["text"], title_to_id.get(p.get("doc", "")), score)
        c["gold"], c["source"] = "YES", "holdout:rewrite"
        pos.append(c)
    for r in csv.DictReader(ATTACKS.open(encoding="utf-8")):
        if r["technique"] == "document_rewrite":
            c = doc_case(docs, r["text"], None, score)
            c["gold"], c["source"] = "YES", "attacks.csv:document_rewrite"
            pos.append(c)

    if negatives_file:
        neg_texts = [(t, "custom") for t in read_negatives_file(negatives_file)]
    else:
        neg_texts = [(r["text"], "prompts.csv:clean") for r in rows if r["label"] == "clean"]
        neg_texts += [(n["text"], "holdout:same-topic") for n in holdout["negatives"]]
    neg = []
    for text, src in neg_texts:
        c = doc_case(docs, text, None, score)
        c["gold"], c["source"] = "NO", src
        neg.append(c)

    ent = []
    for r in rows:
        if r["label"] == "leak" and "person_email_phone" in r["entity_types"]:
            c = entity_case(r["text"])
            if c:
                c["source"] = "prompts.csv:person_email_phone"
                ent.append(c)
    return {"positives": pos, "negatives": neg, "entities": ent}


def ask(url: str, model: str, user: str, timeout: float) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0, "num_predict": 80, "num_ctx": 2048},
        }
    ).encode()
    req = urllib.request.Request(f"{url}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["message"]["content"]


def load_test(path: Path) -> list[dict]:
    cases = []
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        meta = row["meta"]
        cases.append({"input": row["messages"][0]["content"], "gold": json.loads(row["messages"][1]["content"])["verdict"],
                      "type": meta["type"], "source": meta.get("source", ""), "slice": meta.get("slice", ""),
                      "d7": bool(meta.get("d7_neg60"))})
    return cases


def legacy_cases(score: float, negatives_file: Path | None) -> list[dict]:
    sets = build_sets(score, negatives_file)
    out = []
    for name, cases in sets.items():
        for c in cases:
            out.append({"input": build_input(c["prompt"], c["candidate"]), "gold": c["gold"],
                        "type": "entity" if name == "entities" else "doc_chunk", "source": c.get("source", ""),
                        "slice": c.get("source", ""), "d7": name == "negatives"})
    return out


def run_model(model: str, cases: list[dict], url: str, timeout: float) -> dict:
    started = time.perf_counter()
    results = []
    for n, c in enumerate(cases, 1):
        for attempt in range(8):  # Ollama may restart or reload a model: wait and retry instead of losing the run
            try:
                raw = ask(url, model, c["input"], timeout)
                break
            except (urllib.error.URLError, TimeoutError, OSError, ConnectionError):
                if attempt == 7:
                    raise
                time.sleep(15)
        if n % 50 == 0:
            print(f"{model}: {n}/{len(cases)} rows, {time.perf_counter() - started:.0f}s", file=sys.stderr, flush=True)
        v = parse_verdict(raw)
        reason = ""
        try:
            m = re.search(r"\{.*?\}", raw, re.S)
            reason = json.loads(m.group(0)).get("reason", "") if m else ""
        except (json.JSONDecodeError, AttributeError):
            pass
        results.append({**c, "pred": v, "format_ok": v is not None and reason_ok(str(reason)), "raw": raw[:200]})
    return {"model": model, "cases": results, "seconds": time.perf_counter() - started}


def _confusion(cs: list[dict]) -> tuple[int, int, int, int]:
    tp = sum(c["gold"] == "YES" and c["pred"] == "YES" for c in cs)
    fn = sum(c["gold"] == "YES" and c["pred"] != "YES" for c in cs)
    fp = sum(c["gold"] == "NO" and c["pred"] == "YES" for c in cs)
    tn = sum(c["gold"] == "NO" and c["pred"] != "YES" for c in cs)
    return tp, fn, fp, tn


def metrics(res: dict) -> dict:
    cs = res["cases"]
    tp, fn, fp, tn = _confusion(cs)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    # precision if leaks were 30% of the traffic (the real base rate), not the mix of this test set
    p30 = rec * BASE_RATE / (rec * BASE_RATE + fpr * (1 - BASE_RATE)) if rec or fpr else 0.0
    d7 = [c for c in cs if c["d7"]]
    by_type = {}
    for ty in sorted({c["type"] for c in cs}):
        t_tp, t_fn, t_fp, t_tn = _confusion([c for c in cs if c["type"] == ty])
        by_type[ty] = (t_tp / (t_tp + t_fn) if t_tp + t_fn else None, t_fp / (t_fp + t_tn) if t_fp + t_tn else None)
    by_slice = {}
    for sl in sorted({c["slice"] for c in cs}):
        sc = [c for c in cs if c["slice"] == sl]
        ok = sum(c["pred"] == c["gold"] for c in sc)
        by_slice[sl] = (ok, len(sc), sc[0]["gold"] if len({c["gold"] for c in sc}) == 1 else "mixed")
    by_source = {}
    for so in sorted({c["source"] for c in cs}):
        sc = [c for c in cs if c["source"] == so]
        by_source[so] = (sum(c["pred"] == c["gold"] for c in sc), len(sc))
    return {
        "by_source": by_source,
        "precision": prec, "recall": rec, "precision_at_base_rate": p30, "fp": fp, "negatives": fp + tn,
        "d7_fp": sum(c["pred"] == "YES" for c in d7), "d7_n": len(d7), "by_type": by_type, "by_slice": by_slice,
        "unparsed": sum(c["pred"] is None for c in cs), "format_ok": sum(c["format_ok"] for c in cs) / len(cs),
        "seconds": res["seconds"], "n": len(cs),
    }


def report(all_metrics: list[tuple[str, dict]], cases: list[dict]) -> str:
    yes = sum(c["gold"] == "YES" for c in cases)
    lines = [
        "# Judge evaluation (D7)", "",
        f"Test set: {len(cases)} rows ({yes} leaks, {len(cases) - yes} negatives, "
        f"{sum(c['d7'] for c in cases)} of them the original D7 negatives). Test data only; none of it is in the training set.", "",
        "| model | precision | recall | precision at 30% leaks | false positives on the original 60 | all false positives | unparsed | JSON and reason ok | seconds |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, m in all_metrics:
        lines.append(
            f"| {name} | {m['precision']:.0%} | {m['recall']:.0%} | {m['precision_at_base_rate']:.0%} | "
            f"**{m['d7_fp']} of {m['d7_n']}** | {m['fp']} of {m['negatives']} | {m['unparsed']} | "
            f"{m['format_ok']:.0%} | {m['seconds']:.0f} |")
    lines += ["", "### By candidate type (recall on leaks / false positive rate on negatives)", "",
              "| model | " + " | ".join(f"{ty}" for ty in all_metrics[0][1]["by_type"]) + " |",
              "|---|" + "---|" * len(all_metrics[0][1]["by_type"])]
    for name, m in all_metrics:
        cells = [f"{'recall ' + format(r, '.0%') if r is not None else ''}{' / ' if r is not None and f is not None else ''}"
                 f"{'FP ' + format(f, '.0%') if f is not None else ''}" for r, f in m["by_type"].values()]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    sources = sorted(all_metrics[0][1]["by_source"])
    lines += ["", "### By source (correct / rows)", "", "| source | " + " | ".join(n for n, _ in all_metrics) + " |",
              "|---|" + "---|" * len(all_metrics)]
    for so in sources:
        lines.append(f"| {so} | " + " | ".join(f"{m['by_source'][so][0]}/{m['by_source'][so][1]}" for _, m in all_metrics) + " |")
    slices = sorted(all_metrics[0][1]["by_slice"])
    lines += ["", "### By slice (correct / rows; for a YES slice that is recall, for a NO slice it is 1 minus the false positive rate)", "",
              "| slice | kind | " + " | ".join(n for n, _ in all_metrics) + " |", "|---|---|" + "---|" * len(all_metrics)]
    for sl in slices:
        kind = all_metrics[0][1]["by_slice"][sl][2]
        lines.append(f"| {sl} | {kind} | " + " | ".join(
            f"{m['by_slice'][sl][0]}/{m['by_slice'][sl][1]}" for _, m in all_metrics) + " |")
    lines += ["", "Precision and recall are over all rows. An answer that is not valid JSON counts as NO. 'Precision at 30% leaks' "
              "re-weights the false positive rate to the real base rate. Reference from PROGRESS.md: untuned gemma3:1b gave "
              "42 false positives out of the 60 (earlier prompt, so not exactly comparable).", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="*", help="Ollama model names, e.g. gemma3:1b dna-judge")
    ap.add_argument("--url", default="http://localhost:11434")
    ap.add_argument("--test", type=Path, default=ROOT / "data" / "finetune" / "test.jsonl", help="test file from gen_judge_test.py")
    ap.add_argument("--legacy", action="store_true", help="use the older set built from data/eval (see --score, --negatives)")
    ap.add_argument("--score", type=float, default=0.89, help="legacy only: stand-in similarity score for paraphrase candidates")
    ap.add_argument("--negatives", type=Path, help="legacy only: replace the 60 negatives (csv with text column, json list or text file)")
    ap.add_argument("--out", type=Path, help="also write the tables to this markdown file")
    ap.add_argument("--dump", type=Path, help="write every answer (gold, prediction, raw text) to this jsonl file, for error analysis")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--dry-run", action="store_true", help="only describe the test set")
    args = ap.parse_args()

    if args.legacy or not args.test.exists():
        if not args.legacy:
            print(f"{args.test} not found (run scripts/gen_judge_test.py), using the legacy set", file=sys.stderr)
        cases = legacy_cases(args.score, args.negatives)
    else:
        cases = load_test(args.test)
    d7 = sum(c["d7"] for c in cases)
    print(f"test set: {len(cases)} rows, {sum(c['gold'] == 'YES' for c in cases)} leaks, {d7} original D7 negatives", file=sys.stderr)
    if d7 != 60 and not args.negatives:
        print(f"warning: expected 60 original negatives, found {d7}", file=sys.stderr)
    if args.dry_run or not args.models:
        print(cases[0]["input"])
        return
    results = []
    for model in args.models:
        try:
            res = run_model(model, cases, args.url, args.timeout)
            m = metrics(res)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            sys.exit(f"Could not reach Ollama at {args.url} for {model}: {e}. Start it with `make local`.")
        results.append((model, m))
        if args.dump:
            with args.dump.open("a", encoding="utf-8") as f:
                for c in res["cases"]:
                    f.write(json.dumps({"model": model, **{k: c[k] for k in ("gold", "pred", "type", "source", "slice", "d7", "raw", "input")}},
                                       ensure_ascii=False) + "\n")
        print(f"{model}: precision {m['precision']:.0%}, recall {m['recall']:.0%}, "
              f"false positives on the 60: {m['d7_fp']}/{m['d7_n']}", file=sys.stderr)
    text = report(results, cases)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
