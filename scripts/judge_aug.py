"""Label-preserving rewrites of a judge example (D7), used on the training AND the test data.

People type Greek in Latin letters (Greeklish), in capitals, without accents and with typos, and the
judge must keep its answer. Each rewrite changes only the PROMPT (and, for entity candidates, the span
and its context the same way). The registered chunk is never touched: it is what the company stored.

  greeklish   Greek letters to Latin ones (kane mou ena plano...)
  upper       CAPITALS without accents
  noaccent    accents removed
  typo        two words get two neighbouring letters swapped (documents only: a span must stay exact)

Standard library plus the brain's own language() so `prompt_lang` is recomputed like the brain would.
"""

import random
import re
import unicodedata

KINDS_DOC = ("greeklish", "upper", "noaccent", "typo")
KINDS_ENTITY = ("greeklish", "upper", "noaccent")

_DIGRAPHS = [("ου", "ou"), ("αι", "e"), ("ει", "i"), ("οι", "i"), ("μπ", "b"), ("ντ", "d"), ("γκ", "g"),
             ("γγ", "ng"), ("ευ", "ef"), ("αυ", "af")]
_LETTERS = dict(zip("αβγδεζηθικλμνξοπρστυφχψω",
                    ["a", "v", "g", "d", "e", "z", "i", "th", "i", "k", "l", "m", "n", "x", "o", "p", "r", "s",
                     "t", "y", "f", "ch", "ps", "o"]))
_WORD = re.compile(r"[\w]+", re.UNICODE)


def strip_accents(s: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.combining(ch):
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def _greeklish_word(w: str) -> str:
    low = strip_accents(w).lower().replace("ς", "σ")
    if not re.search("[α-ω]", low):
        return w
    for gr, la in _DIGRAPHS:
        low = low.replace(gr, la)
    out = "".join(_LETTERS.get(c, c) for c in low)
    if w.isupper() and len(w) > 1:
        return out.upper()
    return out.capitalize() if w[0].isupper() else out


def greeklish(s: str) -> str:
    return _WORD.sub(lambda m: _greeklish_word(m.group(0)), s)


def upper(s: str) -> str:
    return strip_accents(s).upper()


def noaccent(s: str) -> str:
    return strip_accents(s)


def typo(s: str, rng: random.Random) -> str:
    words = list(_WORD.finditer(s))
    cands = [m for m in words if len(m.group(0)) >= 5 and m.group(0).isalpha()]
    if not cands:
        return s
    out = s
    for m in sorted(rng.sample(cands, min(2, len(cands))), key=lambda m: -m.start()):
        w = m.group(0)
        i = rng.randint(1, len(w) - 3)
        w2 = w[:i] + w[i + 1] + w[i] + w[i + 2 :]
        out = out[: m.start()] + w2 + out[m.end() :]
    return out


def apply(text: str, kind: str, rng: random.Random) -> str:
    if kind == "greeklish":
        return greeklish(text)
    if kind == "upper":
        return upper(text)
    if kind == "noaccent":
        return noaccent(text)
    if kind == "typo":
        return typo(text, rng)
    raise ValueError(kind)


def augment(e: dict, kind: str, rng: random.Random, lang_fn) -> dict | None:
    """A rewritten copy of example `e` (keys: prompt, cand, verdict, reason, meta), or None if it changes nothing."""
    cand = dict(e["cand"])
    if cand["type"] == "entity":
        if kind == "typo":
            return None
        prompt = apply(e["prompt"], kind, rng)
        cand["span"] = apply(cand["span"], kind, rng)
        cand["context"] = apply(cand["context"], kind, rng)
        if cand["span"] not in prompt:
            return None
    else:
        prompt = apply(e["prompt"], kind, rng)
        cand["prompt_lang"] = lang_fn(prompt)
    if prompt == e["prompt"]:
        return None
    meta = dict(e["meta"])
    meta["sub"] = meta["sub"] + "+" + kind
    meta["aug"] = kind
    return {"prompt": prompt, "cand": cand, "verdict": e["verdict"], "reason": e["reason"], "meta": meta}
