"""X27: turn a personal gateway key into a user and team, so the client never says who it is.

The gateway (LiteLLM) owns the keys. We ask it with the admin key; the answer is cached for a
minute and only successes are cached, so a revoked key stops working within that minute.
"""

import hashlib
import time
from dataclasses import dataclass

import httpx

from brain.config import settings

CACHE_SECONDS = 60.0
_cache: dict[str, tuple[float, "Identity"]] = {}


@dataclass(frozen=True)
class Identity:
    user_id: str
    team: str


class GatewayUnavailable(RuntimeError):
    """The gateway could not be asked, which is different from the key being wrong."""


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def bearer_token(header: str | None) -> str | None:
    """The key from an `Authorization: Bearer <key>` header, or None."""
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    token = token.strip()
    return token if scheme.lower() == "bearer" and token else None


def resolve_key(key: str, client: httpx.Client | None = None) -> Identity | None:
    """The user and team a key belongs to, None if the key is unknown or has no user."""
    now = time.monotonic()
    digest = _digest(key)
    hit = _cache.get(digest)
    if hit is not None and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    own = client is None
    http = client or httpx.Client(base_url=settings.gateway_url, timeout=5.0)
    try:
        resp = http.get(
            "/key/info",
            params={"key": key},
            headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
        )
    except httpx.HTTPError as err:
        raise GatewayUnavailable("The gate could not check your key.") from err
    finally:
        if own:
            http.close()
    if resp.status_code in (400, 401, 403, 404):
        return None
    if resp.status_code != 200:
        raise GatewayUnavailable("The gate could not check your key.")
    try:
        info = resp.json().get("info") or {}
    except ValueError:
        return None
    user = info.get("user_id")
    if not isinstance(user, str) or not user:
        return None
    found = Identity(user_id=user, team=str(info.get("team_id") or "unknown"))
    _cache[digest] = (now, found)
    return found


def forget_all() -> None:
    _cache.clear()
