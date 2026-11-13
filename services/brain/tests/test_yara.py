import pytest

from brain.detection.pipeline import inspect_text
from brain.detection.yara_rules import find_yara
from brain.policy.engine import Decision

PEM = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----"


@pytest.mark.parametrize(
    ("text", "entity", "category"),
    [
        (PEM, "PRIVATE_KEY", "secret"),
        (
            "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_SECRET",
            "secret",
        ),
        (
            "DATABASE_URL=postgres://admin:s3cretPass@db.internal.example:5432/app",
            "DB_CONNECTION",
            "secret",
        ),
        (
            "DefaultEndpointsProtocol=https;AccountName=x;AccountKey=" + "A" * 44 + "==",
            "AZURE_CONNECTION",
            "secret",
        ),
        ('password = "hunter2hunter2"', "PASSWORD", "secret"),
        ("curl https://billing.corp.aegean.gr/api", "INTERNAL_HOST", "source_code"),
        ("// Copyright (c) 2024 Aegean Meridian Consulting", "LICENSE_HEADER", "source_code"),
        ("import com.aegeanmeridian.billing.Invoice;", "COMPANY_PACKAGE", "source_code"),
    ],
)
def test_rules_catch_their_target(text: str, entity: str, category: str) -> None:
    found = find_yara(text)
    assert any(f.entity == entity and f.category == category for f in found), found


@pytest.mark.parametrize(
    "text",
    [
        "Explain what a private key is and how TLS uses it",
        "Our password policy needs 12 characters",
        "Visit https://example.com/docs for the manual",
        "",
    ],
)
def test_ordinary_text_has_no_hits(text: str) -> None:
    assert find_yara(text) == []


def test_offsets_are_character_offsets_even_with_greek_text() -> None:
    text = "Το κλειδί μου: " + PEM
    f = find_yara(text)[0]
    assert text[f.start : f.end].startswith("-----BEGIN")


def test_a_pem_block_is_masked_and_a_code_marker_warns() -> None:
    masked = inspect_text(PEM, finders=[find_yara])
    assert masked.verdict.decision == Decision.MASK
    assert "BEGIN RSA PRIVATE KEY" not in masked.masked_text
    code = inspect_text("import com.aegeanmeridian.billing.Invoice;", finders=[find_yara])
    assert code.verdict.decision == Decision.WARN
