"""A value written normally, with spaces or dashes, is masked; only a hidden one warns.

The de-spaced copy of the text finds a spaced IBAN or card a second time. That second find must
not turn a mask into a warning, or every IBAN typed in groups would be refused as hidden.
"""

import pytest

from brain.detection.patterns import Finding, find_patterns
from brain.detection.pipeline import inspect_text
from brain.policy.engine import Decision

CARD = "4111 1111 1111 1111"
HIDDEN_CARD = " ".join("4111111111111111")


def _spaced(iban: str) -> str:
    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


@pytest.mark.parametrize(
    "text",
    [
        f"card {CARD}",
        f"card {CARD.replace(' ', '-')}",
        f"card {CARD} exp 12 26",  # two de-spaced copies overlap here
        "amex 3782 822463 10005",
        "call me on 691 234 5678",
    ],
)
def test_values_written_in_groups_are_masked_not_warned(text: str) -> None:
    result = inspect_text(text)
    assert result.verdict.decision == Decision.MASK
    assert "1111" not in result.masked_text and "234 5678" not in result.masked_text


def test_a_spaced_iban_after_plain_words_is_masked(valid_iban: str) -> None:
    result = inspect_text(f"Pay to {_spaced(valid_iban)} today")
    assert result.verdict.decision == Decision.MASK
    assert result.masked_text == "Pay to [IBAN_1] today"
    assert [f.entity for f in result.findings] == ["IBAN"]


def test_a_value_hidden_by_spacing_still_warns() -> None:
    result = inspect_text(f"card {HIDDEN_CARD}")
    assert result.verdict.decision == Decision.WARN
    assert [f.entity for f in result.findings] == ["CARD"]  # once, not once per copy


def test_a_hidden_second_copy_of_a_visible_value_still_warns() -> None:
    result = inspect_text(f"card {CARD}, again {HIDDEN_CARD}")
    assert result.verdict.decision == Decision.WARN
    assert result.masked_text == f"card [CARD_1], again {HIDDEN_CARD}"


def test_a_view_finder_hit_on_a_masked_value_is_not_counted_as_hidden() -> None:
    def all_cards(text: str) -> list[Finding]:
        return [f for f in find_patterns(text) if f.entity == "CARD"]

    result = inspect_text(f"card {CARD}", view_finders=[all_cards])
    assert result.verdict.decision == Decision.MASK


@pytest.mark.parametrize(
    "text",
    [
        "ids 1234 5678 9012 3456 7890",  # five groups: part of a longer run, not a card
        "ref 4111 1111 1111 1112",  # fails Luhn
        "card 4111 1111-1111 1111",  # mixed separators are not a printed card
    ],
)
def test_grouped_card_pattern_is_strict(text: str) -> None:
    assert not any(f.entity == "CARD" for f in find_patterns(text))
