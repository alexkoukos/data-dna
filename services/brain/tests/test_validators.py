from brain.detection.validators import afm_ok, amka_ok, iban_ok, luhn_ok


def test_luhn_known_test_card() -> None:
    assert luhn_ok("4111111111111111")
    assert not luhn_ok("4111111111111112")


def test_afm_valid_and_invalid(valid_afm: str) -> None:
    assert afm_ok(valid_afm)
    wrong = valid_afm[:-1] + str((int(valid_afm[-1]) + 1) % 10)
    assert not afm_ok(wrong)
    assert not afm_ok("000000000")
    assert not afm_ok("12345")


def test_amka_needs_date_and_luhn(valid_amka: str) -> None:
    assert amka_ok(valid_amka)
    assert not amka_ok("320395" + valid_amka[6:])  # day 32
    assert not amka_ok(valid_amka[:-1] + str((int(valid_amka[-1]) + 1) % 10))


def test_iban_greek(valid_iban: str) -> None:
    assert len(valid_iban) == 27
    assert iban_ok(valid_iban)
    assert not iban_ok(valid_iban[:-1] + ("0" if valid_iban[-1] != "0" else "1"))
    assert not iban_ok("GR12")
