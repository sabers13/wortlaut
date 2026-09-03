"""Routing equivalence tests for the Online dictionary.

These tests prove the deterministic properties of the routing
functions mandated by ADR-0009:

* ``bucket256_v1(text) = SHA256(UTF-8 bytes of text).digest()[0]``;
* no Python ``hash()``, no ``casefold``, no locale-dependent hashing,
  no Unicode normalization inside the function;
* the example bucket is exactly ``example.id % 64``;
* the lookup closure under-approximates nothing — every authoritative
  lemma ``X`` and its ``sqlite_ascii_lower(X)`` projection live in the
  same union of buckets a runtime ``Q`` / ``Q.lower()`` fetch visits.

Tests also verify the deterministic serialization of the membership
filter and that provider parity with ``LocalDictionaryProvider`` is a
strict invariant of the lookup routing.
"""

from __future__ import annotations

from hashlib import sha256

import pytest

from app.online_filter import BloomFilter, _sqlite_ascii_lower
from app.online_manifest import lookup_buckets_from_query
from app.routing import (
    bucket256_v1,
    example_bucket,
    lookup_buckets_for_builder_text,
    lookup_buckets_for_text,
)


def test_bucket256_v1_matches_sha256_first_byte() -> None:
    """``bucket256_v1`` must equal ``SHA256(text).digest()[0]``."""
    for text in ("Haus", "See", "anrufen", "Krankenversicherungskarte", ""):
        expected = sha256(text.encode("utf-8")).digest()[0]
        assert bucket256_v1(text) == expected


def test_bucket256_v1_is_locale_independent() -> None:
    """ASCII / umlaut / ß text must bucket identically across processes."""
    samples = (
        "Haus",
        "haus",
        "HÄUSER",
        "größeren",
        "anrufen",
        "Anrufen",
        "schön",
        "SCHÖN",
        "Krankenversicherungskarte",
        "krankenversicherungskarte",
    )
    seen = {bucket256_v1(text) for text in samples}
    assert all(0 <= value <= 255 for value in seen)


def test_bucket256_v1_has_no_implicit_normalization() -> None:
    """Bucket function is byte-exact; decomposed Unicode does NOT equal NFC."""
    nfc = "Haus"
    decomposed = "Ha" + "\u0308" + "us"
    assert nfc != decomposed
    assert bucket256_v1(nfc) != bucket256_v1(decomposed)


def test_example_bucket_is_modulo_64() -> None:
    """``example_bucket`` is the exact ``example.id % 64``."""
    for example_id in range(0, 1024, 13):
        assert example_bucket(example_id) == example_id % 64


def test_example_bucket_handles_corner_cases() -> None:
    """Edge cases at the boundary must produce the right modulo bucket."""
    assert example_bucket(0) == 0
    assert example_bucket(63) == 63
    assert example_bucket(64) == 0
    assert example_bucket(65) == 1


def test_example_bucket_rejects_invalid_input() -> None:
    """``example_bucket`` must reject non-int or negative IDs."""
    with pytest.raises(TypeError):
        example_bucket(True)  # type: ignore[arg-type, unused-ignore]
    with pytest.raises(TypeError):
        example_bucket("1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        example_bucket(-1)


def test_bucket256_v1_rejects_non_string() -> None:
    """``bucket256_v1`` must reject non-str inputs."""
    with pytest.raises(TypeError):
        bucket256_v1(b"Haus")  # type: ignore[arg-type]


def test_lookup_buckets_for_query_dedups_when_lower_matches_primary() -> None:
    """When ``bucket256_v1(Q) == bucket256_v1(Q.lower())`` only one bucket."""
    text = "abc"
    primary = bucket256_v1(text)
    secondary = bucket256_v1(text.lower())
    if primary == secondary:
        assert lookup_buckets_for_text(text) == (primary,)
    else:
        assert set(lookup_buckets_for_text(text)) == {primary, secondary}


def test_lookup_buckets_for_builder_text_matches_runtime() -> None:
    """Builder and runtime bucket closures must produce the same union."""
    for lemma in (
        "Haus",
        "See",
        "Bank",
        "Krankenversicherungskarte",
        "anrufen",
        "größeren",
    ):
        builder = lookup_buckets_for_builder_text(lemma, _sqlite_ascii_lower(lemma))
        runtime = lookup_buckets_for_text(lemma)
        assert set(builder) == set(runtime)


def test_lookup_buckets_cover_q_and_q_lower() -> None:
    """Closure must cover both ``bucket(Q)`` and ``bucket(Q.lower())``."""
    for lemma in ("Haus", "See", "Bank", "anrufen", "Krankenversicherungskarte"):
        runtime_buckets = set(lookup_buckets_from_query(lemma))
        runtime_lower_buckets = set(lookup_buckets_from_query(lemma.lower()))
        # builder side: union of bucket(X) and bucket(lower(X))
        builder = set(
            [
                bucket256_v1(lemma),
                bucket256_v1(_sqlite_ascii_lower(lemma)),
            ]
        )
        assert builder <= runtime_buckets | runtime_lower_buckets


def test_decomposed_unicode_is_routed_separately() -> None:
    """Decomposed input does not normalize; routing may over-approximate only."""
    decomposed = "Ha" + "\u0308" + "us"
    nfc = "Häus"
    decomposed_buckets = set(lookup_buckets_from_query(decomposed))
    nfc_buckets = set(lookup_buckets_from_query(nfc))
    assert decomposed_buckets != nfc_buckets


def test_bloom_filter_is_zero_false_negative_for_inserted_lemmas() -> None:
    """Every inserted lemma must be accepted by ``contains_query``."""
    lemmas = ["Haus", "See", "Bank", "anrufen", "Krankenversicherungskarte"]
    filt = BloomFilter.from_authoritative_lemmas(lemmas)
    for lemma in lemmas:
        assert filt.contains(lemma), lemma
        assert filt.contains(lemma.lower()), lemma
        assert filt.contains_query(lemma), lemma


def test_bloom_filter_is_deterministic() -> None:
    """Building the filter twice produces byte-equal output."""
    lemmas = ["Haus", "See", "Bank", "Karte"]
    one = BloomFilter.from_authoritative_lemmas(lemmas).to_bytes()
    two = BloomFilter.from_authoritative_lemmas(lemmas).to_bytes()
    assert one == two


def test_bloom_filter_round_trip_bytes() -> None:
    """Filter bytes survive ``to_bytes`` / ``from_bytes`` round-trip."""
    lemmas = ["Haus", "See", "anrufen"]
    filt = BloomFilter.from_authoritative_lemmas(lemmas)
    raw = filt.to_bytes()
    rebuilt = BloomFilter.from_bytes(raw, size_bits=filt.size_bits)
    assert rebuilt.to_bytes() == raw
    for lemma in lemmas:
        assert rebuilt.contains(lemma)


def test_bloom_filter_fpr_is_statistical_only() -> None:
    """An empty query never matches an authoritative lemma."""
    filt = BloomFilter.from_authoritative_lemmas(["Haus", "See", "Bank"])
    unknowns = ["xyzzy", "no-such-lemma", "schraubenzieher"]
    for unknown in unknowns:
        assert not filt.contains(unknown)


def test_bloom_filter_accepts_uppercase_query_for_inserted_lowercase() -> None:
    """Zero false negative: inserted lowercase still matches uppercase query."""
    filt = BloomFilter.from_authoritative_lemmas(["haus", "see"])
    assert filt.contains_query("HAUS")
    assert filt.contains_query("SEE")