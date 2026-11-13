from brain.detection.patterns import find_patterns, mask, unmask


def test_finds_and_masks_iban_and_key(valid_iban: str) -> None:
    text = f"Pay to {valid_iban} and use sk-live-abcdefghijklmnopqrstuv"
    findings = find_patterns(text)
    assert {f.entity for f in findings} == {"IBAN", "OPENAI_KEY"}
    masked, mapping = mask(text, findings)
    assert valid_iban not in masked and "sk-live" not in masked
    assert unmask(masked, mapping) == text


def test_greek_ids(valid_afm: str, valid_amka: str) -> None:
    entities = {f.entity for f in find_patterns(f"ΑΦΜ {valid_afm}, ΑΜΚΑ {valid_amka}")}
    assert entities == {"AFM", "AMKA"}


def test_random_nine_digits_are_not_afm() -> None:
    assert find_patterns("order number 123456789") == []


def test_greek_identifiers_without_a_checksum() -> None:
    from brain.detection.patterns import find_patterns

    def found(text: str) -> dict[str, str]:
        return {f.entity: f.value for f in find_patterns(text)}

    assert found("Η ταυτότητά μου είναι ΑΕ 123456") == {"ADT": "ΑΕ 123456"}
    assert found("plate ΥΝΑ-1234") == {"PLATE": "ΥΝΑ-1234"}
    assert found("my passport number is AK1234567") == {"PASSPORT": "AK1234567"}
    assert found("ΓΕΜΗ 123456789012") == {"GEMI": "123456789012"}
    assert found("call +30 694 123 4567") == {"PHONE_GR": "+30 694 123 4567"}
    assert found("ring 6941234567") == {"PHONE_GR": "6941234567"}
    assert found("office 210 123 4567") == {"PHONE_GR": "210 123 4567"}


def test_greek_identifier_patterns_leave_ordinary_numbers_alone() -> None:
    from brain.detection.patterns import find_patterns

    for text in (
        "order 2123456789 shipped",  # ten digits starting with 2, no prefix or spaces
        "reference 123456789012 for the invoice",  # twelve digits without the word GEMI
        "serial AK1234567 on the box",  # passport shape without the word passport
        "we sell 2024 models in 12 cities",
        "Room ABC 1234",  # letters that never appear on Greek plates
    ):
        assert find_patterns(text) == [], text
