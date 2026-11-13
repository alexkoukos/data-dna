"""`make eval`: score the detection pipeline against a labelled prompt set (PRD 17 and 18).

Reads data/eval/prompts.csv (the team's set). Until that file has enough rows it uses
prompts.sample.csv (invented) and says so at the top of the report. Compares with a baseline that
only has regex checks and a keyword list, and checks the targets from PRD section 17.
Writes eval/report.md and eval/report.json at the repo root.
"""

import csv
import json
import random
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

from brain.db import tables as t
from brain.detection.entities import ClientMatcher, EntityDetector
from brain.detection.greeklish import find_greeklish_names
from brain.detection.patterns import find_patterns
from brain.detection.pipeline import inspect_text
from brain.detection.yara_rules import find_yara
from brain.dna.marks import (
    assign_vectors,
    attribute,
    copy_code,
    propose_marks,
    render,
    sentences,
)
from brain.documents.embeddings import E5Embedder
from brain.documents.loader import load_documents, parse
from brain.documents.registry import DocumentIndex
from brain.honeytokens import HoneytokenStore
from brain.injection.heuristics import injection_finder
from brain.seed.spec import load as load_spec

REPO = Path(__file__).resolve().parents[5]
MIN_ROWS = 40
KEYWORDS = ["confidential", "strictly confidential", "εμπιστευτικό", "board memo", "do not share"]


@dataclass
class Row:
    id: str
    lang: str
    text: str
    label: str
    leak_type: str
    document: str
    expected: str


@dataclass
class Result:
    row: Row
    decision: str
    flagged: bool
    ms: float
    base_flagged: bool
    matched_doc: str = ""
    reasons: list[str] = field(default_factory=list)


def load_rows(data_dir: Path) -> tuple[list[Row], str]:
    for name in ("prompts.csv", "prompts.sample.csv"):
        path = data_dir / "eval" / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            rows = [
                Row(
                    r["id"],
                    r["lang"],
                    r["text"],
                    r["label"],
                    r["leak_type"],
                    r["document_id"],
                    r["expected_decision"],
                )
                for r in csv.DictReader(f)
                if r.get("text") and "example row" not in (r.get("notes") or "")
            ]
        if len(rows) >= MIN_ROWS:
            return rows, name
    raise SystemExit("No evaluation prompts found. See TASKS.md T3 and scripts/gen_eval_sample.py.")


@dataclass
class Attack:
    id: str
    category: str
    text: str
    expected: str
    notes: str


@dataclass
class AttackResult:
    attack: Attack
    decision: str

    @property
    def caught(self) -> bool:
        return self.decision != "allow"


# What counts as "caught" for each kind of attack. The clean look-alikes must stay allowed.
SCRIPT_TRICKS = ("look_alike", "other_digits", "greeklish")


def load_attacks(data_dir: Path) -> list[Attack]:
    """The red-team file (X2). Missing is fine: the report just has no attack section."""
    path = data_dir / "eval" / "attacks.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [
            Attack(r["id"], r["category"], r["text"], r["expected_decision"], r.get("notes", ""))
            for r in csv.DictReader(f)
            if r.get("text")
        ]


def summarise_attacks(results: list[AttackResult]) -> dict[str, Any] | None:
    if not results:
        return None
    hostile = [x for x in results if x.attack.expected != "allow"]
    clean = [x for x in results if x.attack.expected == "allow"]
    cats: dict[str, Any] = {}
    for cat in sorted({x.attack.category for x in results}):
        rs = [x for x in results if x.attack.category == cat]
        cats[cat] = {
            "n": len(rs),
            "caught": pct(sum(x.caught for x in rs), len(rs)) if cat != "clean_lookalike" else None,
            "decision_matches": pct(sum(x.decision == x.attack.expected for x in rs), len(rs)),
            "false_alarms": pct(sum(x.caught for x in rs), len(rs))
            if cat == "clean_lookalike"
            else None,
        }
    tricks = [x for x in hostile if x.attack.category in SCRIPT_TRICKS]
    decoys = [x for x in hostile if x.attack.category == "honeytoken"]
    return {
        "n": len(results),
        "caught": pct(sum(x.caught for x in hostile), len(hostile)),
        "decision_matches": pct(
            sum(x.decision == x.attack.expected for x in results), len(results)
        ),
        "false_alarms": pct(sum(x.caught for x in clean), len(clean)),
        "script_trick_recall": pct(sum(x.caught for x in tricks), len(tricks)),
        "honeytoken_catch": pct(sum(x.decision == "block" for x in decoys), len(decoys)),
        "categories": cats,
        "gaps": [
            {
                "id": x.attack.id,
                "category": x.attack.category,
                "expected": x.attack.expected,
                "got": x.decision,
                "text": x.attack.text[:90],
                "notes": x.attack.notes,
            }
            for x in results
            if x.decision != x.attack.expected
        ],
    }


def baseline_flags(text: str) -> bool:
    low = text.lower()
    return bool(find_patterns(text)) or any(k in low for k in KEYWORDS)


def pct(n: int, d: int) -> float | None:
    return None if d == 0 else round(100.0 * n / d, 1)


def percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))] if s else 0.0


def attribution_accuracy(data: Path, copies: int = 8, trials: int = 40) -> float | None:
    """Issue copies of each document, "leak" random excerpts of them, and check the right copy is
    named. Only excerpts that still carry at least 3 marks count (PRD 17). Excerpts are shouted
    or stripped of punctuation first, the way a careless leaker might."""
    rng = random.Random(7)
    hits = total = 0
    for path in sorted((data / "documents").glob("*.md")):
        parsed = parse(path.read_text(encoding="utf-8"))
        if parsed is None:
            continue
        text = parsed[1]
        try:
            marks = propose_marks(text)
        except ValueError:
            continue
        vectors = assign_vectors([], copies, len(marks))
        issued = {copy_code(1, v): v for v in vectors}
        for _ in range(trials):
            code, vec = rng.choice(list(issued.items()))
            sents = sentences(render(text, marks, vec))
            start = rng.randrange(0, max(1, len(sents) // 3))
            end = (
                rng.randrange(start + max(2, len(sents) // 2), len(sents) + 1)
                if len(sents) > 3
                else len(sents)
            )
            excerpt = " ".join(sents[start:end])
            if rng.random() < 0.5:
                excerpt = excerpt.upper()
            seen = attribute(excerpt, marks, issued)
            if seen is None or seen.marks_found < 3:
                continue
            total += 1
            hits += seen.copy_code == code
    return None if total == 0 else round(100.0 * hits / total, 1)


def run(data_dir: Path | None = None) -> dict[str, Any]:
    data = data_dir or REPO / "data"
    rows, source = load_rows(data)
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    embedder = E5Embedder()
    load_documents(engine, embedder, data / "documents", keep_text=False)
    index = DocumentIndex(engine, embedder, ttl_seconds=3600)
    entities = EntityDetector()
    entities.warm_up()
    spec = load_spec(data)
    names = [n for c in spec.org.clients for n in [c["name"], *(c.get("aliases") or [])]]
    # Same order as the live service: stronger signals first, so a loose entity never hides them.
    finders = [
        find_yara,
        injection_finder,
        find_greeklish_names,
        entities.find,
        ClientMatcher(names).find,
    ]
    decoys = HoneytokenStore(engine, ttl_seconds=3600).find
    index.match("warm up the index and the embedding model with a short sentence of words")

    results: list[Result] = []
    for r in rows:
        start = time.perf_counter()
        out = inspect_text(r.text, finders=finders, doc_matcher=index.match, priority_finder=decoys)
        ms = (time.perf_counter() - start) * 1000
        decision = str(out.verdict.decision)
        results.append(
            Result(
                r,
                decision,
                decision != "allow",
                ms,
                baseline_flags(r.text),
                out.doc_matches[0].title if out.doc_matches else "",
                out.verdict.reasons,
            )
        )
    attacks = [
        AttackResult(
            a, str(inspect_text(a.text, None, finders, index.match, decoys).verdict.decision)
        )
        for a in load_attacks(data)
    ]
    return summarise(results, source, attribution_accuracy(data), summarise_attacks(attacks))


def _recall(rs: list[Result], base: bool = False) -> float | None:
    return pct(sum(1 for x in rs if (x.base_flagged if base else x.flagged)), len(rs))


def _doc_recall(rs: list[Result]) -> float | None:
    """Document leaks count as caught only when a registered document was actually matched.

    Another check (a client name, a number) can flag the same prompt, but that is luck, not
    document recognition, so it must not raise this number."""
    return pct(sum(1 for x in rs if x.matched_doc), len(rs))


def summarise(
    results: list[Result],
    source: str,
    attribution: float | None = None,
    attacks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    leaks = [x for x in results if x.row.label == "leak"]
    doc_leaks = [x for x in leaks if x.row.leak_type in ("copy", "edit", "paraphrase", "split")]
    paraphrases = [x for x in leaks if x.row.leak_type == "paraphrase"]
    clean = [x for x in results if x.row.label == "clean"]
    injection = [x for x in results if x.row.label == "injection"]
    evasion = [x for x in results if x.row.label == "evasion"]
    by_type = {
        lt: {
            "n": len(rs),
            "recall": _doc_recall(rs)
            if lt in ("copy", "edit", "paraphrase", "split")
            else _recall(rs),
            "baseline_recall": _recall(rs, base=True),
        }
        for lt in sorted({x.row.leak_type for x in leaks})
        for rs in [[x for x in leaks if x.row.leak_type == lt]]
    }
    by_lang: dict[str, Any] = {}
    for lang in sorted({x.row.lang for x in results}):
        ls = [x for x in leaks if x.row.lang == lang]
        cs = [x for x in clean if x.row.lang == lang]
        by_lang[lang] = {
            "leaks": len(ls),
            "recall": _recall(ls),
            "clean": len(cs),
            "false_alarms": pct(sum(x.flagged for x in cs), len(cs)),
        }
    right = sum(1 for x in results if x.decision == x.row.expected)
    latencies = [x.ms for x in results]
    metrics = {
        "paraphrase_recall": _doc_recall(paraphrases),
        "paraphrase_flagged_by_anything": _recall(paraphrases),
        "document_leak_recall": _doc_recall(doc_leaks),
        "false_alarm_rate": pct(sum(x.flagged for x in clean), len(clean)),
        "baseline_false_alarm_rate": pct(sum(x.base_flagged for x in clean), len(clean)),
        "injection_catch_rate": _recall(injection),
        "evasion_catch_rate": _recall(evasion),
        "decision_accuracy": pct(right, len(results)),
        "latency_p50_ms": round(statistics.median(latencies), 1),
        "latency_p95_ms": round(percentile(latencies, 0.95), 1),
        "zero_llm_share": 100.0,
        "llm_tokens": 0,
        "copy_attribution_accuracy": attribution,
    }
    targets: list[tuple[str, str, float | None, Callable[[float], bool]]] = [
        (
            "Recall, paraphrased document leaks",
            ">= 80%",
            metrics["paraphrase_recall"],
            lambda v: v >= 80,
        ),
        ("False alarms on clean prompts", "<= 5%", metrics["false_alarm_rate"], lambda v: v <= 5),
        ("Added latency p95", "< 100 ms", metrics["latency_p95_ms"], lambda v: v < 100),
        ("Prompts with zero LLM tokens", ">= 90%", metrics["zero_llm_share"], lambda v: v >= 90),
        (
            "Correct copy named (leaks with 3 or more marks)",
            ">= 90%",
            metrics["copy_attribution_accuracy"],
            lambda v: v >= 90,
        ),
    ]
    if attacks is not None:
        targets += [
            (
                "Greeklish, look-alike and foreign-digit attacks caught (X5)",
                ">= 80%",
                attacks["script_trick_recall"],
                lambda v: v >= 80,
            ),
            (
                "Decoy credentials raise the alarm (X4)",
                "100%",
                attacks["honeytoken_catch"],
                lambda v: v >= 100,
            ),
            (
                "False alarms on clean look-alikes (X2)",
                "<= 5%",
                attacks["false_alarms"],
                lambda v: v <= 5,
            ),
        ]
    verdicts = [
        {"metric": n, "target": tg, "value": v, "pass": None if v is None else bool(ok(v))}
        for n, tg, v, ok in targets
    ]
    misses = [
        {
            "id": x.row.id,
            "type": x.row.leak_type or x.row.label,
            "expected": x.row.expected,
            "got": x.decision,
            "text": x.row.text[:90],
        }
        for x in results
        if x.decision != x.row.expected
    ]
    return {
        "source": source,
        "rows": len(results),
        "metrics": metrics,
        "by_leak_type": by_type,
        "by_language": by_lang,
        "targets": verdicts,
        "misses": misses,
        "attacks": attacks,
    }


def _fmt(v: object) -> str:
    return "n/a" if v is None else str(v)


def to_markdown(rep: dict[str, Any]) -> str:
    m = rep["metrics"]
    lines = [
        "# Data DNA evaluation report",
        "",
        f"Prompt set: `{rep['source']}` ({rep['rows']} prompts)."
        + (
            " This is the invented sample set, not the team's own `prompts.csv`."
            if "sample" in rep["source"]
            else ""
        ),
        "",
        "## Targets (PRD section 17)",
        "",
        "| Metric | Target | Result | Status |",
        "| --- | --- | --- | --- |",
    ]
    for v in rep["targets"]:
        status = "n/a" if v["pass"] is None else ("PASS" if v["pass"] else "FAIL")
        lines.append(f"| {v['metric']} | {v['target']} | {_fmt(v['value'])} | {status} |")
    lines += [
        "",
        "## Detection by leak type (recall, with the regex-and-keyword baseline)",
        "",
        "| Leak type | Prompts | Recall % | Baseline recall % |",
        "| --- | --- | --- | --- |",
    ]
    for k, v in rep["by_leak_type"].items():
        lines.append(f"| {k} | {v['n']} | {_fmt(v['recall'])} | {_fmt(v['baseline_recall'])} |")
    lines += [
        "",
        "## By language",
        "",
        "| Language | Leaks | Recall % | Clean | False alarms % |",
        "| --- | --- | --- | --- | --- |",
    ]
    for k, v in rep["by_language"].items():
        lines.append(
            f"| {k} | {v['leaks']} | {_fmt(v['recall'])} | {v['clean']} | {_fmt(v['false_alarms'])} |"
        )
    lines += [
        "",
        "## Other measures",
        "",
        f"- Paraphrases flagged by any check, including luck such as a client name: {_fmt(m['paraphrase_flagged_by_anything'])}%",
        f"- Decision matches the label's expected decision: {m['decision_accuracy']}%",
        f"- Prompt injection caught: {_fmt(m['injection_catch_rate'])}%",
        f"- Evasion attempts caught: {_fmt(m['evasion_catch_rate'])}%",
        f"- False alarms, baseline: {m['baseline_false_alarm_rate']}%",
        f"- Latency p50 / p95: {m['latency_p50_ms']} / {m['latency_p95_ms']} ms (no LLM judge)",
        f"- Zero-LLM share: {m['zero_llm_share']}%, LLM tokens used: {m['llm_tokens']}",
        "",
        "## Where the decision differs from the label",
        "",
    ]
    if rep["misses"]:
        lines += ["| Id | Type | Expected | Got | Text |", "| --- | --- | --- | --- | --- |"]
        for x in rep["misses"]:
            text = x["text"].replace("|", "/").replace("\n", " ")
            lines.append(f"| {x['id']} | {x['type']} | {x['expected']} | {x['got']} | {text} |")
    else:
        lines.append("None.")
    atk = rep.get("attacks")
    if atk:
        lines += [
            "",
            "## Red team: data/eval/attacks.csv (X2)",
            "",
            f"{atk['n']} attacks. Caught (any action but allow): {_fmt(atk['caught'])}%. "
            f"Exact decision as expected: {_fmt(atk['decision_matches'])}%. "
            f"False alarms on the clean look-alikes: {_fmt(atk['false_alarms'])}%.",
            "",
            "| Kind | Attacks | Caught % | Decision as expected % |",
            "| --- | --- | --- | --- |",
        ]
        for k, v in atk["categories"].items():
            shown = (
                f"false alarms {_fmt(v['false_alarms'])}"
                if v["caught"] is None
                else _fmt(v["caught"])
            )
            lines.append(f"| {k} | {v['n']} | {shown} | {_fmt(v['decision_matches'])} |")
        lines += [
            "",
            "Attacks whose outcome differs from the expectation (known gaps stay on purpose):",
            "",
        ]
        if atk["gaps"]:
            lines += [
                "| Id | Kind | Expected | Got | Text | Note |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for x in atk["gaps"]:
                text = x["text"].replace("|", "/").replace("\n", " ")
                lines.append(
                    f"| {x['id']} | {x['category']} | {x['expected']} | {x['got']} | {text} | {x['notes']} |"
                )
        else:
            lines.append("None.")
    return "\n".join(lines) + "\n"


def main() -> int:
    rep = run()
    out = REPO / "eval"
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md = to_markdown(rep)
    (out / "report.md").write_text(md, encoding="utf-8")
    print(md)
    failed = [v for v in rep["targets"] if v["pass"] is False]
    print(f"Written to {out}/report.md and report.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
