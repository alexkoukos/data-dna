"""HMAC-SHA256 tags over shares and values. The key comes from a docker secret, never a vault.

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

DEFAULT_KEY_FILE = "/run/secrets/hmac_key"
DEFAULT_FALLBACK_FILE = "/var/dna/keys/hmac_key"
log = logging.getLogger(__name__)


class IntegrityError(Exception):
    """A tag did not match: a share or value was changed, moved or lost."""


def load_key(path: str | None = None, fallback: str | None = None) -> bytes:
    """Read the HMAC key from the docker secret file.

    A clean clone has no secrets/hmac_key (it is gitignored) and compose then mounts an empty
    directory in its place. So that `docker compose up` still works, a key is generated once and
    kept in `fallback`, a volume only the app mounts (never a vault), with a warning. Provide a
    real key with scripts/gen_hmac_key.sh.
    """
    path = path or os.environ.get("HMAC_KEY_FILE", DEFAULT_KEY_FILE)
    fallback = fallback or os.environ.get("HMAC_FALLBACK_FILE", DEFAULT_FALLBACK_FILE)
    p = Path(path)
    if not p.is_file() or not p.read_text().strip():
        f = Path(fallback)
        if not f.is_file():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(secrets.token_hex(32))
            f.chmod(0o600)
        log.warning("no HMAC key secret found; using a generated key (scripts/gen_hmac_key.sh)")
        p = f
    key = p.read_text().strip().encode()
    if len(key) < 32:
        raise ValueError("HMAC key is too short (run scripts/gen_hmac_key.sh)")
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
