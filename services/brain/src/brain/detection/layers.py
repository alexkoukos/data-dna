"""Which level of the pipeline caught what, in the order the pipeline runs them (X1).

Cheapest first (PRD section 9). Every level is listed, fired or not, so a person trying to break
the gateway can see which ones their text got past.
"""

from dataclasses import dataclass

from brain.detection.pipeline import InspectResult


@dataclass(frozen=True)
class Layer:
    id: str
    level: int
    label: str
    fired: bool
    detail: str


def _count(items: list[str]) -> str:
    names = sorted(set(items))
    return ", ".join(f"{n} ×{items.count(n)}" if items.count(n) > 1 else n for n in names)


def explain(result: InspectResult) -> list[Layer]:
    by_cat: dict[str, list[str]] = {}
    for f in result.findings:
        by_cat.setdefault(f.category, []).append(f.entity)

    def hit(*cats: str) -> str:
        return _count([e for c in cats for e in by_cat.get(c, [])])

    docs = "; ".join(
        f"{m.kind} of a {m.sensitivity} document ({m.score:.2f})" for m in result.doc_matches
    )
    rows = [
        ("normalise", "Cleaning of tricks", ", ".join(result.evasion_signals)),
        ("honeytoken", "Decoy credentials", hit("honeytoken")),
        ("identifiers", "Identifiers and checksums", hit("iban", "greek_id", "card")),
        ("rules", "Secrets and code rules", hit("secret", "source_code")),
        ("injection", "Prompt injection", hit("injection")),
        ("people", "Names, emails, phones", hit("person_email_phone")),
        ("clients", "Client names", hit("client_name")),
        ("documents", "Document matching", docs),
    ]
    return [
        Layer(i, n, label, bool(detail), detail) for n, (i, label, detail) in enumerate(rows, 1)
    ]
