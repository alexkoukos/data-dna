"""X17: a one-click compliance report mapped to GDPR, NIS2 and the EU AI Act.

The mapping says which duty each Data DNA control helps with. It supports the company's own
compliance work; it is not legal advice and does not certify anything. The same table is kept
in docs/business/compliance-mapping.md for people to read and edit.
"""

import io
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlalchemy as sa
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from brain.db import tables as t
from brain.policy.store import audit_table


@dataclass(frozen=True)
class Mapping:
    framework: str
    reference: str
    duty: str
    control: str
    evidence_key: str  # which live number backs it up


MAPPING: tuple[Mapping, ...] = (
    Mapping(
        "GDPR",
        "Art. 5(1)(c)",
        "Data minimisation: only what is necessary is processed.",
        "Personal identifiers (AFM, AMKA, IBAN, names, contact details) are masked before a "
        "prompt reaches a cloud model.",
        "masked",
    ),
    Mapping(
        "GDPR",
        "Art. 5(1)(f), Art. 32",
        "Integrity, confidentiality and appropriate security of processing.",
        "Every prompt is checked before it leaves; restricted documents are blocked; incidents "
        "show only pseudonyms and masked previews.",
        "checked",
    ),
    Mapping(
        "GDPR",
        "Art. 25",
        "Data protection by design and by default.",
        "The safe action is the default: personal data is masked or answered on a local model "
        "unless a policy says otherwise. Policy changes are audited.",
        "policy_changes",
    ),
    Mapping(
        "GDPR",
        "Art. 33, Art. 34",
        "Detect, record and assess personal data breaches.",
        "Each blocked, warned or masked event is recorded with time, team and reason, which helps "
        "show whether personal data actually left the company.",
        "incidents",
    ),
    Mapping(
        "GDPR",
        "Chapter V (Art. 44 onwards)",
        "Limit transfers of personal data to third countries.",
        "Confidential content is answered by the local model, so it does not go to a cloud "
        "provider outside the company.",
        "local",
    ),
    Mapping(
        "NIS2",
        "Art. 21(2)(a), (e)",
        "Risk analysis and security policies; security in acquiring and using systems.",
        "A tool inventory shows which AI tools are used and which are not approved, with a "
        "risk rating and an approved alternative.",
        "unapproved",
    ),
    Mapping(
        "NIS2",
        "Art. 21(2)(b), Art. 23",
        "Incident handling and reporting.",
        "A searchable incident log with the layers that fired and a replay of the masked "
        "prompt supports early warning and the follow-up report.",
        "incidents",
    ),
    Mapping(
        "NIS2",
        "Art. 21(2)(i)",
        "Access control and asset management.",
        "Per-user keys, pseudonymised identities and a two-person approval before a real "
        "identity is revealed.",
        "reveals",
    ),
    Mapping(
        "EU AI Act",
        "Art. 26(2), 26(5)",
        "Deployers assign human oversight and monitor how AI systems are used.",
        "Warn decisions ask a person to confirm; the dashboard shows usage per tool and team.",
        "warned",
    ),
    Mapping(
        "EU AI Act",
        "Art. 26(6)",
        "Deployers of high-risk systems keep automatically generated logs for at least six months.",
        "Decisions are logged automatically. Retention is set by RETENTION_DAYS (default 30), "
        "so raise it to meet a longer duty.",
        "incidents",
    ),
    Mapping(
        "EU AI Act",
        "Art. 4",
        "AI literacy of staff.",
        "Warnings and reasons are written in plain words, so each blocked message teaches the "
        "person what to do instead.",
        "incidents",
    ),
)

DISCLAIMER = (
    "This report supports your own compliance work. It is not legal advice and it is not a "
    "certification. A lawyer or data protection officer should confirm how each duty applies to "
    "your company."
)


def gather_evidence(conn: sa.Connection, demo: bool) -> dict[str, int]:
    inc = t.incidents.c

    def count(*where: sa.ColumnElement[bool]) -> int:
        return int(
            conn.execute(
                sa.select(sa.func.count()).select_from(t.incidents).where(*where)
            ).scalar_one()
        )

    checked = conn.execute(
        sa.select(sa.func.coalesce(sa.func.sum(t.counters_daily.c.checked), 0))
    ).scalar_one()
    unapproved = conn.execute(
        sa.select(sa.func.count())
        .select_from(t.ai_tools)
        .where(t.ai_tools.c.approval == "unapproved")
    ).scalar_one()
    reveals = conn.execute(sa.select(sa.func.count()).select_from(t.reveal_requests)).scalar_one()
    policy_changes = conn.execute(
        sa.select(sa.func.count())
        .select_from(audit_table)
        .where(audit_table.c.action == "policy.update")
    ).scalar_one()
    return {
        "checked": int(checked),
        "incidents": count(),
        "masked": count(inc.decision == "mask"),
        "warned": count(inc.decision == "warn"),
        "local": count(inc.decision == "local"),
        "blocked": count(inc.decision == "block"),
        "unapproved": int(unapproved),
        "reveals": int(reveals),
        "policy_changes": int(policy_changes),
        "demo": int(demo),
    }


_EVIDENCE_TEXT = {
    "masked": "{} events masked",
    "checked": "{} prompts checked",
    "policy_changes": "{} audited policy changes",
    "incidents": "{} incidents recorded",
    "local": "{} answered locally",
    "unapproved": "{} unapproved tools seen",
    "reveals": "{} identity reveal requests",
    "warned": "{} warnings issued",
}


def render_pdf(evidence: dict[str, int], now: datetime | None = None) -> bytes:
    now = now or datetime.now(UTC)
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=11)
    head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Data DNA compliance report",
    )
    story: list[Flowable] = [
        Paragraph("Data DNA compliance report", styles["Title"]),
        Paragraph(f"Generated {now:%d %B %Y, %H:%M} UTC", styles["Normal"]),
        Spacer(1, 4 * mm),
    ]
    if evidence.get("demo"):
        story += [
            Paragraph(
                "<b>Demo data.</b> The numbers below come from a synthetic company.",
                styles["Normal"],
            ),
            Spacer(1, 3 * mm),
        ]
    summary = (
        f"{evidence['checked']} prompts were checked. {evidence['incidents']} needed action: "
        f"{evidence['blocked']} blocked, {evidence['masked']} masked, {evidence['warned']} warned, "
        f"{evidence['local']} answered on the local model."
    )
    story += [Paragraph("Summary", styles["Heading2"]), Paragraph(summary, styles["BodyText"])]
    rows = [
        [
            Paragraph(h, head)
            for h in ("Framework", "Reference", "Duty", "How Data DNA helps", "Evidence")
        ]
    ]
    for m in MAPPING:
        n = evidence.get(m.evidence_key, 0)
        rows.append(
            [
                Paragraph(m.framework, cell),
                Paragraph(m.reference, cell),
                Paragraph(m.duty, cell),
                Paragraph(m.control, cell),
                Paragraph(_EVIDENCE_TEXT[m.evidence_key].format(n), cell),
            ]
        )
    table = Table(rows, colWidths=[18 * mm, 24 * mm, 42 * mm, 66 * mm, 30 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]
        )
    )
    story += [
        Spacer(1, 5 * mm),
        Paragraph("Duties and controls", styles["Heading2"]),
        table,
        Spacer(1, 5 * mm),
        Paragraph("Limits", styles["Heading2"]),
        Paragraph(DISCLAIMER, styles["BodyText"]),
    ]
    doc.build(story)
    return buf.getvalue()
