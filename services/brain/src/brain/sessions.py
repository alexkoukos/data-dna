"""Short-lived placeholder maps, so a masked value can be restored in the answer for its owner.

Held in memory only (never written to disk or logs) and dropped after the TTL.
"""

import threading
import time
import uuid
from dataclasses import dataclass


@dataclass
class _Entry:
    user_id: str
    mapping: dict[str, str]
    expires_at: float


class SessionStore:
    def __init__(self, ttl_seconds: float = 900.0) -> None:
        self._ttl = ttl_seconds
        self._items: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, mapping: dict[str, str]) -> str:
        session_id = uuid.uuid4().hex
        now = time.monotonic()
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v.expires_at > now}
            self._items[session_id] = _Entry(user_id, dict(mapping), now + self._ttl)
        return session_id

    def get(self, session_id: str, user_id: str) -> dict[str, str] | None:
        """The map, only for the user it was created for and only before it expires."""
        with self._lock:
            entry = self._items.get(session_id)
            if entry is None or entry.expires_at <= time.monotonic() or entry.user_id != user_id:
                return None
            return dict(entry.mapping)


sessions = SessionStore()
