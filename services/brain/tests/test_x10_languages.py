import pytest

from brain.documents.chunking import language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Der Vertrag mit dem Kunden ist nicht für die Veröffentlichung bestimmt.", "de"),
        ("Le contrat avec le client n'est pas destiné à la publication dans les médias.", "fr"),
        ("The contract with the client is not for release to the press or the public.", "en"),
        ("Η σύμβαση με τον πελάτη δεν προορίζεται για δημοσίευση.", "el"),
        ("ok", "en"),
        ("", "en"),
    ],
)
def test_language_is_detected(text: str, expected: str) -> None:
    assert language(text) == expected
