"""Write shared/fixtures/l1.json: invented texts with the findings both L1 engines must return.

Run: uv run --project services/brain python scripts/gen_l1_fixtures.py
The Python brain test (tests/test_l1_parity.py) and the extension test (extension/tests/l1.test.ts)
both read the file, so the two rule sets cannot drift apart. Every value here is made up.
"""

import base64
import json
from pathlib import Path

from brain.detection.validators import afm_check_digit, iban_with_check, luhn_ok

OUT = Path(__file__).resolve().parent.parent / "shared" / "fixtures" / "l1.json"


def amka(prefix10: str) -> str:
    for d in "0123456789":
        if luhn_ok(prefix10 + d):
            return prefix10 + d
    raise ValueError(prefix10)


AFM2 = "12345678" + afm_check_digit("12345678")
AMKA = amka("0101900" + "123")
IBAN = iban_with_check("GR", "01101250000000012300695")
IBAN_SPACED = " ".join(IBAN[i : i + 4] for i in range(0, len(IBAN), 4))
BAD_IBAN = IBAN[:-1] + ("0" if IBAN[-1] != "0" else "1")
CARD = "4111111111111111"
OPENAI = "sk-proj-" + "Ab3dE6gH9jK2mN5pQ8sT"
AWS = "AKIA" + "ABCDEFGHIJ234567"
GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
SLACK = "xoxb-123456789012-abcdefghij"
GOOGLE = "AIza" + "SyA1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q"

cases: list[dict[str, object]] = []


def add(name: str, text: str, found: list[tuple[str, str]], **extra: object) -> None:
    cases.append(
        {
            "name": name,
            "text": text,
            "expect": [{"entity": e, "value": v} for e, v in found],
            **extra,
        }
    )


add("clean english", "Please summarise the attached meeting notes in three bullet points.", [])
add("clean greek", "Μπορείς να γράψεις ένα σύντομο email για την αλλαγή ωραρίου;", [])
add("afm valid", f"Ο ΑΦΜ του πελάτη είναι {AFM2}.", [("AFM", AFM2)])
add("afm bad checksum", "Ο ΑΦΜ είναι 123456789 αλλά είναι λάθος.", [])
add("amka valid", f"AMKA {AMKA} for the new hire", [("AMKA", AMKA)])
add("card valid", f"Charge card {CARD} for the order", [("CARD", CARD)])
add("card bad luhn", "Order number 4111111111111112 is not a card", [])
add("iban valid", f"Pay to {IBAN} today", [("IBAN", IBAN)])
add("iban spaced", f"Pay to {IBAN_SPACED} today", [("IBAN", IBAN_SPACED)])
add("iban bad checksum", f"Pay to {BAD_IBAN} today", [])
add("openai key", f"export OPENAI_API_KEY={OPENAI}", [("OPENAI_KEY", OPENAI)])
add("aws key", f"aws_access_key_id = {AWS}", [("AWS_ACCESS_KEY", AWS)])
add("github token", f"git clone https://{GH}@github.com/x/y", [("GITHUB_TOKEN", GH)])
add("slack token", f"SLACK={SLACK}", [("SLACK_TOKEN", SLACK)])
add("google key", f"key={GOOGLE}", [("GOOGLE_API_KEY", GOOGLE)])
add(
    "private key header",
    "-----BEGIN RSA PRIVATE KEY-----\nMIIE",
    [("PRIVATE_KEY", "-----BEGIN RSA PRIVATE KEY-----")],
)
add("police id", "Ταυτότητα ΑΕ 123456 του υπαλλήλου", [("ADT", "ΑΕ 123456")])
add("number plate", "The car, ΥΝΑ-1234, was parked outside", [("PLATE", "ΥΝΑ-1234")])
add("passport", "Passport number: AB1234567", [("PASSPORT", "AB1234567")])
add("gemi", "Η εταιρεία με ΓΕΜΗ 123456789012 έκλεισε", [("GEMI", "123456789012")])
add("greek mobile", "Πάρε με στο 6912345678 αύριο", [("PHONE_GR", "6912345678")])
add("greek mobile +30", "Call +30 6912345678 after lunch", [("PHONE_GR", "+30 6912345678")])
add(
    "email",
    "Send it to maria.papadopoulou@example.gr please",
    [("EMAIL", "maria.papadopoulou@example.gr")],
    l1Only=True,
)
add(
    "two findings",
    f"IBAN {IBAN} and AFM {AFM2}",
    [("IBAN", IBAN), ("AFM", AFM2)],
)
# Evasion: the value is read from a hidden view, so it cannot be masked in place.
add(
    "afm spaced digits",
    "tax id " + " ".join(AFM2),
    [("AFM", AFM2)],
    hidden=True,
    signals=["spaced_digits"],
)
add(
    "base64 key",
    "token: " + base64.b64encode(f"key={OPENAI}".encode()).decode(),
    [("OPENAI_KEY", OPENAI)],
    hidden=True,
    signals=["base64"],
)
add(
    "invisible characters in afm",
    "AFM " + AFM2[:4] + "​" + AFM2[4:],
    [("AFM", AFM2)],
    signals=["invisible_characters"],
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(cases)} cases to {OUT}")
