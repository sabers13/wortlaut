"""Deterministic membership filter for the Online dictionary.

ADR-0009 requires a Bloom-style membership accelerator over the
authoritative lemma set that has:

* zero false negatives for runtime checks against ``Q`` and
  ``Q.lower()``;
* a statistical false-positive rate (no deterministic guarantee);
* deterministic construction so the same authoritative input yields
  the same filter bytes.

This module builds the filter for every authoritative ``lemma.lemma``
value ``X`` using the closure rule from
:func:`app.online_manifest.lookup_buckets_from_query`: both
``bucket256_v1(X)`` and ``bucket256_v1(sqlite_ascii_lower(X))`` are
inserted. Runtime checks probe both ``Q`` and ``Q.lower()``.

The implementation uses a single-bit ``bytes`` buffer addressed by
``bucket256_v1(text)`` and a second independent bit per text derived
from the second preimage of the same SHA-256 digest. This is a tiny,
deterministic Bloom-of-two and is sufficient to guarantee closure with
the lookup routing for the corpus sizes the Slice 11 tests cover.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256


def _bit_positions(text: str) -> tuple[int, int]:
    """Return two distinct deterministic bit positions for ``text``.

    Both positions live in ``[0, 2 * 256)`` so each bit's index lives in
    exactly one of two independent 256-bit lanes. The first position is
    the first byte of ``SHA256(UTF-8 bytes of text)`` (i.e.
    ``bucket256_v1(text)``); the second position is derived from the
    second byte of the same SHA-256 digest, guaranteeing a second
    preimage-independent position from the same input.
    """
    digest = sha256(text.encode("utf-8")).digest()
    pos1 = digest[0]
    pos2 = 256 + digest[1]
    if pos1 == pos2 - 256:
        pos2 = 256 + ((pos1 + 1) % 256)
    return pos1, pos2


def _sqlite_ascii_lower(value: str) -> str:
    """Reproduce SQLite built-in ``lower()`` for ASCII-oriented text.

    The Online corpus indexes each lemma ``X`` under both
    ``bucket256_v1(X)`` and ``bucket256_v1(sqlite_ascii_lower(X))``. SQLite
    ``lower()`` lowers ASCII A-Z to a-z and passes all other code points
    through unchanged; non-ASCII German letters are therefore NOT lowered
    by SQLite.
    """
    return "".join(
        ch.lower() if "A" <= ch <= "Z" else ch
        for ch in value
    )


@dataclass(frozen=True, slots=True)
class BloomFilter:
    """Immutable membership filter exposing deterministic serialization."""

    bits: bytearray
    size_bits: int

    def __post_init__(self) -> None:
        if self.size_bits <= 0 or self.size_bits % 8 != 0:
            raise ValueError("size_bits must be a positive multiple of 8")
        if len(self.bits) * 8 < self.size_bits:
            raise ValueError("bits buffer is smaller than size_bits")

    @classmethod
    def empty(cls, size_bits: int = 512) -> "BloomFilter":
        """Construct an empty filter of the given size."""
        if size_bits <= 0 or size_bits % 8 != 0:
            raise ValueError("size_bits must be a positive multiple of 8")
        return cls(bits=bytearray(size_bits // 8), size_bits=size_bits)

    @classmethod
    def from_authoritative_lemmas(
        cls,
        lemmas: Iterable[str],
        *,
        size_bits: int = 512,
    ) -> "BloomFilter":
        """Construct a filter by inserting each lemma under both forms."""
        if size_bits <= 0 or size_bits % 8 != 0:
            raise ValueError("size_bits must be a positive multiple of 8")
        bits = bytearray(size_bits // 8)
        for lemma in lemmas:
            for variant in (lemma, _sqlite_ascii_lower(lemma)):
                for pos in _bit_positions(variant):
                    bits[pos // 8] |= 1 << (pos % 8)
        return cls(bits=bits, size_bits=size_bits)

    def contains(self, text: str) -> bool:
        """Return ``True`` when the filter reports membership for ``text``.

        A ``False`` result means "definitely not a member". A ``True``
        result is a probabilistic false-positive candidate; it is never a
        false negative for any text inserted via
        :meth:`from_authoritative_lemmas`.
        """
        for pos in _bit_positions(text):
            byte = self.bits[pos // 8]
            if not (byte & (1 << (pos % 8))):
                return False
        return True

    def contains_query(self, query: str) -> bool:
        """Return ``True`` if the filter accepts either ``Q`` or ``Q.lower()``."""
        return self.contains(query) or self.contains(query.lower())

    def to_bytes(self) -> bytes:
        """Return an immutable copy of the filter bytes."""
        return bytes(self.bits)

    @classmethod
    def from_bytes(cls, payload: bytes, *, size_bits: int = 512) -> "BloomFilter":
        """Construct a filter from previously-serialized bytes."""
        if size_bits <= 0 or size_bits % 8 != 0:
            raise ValueError("size_bits must be a positive multiple of 8")
        if len(payload) * 8 < size_bits:
            raise ValueError("payload smaller than size_bits")
        return cls(bits=bytearray(payload[: size_bits // 8]), size_bits=size_bits)


__all__ = ["BloomFilter", "_sqlite_ascii_lower"]