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


def test_inspect_over_the_cap_is_413_with_next_step() -> None:
    body = {"messages": [{"role": "user", "content": "a " * 60_000}]}
    r = client.post("/v1/inspect", json=body)
    assert r.status_code == 413 and "Shorten it" in r.json()["detail"]


def test_too_many_attachments_is_422() -> None:
    item = {"filename": "a.txt", "content_base64": "aGk="}
    body = {"messages": [{"role": "user", "content": "hi"}], "attachments": [item] * 11}
    assert client.post("/v1/inspect", json=body).status_code == 422


def test_a_huge_declared_body_is_413_before_parsing() -> None:
    r = client.post("/v1/inspect", content=b"{}", headers={"Content-Length": str(16 * 1024 * 1024)})
    assert r.status_code in (413, 400)


def test_user_row_id_survives_a_concurrent_first_insert(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import sqlalchemy as sa
    from sqlalchemy.pool import StaticPool

    from brain.db import tables as t
    from brain.records import user_row_id

    e = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(e)
    with e.begin() as c:
        first = user_row_id(c, "racer", "team")
    with e.begin() as c:
        c.execute(sa.delete(t.users))
        c.execute(sa.insert(t.users).values(id=first, pseudonym="racer", team="other"))
        # another request inserted the same person after we looked: no error, same row
        assert user_row_id(c, "racer", "team") == first
        assert len(c.execute(sa.select(t.users)).all()) == 1
