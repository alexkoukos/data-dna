import pytest

from brain.detection.entities import ClientMatcher, EntityDetector
from brain.detection.pipeline import inspect_text
from brain.policy.engine import Decision


@pytest.fixture(scope="module")
def detector() -> EntityDetector:
    d = EntityDetector()
    d.warm_up()
    return d


def kinds(findings: list) -> set[tuple[str, str]]:  # type: ignore[type-arg]
    return {(f.entity, f.value) for f in findings}


def test_english_person_email_and_phone(detector: EntityDetector) -> None:
    text = "Please email John Smith at john.smith@acme.com or call +30 210 1234567"
    found = kinds(detector.find(text))
    assert ("PERSON", "John Smith") in found
    assert ("EMAIL", "john.smith@acme.com") in found
    assert any(e == "PHONE" for e, _ in found)


def test_greek_person_email_and_mobile(detector: EntityDetector) -> None:
    text = "Ο Γιώργος Παπαδόπουλος έστειλε email στο g.papa@firm.gr και τηλ 6944123456"
    found = kinds(detector.find(text))
    assert ("PERSON", "Γιώργος Παπαδόπουλος") in found
    assert ("EMAIL", "g.papa@firm.gr") in found
    assert ("PHONE", "6944123456") in found


def test_offsets_point_at_the_original_text(detector: EntityDetector) -> None:
    text = "Contact maria.k@example.org today"
    f = next(x for x in detector.find(text) if x.entity == "EMAIL")
    assert text[f.start : f.end] == "maria.k@example.org"


@pytest.mark.parametrize(
    "text",
    [
        "Summarize our meeting notes",
        "Γράψε μου ένα σύντομο email για να μεταθέσω μια συνάντηση στην Πέμπτη.",
        "Explain how a hash map handles collisions",
        "Order number 123456789 shipped on Monday",
    ],
)
def test_ordinary_text_is_not_flagged(detector: EntityDetector, text: str) -> None:
    assert detector.find(text) == []


def test_empty_text_is_fine(detector: EntityDetector) -> None:
    assert detector.find("") == []
    assert detector.find("   ") == []


def test_client_names_ignore_case_and_accents() -> None:
    m = ClientMatcher(["Delphi Insurance", "Πειραιώς Λογιστική"])
    assert kinds(m.find("draft a note for DELPHI INSURANCE about renewals")) == {
        ("CLIENT", "DELPHI INSURANCE")
    }
    assert kinds(m.find("συμβόλαιο για πειραιως λογιστικη")) == {("CLIENT", "πειραιως λογιστικη")}


def test_client_names_need_whole_words() -> None:
    m = ClientMatcher(["Delphi Insurance"])
    assert m.find("the Delphi Insurances team") == []
    assert m.find("") == []
    assert ClientMatcher([]).find("anything") == []


def test_client_offsets_survive_accent_stripping() -> None:
    text = "Ο πελάτης Πειραιώς Λογιστική ζήτησε προσφορά"
    m = ClientMatcher(["Πειραιώς Λογιστική"])
    f = m.find(text)[0]
    assert text[f.start : f.end] == "Πειραιώς Λογιστική"


def test_pipeline_masks_a_person_and_restores_them(detector: EntityDetector) -> None:
    text = "Write to John Smith at john.smith@acme.com"
    result = inspect_text(text, finders=[detector.find])
    assert result.verdict.decision == Decision.MASK
    assert "john.smith@acme.com" not in result.masked_text
    assert "John Smith" not in result.masked_text
    assert set(result.placeholders.values()) >= {"John Smith", "john.smith@acme.com"}


def test_client_name_is_a_warn_by_default() -> None:
    m = ClientMatcher(["Delphi Insurance"])
    result = inspect_text("Summarise the Delphi Insurance contract", finders=[m.find])
    assert result.verdict.decision == Decision.WARN
    assert any("client name" in r for r in result.verdict.reasons)


def test_a_checksum_finding_is_not_replaced_by_a_looser_one(
    detector: EntityDetector, valid_iban: str
) -> None:
    result = inspect_text(f"Pay {valid_iban} to John Smith", finders=[detector.find])
    entities = [f.entity for f in result.findings]
    assert "IBAN" in entities and "PERSON" in entities
    assert entities.count("IBAN") == 1
