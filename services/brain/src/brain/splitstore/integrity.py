"""HMAC-SHA256 tags over shares and values. The key lives in an app-only volume, never a vault.

Never a plain hash of a value: low-entropy values (salaries) would be brute-forceable from it.
Messages are "<role>|record_id|field|<kind byte><payload>". record_id and field may not contain
"|", so two different (record_id, field) pairs can never produce the same message.
"""

import hashlib
import hmac
import logging
import os
import secrets
from pathlib import Path

DEFAULT_KEY_FILE = "/var/dna/keys/hmac_key"
DEFAULT_FALLBACK_FILE = DEFAULT_KEY_FILE
log = logging.getLogger(__name__)


class IntegrityError(Exception):
    """A tag did not match: a share or value was changed, moved or lost."""


def load_key(path: str | None = None, fallback: str | None = None) -> bytes:
    """Read the HMAC key, creating it on first start.

    By default the key lives in `/var/dna/keys`, a volume only the app mounts (never a vault), and
    is generated there once with mode 600, so a plain `docker compose up` needs no setup. To use
    your own key, point `HMAC_KEY_FILE` at a mounted file; if that file is missing or empty a key
    is generated into `fallback` instead and a warning is logged.
    """
    path = path or os.environ.get("HMAC_KEY_FILE", DEFAULT_KEY_FILE)
    fallback = fallback or os.environ.get("HMAC_FALLBACK_FILE", DEFAULT_FALLBACK_FILE)
    p = Path(path)
    try:
        usable = p.is_file() and bool(p.read_text().strip())
        if not usable:
            f = Path(fallback)
            if not f.is_file():
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(secrets.token_hex(32))
                f.chmod(0o600)
            if p == f:
                log.info("generated the HMAC key for the split store on first start")
            else:
                log.warning("no HMAC key found at %s; using a generated key in %s", p, f)
            p = f
        key = p.read_text().strip().encode()
    except OSError as e:
        raise ValueError(
            f"The HMAC key file cannot be read ({e.strerror}). Check its permissions, then restart."
        ) from e
    if len(key) < 32:
        raise ValueError(
            "The HMAC key is too short. Use at least 32 characters, or delete the file."
        )
    return key


def check_names(record_id: str, field: str) -> None:
    if not record_id or not field or "|" in record_id or "|" in field:
        raise ValueError('record_id and field must be non-empty and must not contain "|"')


def tag(key: bytes, role: str, record_id: str, field: str, kind: str, payload: bytes) -> bytes:
    """role is "A" (share_a), "B" (share_b) or "V" (the value)."""
    msg = b"|".join([role.encode(), record_id.encode(), field.encode(), kind.encode() + payload])
    return hmac.new(key, msg, hashlib.sha256).digest()


def same(a: bytes | memoryview | None, b: bytes) -> bool:
    return a is not None and hmac.compare_digest(bytes(a), b)
