"""Run all checks on one prompt, cheapest first. Document checks plug in here later."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from brain.detection.normalize import normalise
from brain.detection.patterns import Finding, find_patterns, mask
from brain.documents.registry import DocMatch
from brain.policy.engine import Decision, Verdict, decide
from brain.policy.store import PolicySet


@dataclass
class InspectResult:
    verdict: Verdict
    findings: list[Finding]
    masked_text: str
    placeholders: dict[str, str]
    evasion_signals: list[str]
    doc_matches: list[DocMatch]


Finder = Callable[[str], list[Finding]]


def _add_without_overlap(base: list[Finding], extra: list[Finding]) -> list[Finding]:
    """Checksum-validated findings win: a looser finder never replaces or splits them."""
    out = list(base)
    for f in extra:
        if not any(f.start < b.end and b.start < f.end for b in out):
            out.append(f)
    return sorted(out, key=lambda f: f.start)


HIGH_CONFIDENCE = 0.91  # a rewrite scoring below this is a likely match, not a certain one


def _effective_sensitivity(m: DocMatch) -> str:
    """A likely (not certain) rewrite of a restricted document is answered locally, not blocked.

    Copies and near copies still block. The data stays inside either way, so a wrong guess costs
    the person a slower local answer instead of a refusal.
    """
    if m.sensitivity == "restricted" and m.kind == "paraphrase" and m.score < HIGH_CONFIDENCE:
        return "confidential"
    return m.sensitivity


def inspect_text(
    text: str,
    policies: PolicySet | None = None,
    finders: Sequence[Finder] = (),
    doc_matcher: Callable[[str], list[DocMatch]] | None = None,
) -> InspectResult:
    norm = normalise(text)
    findings = find_patterns(norm.text)
    for finder in finders:
        findings = _add_without_overlap(findings, finder(norm.text))
    hidden: list[Finding] = []
    for view in norm.extra_views:
        hidden.extend(find_patterns(view))
    categories = [f.category for f in findings + hidden]
    doc_matches = doc_matcher(norm.text) if doc_matcher else []
    verdict = decide(
        categories,
        document_sensitivities=[_effective_sensitivity(m) for m in doc_matches],
        evasion_signals=norm.evasion_signals,
        category_actions=policies.categories if policies else None,
        sensitivity_actions=policies.sensitivity if policies else None,
    )
    # Evasion that hides an identifier cannot be masked in place: escalate to warn.
    if hidden and verdict.decision == Decision.MASK:
        verdict.decision = Decision.WARN
    masked, placeholders = mask(norm.text, findings)
    return InspectResult(
        verdict, findings + hidden, masked, placeholders, norm.evasion_signals, doc_matches
    )
