"""X25: calibrate the paraphrase threshold without training anything.

Sweeps the cosine cutoff over the labelled sets in services/brain/tests/data (paraphrases.json
and holdout.json), measures recall (rewrites found) and false alarm rate (ordinary questions
flagged) at each cutoff, and writes docs/calibration.md and docs/calibration.svg. It also says
which cutoff it would pick: the highest recall whose false alarm rate stays under the budget.

Run from the repo root:  make calibrate
Uses the real embedding model (needs it cached, see make setup). Invented data only.
"""

import json
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "services" / "brain" / "tests" / "data"
OUT = REPO / "docs"
FALSE_ALARM_BUDGET = 0.25
SWEEP = [round(0.80 + i * 0.01, 2) for i in range(0, 17)]  # 0.80 .. 0.96

sys.path.insert(0, str(REPO / "services" / "brain" / "src"))


def best_scores() -> dict[str, list[float]]:
    """Per labelled text, the best cosine reached (0 when nothing reaches the floor)."""
    from brain.db import tables as t
    from brain.documents import registry
    from brain.documents.embeddings import E5Embedder
    from brain.documents.loader import load_documents
    from brain.documents.registry import DocumentIndex

    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    emb = E5Embedder()
    load_documents(engine, emb, REPO / "data" / "documents", keep_text=False)
    index = DocumentIndex(engine, emb, ttl_seconds=0)
    floor = SWEEP[0] - 0.05
    registry.PARAPHRASE_COSINE = floor  # report every candidate, we apply the cutoffs here
    registry.CROSS_LANGUAGE_COSINE = floor
    pos: list[float] = []
    neg: list[float] = []
    for name in ("paraphrases.json", "holdout.json"):
        data = json.loads((DATA / name).read_text("utf-8"))
        for p in (x for x in data["positives"] if x.get("kind") != "copy"):
            hits = [h.score for h in index.match(p["text"]) if h.title == p["doc"]]
            pos.append(max(hits, default=0.0))
        for n in data["negatives"]:
            neg.append(max((h.score for h in index.match(n["text"])), default=0.0))
    return {"pos": pos, "neg": neg}


def sweep(scores: dict[str, list[float]]) -> list[dict[str, float]]:
    rows = []
    for c in SWEEP:
        recall = sum(s >= c for s in scores["pos"]) / len(scores["pos"])
        false_rate = sum(s >= c for s in scores["neg"]) / len(scores["neg"])
        rows.append({"cutoff": c, "recall": round(recall, 3), "false_alarm": round(false_rate, 3)})
    return rows


def choose(rows: list[dict[str, float]]) -> dict[str, float]:
    ok = [r for r in rows if r["false_alarm"] <= FALSE_ALARM_BUDGET]
    return max(ok, key=lambda r: (r["recall"], r["cutoff"])) if ok else rows[-1]


def svg(rows: list[dict[str, float]], pick: dict[str, float]) -> str:
    w, h, pad = 640, 360, 48

    def x(c: float) -> float:
        return pad + (c - SWEEP[0]) / (SWEEP[-1] - SWEEP[0]) * (w - 2 * pad)

    def y(v: float) -> float:
        return h - pad - v * (h - 2 * pad)

    def line(key: str, colour: str) -> str:
        pts = " ".join(f"{x(r['cutoff']):.1f},{y(r[key]):.1f}" for r in rows)
        return f'<polyline fill="none" stroke="{colour}" stroke-width="2.5" points="{pts}"/>'

    grid = "".join(
        f'<line x1="{pad}" x2="{w - pad}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#d8dbe2"/>'
        f'<text x="{pad - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end">{int(v * 100)}%</text>'
        for v in (0, 0.25, 0.5, 0.75, 1)
    )
    ticks = "".join(
        f'<text x="{x(r["cutoff"]):.1f}" y="{h - pad + 16}" font-size="11" text-anchor="middle">'
        f"{r['cutoff']:.2f}</text>"
        for r in rows[::2]
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif">'
        f'<rect width="{w}" height="{h}" fill="white"/>{grid}{ticks}'
        f"{line('recall', '#1d6fd1')}{line('false_alarm', '#c2410c')}"
        f'<line x1="{x(pick["cutoff"]):.1f}" x2="{x(pick["cutoff"]):.1f}" y1="{pad}" '
        f'y2="{h - pad}" stroke="#16794a" stroke-dasharray="5 4"/>'
        f'<text x="{pad}" y="24" font-size="14" font-weight="600">Paraphrase cutoff: recall and '
        f"false alarms</text>"
        f'<text x="{w - pad}" y="24" font-size="12" text-anchor="end" fill="#1d6fd1">'
        f"blue: rewrites found</text>"
        f'<text x="{w - pad}" y="40" font-size="12" text-anchor="end" fill="#c2410c">'
        f"orange: false alarms</text>"
        f'<text x="{x(pick["cutoff"]) + 6:.1f}" y="{pad + 14}" font-size="12" fill="#16794a">'
        f"picked {pick['cutoff']:.2f}</text></svg>"
    )


def report(rows: list[dict[str, float]], pick: dict[str, float], n: tuple[int, int]) -> str:
    table = "\n".join(
        f"| {r['cutoff']:.2f} | {r['recall']:.0%} | {r['false_alarm']:.0%} |"
        f"{' ← picked' if r is pick else ''}"
        for r in rows
    )
    return f"""# Calibration of the paraphrase cutoff (X25)

No training is involved. `scripts/calibrate.py` replays {n[0]} labelled rewrites and {n[1]} ordinary
questions through the real pipeline and measures what each cutoff would do.

![recall and false alarms by cutoff](calibration.svg)

| Cutoff | Rewrites found | False alarms |
|---|---|---|
{table}

**Pick:** {pick["cutoff"]:.2f}, the highest recall with false alarms at or under
{FALSE_ALARM_BUDGET:.0%}. The code uses `PARAPHRASE_COSINE` in
`services/brain/src/brain/documents/registry.py`; change it only after re-running `make calibrate`.

A false alarm sends the message to the local model; it never blocks. That is why a
budget of {FALSE_ALARM_BUDGET:.0%} is acceptable. All data is invented. Re-run after changing the
embedding model, the chunking or the document set.
"""


def main() -> None:
    scores = best_scores()
    rows = sweep(scores)
    pick = choose(rows)
    OUT.mkdir(exist_ok=True)
    (OUT / "calibration.svg").write_text(svg(rows, pick), encoding="utf-8")
    (OUT / "calibration.md").write_text(
        report(rows, pick, (len(scores["pos"]), len(scores["neg"]))), encoding="utf-8"
    )
    print(f"Picked cutoff {pick['cutoff']:.2f}: recall {pick['recall']:.0%}, "
          f"false alarms {pick['false_alarm']:.0%}. Wrote docs/calibration.md and .svg")


if __name__ == "__main__":
    main()
