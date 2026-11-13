from fastapi.testclient import TestClient

from brain.main import app

client = TestClient(app)


def test_healthz() -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_inspect_masks_iban(valid_iban: str) -> None:
    body = {"messages": [{"role": "user", "content": f"Στείλε στο {valid_iban}"}]}
    r = client.post("/v1/inspect", json=body).json()
    assert r["decision"] == "mask"
    assert valid_iban not in r["masked_messages"][0]["content"]


def test_inspect_clean_allows() -> None:
    body = {"messages": [{"role": "user", "content": "Πες μου ένα ανέκδοτο"}]}
    assert client.post("/v1/inspect", json=body).json()["decision"] == "allow"


def test_spaced_afm_escalates_to_warn(valid_afm: str) -> None:
    spaced = " ".join(valid_afm)
    body = {"messages": [{"role": "user", "content": f"ΑΦΜ {spaced}"}]}
    r = client.post("/v1/inspect", json=body).json()
    assert r["decision"] == "warn"
    assert "spaced_digits" in r["evasion_signals"]
