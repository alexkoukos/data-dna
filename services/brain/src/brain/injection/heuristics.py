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
