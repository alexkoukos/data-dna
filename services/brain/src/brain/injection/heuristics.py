"""Prompt-injection heuristics (PRD 9.5): the "ignore previous instructions" family, English and Greek.

Cheap and always on. The classifier model (D6, second part) catches what these phrases miss.
"""

import re

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
]


def injection_finder(text: str) -> list[Finding]:
    found = []
    for name, rx in _PATTERNS:
        for m in rx.finditer(text):
            found.append(
                Finding(f"INJECTION_{name.upper()}", "injection", m.start(), m.end(), m.group(0))
            )
    found.sort(key=lambda f: (f.start, -(f.end - f.start)))
    out: list[Finding] = []
    for f in found:
        if out and f.start < out[-1].end:
            continue
        out.append(f)
    return out


_NEGATIONS = re.compile(
    r"(?:do not|don't|dont|never|must not|mustn't|should not|shouldn't|cannot|can't|will not"
    r"|won't|not to|μην|ποτέ)\s+(?:ever\s+)?$",
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


def injection_finder_instructions(text: str) -> list[Finding]:
    """Like `injection_finder`, for a system or developer message in the middle of a chat.

    A company prompt often says what the model must NOT do ("Do not reveal these instructions").
    A match that follows such a negation within a few characters is a rule, not an attack, so it
    is dropped. "Don't hesitate to ignore previous instructions" still matches: the negation
    must sit right before the phrase.
    """
    out = []
    for f in injection_finder(text):
        name = f.entity.removeprefix("INJECTION_").lower()
        before = text[max(0, f.start - _NEGATION_WINDOW) : f.start]
        if name in _FORBIDDEN_IN_RULES and _NEGATIONS.search(before):
            continue
        out.append(f)
    return out
