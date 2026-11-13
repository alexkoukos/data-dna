"""Pattern checks: identifiers validated by checksum, cards and secrets."""

import re
from dataclasses import dataclass

from brain.detection.validators import afm_ok, amka_ok, iban_ok, luhn_ok


@dataclass(frozen=True)
class Finding:
    entity: str
    category: str
    start: int
    end: int
    value: str

    @property
    def masked_preview(self) -> str:
        v = self.value
        return v[:2] + "•" * max(len(v) - 6, 2) + v[-4:] if len(v) > 6 else "•" * len(v)


_DIGITS = re.compile(r"(?<!\d)\d{9,19}(?!\d)")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,3})?\b")
_SECRETS = [
    ("openai_key", re.compile(r"\bsk-(?:live-|proj-)?[A-Za-z0-9_\-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


# More Greek identifiers (X6). They have no checksum we can verify, so each one needs a word that
# says what it is just before it. A bare "ΑΒΓ 1234" could be anything; "πινακίδα ΑΒΓ 1234" is not.
_GR = (
    "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ"  # Greek capitals that also exist in the Latin alphabet (plates use only these)
)
_LETTERS = f"[A-Z{_GR}]"
_FILLER = r"(?:is|my|its|number|no|της|του|μου|είναι|ο|η|με|αριθμός|αριθμό|αρ)"
_SEP = rf"(?:[\s:.#\-–]|\b{_FILLER}\b)*"
_CONTEXT: list[tuple[str, re.Pattern[str]]] = [
    (
        "ADT",  # identity card: two letters and six digits
        re.compile(
            r"(?:ΑΔΤ|Α\.Δ\.Τ\.?|ταυτότητ\w*|δελτίο ταυτότητας|identity card|id card|ID no\.?)"
            + _SEP
            + rf"({_LETTERS}{{1,2}}[ -]?\d{{6}})(?!\d)",
            re.IGNORECASE,
        ),
    ),
    (
        "PLATE",  # three letters (Greek capitals that look Latin) and four digits
        re.compile(
            r"(?:πινακίδα|πινακίδες|αριθμός κυκλοφορίας|αρ\. κυκλοφορίας"
            r"|license plate|licence plate|number plate|plate number|registration plate|plate)"
            + _SEP
            + rf"({_LETTERS}{{3}}[ -]?\d{{4}})(?!\d)",
            re.IGNORECASE,
        ),
    ),
    (
        "GEMI",  # business registry number, 9 to 12 digits
        re.compile(
            r"(?:ΓΕΜΗ|ΓΕ\.ΜΗ\.?|Γ\.Ε\.ΜΗ\.?|GEMI|G\.E\.MI\.?)(?: number| no\.?| αριθμός| αρ\.)?"
            + _SEP
            + r"(\d{9,12})(?!\d)",
            re.IGNORECASE,
        ),
    ),
    (
        "PASSPORT",  # two letters and seven digits
        re.compile(
            r"(?:διαβατήριο\w*|passport(?: number| no\.?)?|αριθμός διαβατηρίου)"
            + _SEP
            + rf"({_LETTERS}{{2}}[ -]?\d{{7}})(?!\d)",
            re.IGNORECASE,
        ),
    ),
]


def find_greek_context_ids(text: str) -> list[Finding]:
    found: list[Finding] = []
    for entity, rx in _CONTEXT:
        for m in rx.finditer(text):
            found.append(Finding(entity, "greek_id", m.start(1), m.end(1), m.group(1)))
    return found


def find_patterns(text: str) -> list[Finding]:
    found: list[Finding] = []
    found.extend(find_greek_context_ids(text))
    for m in _IBAN.finditer(text):
        if iban_ok(m.group(0)):
            found.append(Finding("IBAN", "iban", m.start(), m.end(), m.group(0)))
    for m in _DIGITS.finditer(text):
        d = m.group(0)
        if len(d) == 9 and afm_ok(d):
            found.append(Finding("AFM", "greek_id", m.start(), m.end(), d))
        elif len(d) == 11 and amka_ok(d):
            found.append(Finding("AMKA", "greek_id", m.start(), m.end(), d))
        elif 13 <= len(d) <= 19 and luhn_ok(d):
            found.append(Finding("CARD", "card", m.start(), m.end(), d))
    for name, rx in _SECRETS:
        for m in rx.finditer(text):
            found.append(Finding(name.upper(), "secret", m.start(), m.end(), m.group(0)))
    return _dedupe(found)


def _dedupe(items: list[Finding]) -> list[Finding]:
    items.sort(key=lambda f: (f.start, -(f.end - f.start)))
    out: list[Finding] = []
    for f in items:
        if out and f.start < out[-1].end:
            continue
        out.append(f)
    return out


def mask(text: str, findings: list[Finding]) -> tuple[str, dict[str, str]]:
    """Replace findings with placeholders. Returns masked text and placeholder map."""
    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}
    parts: list[str] = []
    last = 0
    for f in sorted(findings, key=lambda f: f.start):
        counters[f.entity] = counters.get(f.entity, 0) + 1
        token = f"[{f.entity}_{counters[f.entity]}]"
        mapping[token] = f.value
        parts.append(text[last : f.start])
        parts.append(token)
        last = f.end
    parts.append(text[last:])
    return "".join(parts), mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text
