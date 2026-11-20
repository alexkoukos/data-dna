# Evaluation

How we measured accuracy and speed, and what the numbers are. Every figure comes from a command in the last column of the first table; run it to check. All data is synthetic (`gen_org.py --seed 42`). Measured on Linux, Docker.

## Method

- **Labelled set.** `data/eval/prompts.csv`: 195 prompts in Greek and English: copies, edits, paraphrases, pattern leaks, leaks split over several messages, and clean prompts. The expected decision is written before the result is looked at, so gaps stay in the file.
- **Baseline.** A regex-and-keyword matcher scored on the same prompts, to show what rules alone would catch.
- **Attack sets.** `data/eval/attacks.csv` (80, by technique) and `data/eval/attacks_scripts.csv` (80, by kind, including 8 harmless look-alikes that must not be flagged).
- **External red team.** `make redteam`: curated promptfoo cases and known attack prompts from garak, sent to the gateway.
- **Calibration.** The paraphrase cutoff was chosen by sweeping labelled rewrites against ordinary questions ([calibration.md](calibration.md)).

## Results

| Measure | Result | Target | Command |
| --- | --- | --- | --- |
| Paraphrased document leaks found | 100% (40 of 40); baseline 5.0% | 80% | `make eval` |
| False alarms on clean prompts | 2.1% | 5% | `make eval` |
| Prompts needing zero LLM tokens | 100% | 90% | `make eval` |
| Correct copy named when a document leaks (3+ marks) | 99.2% | 90% | `make eval` |
| Greeklish, look-alike and foreign-digit attacks caught | 100% | 80% | `make eval` |
| Decoy credentials raise the alarm | 100% | 100% | `make eval` |
| Prompt injection caught | 100% | | `make eval` |
| Attack set `attacks.csv` | 80 of 80 as expected | | `make eval` |
| Attack set `attacks_scripts.csv` | 80 of 80 as expected | | `make eval` |
| False alarms on clean look-alikes | 0.0% | 5% | `make eval` |
| Decision equals the label's expected decision | 94.4% | | `make eval` |
| Added latency, one request at a time (p50 / p95) | 20.8 / 58.0 ms | p95 under 100 ms | `make eval` |
| promptfoo curated cases | 25 of 25 | | `make redteam` |
| Unit tests | 1,154 brain (89% coverage with the OCR extra; 57 need the running stack), 148 web, 48 extension (43 + 5 node) | | `make check` |

Detection tables by leak type and language are in [`eval/report.md`](../eval/report.md); the red-team run is in [`eval/redteam/report.md`](../eval/redteam/report.md). Both are committed.

## Measured against the brief

| Brief asks | Evidence |
| --- | --- |
| Where do you look? | At the gateway in front of every model call, plus proxy and DNS logs for tools that bypass it. The brain adds 58 ms at p95 for a single request. |
| What counts as sensitive? | Checksummed identifiers, secrets, people and client names, source code, and registered documents even when reworded. |
| Rules, ML or LLM? | All three, cheapest first. No LLM judge is needed on the evaluation set. Rules alone find 5% of paraphrases; embeddings find all 40. |
| What happens on a hit? | Five outcomes, each with a reason and an approved alternative. Masked values are restored in the person's own answer. |
| How do you prove it works? | The labelled set with a baseline, two attack sets, and the external red-team run above. |
| Who watches the watcher? | No raw prompts stored, sealed identities, an audit log, retention, and a test per claim. See [ARCHITECTURE.md](ARCHITECTURE.md) section 10. |

## Scope

Traffic that bypasses the gateway, documents retyped by hand or photographed with a phone outside the gate (a photo or scan sent through the gate is read with OCR), and slow leaks beyond the 24-hour session window are outside what Sentry inspects. Details in [THREAT_MODEL.md](THREAT_MODEL.md).

## Experiment: a small judge for borderline matches

We trained a LoRA adapter on gemma3:1b to answer YES or NO to "does this prompt leak this candidate?" ([experiments/judge-finetune.md](experiments/judge-finetune.md)). On a 639-row held-out set it reached 96% precision and 91% recall, against 53% precision for the untuned model ([`eval/judge_eval_tuned.md`](../eval/judge_eval_tuned.md)). It is **not part of the shipped pipeline**: the brain decides without any model call, and `eval/judge_*.md` document the experiment only.

## Reproduce

```bash
make up            # start the stack
make eval          # detection report, writes eval/report.md
make redteam       # promptfoo and garak
make check         # lint, types, all unit tests
make e2e           # browser and accessibility specs
```
