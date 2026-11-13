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
