"""X5: Greeklish, look-alike characters and digits from other scripts."""

import pytest

from brain.detection.confusables import digit_lookalike_view, fold_mixed_tokens
from brain.detection.greeklish import find_greeklish_names
from brain.detection.normalize import normalise
from brain.detection.pipeline import inspect_text
from brain.detection.validators import afm_check_digit, iban_with_check
from brain.policy.engine import Decision

ARABIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def test_digits_from_other_scripts_become_ascii(valid_afm: str) -> None:
    typed = valid_afm.translate(ARABIC)
    n = normalise("ΑΦΜ " + typed)
    assert n.text.endswith(valid_afm) and "unicode_digits" in n.evasion_signals
    res = inspect_text("My tax number is " + typed)
    assert res.verdict.decision == Decision.MASK
    assert valid_afm not in res.masked_text and "[AFM_1]" in res.masked_text


def test_greek_capitals_where_latin_letters_belong_are_folded() -> None:
    key = "ΑΚΙΑ" + "1234567890ABCDEF"  # the first four are Greek letters
    res = inspect_text(f"deploy with {key} now")
    assert res.verdict.decision == Decision.MASK
    assert "mixed_alphabets" in res.evasion_signals
    assert key not in res.masked_text


def test_cyrillic_look_alike_inside_an_iban(valid_iban: str) -> None:
    disguised = valid_iban.replace("0", "О", 1)  # Cyrillic О instead of a zero
    assert disguised != valid_iban
    res = inspect_text("pay to " + disguised)
    assert res.verdict.decision != Decision.ALLOW


def test_letter_o_typed_for_zero_is_read_as_zero() -> None:
    base = "10234567"
    afm = base + afm_check_digit(base)
    typed = afm.replace("0", "O")
    assert digit_lookalike_view(typed) == afm
    res = inspect_text("number " + typed)
    assert res.verdict.decision != Decision.ALLOW
    assert "digit_lookalikes" in res.evasion_signals


def test_every_zero_typed_as_the_letter_o_is_still_read() -> None:
    typed = iban_with_check("GR", "01101250000000012300695").replace("0", "O")
    assert typed.count("O") >= 6
    res = inspect_text("Pay " + typed)
    assert res.verdict.decision != Decision.ALLOW


def test_ordinary_words_do_not_trigger_the_digit_view() -> None:
    assert digit_lookalike_view("Illinoisville Oolong Hello-World") is None


def test_greek_and_russian_words_are_never_changed() -> None:
    for text in ["Καλημέρα σας, ο κύριος Παπαδόπουλος", "ΟΙ ΑΝΘΡΩΠΟΙ ΤΗΣ ΕΤΑΙΡΕΙΑΣ", "Привет мир"]:
        assert fold_mixed_tokens(text) == (text, False)
        assert normalise(text).evasion_signals == []


def test_a_greek_name_with_a_latin_letter_goes_back_to_greek() -> None:
    assert fold_mixed_tokens("Παπαδόπoυλος")[0] == "Παπαδόπουλος"  # the o is Latin


@pytest.mark.parametrize(
    "text",
    [
        "send it to giorgos papadopoulos tomorrow",
        "Please call Maria Georgiou",
        "contact nikos alexiou about the contract",
        "Dimitris Karagiannis earns too much",
        "ask vasilis michailidis",
    ],
)
def test_greeklish_names_are_people(text: str) -> None:
    assert find_greeklish_names(text)
    res = inspect_text(text, finders=[find_greeklish_names])
    assert res.verdict.decision == Decision.MASK
    assert "[PERSON_1]" in res.masked_text


def test_greeklish_name_takes_the_first_name_with_it() -> None:
    assert find_greeklish_names("email giorgos papadopoulos now")[0].value == "giorgos papadopoulos"


@pytest.mark.parametrize(
    "text",
    [
        "The kitchen renovation is on schedule",
        "Explain how a hash map works",
        "Ο Παπαδόπουλος είναι εδώ",  # Greek script is the Greek model's job
        "Please summarise the quarterly numbers",
        "Our policy is a good one for pavlova lovers",
        "Order 123456789012 was shipped on 2026-11-13",
    ],
)
def test_ordinary_text_is_left_alone(text: str) -> None:
    assert find_greeklish_names(text) == []
    res = inspect_text(text, finders=[find_greeklish_names])
    assert res.verdict.decision == Decision.ALLOW
