# Train the borderline judge (D7)

Goal: a small local model that answers YES or NO, in JSON, to "does this prompt really leak this candidate?",
so the brain can sort the borderline matches that today only send a message to the local model. The untuned
gemma3:1b said YES to 42 of 60 harmless questions (PROGRESS.md, 2026-11-14), so we teach it with LoRA.

Everything below was written without a GPU on the dev machine: the data steps are tested, the Kaggle and GGUF
steps are not. Do the short trial run (step 3) before the full one.

## What is in the repo

| File | What it is |
|---|---|
| `data/train_org/` | the invented training company (Taygetos Oils): 8 documents |
| `data/finetune/train.jsonl`, `val.jsonl` | round 2: 1643 + 289 examples, 30% YES, 44% Greek (made by `python3 scripts/gen_finetune.py`) |
| `data/finetune/test.jsonl` | 639 rows from two other companies, never trained on (`scripts/gen_judge_test.py`) |
| `scripts/judge_format.py` | the exact input and output the judge sees (used by data, training and eval) |
| `scripts/train_judge_lora.py` | the training script |
| `scripts/judge.Modelfile` | turns the result into an Ollama model |
| `scripts/eval_judge.py` | compares models on the test set |

Row format: `messages` (user turn = instruction + PROMPT + CANDIDATE, assistant turn = `{"verdict","reason"}`),
`text` (the same with Gemma markers; the training script reads this), `meta` (kind, language; ignored).

## 1. Get Gemma 3 1B on Kaggle
Either:
- **Kaggle Models (no token):** in the notebook, Add Input, Models, search "Gemma 3", pick `gemma-3-1b-it`
  (Transformers). The path looks like `/kaggle/input/gemma-3/transformers/gemma-3-1b-it/1`.
- **Hugging Face:** accept the licence at huggingface.co/google/gemma-3-1b-it, create a read token, store it as a
  Kaggle Secret named `HF_TOKEN`, and use `--base google/gemma-3-1b-it`.

## 2. Upload the data
Kaggle, Datasets, New Dataset, name it `dna-judge-data`, upload these four files:
`data/finetune/train.jsonl`, `data/finetune/val.jsonl`, `scripts/train_judge_lora.py`, `scripts/judge_format.py`.

## 3. Notebook (settings: Accelerator GPU T4 x2 or P100, Internet on)
```python
!pip -q install -U transformers peft accelerate
D = "/kaggle/input/dna-judge-data"
BASE = "/kaggle/input/gemma-3/transformers/gemma-3-1b-it/1"   # or "google/gemma-3-1b-it"

# 1) files are fine (no GPU used)
!python {D}/train_judge_lora.py --check-data --train {D}/train.jsonl --val {D}/val.jsonl
# 2) short trial: one epoch, see that the loss falls and the validation line prints
!python {D}/train_judge_lora.py --base {BASE} --train {D}/train.jsonl --val {D}/val.jsonl --out /kaggle/working/trial --epochs 1
# 3) the real run (about 3 epochs; expect 15 to 40 minutes on a T4)
!python {D}/train_judge_lora.py --base {BASE} --train {D}/train.jsonl --val {D}/val.jsonl --out /kaggle/working/dna-judge
!cd /kaggle/working && zip -rq dna-judge.zip dna-judge/merged dna-judge/adapter
```
If it runs out of memory: `--batch 2 --accum 8`, or `--max-len 640`. The script prints the loss every 10 steps and, at
the end, a validation line (precision, recall, false positives, answers that are not valid JSON). Download
`dna-judge.zip` from the notebook's Output tab.

## 4. Turn it into an Ollama model (on your machine)
```bash
unzip dna-judge.zip
git clone --depth 1 https://github.com/ggml-org/llama.cpp && pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
python llama.cpp/convert_hf_to_gguf.py dna-judge/merged --outfile scripts/dna-judge.gguf --outtype f16
```
Then give it its own Ollama. Do NOT use the one from `make local`: `make up` (or `docker compose up`) recreates the stack and
removes it, which killed two evaluation runs. `make judge-ollama` starts a separate container (`judge-ollama`, port 11435)
that reuses the same model volume:
```bash
make local            # once, so that gemma3:1b and dna-local exist in the volume
make judge-ollama
docker cp scripts/dna-judge.gguf judge-ollama:/tmp/dna-judge.gguf
docker cp scripts/judge.Modelfile judge-ollama:/tmp/judge.Modelfile
docker exec judge-ollama sh -c "cd /tmp && sed -i 's#FROM ./dna-judge.gguf#FROM /tmp/dna-judge.gguf#' judge.Modelfile && ollama create dna-judge -f judge.Modelfile"
```
If `convert_hf_to_gguf.py` stops with `assert max(tokenizer.vocab.values()) < vocab_size`, the saved tokenizer has an extra
`<image_soft_token>` (id 262144) from a newer transformers. `train_judge_lora.py` now removes it; for a model trained before
that, delete the entry with `"id": 262144` from `added_tokens` in `merged/tokenizer.json` (and `image_token` in
`tokenizer_config.json`) and run the converter again. The model weights are not affected.

(`f16` is about 2 GB; a 4-bit file is smaller but check quality first.) If the model answers with garbage or never
stops, the template is the usual suspect: compare with `ollama show --modelfile gemma3:1b`.

## 5. Measure
```bash
make judge-eval      # = eval_judge.py dna-judge dna-local --url http://localhost:11435 (dna-local is gemma3:1b with 4 threads); about 30 to 50 minutes per model on a laptop CPU
```
Read, in this order: the false positives on the original 60 (was 42 with the untuned model), precision at 30% leaks,
recall, then the per-slice table. The `gold_new` slices are the ones written for this test.
Rough bar for adopting the judge (our suggestion, change it if the team disagrees): at most 5 of the 60 wrong, recall of
80% or more, and at least 95% of answers valid JSON.

## Results so far
Round 1 (1286 + 227 examples), on the 639-row test set, tuned against plain gemma3:1b (`eval/judge_eval.md`,
`eval/judge_eval_tuned.md`, wrong answers in `eval/judge_errors.md`):

| | gemma3:1b | tuned |
|---|---|---|
| false positives on the original 60 | 36 | 1 |
| precision at 30% leaks | 35% | 92% |
| recall | 94% | 91% |
| valid JSON with a short reason | 0% | 100% |

The 40 wrong answers pointed at client names (13 missed), short document fragments, surnames alone, public-newsletter text and
a few doubtful labels. Round 2 data adds, for exactly those: about 3 times more client-name examples (13 new invented clients, with look-alike
words such as Meltemi or Kronos used in their ordinary meaning as negatives), 62 short fragments, a second public document,
more surnames, editing and number-only prompts. Retrain on the new `train.jsonl` and `val.jsonl` and run `make judge-eval` again.

## 6. If it is not good enough
- **Great on `val.jsonl`, weak on the test set:** it learned our templates. Add more different documents and more
  hand-written rewrites to `scripts/gen_finetune.py` (`FACTS`), not more of the same.
- **Many false positives in one slice** (see the per-slice table): add negatives like those, written by hand.
- **Misses leaks in one slice** (cross-language, summaries, indirect questions): add positives like those.
- **Too many YES overall:** train one more epoch, or lower the learning rate to `1e-4`.
- Regenerate with `python3 scripts/gen_finetune.py` (it refuses any overlap with the test data), retrain, re-evaluate.
Never train on `test.jsonl` or on anything in `data/eval/`.

## Using it later
Nothing in the brain calls the judge yet (D7 is "evaluated, not adopted"). If it passes step 5, the brain builds the
input with `judge_format.build_input(prompt, candidate)` and sends it to the gateway's local route. The candidate is
the `DocMatch` of a borderline paraphrase (plus the matched chunk text) or a `Finding`. Cache answers by hash.
