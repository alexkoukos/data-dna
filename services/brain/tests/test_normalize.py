import base64

from brain.detection.normalize import normalise


def test_invisible_characters_removed() -> None:
    n = normalise("pass​word")
    assert n.text == "password"
    assert "invisible_characters" in n.evasion_signals


def test_spaced_digits_create_extra_view() -> None:
    n = normalise("my id is 1 2 3 4 5 6 7 8 9 0")
    assert "1234567890" in n.extra_views
    assert "spaced_digits" in n.evasion_signals


def test_base64_is_decoded() -> None:
    hidden = base64.b64encode(b"secret client list").decode()
    n = normalise(f"look at {hidden}")
    assert "secret client list" in n.extra_views
    assert "base64" in n.evasion_signals


def test_plain_text_has_no_signals() -> None:
    assert normalise("Γράψε ένα email για τη συνάντηση").evasion_signals == []


def test_an_identifier_typed_one_character_at_a_time_is_seen() -> None:
    n = normalise("Check this account: G R 1 6 0 1 1 0 1 2 5 0 0 0 0 0 0 0 0 1 2 3 0 0 6 9 5")
    assert "spaced_characters" in n.evasion_signals
    assert any("GR1601101250000000012300695" in v for v in n.extra_views)


def test_ordinary_sentences_with_single_letters_are_left_alone() -> None:
    n = normalise("Plan A or B or C, see page 2 and 3 for the x y z chart")
    assert "spaced_characters" not in n.evasion_signals


def test_an_identifier_typed_in_short_groups_is_seen() -> None:
    n = normalise("Check this account: GR 06 01 10 12 54 65 90 85 38 01 29 11 0")
    assert "spaced_characters" in n.evasion_signals
    assert any("GR0601101254659085380129110" in v for v in n.extra_views)
