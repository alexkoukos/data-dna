"""Register the documents in data/documents/ on start (demo set and the team's own).

Each file starts with a small header, then the text:

    ---
    title: Board memo: expansion into the Balkans
    sensitivity: restricted
    ---
    The memo text...

A header may list decoy credentials planted in the text (X4). They are stored as honeytokens, and
a prompt that contains one raises the alarm.

    honeytokens:
      - AKIAXXXXXXXXXXXXXXXX

Files named `*.sample.md` are invented examples. They are skipped once a real file exists.

A document can carry translations: `salary-bands.en.md` next to `salary-bands.md` holds the same
text in English (header optional). An English rewrite of a Greek document is then compared with
English text. A translation is only used for matching; it is never shown.
"""

import logging
import re
from pathlib import Path

import yaml
from sqlalchemy.engine import Engine

from brain.documents.embeddings import Embedder
from brain.documents.registry import register_document
from brain.honeytokens import Honeytoken, HoneytokenStore

log = logging.getLogger(__name__)

_TRANSLATION = re.compile(r"\.[a-z]{2}\.md$")


def parse(raw: str) -> tuple[dict[str, str], str] | None:
    if not raw.startswith("---"):
        return None
    _, header, body = raw.split("---", 2)
    meta = yaml.safe_load(header) or {}
    if not isinstance(meta, dict) or "title" not in meta or "sensitivity" not in meta:
        return None
    return {k: str(v) for k, v in meta.items()}, body.strip()


def header_honeytokens(raw: str) -> list[Honeytoken]:
    """Decoy values listed in a document header. The kind is guessed from the shape."""
    if not raw.startswith("---"):
        return []
    meta = yaml.safe_load(raw.split("---", 2)[1]) or {}
    values = meta.get("honeytokens") if isinstance(meta, dict) else None
    out: list[Honeytoken] = []
    for v in values if isinstance(values, list) else []:
        s = str(v).strip()
        kind = "mailbox" if "@" in s else "aws_key" if s.startswith("AKIA") else "api_key"
        out.append(Honeytoken(kind, s))
    return out


def load_documents(engine: Engine, embedder: Embedder, folder: Path, keep_text: bool) -> int:
    files = [f for f in sorted(folder.glob("*.md")) if not _TRANSLATION.search(f.name)]
    real = [f for f in files if not f.name.endswith(".sample.md")]
    count = 0
    for f in real or files:
        parsed = parse(f.read_text(encoding="utf-8"))
        if parsed is None:
            log.warning("Skipping %s: it needs a header with title and sensitivity", f.name)
            continue
        meta, body = parsed
        translations = [_translation_text(x) for x in sorted(folder.glob(f"{f.stem}.??.md"))]
        try:
            doc_id, _ = register_document(
                engine, embedder, meta["title"], meta["sensitivity"], body, keep_text, translations
            )
            HoneytokenStore(engine).register(doc_id, header_honeytokens(f.read_text("utf-8")))
            count += 1
        except ValueError:
            log.warning("Skipping %s: no text", f.name)
    return count


def _translation_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    parsed = parse(raw)
    return parsed[1] if parsed else raw.strip()
