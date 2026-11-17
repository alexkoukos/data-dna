"""LoRA fine-tune of gemma3:1b as the D7 borderline judge. Made to run on a Kaggle GPU notebook (guide: docs/JUDGE_FINETUNE.md).

  python3 train_judge_lora.py --check-data                    no GPU needed: checks the files and prints sizes
  python3 train_judge_lora.py --base /kaggle/input/.../gemma-3-1b-it --out /kaggle/working/dna-judge

Reads  train.jsonl and val.jsonl (made by scripts/gen_finetune.py): the `text` column holds the whole chat in Gemma
       markers; only the model turn (the JSON answer) is trained on, the long prompt is masked out of the loss.
Writes <out>/adapter  the LoRA weights (small)
       <out>/merged   the adapter merged into the base model, ready for GGUF and Ollama

Untested on a GPU by the author of this file (no GPU on the dev machine): run --check-data first, then a short
trial (--epochs 1) before the full run. Needs: torch, transformers, peft, accelerate (Kaggle has torch; pip the rest).
"""

import argparse
import inspect
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")  # one GPU: gradient checkpointing and DataParallel do not mix
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from judge_format import parse_verdict  # noqa: E402  (copy judge_format.py next to this file on Kaggle)

MODEL_MARK = "<start_of_turn>model\n"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def split_turns(text: str) -> tuple[str, str]:
    """(everything up to and including the model marker, the model's answer with its end marker)."""
    i = text.index(MODEL_MARK) + len(MODEL_MARK)
    return text[:i], text[i:]


def check_data(train: Path, val: Path) -> None:
    for name, path in (("train", train), ("val", val)):
        rows = load_rows(path)
        yes = 0
        longest = 0
        for r in rows:
            prompt, answer = split_turns(r["text"])
            verdict = json.loads(answer.replace("<end_of_turn>", "").strip())["verdict"]
            assert verdict in ("YES", "NO"), verdict
            assert answer.rstrip().endswith("<end_of_turn>"), "answer must end with <end_of_turn>"
            yes += verdict == "YES"
            longest = max(longest, len(r["text"]))
        print(f"{name}: {len(rows)} rows, {yes / len(rows):.1%} YES, longest {longest} characters")
    print("ok: every row has a user turn, a JSON model turn and an end marker")


def build_features(tok, rows: list[dict], max_len: int) -> list[dict]:
    feats, dropped = [], 0
    for r in rows:
        prompt, answer = split_turns(r["text"])
        p_ids = tok(prompt, add_special_tokens=True)["input_ids"]  # adds <bos> once
        a_ids = tok(answer, add_special_tokens=False)["input_ids"]
        if len(p_ids) + len(a_ids) > max_len:
            dropped += 1
            continue
        feats.append({"input_ids": p_ids + a_ids, "labels": [-100] * len(p_ids) + a_ids})
    if dropped:
        print(f"dropped {dropped} rows longer than {max_len} tokens", file=sys.stderr)
    return feats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", type=Path, default=HERE / "train.jsonl")
    ap.add_argument("--val", type=Path, default=HERE / "val.jsonl")
    ap.add_argument("--base", default="google/gemma-3-1b-it", help="path to gemma-3-1b-it or a Hugging Face id")
    ap.add_argument("--out", type=Path, default=Path("dna-judge"))
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--max-len", type=int, default=768)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--check-data", action="store_true")
    args = ap.parse_args()

    if args.check_data:
        check_data(args.train, args.val)
        return

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    torch.manual_seed(args.seed)
    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8
    dtype = torch.bfloat16 if bf16 else torch.float32  # Gemma 3 is unstable in fp16; a T4 has no bf16, so fp32
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype, attn_implementation="eager")
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    train = build_features(tok, load_rows(args.train), args.max_len)
    val = build_features(tok, load_rows(args.val), args.max_len)

    def collate(batch: list[dict]) -> dict:
        n = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id
        ids = torch.tensor([b["input_ids"] + [pad] * (n - len(b["input_ids"])) for b in batch])
        lab = torch.tensor([b["labels"] + [-100] * (n - len(b["labels"])) for b in batch])
        att = torch.tensor([[1] * len(b["input_ids"]) + [0] * (n - len(b["input_ids"])) for b in batch])
        return {"input_ids": ids, "labels": lab, "attention_mask": att}

    steps_per_epoch = -(-len(train) // (args.batch * args.accum))
    warmup = max(1, int(0.05 * steps_per_epoch * args.epochs))  # a step count works in old and new transformers
    kw = dict(
        output_dir=str(args.out / "trainer"), num_train_epochs=args.epochs, learning_rate=args.lr,
        per_device_train_batch_size=args.batch, per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=args.accum, lr_scheduler_type="cosine", warmup_steps=warmup,
        logging_steps=10, save_strategy="no", report_to="none", bf16=bf16, seed=args.seed,
        remove_unused_columns=False, optim="adamw_torch")
    key = "eval_strategy" if "eval_strategy" in inspect.signature(TrainingArguments.__init__).parameters else "evaluation_strategy"
    kw[key] = "epoch"
    trainer = Trainer(model=model, args=TrainingArguments(**kw), train_dataset=train, eval_dataset=val, data_collator=collate)
    trainer.train()

    (args.out).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out / "adapter")

    # quick check on the validation file: how often does the greedy answer match, and how many false positives
    model.eval()
    rows = load_rows(args.val)
    tp = fp = fn = tn = bad = 0
    for r in rows:
        prompt, answer = split_turns(r["text"])
        gold = json.loads(answer.replace("<end_of_turn>", "").strip())["verdict"]
        ids = tok(prompt, return_tensors="pt", add_special_tokens=True).to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=60, do_sample=False)
        pred = parse_verdict(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))
        bad += pred is None
        tp += gold == "YES" and pred == "YES"
        fn += gold == "YES" and pred != "YES"
        fp += gold == "NO" and pred == "YES"
        tn += gold == "NO" and pred != "YES"
    print(f"validation: precision {tp / max(1, tp + fp):.0%}, recall {tp / max(1, tp + fn):.0%}, "
          f"false positives {fp} of {fp + tn}, not valid JSON {bad} of {len(rows)}")

    merged = model.merge_and_unload().to(torch.bfloat16)  # half the file size; GGUF conversion reads it fine
    merged.save_pretrained(args.out / "merged", safe_serialization=True)
    tok.save_pretrained(args.out / "merged")
    print(f"saved {args.out / 'adapter'} and {args.out / 'merged'}")


if __name__ == "__main__":
    main()
