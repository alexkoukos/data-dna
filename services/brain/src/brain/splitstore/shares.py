"""Additive secret sharing. Pure functions, no I/O.

Numbers: values live in Z_P with P = 2^127 - 1 (a Mersenne prime). share_a is uniform random,
share_b = (value - share_a) mod P, so either share alone is uniform and says nothing. Decoding is
centered, so values in [-(P // 2), P // 2] round-trip (negatives included). Money is integer cents.

Bytes and text: XOR with a random pad of equal length. Text is UTF-8, so Greek works.
"""

import secrets

P = 2**127 - 1
MAX_ABS = P // 2


def split_int(value: int) -> tuple[int, int]:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("numbers must be int (store money as integer cents)")
    if abs(value) > MAX_ABS:
        raise ValueError("number out of range (|value| must be at most 2^126 - 1)")
    share_a = secrets.randbelow(P)  # CSPRNG
    return share_a, (value - share_a) % P


def center(x: int) -> int:
    """Map a residue in [0, P) to the centered range [-(P // 2), P // 2]."""
    x %= P
    return x - P if x > MAX_ABS else x


def join_int(share_a: int, share_b: int) -> int:
    return center(share_a + share_b)


def split_bytes(data: bytes) -> tuple[bytes, bytes]:
    pad = secrets.token_bytes(len(data))
    return pad, bytes(x ^ y for x, y in zip(data, pad, strict=True))


def join_bytes(share_a: bytes, share_b: bytes) -> bytes:
    if len(share_a) != len(share_b):
        raise ValueError("shares have different lengths")
    return bytes(x ^ y for x, y in zip(share_a, share_b, strict=True))


def int_to_bytes(share: int) -> bytes:
    return share.to_bytes(16, "big")
