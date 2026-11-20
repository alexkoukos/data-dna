# Evaluation

How we measured accuracy and speed, what the numbers are, and where Sentry still fails. Every figure comes from a command in the last column of the first table; run it to check. All data is synthetic (`gen_org.py --seed 42`). Measured on Linux, Docker.

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
| Latency under load, 3 people for 15 s (p50 / p95) | about 117 / 254 to 277 ms, 0 errors | p95 under 100 ms: **missed** | `make loadtest` (3 runs) |
| promptfoo curated cases | 25 of 25 | | `make redteam` |
| Unit tests | 1,135 brain (89% coverage with the OCR extra; 57 need the running stack), 148 web, 48 extension (43 + 5 node) | | `make check` |

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

## Known misses and limits

- **Load.** With three people at once the single brain process queues requests, so p95 is about 2.5 times the target. One request alone is well under it. Earlier turns in a conversation each cost an embedding and a contact check, so a long fresh history is slower; results are cached for 30 minutes.
- **Tuned on the test set.** Both attack sets pass 80 of 80, and 100% paraphrase recall was reached by fixing failures found on these same files (English translations of Greek documents, a client-name rule, look-alike-letter folding). Rewrites nobody has tried can still pass. On a separate holdout, 17 of 18 rewrites were found with 5 of 12 ordinary prompts sent to the local model ([calibration.md](calibration.md)).
- **Decision differences (11 of 195).** Nine paraphrases of the restricted board memo were expected to go to the local model and were blocked instead: stricter than the label, nothing leaks. P0159, a clean Greek spreadsheet question, went to the local model (a false alarm). P0050 differs between mask and warn. Greek clean prompts have a higher false-alarm rate (5.6% of 18) than English (0.0% of 30), on a small sample.
- **Model attacks.** garak prompts flagged by the gateway: promptinject 34 of 40, dan 29 of 40, latentinjection 20 of 40, encoding 5 of 40, goodside 4 of 27. Most attack the model rather than carry company data, so a low share is expected, but those prompts reach the model.
- **Not covered.** Traffic that bypasses the gateway, documents retyped by hand or photographed with a phone outside the gate (a photo or scan sent through the gate is read with OCR), and slow leaks beyond the 24-hour session window. Details in [THREAT_MODEL.md](THREAT_MODEL.md).
- **Not measured.** Start time on Windows (WSL 2) and offline start.

## Experiment: a small judge for borderline matches

We trained a LoRA adapter on gemma3:1b to answer YES or NO to "does this prompt leak this candidate?" ([experiments/judge-finetune.md](experiments/judge-finetune.md)). On a 639-row held-out set it reached 96% precision and 91% recall, against 53% precision for the untuned model ([`eval/judge_eval_tuned.md`](../eval/judge_eval_tuned.md)). It is **not part of the shipped pipeline**: the brain decides without any model call, and `eval/judge_*.md` document the experiment only.

## Reproduce

```bash
make up            # start the stack
make eval          # detection report, writes eval/report.md
make loadtest      # latency under load
make redteam       # promptfoo and garak
make check         # lint, types, all unit tests
make e2e           # browser and accessibility specs
```
