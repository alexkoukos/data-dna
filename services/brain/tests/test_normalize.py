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
