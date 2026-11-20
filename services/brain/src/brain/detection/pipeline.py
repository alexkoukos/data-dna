"""Run all checks on one prompt, cheapest first. Document checks plug in here later."""

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass

from brain.detection.normalize import Normalised, normalise
from brain.detection.patterns import Finding, find_patterns, mask
from brain.documents.registry import DocMatch
from brain.policy.engine import PRECEDENCE, Decision, Verdict, decide
from brain.policy.store import PolicySet


@dataclass
class InspectResult:
    verdict: Verdict
    findings: list[Finding]
    masked_text: str
    placeholders: dict[str, str]
    evasion_signals: list[str]
    doc_matches: list[DocMatch]
    text: str = ""
    stopped_early: bool = False  # the language models were skipped: the cheap checks blocked


Finder = Callable[[str], list[Finding]]


def _add_without_overlap(base: list[Finding], extra: list[Finding]) -> list[Finding]:
    """Checksum-validated findings win: a looser finder never replaces or splits them."""
    out = list(base)
    for f in extra:
        if not any(f.start < b.end and b.start < f.end for b in out):
            out.append(f)
    return sorted(out, key=lambda f: f.start)


def _view_findings(norm: Normalised, view_finders: Sequence[Finder]) -> list[Finding]:
    """What the other readings of a text (de-spaced, decoded, ROT13...) find, once per value."""
    found: list[Finding] = []
    for view in norm.extra_views:
        found.extend(find_patterns(view))
        for vf in view_finders:
            found.extend(vf(view))
    for view in norm.phrase_views:
        for vf in view_finders:
            found.extend(vf(view))
    seen: set[tuple[str, str]] = set()
    out: list[Finding] = []
    for f in found:
        key = (f.entity, "".join(f.value.split()))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


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
    doc_matcher: Callable[..., list[DocMatch]] | None = None,
    priority_finder: Finder | None = None,
    view_finders: Sequence[Finder] = (),
    placeholders: Mapping[str, str] | None = None,
    mask_injection: bool = True,
    expensive: Collection[Finder] = (),
    early_stop: bool = False,
) -> InspectResult:
    """Run every check on one text.

    With `early_stop`, the cheap finders run first and the `expensive` ones (models) only run if
    the cheap ones did not already decide to block. The document matcher always runs, because
    session memory, copy attribution and the incident record depend on it. Findings are always
    merged in the order of `finders`, so when nothing blocks the result is exactly the same as
    without `early_stop`.
    """
    norm = normalise(text)
    findings = find_patterns(norm.text)
    if priority_finder is not None:
        # Decoy credentials look like real keys. They are looked for first and replace the
        # ordinary secret finding, so the alarm names a leaked document, not just "a key".
        decoys = priority_finder(norm.text)
        findings = _add_without_overlap(decoys, findings)
    exact = findings  # pattern and decoy findings, before the looser finders
    stopped = False
    if early_stop and expensive:
        found: dict[int, list[Finding]] = {
            n: f(norm.text) for n, f in enumerate(finders) if f not in expensive
        }

        def merged(base: list[Finding]) -> list[Finding]:
            for n in sorted(found):
                base = _add_without_overlap(base, found[n])
            return base

        quick = merged(findings)
        stopped = (
            decide(
                [f.category for f in quick],
                evasion_signals=norm.evasion_signals,
                category_actions=policies.categories if policies else None,
                sensitivity_actions=policies.sensitivity if policies else None,
            ).decision
            == Decision.BLOCK
        )
        if not stopped:
            for n, f in enumerate(finders):
                if n not in found:
                    found[n] = f(norm.text)
        findings = merged(findings)
    else:
        for finder in finders:
            findings = _add_without_overlap(findings, finder(norm.text))
    hidden = _view_findings(norm, view_finders)
    if hidden:
        # A value written normally ("4111 1111 1111 1111") is found again in the de-spaced copy.
        # Only what the copies still find once the exact findings are masked was hidden. Looser
        # finders (a phone shape over "0/9/0/9/...") do not count: spacing a value out is evasion.
        hidden = _view_findings(normalise(mask(norm.text, exact)[0]), view_finders)
    categories = [f.category for f in findings + hidden]
    doc_matches = doc_matcher(norm.text) if doc_matcher else []
    if doc_matcher and not doc_matches and "client_name" in categories:
        # The name of the counterparty in a document's title, plus a near miss against that
        # document, is two signals, not one.
        names = [f.value for f in findings + hidden if f.category == "client_name"]
        doc_matches = doc_matcher(norm.text, relaxed_for=names)
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
    to_mask = findings if mask_injection else [f for f in findings if f.category != "injection"]
    masked, placeholders = mask(norm.text, to_mask, placeholders)
    return InspectResult(
        verdict,
        findings + hidden,
        masked,
        placeholders,
        norm.evasion_signals,
        doc_matches,
        norm.text,
        stopped_early=stopped,
    )


TOOL_DESCRIPTION_NOTE = (
    "A tool description contains instruction-like wording. Check the tool before you send."
)


def cap_injection(result: InspectResult, policies: PolicySet | None) -> None:
    """Lower a block that only the injection check caused to a warning, in place.

    Used for tool descriptions: they are long, written by the tool's author and often say things
    like "ignore the previous result", so wording alone must not stop the whole request. A real
    secret, decoy credential or protected document in the same text still decides on its own.
    """
    verdict = result.verdict
    if verdict.decision != Decision.BLOCK or not any(
        f.category == "injection" for f in result.findings
    ):
        return
    others = decide(
        [f.category for f in result.findings if f.category != "injection"],
        document_sensitivities=[_effective_sensitivity(m) for m in result.doc_matches],
        evasion_signals=result.evasion_signals,
        category_actions=policies.categories if policies else None,
        sensitivity_actions=policies.sensitivity if policies else None,
    )
    if others.decision == Decision.BLOCK:
        return
    if PRECEDENCE[others.decision] < PRECEDENCE[Decision.WARN]:
        others.decision = Decision.WARN
    verdict.decision = others.decision
    verdict.reasons = [*others.reasons, TOOL_DESCRIPTION_NOTE]
