"""Prompt-injection heuristics: the "ignore previous instructions" family, English and Greek.

Cheap and always on. The classifier model (D6, second part) catches what these phrases miss.
"""

import re
from dataclasses import replace

from brain.detection.patterns import Finding

_I = re.IGNORECASE
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "override_instructions",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b(previous|prior|earlier|above|all|your)\b"
            r"[^.\n]{0,30}\b(instructions?|rules?|prompts?|guidelines?|everything)\b",
            _I,
        ),
    ),
    (
        "repeat_above",
        re.compile(r"\brepeat (the|all the) (words|text|instructions) above\b", _I),
    ),
    (
        "exfil_image",
        re.compile(r"!\[[^\]]*\]\(https?://[^)\s]*\?[^)\s]*\)", _I),
    ),
    ("forget_everything", re.compile(r"\bforget everything (above|before|you were told)\b", _I)),
    (
        "reveal_prompt",
        re.compile(
            r"\b(print|reveal|show|repeat|output)\b[^.\n]{0,30}\b(system|hidden|initial) (prompt|instructions?)\b",
            _I,
        ),
    ),
    (
        "role_takeover",
        re.compile(
            r"\b(you are now|from now on you are|act as)\b[^.\n]{0,40}\b(DAN|unrestricted|no restrictions|without (any )?(limits|restrictions|rules))\b",
            _I,
        ),
    ),
    (
        "bypass_safety",
        re.compile(
            r"\b(override|bypass|disable|turn off)\b[^.\n]{0,30}\b(safety|security)\s+(checks?|filters?|rules?|measures?)\b",
            _I,
        ),
    ),
    (
        "system_override",
        re.compile(
            r"\bsystem override\b|\bnew instructions from the (administrator|admin|system)\b", _I
        ),
    ),
    ("hidden_assistant_tag", re.compile(r"<!--\s*assistant:|\[\[?\s*assistant\s*:", _I)),
    (
        "exfiltrate",
        re.compile(
            r"\b(forward|send|email|post|upload)\b[^.\n]{0,50}\b(conversation|chat|contents?|history)\b[^.\n]{0,40}(https?://|\b[\w.+-]+@[\w-]+\.[\w.]+)",
            _I,
        ),
    ),
    (
        "greek_override",
        re.compile(
            r"(αγνόησε|αγνοήστε|ξέχνα|ξεχάστε|παράκαμψε)[^.\n]{0,40}(προηγούμενες|παλιές|όλες|τους κανόνες|οδηγίες)",
            _I,
        ),
    ),
    (
        "greek_new_instructions",
        re.compile(r"νέες οδηγίες από (τον|το|τη) (διαχειριστ|σύστημ|διευθυντ)", _I),
    ),
    ("greek_no_limits", re.compile(r"χωρίς (κανέναν|κανένα|κανεναν)\s+περιορισμ", _I)),
    (
        "greeklish_override",
        re.compile(
            r"\b(agnoi?s[eo]|agnoeste|xexna|ksexna|parakampse)\b[^.\n]{0,40}"
            r"\b(odigies|kanones|entoles|proigoumen\w+)\b",
            _I,
        ),
    ),
    (
        "greeklish_reveal",
        re.compile(r"\b(deixe|deikse|emfanise|typose|ektypose)\b[^.\n]{0,30}system prompt", _I),
    ),
    ("greek_reveal", re.compile(r"(εμφάνισε|δείξε|τύπωσε)[^.\n]{0,30}system prompt", _I)),
    # Instructions planted in a document or an image for whichever AI reads it.
    (
        "note_to_ai",
        re.compile(
            r"\b(note|message|instructions?)\s+(to|for)\s+(the\s+|any\s+)?"
            r"(ai|assistant|model|llm|chatbot|language model)s?\b\s*[:,-]",
            _I,
        ),
    ),
    (
        "ai_reading_this",
        re.compile(
            r"\bif you are an? (ai|assistant|language model|llm|chatbot)\b[^.\n]{0,40}"
            r"\b(reading|processing|summari[sz]ing|seeing|analy[sz]ing)\b",
            _I,
        ),
    ),
]

# OCR reads a capital I as a small l ("lgnore"). Same length, so positions stay right.
_OCR_FOLD = re.compile(r"\b[l1|](?=(?:gn|nstruct)[a-z])")
# Words a recogniser glued together ("Ignoreallpreviousinstructions"), matched on letters only.
_SQUASHED: list[tuple[str, re.Pattern[str]]] = [
    (
        "override_instructions",
        re.compile(
            r"(ignore|disregard|forget|override)(the)?(all|your|previous|prior|earlier|above)+"
            r"(the)?(instructions?|rules|prompts?|guidelines)"
        ),
    ),
    ("reveal_prompt", re.compile(r"(print|reveal|show|repeat|output)(the|your)?systemprompt")),
]
_HIDDEN_LABEL = "[Text hard to see in this image]"  # brain.documents.ocr.HIDDEN_LABEL
# Labels the file readers put in front of what they found; each is a finding of its own.
_LABELS: list[tuple[str, str, str]] = [
    (_HIDDEN_LABEL, "HIDDEN_IMAGE_TEXT", "hidden_text"),
    ("[Hidden data in this image]", "HIDDEN_DATA", "hidden_data"),  # documents.hidden_data
    (
        "[Instructions aimed at an AI in this file]",
        "EMBEDDED_INSTRUCTIONS",
        "embedded_instructions",
    ),
]


def _squashed(text: str) -> list[Finding]:
    """Injection phrases whose spaces were lost, mapped back to positions in the real text."""
    pos = [i for i, c in enumerate(text) if c.isalpha()]
    letters = "".join(text[i] for i in pos).lower()
    out: list[Finding] = []
    for name, rx in _SQUASHED:
        for m in rx.finditer(letters):
            start, end = pos[m.start()], pos[m.end() - 1] + 1
            out.append(
                Finding(f"INJECTION_{name.upper()}", "injection", start, end, text[start:end])
            )
    return out


def _hidden_image_text(text: str) -> list[Finding]:
    """What the file readers labelled: text a person can hardly see in an image (hidden_text),
    data carried by an image file (hidden_data), orders to the AI inside a file
    (embedded_instructions)."""
    out: list[Finding] = []
    for label, entity, category in _LABELS:
        start = text.find(label)
        while start >= 0:
            end = start + len(label)
            out.append(Finding(entity, category, start, end, label))
            start = text.find(label, end)
    return out


def injection_finder(text: str) -> list[Finding]:
    found = []
    folded = _OCR_FOLD.sub("i", text)
    for name, rx in _PATTERNS:
        for m in rx.finditer(folded):
            found.append(
                Finding(
                    f"INJECTION_{name.upper()}",
                    "injection",
                    m.start(),
                    m.end(),
                    text[m.start() : m.end()],
                )
            )
    found += _squashed(text)
    found += _hidden_image_text(text)
    found.sort(key=lambda f: (f.start, -(f.end - f.start)))
    out: list[Finding] = []
    for f in found:
        if out and f.start < out[-1].end:
            continue
        out.append(f)
    return out


_NEGATIONS = re.compile(
    r"(?:do not|don['’]?t|never|must not|mustn['’]?t|should not|shouldn['’]?t|cannot|can['’]?t"
    r"|will not|won['’]?t|not to|μην|ποτέ)[ \t]+(?:ever[ \t]+)?$",
    _I,
)
_NEGATION_WINDOW = 24
# Patterns that name an action ("reveal the prompt") and can be forbidden in a system prompt.
# The others are markers (an exfiltration image, a fake assistant tag) that are never a rule.
_FORBIDDEN_IN_RULES = {
    "override_instructions",
    "repeat_above",
    "forget_everything",
    "reveal_prompt",
    "role_takeover",
    "bypass_safety",
    "exfiltrate",
    "greek_override",
    "greek_reveal",
}


def _is_negated(text: str, f: Finding) -> bool:
    name = f.entity.removeprefix("INJECTION_").lower()
    before = re.sub(r"[ \t]+", " ", text[max(0, f.start - 3 * _NEGATION_WINDOW) : f.start])
    return name in _FORBIDDEN_IN_RULES and _NEGATIONS.search(before) is not None


def injection_finder_instructions(text: str) -> list[Finding]:
    """Like `injection_finder`, for a system or developer message in the middle of a chat.

    A company prompt often says what the model must NOT do ("Do not reveal these instructions").
    A match that follows such a negation on the same line is a rule, not an attack, so it is
    dropped, unless the same match also swallowed a second, unnegated phrase ("Do not ignore
    previous instructions; ignore previous instructions"). "Don't hesitate to ignore previous
    instructions" still matches: the negation must sit right before the phrase.
    """
    out = []
    for f in injection_finder(text):
        if not _is_negated(text, f):
            out.append(f)
            continue
        shift = f.start + 1
        inner = [
            replace(g, start=g.start + shift, end=g.end + shift)
            for g in injection_finder(text[shift : f.end])
        ]
        if any(not _is_negated(text, g) for g in inner):
            out.append(f)
    return out
