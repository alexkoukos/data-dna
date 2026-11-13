import random

import pytest

from brain.detection.validators import afm_check_digit, iban_with_check, luhn_ok


@pytest.fixture
def valid_afm() -> str:
    first8 = "12345678"
    return first8 + afm_check_digit(first8)


@pytest.fixture
def valid_amka() -> str:
    # Synthetic: born 15/03/95, then find a Luhn-valid suffix.
    base = "150395" + "1234"
    for d in "0123456789":
        if luhn_ok(base + d):
            return base + d
    raise AssertionError("no luhn digit found")


@pytest.fixture
def valid_iban() -> str:
    rng = random.Random(7)
    bban = "0110125" + "".join(str(rng.randint(0, 9)) for _ in range(16))
    return iban_with_check("GR", bban)
