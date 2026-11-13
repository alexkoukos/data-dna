import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import brain.main as main
from brain.db import tables as t
from brain.dna.marks import (
    Mark,
    assign_vectors,
    attribute,
    copy_code,
    hamming,
    propose_marks,
    render,
    sentences,
)
from brain.documents.embeddings import HashingEmbedder
from brain.policy.store import PolicyStore
from brain.policy.store import metadata as policy_metadata

TEXT = " ".join(
    f"Clause {i} says the supplier delivers batch {i * 3} on day {i + 10} for {i * 1000} euros."
    for i in range(1, 15)
)


def test_proposed_marks_are_6_to_8_spread_out_with_4_distinct_variants() -> None:
    marks = propose_marks(TEXT)
    assert 6 <= len(marks) <= 8
    assert [m.position for m in marks] == sorted({m.position for m in marks})
    for m in marks:
        assert len(set(m.variants)) == 4
    flat = [v for m in marks for v in m.variants]
    assert len(flat) == len(set(flat))


def test_short_documents_are_refused_in_plain_words() -> None:
    with pytest.raises(ValueError, match="sentences"):
        propose_marks("One. Two. Three.")


def test_a_copy_only_adds_text_and_never_changes_the_original() -> None:
    marks = propose_marks(TEXT)
    out = render(TEXT, marks, [0] * len(marks))
    assert len(out) > len(TEXT)
    stripped = out
    for m in marks:
        stripped = stripped.replace(f" ({m.phrase(0)})", "")
    assert stripped == " ".join(sentences(TEXT))
    for original in ("day 11", "2000 euros", "batch 6"):
        assert original in out


def test_any_two_copies_differ_in_at_least_half_the_marks() -> None:
    vectors = assign_vectors([], 20, 7)
    assert all(hamming(a, b) >= 4 for i, a in enumerate(vectors) for b in vectors[i + 1 :])
    more = assign_vectors(vectors, 5, 7)
    assert all(hamming(a, b) >= 4 for a in more for b in vectors)


def test_asking_for_too_many_copies_says_so() -> None:
    with pytest.raises(ValueError, match="fewer recipients"):
        assign_vectors([], 100000, 6)


def _setup() -> tuple[list[Mark], dict[str, list[int]]]:
    marks = propose_marks(TEXT)
    vecs = assign_vectors([], 4, len(marks))
    return marks, {copy_code(1, v): v for v in vecs}


def test_a_full_leak_names_the_copy_with_the_odds() -> None:
    marks, copies = _setup()
    code, vec = next(iter(copies.items()))
    found = attribute(render(TEXT, marks, vec), marks, copies)
    assert found is not None and found.copy_code == code
    assert found.marks_found == found.marks_matching == len(marks)
    assert found.odds == 4 ** len(marks)
    assert f"all {len(marks)} match copy {code}" in found.sentence


def test_the_leak_is_found_after_shouting_and_accent_changes() -> None:
    marks, copies = _setup()
    code, vec = next(iter(copies.items()))
    mangled = render(TEXT, marks, vec).upper().replace("A", "Á")
    found = attribute(mangled, marks, copies)
    assert found is not None and found.copy_code == code


def test_a_partial_leak_still_points_to_one_copy_with_weaker_odds() -> None:
    marks, copies = _setup()
    code, vec = list(copies.items())[1]
    full = render(TEXT, marks, vec)
    half = " ".join(sentences(full)[: len(sentences(full)) // 2])
    found = attribute(half, marks, copies)
    assert found is not None and found.copy_code == code
    assert 1 <= found.marks_matching < len(marks)


def test_a_mix_of_two_copies_names_both() -> None:
    marks, copies = _setup()
    (code_a, va), (code_b, vb) = list(copies.items())[:2]
    mixed = [va[i] if i % 2 == 0 else vb[i] for i in range(len(marks))]
    found = attribute(render(TEXT, marks, mixed), marks, copies)
    assert found is not None
    assert {found.copy_code, found.runner_up} == {code_a, code_b}
    assert "mix of two copies" in found.sentence


def test_text_without_any_mark_has_no_attribution() -> None:
    marks, copies = _setup()
    assert attribute(TEXT, marks, copies) is None
    assert attribute("anything", marks, {}) is None


# --- through the API ----------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    engine = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(engine)
    policy_metadata.create_all(engine)
    with engine.begin() as c:
        for name in ("u-ann", "u-bob", "u-cy"):
            c.execute(sa.insert(t.users).values(pseudonym=name, team="Legal", role="employee"))
    monkeypatch.setattr(main, "policy_store", PolicyStore(engine, ttl_seconds=0))
    monkeypatch.setattr(main, "embedder", HashingEmbedder())
    return TestClient(main.app)


def _register(client: TestClient) -> int:
    r = client.post(
        "/v1/documents", data={"title": "Contract", "sensitivity": "restricted", "text": TEXT}
    )
    return int(r.json()["id"])


def test_propose_approve_issue_render_and_trace_a_leak(client: TestClient) -> None:
    doc = _register(client)
    proposal = client.post(f"/v1/documents/{doc}/dna/propose").json()["marks"]
    assert 6 <= len(proposal) <= 8 and proposal[0]["preview"]
    state = client.post(f"/v1/documents/{doc}/dna/approve", json={"marks": proposal}).json()
    assert state["enabled"] is True
    issued = client.post(
        f"/v1/documents/{doc}/copies", json={"recipients": ["u-ann", "u-bob", "u-cy"]}
    ).json()
    assert len({c["copy_code"] for c in issued}) == 3
    ann = next(c["copy_code"] for c in issued if c["recipient"] == "u-ann")

    page = client.get(f"/v1/documents/{doc}/copies/{ann}")
    assert page.status_code == 200 and "Clause 1" in page.text and "<h1>Contract</h1>" in page.text
    leaked = page.text.split("<p>")[1].split("</p>")[0]

    r = client.post(
        "/v1/inspect",
        json={
            "user_id": "u-thief",
            "team": "Sales",
            "model": "m",
            "messages": [{"role": "user", "content": "Summarise: " + leaked}],
        },
    ).json()
    assert r["decision"] == "block"
    assert any(f"match copy {ann}" in reason for reason in r["reasons"])
    incident = client.get("/v1/incidents?limit=1").json()["items"][0]
    detail = client.get(f"/v1/incidents/{incident['id']}").json()
    assert detail["copy_code"] == ann


def test_state_and_unknown_things_are_plain_errors(client: TestClient) -> None:
    doc = _register(client)
    assert client.get(f"/v1/documents/{doc}/dna").json() == {
        "enabled": False,
        "marks": 0,
        "copies": [],
    }
    no_marks = client.post(f"/v1/documents/{doc}/copies", json={"recipients": ["u-ann"]})
    assert no_marks.status_code == 422 and "Approve the marks" in no_marks.json()["detail"]
    assert client.get(f"/v1/documents/{doc}/copies/ZZZZ").status_code == 404
    assert client.post("/v1/documents/999/dna/propose", data={"text": "x"}).status_code == 422
    proposal = client.post(f"/v1/documents/{doc}/dna/propose").json()["marks"]
    client.post(f"/v1/documents/{doc}/dna/approve", json={"marks": proposal})
    unknown = client.post(f"/v1/documents/{doc}/copies", json={"recipients": ["u-nobody"]})
    assert unknown.status_code == 422 and "u-nobody" in unknown.json()["detail"]
    client.post(f"/v1/documents/{doc}/copies", json={"recipients": ["u-ann"]})
    twice = client.post(f"/v1/documents/{doc}/copies", json={"recipients": ["u-ann"]})
    assert twice.status_code == 422 and "already has a copy" in twice.json()["detail"]
    frozen = client.post(f"/v1/documents/{doc}/dna/approve", json={"marks": proposal})
    assert frozen.status_code == 422 and "cannot change" in frozen.json()["detail"]


def test_bad_mark_lists_are_refused(client: TestClient) -> None:
    doc = _register(client)
    few = client.post(
        f"/v1/documents/{doc}/dna/approve",
        json={"marks": [{"position": 1, "variants": ["a", "b", "c", "d"]}]},
    )
    assert few.status_code == 422 and "6 and 8" in few.json()["detail"]
    same = client.post(
        f"/v1/documents/{doc}/dna/approve",
        json={"marks": [{"position": i, "variants": ["a", "a", "b", "c"]} for i in range(6)]},
    )
    assert same.status_code == 422 and "4 different variants" in same.json()["detail"]
