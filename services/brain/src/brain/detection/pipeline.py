"""Run all checks on one prompt, cheapest first. Document checks plug in here later."""

from dataclasses import dataclass

from brain.detection.normalize import normalise
from brain.detection.patterns import Finding, find_patterns, mask
from brain.policy.engine import Decision, Verdict, decide


@dataclass
class InspectResult:
    verdict: Verdict
    findings: list[Finding]
    masked_text: str
    placeholders: dict[str, str]
    evasion_signals: list[str]


def inspect_text(text: str) -> InspectResult:
    norm = normalise(text)
    findings = find_patterns(norm.text)
    hidden: list[Finding] = []
    for view in norm.extra_views:
        hidden.extend(find_patterns(view))
    categories = [f.category for f in findings + hidden]
    verdict = decide(categories, evasion_signals=norm.evasion_signals)
    # Evasion that hides an identifier cannot be masked in place: escalate to warn.
    if hidden and verdict.decision == Decision.MASK:
        verdict.decision = Decision.WARN
    masked, placeholders = mask(norm.text, findings)
    return InspectResult(verdict, findings + hidden, masked, placeholders, norm.evasion_signals)
