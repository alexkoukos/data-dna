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


MIN_KEY_CHARS = 32


def _read_key(p: Path) -> str:
    return p.read_text().strip() if p.is_file() else ""


def _create_key(f: Path) -> None:
    """Write a new key that only this process can read, never over an existing file."""
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.is_file() and len(_read_key(f)) < MIN_KEY_CHARS:
        f.unlink()  # an empty or cut-short file from a crashed start is not a key
    try:
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w") as out:
        out.write(secrets.token_hex(32))


def load_key(path: str | None = None, fallback: str | None = None) -> bytes:
    """Read the HMAC key, creating it on first start.

    By default the key lives in `/var/dna/keys`, a volume only the app mounts (never a vault), and
    is generated there once with mode 600, so a plain `docker compose up` needs no setup. To use
    your own key, set `HMAC_KEY_FILE` to a file inside a volume you mount into the app; if that
    file is missing or too short a key is generated into `fallback` instead and a warning is
    logged.
    """
    path = path or os.environ.get("HMAC_KEY_FILE", DEFAULT_KEY_FILE)
    fallback = fallback or os.environ.get("HMAC_FALLBACK_FILE", DEFAULT_FALLBACK_FILE)
    p = Path(path)
    try:
        if len(_read_key(p)) < MIN_KEY_CHARS:
            f = Path(fallback)
            if len(_read_key(f)) < MIN_KEY_CHARS:
                _create_key(f)
            if p == f:
                log.info("generated the HMAC key for the split store on first start")
            else:
                log.warning("no HMAC key found at %s; using a generated key in %s", p, f)
            p = f
        key = _read_key(p).encode()
    except OSError as e:
        raise ValueError(
            f"The HMAC key file cannot be read ({e.strerror}). Check its permissions, then restart."
        ) from e
    if len(key) < MIN_KEY_CHARS:
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
