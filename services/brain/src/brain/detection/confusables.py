"""Look-alike characters (X5): Greek and Cyrillic letters that read as Latin ones, and digits from
other scripts. Every map is one character to one character, so offsets never move and a finding in
the folded text can be masked in the original."""

import re
import unicodedata

# Greek capitals and a few small letters that look like a Latin letter, then the same for Cyrillic.
_TO_LATIN = {
    **dict(zip("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ", "ABEZHIKMNOPTYX", strict=True)),
    **dict(zip("οωρυνικ", "owpuvik", strict=True)),
    **dict(zip("АВЕКМНОРСТУХ", "ABEKMHOPCTYX", strict=True)),
    **dict(zip("авекморстух", "abekmopctyx", strict=True)),
    **dict(zip("іјѕїԁɡ", "ijsidg", strict=True)),
}
_LATIN_LETTER = re.compile(r"[A-Za-z]")
_DIGIT = re.compile(r"\d")
_DIGIT_LOOKALIKES = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"})


def ascii_digits(text: str) -> str:
    """Arabic-Indic, Devanagari, fullwidth and other decimal digits become 0 to 9."""
    return "".join(
        str(unicodedata.digit(c)) if c.isdecimal() and not c.isascii() else c for c in text
    )


_GREEK_LETTER = re.compile("[\u0370-\u03ff\u1f00-\u1fff]")
_TO_GREEK = {
    **dict(zip("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ", strict=True)),
    **dict(zip("ovupkiwa", "ονυρκιωα", strict=True)),
}


def _fold_char(ch: str) -> str:
    base = unicodedata.normalize("NFD", ch)[0]
    return _TO_LATIN.get(base, ch)


def _fold_word(word: str) -> str:
    """Make one word a single script. A word with mostly Greek letters keeps its Greek letters and
    takes the look-alike Latin ones into Greek ("Παπαδόπoυλος" with a Latin o). Anything else
    (identifiers with eight or more digits, Latin names) takes the look-alike Greek and Cyrillic
    letters into Latin."""
    greek = len(_GREEK_LETTER.findall(word))
    latin = len(_LATIN_LETTER.findall(word))
    if greek > latin and len(_DIGIT.findall(word)) < 8:
        out = []
        for c in word:
            if c.isascii():
                out.append(_TO_GREEK.get(c, c))
            elif _GREEK_LETTER.match(c):
                out.append(c)
            else:  # Cyrillic look-alike: through Latin into Greek
                latin_c = _fold_char(c)
                out.append(_TO_GREEK.get(latin_c, c) if latin_c != c else c)
        return "".join(out)
    return "".join(_fold_char(c) if not c.isascii() else c for c in word)


def fold_mixed_tokens(text: str) -> tuple[str, bool]:
    """Fold look-alike letters inside words that mix scripts or hold a digit. A purely Greek or
    Russian word is left alone, so ordinary text does not change.

    Returns the text (same length) and whether any word was changed, which is the sign of
    someone dressing up an identifier or a name."""
    out: list[str] = []
    disguised = False
    for part in re.split(r"(\s+)", text):
        if part and not part.isspace() and (_LATIN_LETTER.search(part) or _DIGIT.search(part)):
            folded = _fold_word(part)
            if folded != part:
                disguised = True
            part = folded
        out.append(part)
    return "".join(out), disguised


def digit_lookalike_view(text: str) -> str | None:
    """A view where O, l and I are read as 0 and 1, inside long words that are almost all digits
    and such letters."""
    changed = False
    out: list[str] = []
    for part in re.split(r"(\s+)", text):
        digits = sum(c.isdigit() for c in part)
        lookalikes = sum(c in "OoIl|" for c in part)
        if len(part) >= 9 and digits >= 3 and (digits + lookalikes) / len(part) >= 0.8:
            fixed = part.translate(_DIGIT_LOOKALIKES)
            changed = changed or fixed != part
            part = fixed
        out.append(part)
    return "".join(out) if changed else None
