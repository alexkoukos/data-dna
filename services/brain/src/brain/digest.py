"""X32: the weekly team digest. Brief question 4: "warn and educate".

Built with SQL over the read-only views (v_incidents, v_inventory) and fixed text templates. No
model is called. It holds team-level counts only: no names, no pseudonyms, no message text, no
masked previews. The column of v_incidents that names the user is never selected.
"""

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa

NOTE = (
    "Team-level counts only. This digest has no employee names and no message text, "
    "in line with data minimisation."
)

# What to do instead, per kind of data that fired. Plain words, one sentence each.
TIPS: dict[str, str] = {
    "iban": "Swap bank account numbers for a placeholder like ACCOUNT_1 before asking an AI.",
    "card": "Never paste card numbers. Describe the problem without the number.",
    "greek_id": "Leave out tax and social security numbers (AFM, AMKA). Ask about the process, not the person.",  # noqa: E501
    "secret": "Keep keys and passwords out of prompts. Use a variable name and rotate any key that was pasted.",  # noqa: E501
    "person_email_phone": "Replace names, emails and phone numbers with roles, like 'the customer'.",  # noqa: E501
    "client_name": "Say 'a client' instead of the client's name, or use Company AI for client work.",  # noqa: E501
    "source_code": "Share a minimal example instead of the real code, or use Company AI for internal code.",  # noqa: E501
    "injection": "Text copied from the web or a file can hide instructions. Read it before pasting it in.",  # noqa: E501
    "honeytoken": "A decoy credential from a confidential document appeared. Do not copy from restricted documents.",  # noqa: E501
    "document": "Summarise confidential documents inside Company AI instead of pasting them elsewhere.",  # noqa: E501
}
DEFAULT_TIP = (
    "When a message is stopped, read the reason. It says what to remove or where to send it."
)
UNAPPROVED_TIP = "Use Company AI instead of {tool}. It is approved and keeps the data inside."


def _parse_categories(raw: str | None) -> list[str]:
    """v_incidents casts the category list to text: '{iban,card}' or '["iban", "card"]'."""
    return sorted({c for c in re.findall(r"[A-Za-z_]+", raw or "")})


def _reference(conn: sa.Connection) -> datetime | None:
    """The time of the newest incident, so the demo's seeded week is "this week" too."""
    newest = conn.execute(
        sa.select(sa.func.max(sa.column("ts", sa.DateTime(timezone=True)))).select_from(
            sa.table("v_incidents")
        )
    ).scalar_one()
    if newest is None:
        return None
    return newest if newest.tzinfo else newest.replace(tzinfo=UTC)


def teams(conn: sa.Connection) -> list[str]:
    rows = conn.execute(
        sa.text("SELECT DISTINCT team FROM v_incidents WHERE team IS NOT NULL ORDER BY team")
    )
    return [str(r[0]) for r in rows]


def _window(conn: sa.Connection, team: str, start: datetime, end: datetime) -> list[Any]:
    return list(
        conn.execute(
            sa.text(
                "SELECT decision, categories, tool FROM v_incidents "
                "WHERE team = :team AND ts > :start AND ts <= :end"
            ).bindparams(
                sa.bindparam("start", type_=sa.DateTime(timezone=True)),
                sa.bindparam("end", type_=sa.DateTime(timezone=True)),
            ),
            {"team": team, "start": start, "end": end},
        )
    )


def build(conn: sa.Connection, team: str, ref: datetime | None = None) -> dict[str, Any]:
    """The digest for one team: the last 7 days against the 7 before."""
    ref = ref or _reference(conn)
    if ref is None:
        return _empty(team)
    week = timedelta(days=7)
    this = _window(conn, team, ref - week, ref)
    prev = _window(conn, team, ref - 2 * week, ref - week)

    outcomes = Counter(r[0] for r in this)
    cats: Counter[str] = Counter()
    for r in this:
        cats.update(_parse_categories(r[1]))
    tool_counts = Counter(r[2] or "Unknown" for r in this)
    inventory = {
        str(r[0]): (str(r[1]), str(r[2]))
        for r in conn.execute(sa.text("SELECT name, approval, risk FROM v_inventory"))
    }
    tools = [
        {
            "name": name,
            "count": n,
            "approval": inventory.get(name, ("unknown", ""))[0],
        }
        for name, n in tool_counts.most_common(5)
    ]
    change = len(this) - len(prev)
    top_categories: list[dict[str, Any]] = [
        {"category": c, "count": n} for c, n in cats.most_common(5)
    ]
    return {
        "team": team,
        "note": NOTE,
        "start": (ref - week).date().isoformat(),
        "end": ref.date().isoformat(),
        "incidents": len(this),
        "previous": len(prev),
        "change": change,
        "change_pct": round(100 * change / len(prev)) if prev else None,
        "outcomes": dict(outcomes.most_common()),
        "categories": top_categories,
        "tools": tools,
        "tips": _tips([str(c["category"]) for c in top_categories], tools),
    }


def _empty(team: str) -> dict[str, Any]:
    return {
        "team": team,
        "note": NOTE,
        "start": None,
        "end": None,
        "incidents": 0,
        "previous": 0,
        "change": 0,
        "change_pct": None,
        "outcomes": {},
        "categories": [],
        "tools": [],
        "tips": [DEFAULT_TIP],
    }


def _tips(categories: list[str], tools: list[dict[str, Any]]) -> list[str]:
    """Two or three short tips, from the kinds of data that fired most, in that order."""
    out = [TIPS[c] for c in categories if c in TIPS][:3]
    unapproved = next((t for t in tools if t["approval"] == "unapproved"), None)
    if unapproved is not None and len(out) < 3:
        out.append(UNAPPROVED_TIP.format(tool=unapproved["name"]))
    if not out:
        out.append(DEFAULT_TIP)
    if len(out) < 2:
        out.append(DEFAULT_TIP)
    return out[:3]


def _label(category: str) -> str:
    return category.replace("_", " ")


def _trend(d: dict[str, Any]) -> str:
    if d["previous"] == 0:
        return f"{d['incidents']} this week, none the week before."
    word = "up" if d["change"] > 0 else "down" if d["change"] < 0 else "unchanged"
    pct = f" ({abs(d['change_pct'])}%)" if d["change"] else ""
    by = f" by {abs(d['change'])}{pct}" if d["change"] else ""
    return f"{d['incidents']} this week, {word}{by} on last week ({d['previous']})."


def to_markdown(d: dict[str, Any]) -> str:
    when = f"{d['start']} to {d['end']}" if d["start"] else "no activity yet"
    lines = [f"# Weekly AI digest: {d['team']}", "", f"_{when}_", "", f"> {d['note']}", ""]
    lines += ["## This week", "", _trend(d), ""]
    if d["outcomes"]:
        lines += ["## Outcomes", "", "| Outcome | Count |", "| --- | --- |"]
        lines += [f"| {k} | {v} |" for k, v in d["outcomes"].items()]
        lines.append("")
    if d["categories"]:
        lines += ["## Kinds of data", "", "| Kind | Count |", "| --- | --- |"]
        lines += [f"| {_label(c['category'])} | {c['count']} |" for c in d["categories"]]
        lines.append("")
    if d["tools"]:
        lines += ["## Tools", "", "| Tool | Approval | Count |", "| --- | --- | --- |"]
        lines += [f"| {t['name']} | {t['approval']} | {t['count']} |" for t in d["tools"]]
        lines.append("")
    lines += ["## Do this instead", ""]
    lines += [f"- {tip}" for tip in d["tips"]]
    return "\n".join(lines) + "\n"


def to_email(d: dict[str, Any]) -> dict[str, str]:
    """Subject and plain-text body, ready to paste. Nothing is sent."""
    parts = ["Hello,", "", f"{d['note']}", "", f"This week for {d['team']}: {_trend(d)}"]
    if d["outcomes"]:
        parts.append("Outcomes: " + ", ".join(f"{n} {k}" for k, n in d["outcomes"].items()) + ".")
    if d["categories"]:
        parts.append(
            "Most common data types: "
            + ", ".join(f"{_label(c['category'])} ({c['count']})" for c in d["categories"][:3])
            + "."
        )
    if d["tools"]:
        parts.append(
            "Tools seen: "
            + ", ".join(f"{t['name']} ({t['approval']}, {t['count']})" for t in d["tools"][:3])
            + "."
        )
    parts += ["", "Do this instead:"] + [f"- {tip}" for tip in d["tips"]]
    parts += ["", "Thank you,", "Hive"]
    return {"subject": f"Weekly AI digest for {d['team']}", "body": "\n".join(parts)}
