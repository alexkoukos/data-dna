"""Register the documents in data/documents/ on start (demo set and the team's own).

Each file starts with a small header, then the text:

    ---
    title: Board memo: expansion into the Balkans
    sensitivity: restricted
    ---
    The memo text...

Files named `*.sample.md` are invented examples. They are skipped once a real file exists.
"""

import logging
from pathlib import Path

import yaml
from sqlalchemy.engine import Engine

from brain.documents.embeddings import Embedder
from brain.documents.registry import register_document

log = logging.getLogger(__name__)


def parse(raw: str) -> tuple[dict[str, str], str] | None:
    if not raw.startswith("---"):
        return None
    _, header, body = raw.split("---", 2)
    meta = yaml.safe_load(header) or {}
    if not isinstance(meta, dict) or "title" not in meta or "sensitivity" not in meta:
        return None
    return {k: str(v) for k, v in meta.items()}, body.strip()


def load_documents(engine: Engine, embedder: Embedder, folder: Path, keep_text: bool) -> int:
    files = sorted(folder.glob("*.md"))
    real = [f for f in files if not f.name.endswith(".sample.md")]
    count = 0
    for f in real or files:
        parsed = parse(f.read_text(encoding="utf-8"))
        if parsed is None:
            log.warning("Skipping %s: it needs a header with title and sensitivity", f.name)
            continue
        meta, body = parsed
        try:
            register_document(engine, embedder, meta["title"], meta["sensitivity"], body, keep_text)
            count += 1
        except ValueError:
            log.warning("Skipping %s: no text", f.name)
    return count
