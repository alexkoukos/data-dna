"""Free-text analyst questions (PRD 13, A2): a model writes the SQL, we check it hard, then run it.

The model never sees data, only the schema of three read-only views. Its SQL is accepted only if
it is a single SELECT over those views. On Postgres it also runs as a role that can read nothing
else, in a read-only transaction with a time limit, and is capped at 500 rows. The SQL is always
shown next to the answer, because a model can be wrong.
"""

import re
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.config import settings

ALLOWED_VIEWS = {"v_incidents", "v_tool_usage", "v_inventory"}
MAX_ROWS = 500

VIEW_SQL = {
    "v_incidents": """CREATE VIEW v_incidents AS
SELECT i.id, i.ts, i.team, i.tool, i.channel, i.decision,
       CAST(i.categories AS TEXT) AS categories, i.score, d.title AS document,
       u.pseudonym AS person
FROM incidents i
LEFT JOIN documents d ON d.id = i.document_id
LEFT JOIN users u ON u.id = i.user_id""",
    "v_tool_usage": """CREATE VIEW v_tool_usage AS
SELECT u.day, a.name AS tool, a.approval, a.risk, u.team, u.users, u.requests
FROM tool_usage_daily u JOIN ai_tools a ON a.id = u.tool_id""",
    "v_inventory": """CREATE VIEW v_inventory AS
SELECT name, vendor, category, approval, risk, reason, alternative FROM ai_tools""",
}

SCHEMA_TEXT = """Tables you may query (read only):
v_incidents(id, ts, team, tool, channel, decision, categories, score, document, person)
  decision is one of allow, mask, warn, local, block. categories is text like '{iban,card}'.
  tool is the AI tool used, for example 'Company AI'. person is a pseudonym.
v_tool_usage(day, tool, approval, risk, team, users, requests)
  approval is approved, tolerated or unapproved. risk is low, medium or high.
v_inventory(name, vendor, category, approval, risk, reason, alternative)"""


class AskError(ValueError):
    """The question could not be answered. The message says why and what to do."""


def create_views(engine: Engine) -> None:
    """(Re)create the views, and on Postgres let the read-only role see only them."""
    with engine.begin() as conn:
        for name, sql in VIEW_SQL.items():
            conn.execute(sa.text(f"DROP VIEW IF EXISTS {name}"))
            conn.execute(sa.text(sql))
        if engine.dialect.name == "postgresql":
            conn.execute(sa.text("GRANT USAGE ON SCHEMA public TO analyst_ro"))
            for name in VIEW_SQL:
                conn.execute(sa.text(f"GRANT SELECT ON {name} TO analyst_ro"))


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|attach|detach|pragma|copy|call|do|"
    r"execute|set|reset|vacuum|truncate|merge|replace|lock|listen|notify|load|import)\b",
    re.IGNORECASE,
)
_UNSAFE_NAMES = re.compile(
    r"\b(pg_\w+|information_schema|current_setting|set_config|sqlite_\w+|lo_\w+|dblink\w*)\b|--|/\*",
    re.IGNORECASE,
)
_SOURCES = re.compile(r"\b(?:from|join)\s+([A-Za-z_][\w.]*)", re.IGNORECASE)
_CTES = re.compile(r"\b([A-Za-z_]\w*)\s+as\s*\(", re.IGNORECASE)


def clean_sql(raw: str) -> str:
    """Pull the SQL out of a model answer and accept it only if it is one safe SELECT."""
    text = raw.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    text = text.rstrip().rstrip(";").strip()
    if not text:
        raise AskError("The model did not write a query. Try asking again in other words.")
    if ";" in text:
        raise AskError("Only a single query is allowed. Ask for one thing at a time.")
    if not re.match(r"^(select|with)\b", text, re.IGNORECASE):
        raise AskError("Only questions that read data are allowed.")
    if _FORBIDDEN.search(text) or _UNSAFE_NAMES.search(text):
        raise AskError("That query is not allowed. Questions can only read the three views.")
    ctes = {c.lower() for c in _CTES.findall(text)}
    for source in _SOURCES.findall(text):
        if source.lower() not in ALLOWED_VIEWS | ctes:
            raise AskError(
                f"'{source}' cannot be read. You can ask about: " + ", ".join(sorted(ALLOWED_VIEWS))
            )
    return text


def _prompt(question: str) -> list[dict[str, str]]:
    system = (
        "You write one SQL SELECT query that answers a question about AI usage in a company. "
        "Use only these views and columns, no other tables.\n"
        + SCHEMA_TEXT
        + "\nReply with the SQL only, no explanation. Use standard SQL that works on PostgreSQL. "
        "For 'this week' use ts >= CURRENT_DATE - INTERVAL '7 days' or day >= CURRENT_DATE - 7.\n\n"
        "Examples:\n"
        "Q: How many incidents were blocked per team?\n"
        "SELECT team, COUNT(*) AS blocked FROM v_incidents WHERE decision = 'block' "
        "GROUP BY team ORDER BY blocked DESC\n"
        "Q: Which tools are unapproved and what is their risk?\n"
        "SELECT name, vendor, risk FROM v_inventory WHERE approval = 'unapproved' ORDER BY risk\n"
        "Q: Which team uses ChatGPT (personal) the most?\n"
        "SELECT team, SUM(requests) AS requests FROM v_tool_usage "
        "WHERE tool = 'ChatGPT (personal)' GROUP BY team ORDER BY requests DESC LIMIT 5"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": question}]


def write_sql(question: str) -> str:
    """Ask a model for the SQL: OpenAI when a key is set, otherwise the local model."""
    messages = _prompt(question)
    try:
        if settings.openai_api_key:
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0},
                timeout=60,
            )
            r.raise_for_status()
            return str(r.json()["choices"][0]["message"]["content"])
        r = httpx.post(
            f"{settings.local_llm_url}/api/chat",
            json={
                "model": "dna-local",
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0, "num_predict": 300},
            },
            timeout=120,
        )
        r.raise_for_status()
        return str(r.json()["message"]["content"])
    except (httpx.HTTPError, KeyError, ValueError) as err:
        raise AskError(
            "No model is available to write the query. Use one of the preset questions, "
            "set OPENAI_API_KEY, or start the local model with make local."
        ) from err


def run_free(engine: Engine, question: str, writer: Any = None) -> dict[str, Any]:
    sql = clean_sql((writer or write_sql)(question))
    capped = f"SELECT * FROM ({sql}) AS q LIMIT {MAX_ROWS}"
    try:
        with engine.connect() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(sa.text("SET TRANSACTION READ ONLY"))
                conn.execute(sa.text("SET LOCAL statement_timeout = 3000"))
                conn.execute(sa.text("SET LOCAL ROLE analyst_ro"))
            result = conn.execute(sa.text(capped))
            columns = list(result.keys())
            rows = [[_plain(v) for v in row] for row in result.fetchall()]
            conn.rollback()
    except sa.exc.SQLAlchemyError as err:
        raise AskError(
            "The query the model wrote did not run. Try rephrasing the question."
        ) from err
    return {
        "id": "free",
        "question": question,
        "sql": sql,
        "parameters": {},
        "columns": columns,
        "rows": rows,
    }


def _plain(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value
