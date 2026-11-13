import json
from pathlib import Path

import numpy as np
import pytest
import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

from brain.db import tables as t
from brain.detection.pipeline import inspect_text
from brain.documents.chunking import chunk_text
from brain.documents.embeddings import FastEmbedder, HashingEmbedder
from brain.documents.fingerprint import jaccard, signature
from brain.documents.loader import load_documents, parse
from brain.documents.registry import DocumentIndex, register_document
from brain.policy.engine import Decision

SAMPLES = Path(__file__).parents[3] / "data" / "documents"
MEMO = (
    "The management team recommends opening offices in Sofia and Belgrade during the second "
    "quarter of 2027. The plan assumes an initial investment of four million euros, financed "
    "from retained earnings, with break even expected after twenty two months. We intend to "
    "acquire a small Sofia firm for one and a half million euros which gives us an existing "
    "client base in banking and telecommunications."
)


@pytest.fixture
def engine() -> sa.Engine:
    e = sa.create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    t.metadata.create_all(e)
    return e


def test_chunks_overlap_by_half_and_cover_the_text() -> None:
    text = " ".join(f"w{i}" for i in range(50))
    chunks = chunk_text(text)
    assert chunks[0].split()[:1] == ["w0"] and len(chunks[0].split()) == 20
    assert chunks[1].split()[0] == "w10"
    assert chunks[-1].split()[-1] == "w49"
    assert chunk_text("") == [] and chunk_text("just three words") == ["just three words"]


def test_signatures_ignore_case_accents_and_punctuation() -> None:
    a = signature(
        "Η ΔΙΟΊΚΗΣΗ προτείνει, να ανοίξουμε γραφεία στη Σόφια και το Βελιγράδι πάρα πολύ."
    )
    b = signature("η διοικηση προτεινει να ανοιξουμε γραφεια στη σοφια και το βελιγραδι παρα πολυ")
    assert jaccard(a, b) == 1.0
    assert (
        jaccard(a, signature("something entirely different about cooking pasta tonight ok")) < 0.2
    )


def test_exact_copy_is_found_with_the_right_chunks(engine: sa.Engine) -> None:
    emb = HashingEmbedder()
    doc_id, n = register_document(engine, emb, "Memo", "restricted", MEMO)
    assert n >= 3
    index = DocumentIndex(engine, emb, ttl_seconds=0)
    hits = index.match("Please fix the grammar: " + MEMO[:200])
    assert [h.document_id for h in hits] == [doc_id]
    assert hits[0].kind == "copy" and hits[0].sensitivity == "restricted"
    assert hits[0].matched_chunks and hits[0].total_chunks == n


def test_unrelated_text_and_an_empty_index_match_nothing(engine: sa.Engine) -> None:
    emb = HashingEmbedder()
    assert DocumentIndex(engine, emb, ttl_seconds=0).match(MEMO) == []
    register_document(engine, emb, "Memo", "restricted", MEMO)
    index = DocumentIndex(engine, emb, ttl_seconds=0)
    assert index.match("How do I make a good carbonara with only eggs, cheese and pepper?") == []
    assert index.match("") == []


def test_registering_twice_refills_instead_of_duplicating(engine: sa.Engine) -> None:
    emb = HashingEmbedder()
    first, _ = register_document(engine, emb, "Memo", "internal", MEMO)
    second, _ = register_document(engine, emb, "Memo", "restricted", MEMO)
    assert first == second
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT COUNT(*) FROM documents")).scalar_one() == 1
        assert (
            conn.execute(sa.text("SELECT sensitivity FROM documents")).scalar_one() == "restricted"
        )


def test_text_is_stored_only_when_asked(engine: sa.Engine) -> None:
    emb = HashingEmbedder()
    register_document(engine, emb, "A", "internal", MEMO, keep_text=False)
    register_document(engine, emb, "B", "internal", MEMO, keep_text=True)
    with engine.connect() as conn:
        kept = dict(
            conn.execute(
                sa.text(
                    "SELECT d.title, COUNT(c.text_demo) FROM documents d "
                    "JOIN doc_chunks c ON c.document_id = d.id GROUP BY d.title"
                )
            ).all()
        )
    assert kept["A"] == 0 and kept["B"] > 0


def test_empty_document_is_refused(engine: sa.Engine) -> None:
    with pytest.raises(ValueError, match="no text"):
        register_document(engine, HashingEmbedder(), "Empty", "internal", "   ")


def test_a_restricted_copy_is_blocked_and_a_confidential_one_goes_local(
    engine: sa.Engine,
) -> None:
    emb = HashingEmbedder()
    register_document(engine, emb, "Memo", "restricted", MEMO)
    register_document(engine, emb, "Contract", "confidential", "alpha beta gamma delta " * 12)
    index = DocumentIndex(engine, emb, ttl_seconds=0)
    blocked = inspect_text(MEMO, doc_matcher=index.match)
    assert blocked.verdict.decision == Decision.BLOCK
    assert any("restricted document" in r for r in blocked.verdict.reasons)
    local = inspect_text("alpha beta gamma delta " * 12, doc_matcher=index.match)
    assert local.verdict.decision == Decision.LOCAL


def test_loader_reads_headers_and_prefers_real_files_over_samples(
    engine: sa.Engine, tmp_path: Path
) -> None:
    (tmp_path / "a.sample.md").write_text("---\ntitle: Sample\nsensitivity: internal\n---\n" + MEMO)
    assert load_documents(engine, HashingEmbedder(), tmp_path, keep_text=False) == 1
    (tmp_path / "real.md").write_text("---\ntitle: Real\nsensitivity: restricted\n---\n" + MEMO)
    (tmp_path / "bad.md").write_text("no header here")
    assert load_documents(engine, HashingEmbedder(), tmp_path, keep_text=False) == 1
    with engine.connect() as conn:
        titles = {r[0] for r in conn.execute(sa.text("SELECT title FROM documents"))}
    assert titles == {"Sample", "Real"}
    assert parse("no header") is None


def test_the_shipped_sample_documents_have_valid_headers() -> None:
    files = sorted(SAMPLES.glob("*.sample.md"))
    assert len(files) == 3
    for f in files:
        meta, body = parse(f.read_text(encoding="utf-8")) or ({}, "")
        assert meta["sensitivity"] in {"internal", "confidential", "restricted"}
        assert len(body.split()) > 60


@pytest.mark.slow
def test_go_no_go_paraphrase_recall_with_the_real_model(engine: sa.Engine) -> None:
    """The D3 go/no-go: rewrites of the sample documents are found, ordinary questions are not."""
    emb = FastEmbedder()
    load_documents(engine, emb, SAMPLES, keep_text=False)
    index = DocumentIndex(engine, emb, ttl_seconds=0)
    data = json.loads((Path(__file__).parent / "data" / "paraphrases.json").read_text("utf-8"))
    found = sum(
        1 for p in data["positives"] if any(h.title == p["doc"] for h in index.match(p["text"]))
    )
    false_alarms = [n["text"] for n in data["negatives"] if index.match(n["text"])]
    recall = found / len(data["positives"])
    assert false_alarms == []
    assert recall >= 0.6, f"recall {recall:.2f}"
    assert np.isclose(np.linalg.norm(emb.embed(["x y z"])[0]), 1.0, atol=1e-3)
