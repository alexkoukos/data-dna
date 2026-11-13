"""Policy engine: turns findings into one decision with human-readable reasons."""

from dataclasses import dataclass, field
from enum import StrEnum


class Decision(StrEnum):
    ALLOW = "allow"
    MASK = "mask"
    WARN = "warn"
    LOCAL = "local"
    BLOCK = "block"


# Higher number wins.
PRECEDENCE = {
    Decision.ALLOW: 0,
    Decision.MASK: 1,
    Decision.WARN: 2,
    Decision.LOCAL: 3,
    Decision.BLOCK: 4,
}

DEFAULT_CATEGORY_ACTIONS: dict[str, Decision] = {
    "greek_id": Decision.MASK,
    "iban": Decision.MASK,
    "card": Decision.MASK,
    "secret": Decision.MASK,
    "person_email_phone": Decision.MASK,
    "client_name": Decision.WARN,
    "source_code": Decision.WARN,
    "injection": Decision.BLOCK,
    "honeytoken": Decision.BLOCK,
}

DEFAULT_SENSITIVITY_ACTIONS: dict[str, Decision] = {
    "internal": Decision.LOCAL,
    "confidential": Decision.LOCAL,
    "restricted": Decision.BLOCK,
}


@dataclass
class Verdict:
    decision: Decision
    reasons: list[str] = field(default_factory=list)


def decide(
    categories: list[str],
    document_sensitivities: list[str] | None = None,
    evasion_signals: list[str] | None = None,
    category_actions: dict[str, Decision] | None = None,
    sensitivity_actions: dict[str, Decision] | None = None,
) -> Verdict:
    cat_actions = category_actions or DEFAULT_CATEGORY_ACTIONS
    sens_actions = sensitivity_actions or DEFAULT_SENSITIVITY_ACTIONS
    decision = Decision.ALLOW
    reasons: list[str] = []

    def bump(d: Decision, reason: str) -> None:
        nonlocal decision
        reasons.append(reason)
        if PRECEDENCE[d] > PRECEDENCE[decision]:
            decision = d

    for c in sorted(set(categories)):
        bump(cat_actions.get(c, Decision.WARN), f"Contains {c.replace('_', ' ')}")
    for s in sorted(set(document_sensitivities or [])):
        bump(sens_actions.get(s, Decision.LOCAL), f"Matches a {s} document")
    if evasion_signals:
        reasons.append("Evasion attempt detected: " + ", ".join(evasion_signals))
    return Verdict(decision=decision, reasons=reasons)
