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

# X6: Greek identifiers with no checksum. Letters are the ones shared by the Greek and Latin
# alphabets, because that is all that appears on Greek plates and ID cards. Written with either.
_L = "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧABEZHIKMNOPTYX"
_GREEK_IDS = [
    # Police ID card (ADT): one or two letters and six digits, e.g. "ΑΕ 123456".
    ("ADT", "greek_id", re.compile(rf"(?<![\w])(?P<v>[{_L}]{{1,2}}[ -]?\d{{6}})(?![\w])")),
    # Number plate: three letters and four digits, e.g. "ΥΝΑ-1234".
    ("PLATE", "greek_id", re.compile(rf"(?<![\w])(?P<v>[{_L}]{{3}}[ -]?\d{{4}})(?![\w])")),
    # Passport: two letters and seven digits, only next to the word passport.
    (
        "PASSPORT",
        "greek_id",
        re.compile(
            r"(?:passport|διαβατήριο|διαβατηριο)[^\n.]{0,25}?(?<![A-Za-z])(?P<v>[A-Z]{2}\s?\d{7})(?!\d)",
            re.IGNORECASE,
        ),
    ),
    # Business registry (GEMI) number: twelve digits, only next to its name.
    (
        "GEMI",
        "greek_id",
        re.compile(
            r"(?:GEMI|ΓΕΜΗ|Γ\.Ε\.ΜΗ\.)[^\n.]{0,20}?(?<!\d)(?P<v>\d{12})(?!\d)", re.IGNORECASE
        ),
    ),
    # Greek phone numbers: +30 or 0030 or none, then a mobile (69) or area (2) number.
    (
        "PHONE_GR",
        "person_email_phone",
        re.compile(
            r"(?<![\w+])(?P<v>(?:(?:\+|00)30[ -]?)?69\d[ -]?\d{3}[ -]?\d{4}"
            r"|(?:\+|00)30[ -]?2\d{2,3}[ -]?\d{3}[ -]?\d{4}"
            r"|2\d{2,3}[ -]\d{3}[ -]?\d{4})(?![\w])"
        ),
    ),
]


def _find_greek_ids(text: str) -> list[Finding]:
    out: list[Finding] = []
    for entity, category, rx in _GREEK_IDS:
        for m in rx.finditer(text):
            out.append(Finding(entity, category, m.start("v"), m.end("v"), m.group("v")))
    return out


def find_patterns(text: str) -> list[Finding]:
    found: list[Finding] = []
    found.extend(_find_greek_ids(text))
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
