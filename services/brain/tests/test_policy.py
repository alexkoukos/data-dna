from brain.policy.engine import Decision, decide


def test_clean_is_allowed() -> None:
    assert decide([]).decision == Decision.ALLOW


def test_precedence_block_beats_mask() -> None:
    v = decide(["iban"], document_sensitivities=["restricted"])
    assert v.decision == Decision.BLOCK
    assert len(v.reasons) == 2


def test_confidential_document_goes_local() -> None:
    assert decide([], document_sensitivities=["confidential"]).decision == Decision.LOCAL


def test_client_name_warns() -> None:
    assert decide(["client_name"]).decision == Decision.WARN
