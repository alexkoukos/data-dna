"""X23: the "why" of a decision. Which layers fired, on what, and with what score.

Built from the inspection result only, so it holds no raw text: findings are shown by entity name
and masked preview.
"""

from typing import Any

from brain.detection.patterns import Finding
from brain.detection.pipeline import InspectResult

_LAYERS = (
    ("INJECTION_CLASSIFIER", "Injection model"),
    ("INJECTION_", "Injection phrases"),
    ("YARA_", "Rules (YARA)"),
    ("CLIENT_", "Client list"),
)
_ENTITY_MODEL = {"PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "ORGANIZATION"}


def layer_of(f: Finding) -> str:
    for prefix, name in _LAYERS:
        if f.entity.startswith(prefix):
            return name
    if f.category == "client_name":
        return "Client list"
    if f.category == "source_code":
        return "Rules (YARA)"
    if f.entity in _ENTITY_MODEL:
        return "People and contact model"
    return "Patterns and checksums"


def build_trace(
    result: InspectResult, memory_reasons: list[str] | None = None
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    seen: dict[str, list[Finding]] = {}
    for f in result.findings:
        seen.setdefault(layer_of(f), []).append(f)
    for layer, found in seen.items():
        steps.append(
            {
                "layer": layer,
                "fired": True,
                "score": None,
                "detail": ", ".join(sorted({f"{f.entity} ({f.category})" for f in found})),
            }
        )
    if result.evasion_signals:
        steps.append(
            {
                "layer": "Evasion normalisation",
                "fired": True,
                "score": None,
                "detail": "Seen: " + ", ".join(result.evasion_signals),
            }
        )
    for m in result.doc_matches:
        steps.append(
            {
                "layer": "Document matching",
                "fired": True,
                "score": round(m.score, 3),
                "detail": (
                    f"{m.kind} of a {m.sensitivity} document, "
                    f"{len(m.matched_chunks)} of {m.total_chunks} parts"
                ),
            }
        )
    for reason in memory_reasons or []:
        steps.append({"layer": "Session memory", "fired": True, "score": None, "detail": reason})
    steps.append(
        {
            "layer": "Policy",
            "fired": True,
            "score": None,
            "detail": f"Decision: {result.verdict.decision}",
        }
    )
    return steps
