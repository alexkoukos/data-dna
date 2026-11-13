"""Table definitions for the app (mirror infra/db/init.sql). The SQL file stays the source of truth.

Generic types are used so the same code runs on Postgres and, in unit tests, on SQLite.
"""

import sqlalchemy as sa

metadata = sa.MetaData()

_TEXT_LIST = sa.ARRAY(sa.Text).with_variant(sa.JSON, "sqlite")
_ID = sa.BigInteger().with_variant(sa.Integer, "sqlite")

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("pseudonym", sa.Text, nullable=False, unique=True),
    sa.Column("display_name", sa.Text),
    sa.Column("team", sa.Text, nullable=False),
    sa.Column("role", sa.Text, nullable=False, server_default="employee"),
    sa.Column("created_at", sa.DateTime(timezone=True)),
)
api_keys = sa.Table(
    "api_keys",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
    sa.Column("key_hash", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True)),
    sa.Column("revoked_at", sa.DateTime(timezone=True)),
)
clients = sa.Table(
    "clients",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("aliases", _TEXT_LIST),
)
documents = sa.Table(
    "documents",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id")),
    sa.Column("sensitivity", sa.Text, nullable=False),
    sa.Column("dna_enabled", sa.Boolean, server_default=sa.false()),
    sa.Column("created_at", sa.DateTime(timezone=True)),
)
incidents = sa.Table(
    "incidents",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("ts", sa.DateTime(timezone=True)),
    sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
    sa.Column("team", sa.Text),
    sa.Column("tool", sa.Text),
    sa.Column("channel", sa.Text),
    sa.Column("decision", sa.Text, nullable=False),
    sa.Column("categories", _TEXT_LIST),
    sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id")),
    sa.Column("copy_code", sa.Text),
    sa.Column("score", sa.Float),
    sa.Column("reasons", sa.JSON),
    sa.Column("masked_preview", sa.Text),
    sa.Column("expires_at", sa.DateTime(timezone=True)),
)
ai_tools = sa.Table(
    "ai_tools",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("vendor", sa.Text),
    sa.Column("domains", _TEXT_LIST, nullable=False),
    sa.Column("category", sa.Text),
    sa.Column("approval", sa.Text),
    sa.Column("risk", sa.Text),
    sa.Column("reason", sa.Text),
    sa.Column("alternative", sa.Text),
)
tool_usage_daily = sa.Table(
    "tool_usage_daily",
    metadata,
    sa.Column("day", sa.Date, primary_key=True),
    sa.Column("tool_id", sa.Integer, sa.ForeignKey("ai_tools.id"), primary_key=True),
    sa.Column("team", sa.Text, primary_key=True),
    sa.Column("users", sa.Integer),
    sa.Column("requests", sa.Integer),
)
counters_daily = sa.Table(
    "counters_daily",
    metadata,
    sa.Column("day", sa.Date, primary_key=True),
    sa.Column("team", sa.Text, primary_key=True),
    sa.Column("allowed", sa.Integer, server_default="0"),
    sa.Column("checked", sa.Integer, server_default="0"),
    sa.Column("zero_llm", sa.Integer, server_default="0"),
    sa.Column("llm_tokens", sa.Integer, server_default="0"),
)
