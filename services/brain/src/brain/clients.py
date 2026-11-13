"""Client names from the `clients` table, cached briefly, as a matcher for the pipeline."""

import logging
import threading
import time

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from brain.db import tables as t
from brain.detection.entities import ClientMatcher
from brain.detection.patterns import Finding

log = logging.getLogger(__name__)


class ClientStore:
    def __init__(self, engine: Engine | None, ttl_seconds: float = 30.0) -> None:
        self.engine = engine
        self._ttl = ttl_seconds
        self._matcher = ClientMatcher([])
        self._loaded_at = float("-inf")
        self._lock = threading.Lock()

    def _names(self) -> list[str]:
        if self.engine is None:
            return []
        with self.engine.connect() as conn:
            rows = conn.execute(sa.select(t.clients.c.name, t.clients.c.aliases)).all()
        return [n for name, aliases in rows for n in [name, *(aliases or [])]]

    def find(self, text: str) -> list[Finding]:
        with self._lock:
            if time.monotonic() - self._loaded_at >= self._ttl:
                try:
                    self._matcher = ClientMatcher(self._names())
                except sa.exc.SQLAlchemyError:
                    log.warning("Could not read clients, keeping the last list")
                self._loaded_at = time.monotonic()
            matcher = self._matcher
        return matcher.find(text)
