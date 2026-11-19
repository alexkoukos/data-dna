"""Vercel entrypoint for the brain.

Vercel sends the original public path to a service, so a request to /api/v1/metrics reaches the
brain as /api/v1/metrics. The brain's own routes (and nginx in Docker, which strips /api/) have no
/api prefix, so this wrapper removes it. Everything else, including the lifespan events, is passed
straight through to the real app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brain.main import app as brain_app  # noqa: E402

PREFIX = "/api"


async def app(scope, receive, send):  # type: ignore[no-untyped-def]
    if scope["type"] in ("http", "websocket"):
        path = scope.get("path", "")
        if path == PREFIX or path.startswith(PREFIX + "/"):
            scope = dict(scope)
            scope["path"] = path[len(PREFIX) :] or "/"
            raw = scope.get("raw_path")
            if raw:
                scope["raw_path"] = raw[len(PREFIX) :] or b"/"
    await brain_app(scope, receive, send)
