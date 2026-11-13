"""Database side of DNA marks: save approved marks, issue copies, load them for attribution."""

import sqlalchemy as sa

from brain.db import tables as t
from brain.dna.marks import (
    Attribution,
    Mark,
    assign_vectors,
    attribute,
    copy_code,
    hamming,
    render,
)
from brain.documents.chunking import rebuild_text


class DnaError(ValueError):
    """A refusal the person can act on. `status` is the HTTP status to answer with."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


def stored_text(conn: sa.Connection, document_id: int) -> str | None:
    """The document text, when it was kept (demo mode). None otherwise."""
    rows = conn.execute(
        sa.select(t.doc_chunks.c.text_demo)
        .where(t.doc_chunks.c.document_id == document_id)
        .order_by(t.doc_chunks.c.idx)
    ).all()
    chunks = [r[0] for r in rows]
    if not chunks or any(c is None for c in chunks):
        return None
    return rebuild_text(chunks)


def _document(conn: sa.Connection, document_id: int) -> None:
    if (
        conn.execute(sa.select(t.documents.c.id).where(t.documents.c.id == document_id)).first()
        is None
    ):
        raise DnaError("That document does not exist.", 404)


def load_marks(conn: sa.Connection, document_id: int) -> list[Mark]:
    rows = conn.execute(
        sa.select(t.doc_marks.c.position, t.doc_marks.c.variants)
        .where(t.doc_marks.c.document_id == document_id)
        .order_by(t.doc_marks.c.position)
    ).all()
    return [Mark(r[0], list(r[1])) for r in rows]


def load_copies(conn: sa.Connection, document_id: int) -> dict[str, list[int]]:
    rows = conn.execute(
        sa.select(t.doc_copies.c.copy_code, t.doc_copies.c.variant_vector).where(
            t.doc_copies.c.document_id == document_id
        )
    ).all()
    return {r[0]: [int(x) for x in r[1]] for r in rows}


def save_marks(conn: sa.Connection, document_id: int, marks: list[Mark]) -> None:
    _document(conn, document_id)
    if not 6 <= len(marks) <= 8:
        raise DnaError("Use between 6 and 8 marks.")
    if any(len(m.variants) != 4 or len(set(m.variants)) != 4 for m in marks):
        raise DnaError("Every mark needs 4 different variants.")
    if load_copies(conn, document_id):
        raise DnaError("Copies were already issued with the current marks. They cannot change now.")
    conn.execute(sa.delete(t.doc_marks).where(t.doc_marks.c.document_id == document_id))
    conn.execute(
        sa.insert(t.doc_marks),
        [
            {"document_id": document_id, "position": m.position, "variants": m.variants}
            for m in marks
        ],
    )
    conn.execute(
        sa.update(t.documents).where(t.documents.c.id == document_id).values(dna_enabled=True)
    )


def issue_copies(
    conn: sa.Connection, document_id: int, recipients: list[str]
) -> list[tuple[str, str]]:
    """One copy per recipient pseudonym. Returns (copy code, pseudonym)."""
    _document(conn, document_id)
    marks = load_marks(conn, document_id)
    if not marks:
        raise DnaError("Approve the marks for this document before issuing copies.")
    if not recipients or len(set(recipients)) != len(recipients):
        raise DnaError("Name each recipient once.")
    users = {
        r[0]: r[1]
        for r in conn.execute(
            sa.select(t.users.c.pseudonym, t.users.c.id).where(t.users.c.pseudonym.in_(recipients))
        )
    }
    missing = [r for r in recipients if r not in users]
    if missing:
        raise DnaError(f"Unknown recipient: {', '.join(missing)}. Use a person's pseudonym.")
    already = {
        r[0]
        for r in conn.execute(
            sa.select(t.doc_copies.c.recipient_user_id).where(
                t.doc_copies.c.document_id == document_id
            )
        )
    }
    if any(users[r] in already for r in recipients):
        raise DnaError("Someone on the list already has a copy of this document.")
    existing = list(load_copies(conn, document_id).values())
    vectors = assign_vectors(existing, len(recipients), len(marks), seed=document_id)
    out = []
    for pseudonym, vec in zip(recipients, vectors, strict=True):
        code = copy_code(document_id, vec)
        conn.execute(
            sa.insert(t.doc_copies).values(
                document_id=document_id,
                copy_code=code,
                recipient_user_id=users[pseudonym],
                variant_vector=vec,
            )
        )
        out.append((code, pseudonym))
    return out


def render_copy_html(conn: sa.Connection, document_id: int, code: str) -> tuple[str, str]:
    """(title, text of the copy for this code). Needs the stored text."""
    copies = load_copies(conn, document_id)
    if code not in copies:
        raise DnaError("That copy does not exist.", 404)
    text = stored_text(conn, document_id)
    if text is None:
        raise DnaError(
            "The text of this document is not stored, so the copy cannot be drawn. "
            "Upload the document again with the text.",
            409,
        )
    title = conn.execute(
        sa.select(t.documents.c.title).where(t.documents.c.id == document_id)
    ).scalar_one()
    return str(title), render(text, load_marks(conn, document_id), copies[code])


def attribute_leak(conn: sa.Connection, document_id: int, text: str) -> Attribution | None:
    marks = load_marks(conn, document_id)
    if not marks:
        return None
    return attribute(text, marks, load_copies(conn, document_id))


def min_distance(vectors: list[list[int]]) -> int:
    return min((hamming(a, b) for i, a in enumerate(vectors) for b in vectors[i + 1 :]), default=0)
