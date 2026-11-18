from fastapi.testclient import TestClient

from brain.main import app

client = TestClient(app)


def test_healthz() -> None:
    assert client.get("/healthz").json()["status"] == "ok"


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


def test_a_chunked_body_without_content_length_is_413(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import brain.main as main_mod

    monkeypatch.setattr(main_mod, "MAX_BODY_BYTES", 1000)

    def chunks():  # type: ignore[no-untyped-def]
        for _ in range(10):
            yield b" " * 500

    r = client.post("/v1/inspect", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and "too large" in r.json()["detail"]
    small = {"messages": [{"role": "user", "content": "hi"}]}
    monkeypatch.setattr(main_mod, "MAX_BODY_BYTES", 15 * 1024 * 1024)
    assert client.post("/v1/inspect", json=small).status_code == 200


def test_healthz_reports_the_database(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import sqlalchemy as sa
    from sqlalchemy.pool import StaticPool

    import brain.main as main_mod
    from brain.policy.store import PolicyStore

    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(main_mod, "policy_store", PolicyStore(engine, ttl_seconds=0))
    assert client.get("/healthz").json() == {"status": "ok", "database": "ok"}

    class _Down:
        def connect(self):  # type: ignore[no-untyped-def]
            raise sa.exc.OperationalError("x", {}, Exception("down"))

    monkeypatch.setattr(main_mod.policy_store, "_engine", _Down())
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["database"] == "unreachable"


def test_a_long_history_is_not_refused_and_a_secret_deep_in_it_is_still_found() -> None:
    filler = "The quarterly numbers were discussed at length. " * 2200
    msgs = [{"role": "user", "content": "Here are the old notes."}]
    for _ in range(3):
        msgs += [
            {"role": "assistant", "content": filler},
            {"role": "user", "content": "ok, continue please"},
        ]
    msgs[1]["content"] = "key AKIAIOSFODNN7EXAMPLE " + filler  # the oldest turn, past the budget
    msgs.append({"role": "user", "content": "Thanks, now write a short poem about spring."})
    assert sum(len(m["content"]) for m in msgs) > 300_000
    r = client.post("/v1/inspect", json={"messages": msgs})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] in ("mask", "warn", "block")
    assert any(f["entity"] == "AWS_ACCESS_KEY" or "key" in f["category"] for f in body["findings"])


def test_new_content_over_the_cap_is_413_but_the_same_text_as_history_is_not() -> None:
    big = "a " * 50_500
    assert (
        client.post(
            "/v1/inspect", json={"messages": [{"role": "user", "content": big}]}
        ).status_code
        == 413
    )
    ok = client.post(
        "/v1/inspect",
        json={
            "messages": [
                {"role": "user", "content": big},
                {"role": "assistant", "content": "fine"},
                {"role": "user", "content": "short question"},
            ]
        },
    )
    assert ok.status_code == 200


def _full_width(text: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) if c.isascii() and c.isalnum() else c for c in text)


def test_a_full_width_iban_is_caught_on_the_way_in_and_on_the_way_out(valid_iban: str) -> None:
    wide = _full_width(valid_iban)
    assert wide != valid_iban
    r = client.post("/v1/inspect", json={"messages": [{"role": "user", "content": f"pay {wide}"}]})
    assert r.json()["decision"] == "mask"
    assert "1250" not in r.json()["masked_messages"][0]["content"]
    out = client.post("/v1/inspect-output", json={"text": f"pay {wide}"}).json()
    assert out["changed"] and "[IBAN_OUT_1]" in out["text"] and wide not in out["text"]
