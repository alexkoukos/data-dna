"""YARA rules for secrets and company code (PRD 9.2). Rules live in `rules/*.yar`."""

from pathlib import Path

import yara

from brain.detection.patterns import Finding

RULES_DIR = Path(__file__).with_name("rules")
_rules: yara.Rules | None = None


def _compiled() -> yara.Rules:
    global _rules
    if _rules is None:
        files = {p.stem: str(p) for p in sorted(RULES_DIR.glob("*.yar"))}
        _rules = yara.compile(filepaths=files)
    return _rules


def find_yara(text: str) -> list[Finding]:
    """One Finding per matched string. Offsets are character offsets in `text`."""
    if not text:
        return []
    data = text.encode("utf-8")
    # Map byte offsets back to character offsets, so masking works on non-ASCII text.
    char_at: list[int] = []
    for i, ch in enumerate(text):
        char_at.extend([i] * len(ch.encode("utf-8")))
    char_at.append(len(text))

    found: list[Finding] = []
    for match in _compiled().match(data=data):
        meta = match.meta
        for s in match.strings:
            for inst in s.instances:
                start = char_at[inst.offset]
                end = char_at[inst.offset + inst.matched_length]
                found.append(
                    Finding(
                        str(meta.get("entity", match.rule.upper())),
                        str(meta.get("category", "secret")),
                        start,
                        end,
                        text[start:end],
                    )
                )
    found.sort(key=lambda f: (f.start, -(f.end - f.start)))
    out: list[Finding] = []
    for f in found:
        if out and f.start < out[-1].end:
            continue
        out.append(f)
    return out
