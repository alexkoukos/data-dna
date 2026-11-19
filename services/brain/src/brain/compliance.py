# ruff: noqa: E501  (the HTML and SVG strings below are single lines on purpose)
"""X17: a one-click compliance report mapped to GDPR, NIS2 and the EU AI Act.

The mapping says which duty each Sentry control helps with. It supports the company's own
compliance work; it is not legal advice and does not certify anything. The same table is kept
in docs/business/compliance.md for people to read and edit.
"""

import html
import io
from dataclasses import dataclass
from datetime import UTC, datetime

import sqlalchemy as sa
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
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
        "rerouted": count(inc.decision == "rerouted"),
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
    "rerouted": "{} sent to Company AI instead",
    "unapproved": "{} unapproved tools seen",
    "reveals": "{} identity reveal requests",
    "warned": "{} warnings issued",
}


# Sentry's colours: black bands at the top and bottom, amber accents, a white page with dark text.
NIGHT = colors.HexColor("#0a0908")
AMBER = colors.HexColor("#F59E0B")
AMBER_INK = colors.HexColor("#92400E")  # amber dark enough to read on white (7:1)
INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#4b4b4b")
STRIPE = colors.HexColor("#faf6ef")
RULE = colors.HexColor("#d9d2c5")

_PAGE_W, _PAGE_H = A4
_HEADER_H = 24 * mm
_FOOTER_H = 14 * mm


def _shield(c: Canvas, x: float, y: float, size: float) -> None:
    """The Sentry mark: an amber shield with a dark eye, drawn from the logo's own coordinates."""
    k = size / 74.0
    c.saveState()
    c.translate(x, y)
    c.scale(k, k)
    p = c.beginPath()
    p.moveTo(32, 70)
    p.lineTo(58, 60)
    p.lineTo(58, 38)
    p.curveTo(58, 22, 46, 11, 32, 5)
    p.curveTo(18, 11, 6, 22, 6, 38)
    p.lineTo(6, 60)
    p.close()
    c.setFillColor(AMBER)
    c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(NIGHT)
    c.setLineWidth(3.5)
    e = c.beginPath()
    e.moveTo(32, 52)
    e.curveTo(41, 52, 47, 44, 47, 38)
    e.curveTo(47, 32, 41, 24, 32, 24)
    e.curveTo(23, 24, 17, 32, 17, 38)
    e.curveTo(17, 44, 23, 52, 32, 52)
    c.drawPath(e, stroke=1, fill=0)
    c.setFillColor(NIGHT)
    c.circle(32, 38, 6, stroke=0, fill=1)
    c.restoreState()


def _decorate(c: Canvas, doc: SimpleDocTemplate) -> None:
    """Header and footer bands on every page."""
    c.saveState()
    c.setFillColor(NIGHT)
    c.rect(0, _PAGE_H - _HEADER_H, _PAGE_W, _HEADER_H, stroke=0, fill=1)
    c.setFillColor(AMBER)
    c.rect(0, _PAGE_H - _HEADER_H - 1.2 * mm, _PAGE_W, 1.2 * mm, stroke=0, fill=1)
    _shield(c, 15 * mm, _PAGE_H - _HEADER_H + 6 * mm, 12 * mm)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(31 * mm, _PAGE_H - _HEADER_H + 11 * mm, "Sentry")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#d8d2c6"))
    c.drawRightString(_PAGE_W - 15 * mm, _PAGE_H - _HEADER_H + 11 * mm, "Compliance report")
    c.setFillColor(NIGHT)
    c.rect(0, 0, _PAGE_W, _FOOTER_H, stroke=0, fill=1)
    c.setFillColor(AMBER)
    c.rect(0, _FOOTER_H, _PAGE_W, 0.8 * mm, stroke=0, fill=1)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#d8d2c6"))
    c.drawString(
        15 * mm, 5.2 * mm, "Sentry holds the gate. Supports your own review; not legal advice."
    )
    c.setFillColor(colors.white)
    c.drawRightString(_PAGE_W - 15 * mm, 5.2 * mm, f"Page {doc.page}")
    c.restoreState()


def render_pdf(evidence: dict[str, int], now: datetime | None = None) -> bytes:
    now = now or datetime.now(UTC)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], textColor=INK, fontSize=10, leading=14)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11)
    head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    title = ParagraphStyle(
        "title", parent=styles["Title"], textColor=INK, alignment=0, fontSize=24, leading=28
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"], textColor=INK, fontSize=14, spaceBefore=10, spaceAfter=4
    )
    meta = ParagraphStyle("meta", parent=body, textColor=MUTED, fontSize=9)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=_HEADER_H + 10 * mm,
        bottomMargin=_FOOTER_H + 10 * mm,
        title="Sentry compliance report",
        author="Sentry",
    )
    story: list[Flowable] = [
        Paragraph("Compliance report", title),
        Paragraph(f"Generated {now:%d %B %Y, %H:%M} UTC", meta),
        Spacer(1, 4 * mm),
    ]
    if evidence.get("demo"):
        story += [
            Paragraph(
                f'<font color="{AMBER_INK.hexval()}"><b>Demo data.</b></font> '
                "The numbers below come from a synthetic company.",
                body,
            ),
            Spacer(1, 3 * mm),
        ]
    summary = (
        f"{evidence['checked']} prompts were checked. {evidence['incidents']} needed action: "
        f"{evidence['blocked']} blocked, {evidence['masked']} masked, {evidence['warned']} warned, "
        f"{evidence['local']} answered on the local model."
    )
    story += [Paragraph("Summary", h2), Paragraph(summary, body)]
    rows = [
        [
            Paragraph(h, head)
            for h in ("Framework", "Reference", "Duty", "How Sentry helps", "Evidence")
        ]
    ]
    for m in MAPPING:
        n = evidence.get(m.evidence_key, 0)
        rows.append(
            [
                Paragraph(f"<b>{m.framework}</b>", cell),
                Paragraph(m.reference, cell),
                Paragraph(m.duty, cell),
                Paragraph(m.control, cell),
                Paragraph(_EVIDENCE_TEXT[m.evidence_key].format(n), cell),
            ]
        )
    table = Table(rows, colWidths=[21 * mm, 24 * mm, 41 * mm, 64 * mm, 30 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NIGHT),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, AMBER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, STRIPE]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story += [
        Spacer(1, 5 * mm),
        Paragraph("Duties and controls", h2),
        table,
        Spacer(1, 5 * mm),
        Paragraph("Limits", h2),
        Paragraph(DISCLAIMER, body),
    ]
    doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
    return buf.getvalue()


_HTML_CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#1a1a1a;font:16px/1.5 Poppins,system-ui,-apple-system,"Segoe UI",sans-serif}
header,footer{background:#0a0908;color:#fff}
header{border-bottom:4px solid #F59E0B}
footer{border-top:3px solid #F59E0B;color:#d8d2c6;font-size:13px}
.bar{max-width:1040px;margin:0 auto;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:12px;font-weight:700;font-size:22px;color:#fff}
.bar span{color:#d8d2c6;font-size:14px}
main{max-width:1040px;margin:0 auto;padding:32px 24px 48px}
h1{font-size:34px;line-height:1.15;margin:0 0 4px}
h2{font-size:20px;margin:32px 0 8px}
.meta{color:#4b4b4b;font-size:14px;margin:0 0 16px}
.demo b{color:#92400E}
table{border-collapse:collapse;width:100%;font-size:14px}
th{background:#0a0908;color:#fff;text-align:left;border-bottom:3px solid #F59E0B}
th,td{padding:10px 12px;vertical-align:top}
td{border-bottom:1px solid #d9d2c5}
tbody tr:nth-child(even){background:#faf6ef}
@media (max-width:720px){table,thead,tbody,tr,th,td{display:block}thead{display:none}
td{border:0;padding:4px 12px}tr{border-bottom:1px solid #d9d2c5;padding:8px 0}}
@media print{@page{margin:12mm}header,footer{-webkit-print-color-adjust:exact;print-color-adjust:exact}
th{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

_SHIELD_SVG = (
    '<svg width="30" height="34" viewBox="0 0 64 74" aria-hidden="true" focusable="false">'
    '<path d="M32 4 L58 14 V36 C58 52 46 63 32 69 C18 63 6 52 6 36 V14 Z" fill="#F59E0B"/>'
    '<path d="M32 22 C41 22 47 30 47 36 C47 42 41 50 32 50 C23 50 17 42 17 36 C17 30 23 22 32 22 Z" '
    'fill="none" stroke="#0a0908" stroke-width="3.5"/><circle cx="32" cy="36" r="6" fill="#0a0908"/></svg>'
)


def render_html(evidence: dict[str, int], now: datetime | None = None) -> str:
    """The same report as a web page you can read, print or save as PDF. Everything is escaped."""
    now = now or datetime.now(UTC)
    e = html.escape
    summary = (
        f"{evidence['checked']} prompts were checked. {evidence['incidents']} needed action: "
        f"{evidence['blocked']} blocked, {evidence['masked']} masked, {evidence['warned']} warned, "
        f"{evidence['local']} answered on the local model."
    )
    rows = "".join(
        f"<tr><td><b>{e(m.framework)}</b></td><td>{e(m.reference)}</td><td>{e(m.duty)}</td>"
        f"<td>{e(m.control)}</td><td>{e(_EVIDENCE_TEXT[m.evidence_key].format(evidence.get(m.evidence_key, 0)))}</td></tr>"
        for m in MAPPING
    )
    demo = (
        '<p class="demo"><b>Demo data.</b> The numbers below come from a synthetic company.</p>'
        if evidence.get("demo")
        else ""
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Sentry compliance report</title>"
        f"<style>{_HTML_CSS}</style></head><body>"
        f'<header><div class="bar"><div class="brand">{_SHIELD_SVG}Sentry</div>'
        "<span>Compliance report</span></div></header>"
        f'<main><h1>Compliance report</h1><p class="meta">Generated {now:%d %B %Y, %H:%M} UTC</p>'
        f"{demo}<h2>Summary</h2><p>{e(summary)}</p><h2>Duties and controls</h2>"
        "<table><thead><tr><th>Framework</th><th>Reference</th><th>Duty</th><th>How Sentry helps</th>"
        f"<th>Evidence</th></tr></thead><tbody>{rows}</tbody></table>"
        f"<h2>Limits</h2><p>{e(DISCLAIMER)}</p></main>"
        '<footer><div class="bar">Sentry holds the gate. Supports your own review; not legal advice.'
        "</div></footer></body></html>"
    )
