"""Checksum validators for identifiers. Pure functions, no I/O.

Each validator takes a string of digits (or an IBAN) with separators already removed.
"""

from datetime import date


def luhn_ok(digits: str) -> bool:
    """Luhn mod-10 check, used by payment cards and AMKA."""
    if not digits.isdigit() or len(digits) < 2:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def afm_ok(afm: str) -> bool:
    """Greek tax number (AFM): 9 digits, last one is a weighted mod-11 check digit."""
    if len(afm) != 9 or not afm.isdigit() or afm == "000000000":
        return False
    s = sum(int(afm[i]) * 2 ** (8 - i) for i in range(8))
    return bool((s % 11) % 10 == int(afm[8]))


def afm_check_digit(first8: str) -> str:
    """Return the check digit for 8 AFM digits. Used to build synthetic test data."""
    s = sum(int(first8[i]) * 2 ** (8 - i) for i in range(8))
    return str((s % 11) % 10)


def amka_ok(amka: str) -> bool:
    """Greek social security number (AMKA): DDMMYY birth date + 5 digits, Luhn valid."""
    if len(amka) != 11 or not amka.isdigit():
        return False
    dd, mm, yy = int(amka[0:2]), int(amka[2:4]), int(amka[4:6])
    if not _is_date(dd, mm, yy):
        return False
    return luhn_ok(amka)


def _is_date(dd: int, mm: int, yy: int) -> bool:
    for century in (1900, 2000):
        try:
            date(century + yy, mm, dd)
            return True
        except ValueError:
            continue
    return False


IBAN_LENGTHS = {"GR": 27, "DE": 22, "FR": 27, "IT": 27, "ES": 24, "CY": 28, "GB": 22, "NL": 18}


def iban_ok(iban: str) -> bool:
    """ISO 13616 IBAN check: known length for the country and mod-97 equals 1."""
    iban = iban.replace(" ", "").upper()
    if len(iban) < 15 or not iban[:2].isalpha() or not iban[2:4].isdigit():
        return False
    expected = IBAN_LENGTHS.get(iban[:2])
    if expected is not None and len(iban) != expected:
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(c, 36)) for c in rearranged)
    return int(numeric) % 97 == 1


def iban_with_check(country: str, bban: str) -> str:
    """Build a valid IBAN from a country code and BBAN. Used for synthetic data."""
    rearranged = bban + country + "00"
    numeric = "".join(str(int(c, 36)) for c in rearranged.upper())
    check = 98 - int(numeric) % 97
    return f"{country}{check:02d}{bban}"
