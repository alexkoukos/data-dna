"""The one place that defines what the borderline judge sees and says (D7).

Used by gen_finetune.py (training data) and eval_judge.py (testing any Ollama model), so the brain
can later call the tuned model with the same text and no extra glue.

Input = instruction + the user's prompt + ONE candidate finding, as one line of JSON:

  doc_chunk  a registered-document chunk the prompt matched but not surely: the fields of
             brain.documents.registry.DocMatch (document title, sensitivity, kind, score) plus the
             language of the prompt and of the chunk and the text of the matched chunk.
  entity     a Finding from brain.detection.entities / patterns (category, matched span) plus the
             words around it.

Output = JSON only: {"verdict": "YES" | "NO", "reason": "<max 12 words, entity names only, no values>"}
"""

import json
import re

INSTRUCTION = (
    "You are the borderline judge of a data-leak guard. Decide whether the PROMPT leaks "
    "confidential company information that the CANDIDATE points to. Answer YES only if the prompt "
    "reveals, copies, translates or summarises the candidate's confidential content, or the "
    "candidate is a real person, client or compensation figure. Answer NO for general questions, "
    "public facts and look-alike words. Reply with JSON only: "
    '{"verdict":"YES"|"NO","reason":"<max 12 words, entity names only, no values>"}'
)

MAX_REASON_WORDS = 12


def candidate_json(candidate: dict) -> str:
    return json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))


def doc_candidate(
    title: str,
    sensitivity: str,
    kind: str,
    score: float,
    prompt_lang: str,
    chunk_lang: str,
    chunk: str,
) -> dict:
    return {
        "type": "doc_chunk",
        "document": title,
        "sensitivity": sensitivity,
        "kind": kind,
        "score": round(score, 3),
        "prompt_lang": prompt_lang,
        "chunk_lang": chunk_lang,
        "chunk": chunk,
    }


def entity_candidate(category: str, span: str, context: str) -> dict:
    return {"type": "entity", "category": category, "span": span, "context": context}


def build_input(prompt: str, candidate: dict) -> str:
    return f"{INSTRUCTION}\n\nPROMPT:\n{prompt}\n\nCANDIDATE:\n{candidate_json(candidate)}"


def build_output(verdict: str, reason: str) -> str:
    return json.dumps({"verdict": verdict, "reason": reason}, ensure_ascii=False)


def gemma_text(user: str, model: str) -> str:
    """Native Gemma turn markers, for trainers that take a single `text` column."""
    return (
        f"<start_of_turn>user\n{user}<end_of_turn>\n<start_of_turn>model\n{model}<end_of_turn>\n"
    )


def reason_ok(reason: str) -> bool:
    """At most 12 words and no digits (a digit would be a value)."""
    return 0 < len(reason.split()) <= MAX_REASON_WORDS and not re.search(r"\d", reason)


_JSON = re.compile(r"\{.*?\}", re.S)


def parse_verdict(text: str) -> str | None:
    """YES / NO from a model answer, or None if it did not follow the JSON format."""
    for m in _JSON.finditer(text):
        try:
            v = json.loads(m.group(0)).get("verdict")
        except (json.JSONDecodeError, AttributeError):
            continue
        if v in ("YES", "NO"):
            return v
    return None
