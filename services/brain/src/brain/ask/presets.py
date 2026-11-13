"""Preset analyst questions (PRD section 13): fixed, parameterised SQL that always works.

The SQL is shown beside every answer so the analyst can check it. Each query only reads, and
uses only portable SQL so it runs on Postgres and on the SQLite used in tests. `:since` is
filled in by the code (a number of days back from today), never from user text.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class Preset:
    id: str
    question: str
    days: int
    sql: str


PRESETS: tuple[Preset, ...] = (
    Preset(
        id="client_data_unapproved",
        question="Which teams used unapproved AI tools and also had client data caught this week?",
        days=7,
        sql="""SELECT u.team, SUM(u.requests) AS unapproved_tool_requests, c.client_data_incidents
FROM tool_usage_daily u
JOIN ai_tools a ON a.id = u.tool_id AND a.approval = 'unapproved'
JOIN (
  SELECT team, COUNT(*) AS client_data_incidents
  FROM incidents
  WHERE CAST(categories AS TEXT) LIKE '%client_name%'
    AND ts >= :since
  GROUP BY team
) c ON c.team = u.team
WHERE u.day >= :since
GROUP BY u.team, c.client_data_incidents
ORDER BY c.client_data_incidents DESC, u.team""",
    ),
    Preset(
        id="top_tools",
        question="Which AI tools are used most, and are they approved?",
        days=7,
        sql="""SELECT a.name AS tool, a.approval, SUM(u.requests) AS requests
FROM tool_usage_daily u
JOIN ai_tools a ON a.id = u.tool_id
WHERE u.day >= :since
GROUP BY a.name, a.approval
ORDER BY requests DESC
LIMIT 10""",
    ),
    Preset(
        id="held_by_team",
        question="Which teams had the most messages blocked, warned or kept local this week?",
        days=7,
        sql="""SELECT i.team, i.decision, COUNT(*) AS messages
FROM incidents i
WHERE i.decision IN ('block', 'warn', 'local')
  AND i.ts >= :since
GROUP BY i.team, i.decision
ORDER BY messages DESC, i.team
LIMIT 15""",
    ),
    Preset(
        id="new_unapproved_tools",
        question="Which unapproved AI tools showed up in the last 14 days?",
        days=14,
        sql="""SELECT a.name AS tool, a.risk, MIN(u.day) AS first_seen, SUM(u.requests) AS requests
FROM tool_usage_daily u
JOIN ai_tools a ON a.id = u.tool_id
WHERE a.approval = 'unapproved'
GROUP BY a.name, a.risk
HAVING MIN(u.day) >= :since
ORDER BY first_seen DESC""",
    ),
    Preset(
        id="document_hits",
        question="Which protected documents were pasted into AI tools most this week?",
        days=7,
        sql="""SELECT d.title, d.sensitivity, COUNT(*) AS incidents
FROM incidents i
JOIN documents d ON d.id = i.document_id
WHERE i.ts >= :since
GROUP BY d.title, d.sensitivity
ORDER BY incidents DESC""",
    ),
)

BY_ID = {p.id: p for p in PRESETS}


def _plain(value: Any) -> Any:
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def run_preset(engine: Engine, preset: Preset, today: date | None = None) -> dict[str, Any]:
    since = (today or datetime.now(UTC).date()) - timedelta(days=preset.days)
    with engine.connect() as conn:
        result = conn.execute(sa.text(preset.sql), {"since": since})
        columns = list(result.keys())
        rows = [[_plain(v) for v in row] for row in result.fetchall()]
    return {
        "id": preset.id,
        "question": preset.question,
        "sql": preset.sql,
        "parameters": {"since": since.isoformat()},
        "columns": columns,
        "rows": rows,
    }
