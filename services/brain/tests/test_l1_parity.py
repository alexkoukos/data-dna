"""The brain must agree with the browser L1 checks on shared/fixtures/l1.json.

The extension runs the same file in extension/tests/l1.test.ts, so a rule changed on one side only
fails a test on the other.
"""

import json
from pathlib import Path

import pytest

from brain.detection.pipeline import inspect_text

FIXTURES = Path(__file__).resolve().parents[3] / "shared" / "fixtures" / "l1.json"
CASES = [
    c for c in json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"] if not c.get("l1Only")
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_brain_matches_shared_fixture(case: dict) -> None:
    result = inspect_text(case["text"])
    got = sorted({(f.entity, f.value.replace(" ", "")) for f in result.findings})
    want = sorted((e["entity"], e["value"].replace(" ", "")) for e in case["expect"])
    assert got == want
    for signal in case.get("signals", []):
        assert signal in result.evasion_signals
