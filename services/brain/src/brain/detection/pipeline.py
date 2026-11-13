"""Run all checks on one prompt, cheapest first. Document checks plug in here later."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from brain.detection.normalize import normalise
from brain.detection.patterns import Finding, find_patterns, mask
from brain.policy.engine import Decision, Verdict, decide
from brain.policy.store import PolicySet


@dataclass
class InspectResult:
    verdict: Verdict
    findings: list[Finding]
    masked_text: str
    placeholders: dict[str, str]
    evasion_signals: list[str]


Finder = Callable[[str], list[Finding]]


def _add_without_overlap(base: list[Finding], extra: list[Finding]) -> list[Finding]:
    """Checksum-validated findings win: a looser finder never replaces or splits them."""
    out = list(base)
    for f in extra:
        if not any(f.start < b.end and b.start < f.end for b in out):
            out.append(f)
    return sorted(out, key=lambda f: f.start)


def inspect_text(
    text: str, policies: PolicySet | None = None, finders: Sequence[Finder] = ()
) -> InspectResult:
    norm = normalise(text)
    findings = find_patterns(norm.text)
    for finder in finders:
        findings = _add_without_overlap(findings, finder(norm.text))
    hidden: list[Finding] = []
    for view in norm.extra_views:
        hidden.extend(find_patterns(view))
    categories = [f.category for f in findings + hidden]
    verdict = decide(
        categories,
        evasion_signals=norm.evasion_signals,
        category_actions=policies.categories if policies else None,
        sensitivity_actions=policies.sensitivity if policies else None,
    )
    # Evasion that hides an identifier cannot be masked in place: escalate to warn.
    if hidden and verdict.decision == Decision.MASK:
        verdict.decision = Decision.WARN
    masked, placeholders = mask(norm.text, findings)
    return InspectResult(verdict, findings + hidden, masked, placeholders, norm.evasion_signals)
