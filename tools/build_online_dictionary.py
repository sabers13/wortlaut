"""Build the deterministic Online dictionary corpus from a verified Local asset.

This tool is the Slice 11 builder. It consumes a verified Local
``dictionary_vN.sqlite`` (the same validated PART-A asset the Local
provider opens), partitions every authoritative lemma/sense/example
across the fixed shard families, emits deterministic per-shard SQLite
files, an immutable membership filter, and a strict Online manifest.

Slice 11 uses this tool only against tiny test inputs. Production
execution is gated to Slice 13.

Determinism is total: identical verified input bytes and identical
configuration emit identical shards, identical filter bytes, and an
identical manifest digest. No timestamps, no random UUIDs, and no
non-deterministic SQLite iteration order affect the emitted bytes.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.online_filter import BloomFilter
from app.online_manifest import (
    DEFAULT_DATASET_TOKEN,
    ENTRY_FAMILY_SIZE,
    EXAMPLE_FAMILY_SIZE,
    LOOKUP_FAMILY_SIZE,
    MANIFEST_SCHEMA_VERSION,
    SHARD_FAMILY_ENTRY,
    SHARD_FAMILY_EXAMPLE,
    SHARD_FAMILY_FILTER,
    SHARD_FAMILY_LOOKUP,
    ManifestAsset,
    OnlineManifest,
    TrustedDistribution,
    manifest_hash,
)
from app.routing import bucket256_v1, example_bucket


@dataclass(frozen=True)
class BuildInputs:
    """Inputs needed to build one Online corpus."""

    source_path: Path
    output_dir: Path
    dataset_token: str = DEFAULT_DATASET_TOKEN
    release_tag: str = "dictionary-online-v2"
    base_origin: str = "https://github.com"


# Stable local filename per shard family/bucket; the manifest pairs
# ``name`` with ``path`` (which is the relative URL path used by the
# Online distribution).
def _asset_name(family: str, bucket: int) -> str:
    return f"{family}-{bucket:03d}.sqlite"


def _asset_path(family: str, bucket: int) -> str:
    """Return the relative URL path used by the Online distribution."""
    return f"shards/{family}/{bucket:03d}.sqlite"


def _filter_name() -> str:
    return "membership-filter.bin"


def _filter_path() -> str:
    return "shards/membership-filter.bin"


def _sqlite_ascii_lower(value: str) -> str:
    """Reproduce SQLite built-in ``lower()`` for ASCII-oriented text."""
    return "".join(
        ch.lower() if "A" <= ch <= "Z" else ch for ch in value
    )


def _validate_local_input(source: Path) -> None:
    """Validate the Local input asset before consuming it."""
    if not source.exists():
        raise RuntimeError(f"source dictionary not found: {source}")
    if source.stat().st_size == 0:
        raise RuntimeError(f"source dictionary is empty: {source}")
    digest = sha256(source.read_bytes()).hexdigest()
    if digest != DEFAULT_DATASET_TOKEN:
        raise RuntimeError(
            f"source dictionary SHA-256 {digest} does not match expected "
            f"v2 dataset token {DEFAULT_DATASET_TOKEN}"
        )
    connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        for required_table in (
            "lemma",
            "sense",
            "sense_meaning",
            "example",
            "example_lemma",
            "surface_form",
        ):
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (required_table,),
            ).fetchone()
            if row is None:
                raise RuntimeError(
                    f"source dictionary is missing required table: {required_table}"
                )
    finally:
        connection.close()


def _open_destination(directory: Path) -> sqlite3.Connection:
    """Open a private temporary SQLite file for shard emission."""
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(suffix=".sqlite", dir=str(directory))
    path = Path(name)
    path.unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _atomic_install(source_path: Path, canonical_path: Path) -> None:
    """Atomically install a freshly-written shard into its canonical location."""
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, final_name = tempfile.mkstemp(
        suffix=".sqlite", dir=str(canonical_path.parent)
    )
    final_path = Path(final_name)
    try:
        with os.fdopen(descriptor, "wb") as out:
            out.write(source_path.read_bytes())
            out.flush()
            os.fsync(out.fileno())
        os.replace(final_path, canonical_path)
    finally:
        if final_path.exists():
            final_path.unlink(missing_ok=True)


def _install_blob(source_path: Path, canonical_path: Path) -> None:
    """Atomically install a non-SQLite shard (membership filter)."""
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, final_name = tempfile.mkstemp(
        suffix=".tmp", dir=str(canonical_path.parent)
    )
    final_path = Path(final_name)
    try:
        with os.fdopen(descriptor, "wb") as out:
            out.write(source_path.read_bytes())
            out.flush()
            os.fsync(out.fileno())
        os.replace(final_path, canonical_path)
    finally:
        if final_path.exists():
            final_path.unlink(missing_ok=True)


def _read_authoritative_lemmas(
    connection: sqlite3.Connection,
) -> list[tuple[Any, ...]]:
    """Return all authoritative lemmas in stable id order."""
    rows = connection.execute(
        "SELECT id, semantic_ref, lemma, pos, gender, freq_rank, plural, plural_none, "
        "genitive_sg, aux, separable, particle, reflexive, praesens_3sg, "
        "praeteritum_3sg, partizip_ii, governs, comparative, superlative, ipa, "
        "source, license "
        "FROM lemma ORDER BY id ASC"
    ).fetchall()
    return [tuple(r) for r in rows]


def _read_authoritative_senses(
    connection: sqlite3.Connection,
) -> list[tuple[int, int, str, str, str, int, str | None, str | None, str | None]]:
    """Return all senses in stable id order."""
    rows = connection.execute(
        "SELECT id, lemma_id, semantic_ref, source_namespace, source_ref, ord, "
        "register, source, license FROM sense ORDER BY id ASC"
    ).fetchall()
    return [
        (
            int(r[0]),
            int(r[1]),
            str(r[2]),
            str(r[3]),
            str(r[4]),
            int(r[5]),
            str(r[6]) if r[6] is not None else None,
            str(r[7]) if r[7] is not None else None,
            str(r[8]) if r[8] is not None else None,
        )
        for r in rows
    ]


def _read_authoritative_meanings(
    connection: sqlite3.Connection,
) -> list[tuple[int, int, str, str, int, str, str, str]]:
    """Return all sense_meaning rows in stable id order."""
    rows = connection.execute(
        "SELECT id, sense_id, language, kind, ord, text, source, license "
        "FROM sense_meaning ORDER BY id ASC"
    ).fetchall()
    return [
        (
            int(r[0]),
            int(r[1]),
            str(r[2]),
            str(r[3]),
            int(r[4]),
            str(r[5]),
            str(r[6]),
            str(r[7]),
        )
        for r in rows
    ]


def _read_authoritative_examples(
    connection: sqlite3.Connection,
) -> list[tuple[int, str, str | None, str | None, str | None, str | None, int | None, int]]:
    """Return all example rows in stable id order."""
    rows = connection.execute(
        "SELECT id, de, en, source, source_ref, license, token_count, has_proper "
        "FROM example ORDER BY id ASC"
    ).fetchall()
    return [
        (
            int(r[0]),
            str(r[1]),
            str(r[2]) if r[2] is not None else None,
            str(r[3]) if r[3] is not None else None,
            str(r[4]) if r[4] is not None else None,
            str(r[5]) if r[5] is not None else None,
            int(r[6]) if r[6] is not None else None,
            int(r[7]) if r[7] is not None else 0,
        )
        for r in rows
    ]


def _read_authoritative_surface_forms(
    connection: sqlite3.Connection,
) -> list[tuple[str, int]]:
    """Return all surface_form rows in stable form+lemma order."""
    rows = connection.execute(
        "SELECT form, lemma_id FROM surface_form ORDER BY form ASC, lemma_id ASC"
    ).fetchall()
    return [(str(r[0]), int(r[1])) for r in rows]


def _read_authoritative_example_lemma(
    connection: sqlite3.Connection,
) -> list[tuple[int, int]]:
    """Return all ``example_lemma`` rows in stable lemma+example order."""
    rows = connection.execute(
        "SELECT lemma_id, example_id FROM example_lemma ORDER BY lemma_id ASC, example_id ASC"
    ).fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


def _init_lookup_shard(connection: sqlite3.Connection) -> None:
    """Create the lookup-shard schema.

    The lookup shard carries:

    * the lemma rows the runtime predicate reads;
    * the surface_form rows used for surface-form lookup;
    * a ``sense_route`` table that resolves ``sense_ref -> lemma_ref`` in a
      single bucket-closed fetch. Every authoritative ``sense_ref`` is
      indexed by ``bucket256_v1(sense_ref)`` (the same lookup-family routing
      function used for lemma lookups), so the runtime never scans across
      families to recover the sense-to-lemma mapping.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lemma (
          id           INTEGER PRIMARY KEY,
          semantic_ref TEXT NOT NULL,
          lemma        TEXT NOT NULL,
          pos          TEXT NOT NULL,
          gender       TEXT,
          freq_rank    INTEGER
        );
        CREATE INDEX IF NOT EXISTS ix_lookup_lemma ON lemma(lemma, pos, gender);
        CREATE INDEX IF NOT EXISTS ix_lookup_lower ON lemma(lower(lemma));
        CREATE TABLE IF NOT EXISTS surface_form (
          form      TEXT NOT NULL,
          lemma_id  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_lookup_surface ON surface_form(form);
        CREATE TABLE IF NOT EXISTS sense_route (
          sense_ref TEXT PRIMARY KEY,
          lemma_ref TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_lookup_sense_route_lemma ON sense_route(lemma_ref);
        """
    )


def _init_entry_shard(connection: sqlite3.Connection) -> None:
    """Create the entry-shard schema.

    The entry shard carries the lemma row, its senses, the localized
    meanings attached to those senses, the surface forms and the
    ``example_lemma`` join. It deliberately does **not** carry the
    authoritative ``example`` payload: example rows live in the 64-shard
    example family keyed by ``example.id % 64``. Carrying the full payload
    here would silently allow the runtime to bypass the example family.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lemma (
          id             INTEGER PRIMARY KEY,
          semantic_ref   TEXT NOT NULL,
          lemma          TEXT NOT NULL,
          pos            TEXT NOT NULL,
          gender         TEXT,
          freq_rank      INTEGER,
          plural         TEXT,
          plural_none    INTEGER NOT NULL DEFAULT 0,
          genitive_sg    TEXT,
          aux            TEXT,
          separable      INTEGER NOT NULL DEFAULT 0,
          particle       TEXT,
          reflexive      INTEGER NOT NULL DEFAULT 0,
          praesens_3sg   TEXT,
          praeteritum_3sg TEXT,
          partizip_ii    TEXT,
          governs        TEXT,
          comparative    TEXT,
          superlative    TEXT,
          ipa            TEXT,
          source         TEXT,
          license        TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_entry_lemma_semantic ON lemma(semantic_ref);

        CREATE TABLE IF NOT EXISTS sense (
          id                INTEGER PRIMARY KEY,
          lemma_id          INTEGER NOT NULL,
          semantic_ref      TEXT NOT NULL,
          source_namespace  TEXT NOT NULL,
          source_ref        TEXT NOT NULL,
          ord               INTEGER NOT NULL DEFAULT 0,
          register          TEXT,
          source            TEXT,
          license           TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_entry_sense_semantic ON sense(semantic_ref);

        CREATE TABLE IF NOT EXISTS sense_meaning (
          id        INTEGER PRIMARY KEY,
          sense_id  INTEGER NOT NULL,
          language  TEXT,
          kind      TEXT,
          ord       INTEGER NOT NULL DEFAULT 0,
          text      TEXT,
          source    TEXT,
          license   TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_entry_meaning ON sense_meaning(sense_id, language);

        CREATE TABLE IF NOT EXISTS surface_form (
          form      TEXT NOT NULL,
          lemma_id  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_entry_surface ON surface_form(form);

        CREATE TABLE IF NOT EXISTS example_lemma (
          lemma_id   INTEGER NOT NULL,
          example_id INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_entry_example_lemma ON example_lemma(lemma_id);
        """
    )


def _init_example_shard(connection: sqlite3.Connection) -> None:
    """Create the example-shard schema."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS example (
          id           INTEGER PRIMARY KEY,
          de           TEXT NOT NULL,
          en           TEXT,
          source       TEXT,
          source_ref   TEXT,
          license      TEXT,
          token_count  INTEGER,
          has_proper   INTEGER NOT NULL DEFAULT 0
        );
        """
    )


def _compute_bucket_targets_for_lookup(
    *,
    lemma_text: str,
    lemma_id: int,
    surface_form_lookup: list[tuple[int, str]],
) -> set[int]:
    """Return the deduplicated lookup buckets for one authoritative lemma.

    Mirrors :func:`app.online_manifest.lookup_buckets_from_query` for
    both ``lemma`` and ``lower(lemma)``, plus the same closure for every
    recorded ``surface_form`` row tied to ``lemma_id``.
    """
    targets: set[int] = set()
    primary = bucket256_v1(lemma_text)
    targets.add(primary)
    secondary = bucket256_v1(_sqlite_ascii_lower(lemma_text))
    if secondary != primary:
        targets.add(secondary)
    for _, form in surface_form_lookup:
        if form == form.strip() and form:
            primary_form = bucket256_v1(form)
            targets.add(primary_form)
            secondary_form = bucket256_v1(_sqlite_ascii_lower(form))
            if secondary_form != primary_form:
                targets.add(secondary_form)
    return targets


def _validate_sense_route_partitions(
    *,
    senses: Sequence[tuple[int, int, str, str, str, int, str | None, str | None, str | None]],
    sense_route_partitions: Mapping[int, Sequence[tuple[str, str]]],
    lemma_refs_by_id: Mapping[int, str],
) -> None:
    """Validate that every authoritative ``sense_ref`` is bucket-closed.

    Each authoritative sense must appear in exactly one sense_route
    bucket, the bucket must equal ``bucket256_v1(sense_ref)`` (checked
    explicitly against the actual partition bucket, not assumed from the
    producer), and the routed ``lemma_ref`` must equal the lemma's
    authoritative ``semantic_ref``. Missing, extra, misrouted, or
    mis-bucketed sense_refs are fatal builder errors so the runtime can
    rely on the index.

    Runs in approximately linear time in the number of authoritative
    rows: two precomputed maps (``sense_owner_by_ref`` and the routed
    map) replace the previous nested full-list ``next()`` scans, which
    were O(S*L) and O(S^2) on the real corpus.
    """
    sense_owner_by_ref: dict[str, int] = {}
    for sense_id, lemma_id, sense_ref, _, _, _, _, _, _ in senses:
        if not isinstance(sense_ref, str) or not sense_ref:
            raise RuntimeError(f"sense_id={sense_id} has empty sense_ref")
        if sense_ref in sense_owner_by_ref:
            raise RuntimeError(f"duplicate sense_ref={sense_ref!r}")
        sense_owner_by_ref[sense_ref] = int(lemma_id)
    routed: dict[str, tuple[str, int]] = {}
    for bucket, rows in sense_route_partitions.items():
        for sense_ref, lemma_ref in rows:
            if sense_ref in routed:
                raise RuntimeError(
                    f"duplicate sense_route bucket={bucket} sense_ref={sense_ref!r}"
                )
            actual_bucket = bucket256_v1(str(sense_ref))
            if actual_bucket != int(bucket):
                raise RuntimeError(
                    f"sense_route sense_ref={sense_ref!r} partitioned into "
                    f"bucket {bucket} but bucket256_v1 gives {actual_bucket}"
                )
            routed[sense_ref] = (lemma_ref, int(bucket))
    missing = set(sense_owner_by_ref.keys()) - set(routed.keys())
    if missing:
        sample = sorted(missing)[:5]
        raise RuntimeError(
            f"sense_route missing for sense_refs: {sample} "
            f"(and {len(missing) - len(sample)} more)"
        )
    extra = set(routed.keys()) - set(sense_owner_by_ref.keys())
    if extra:
        sample = sorted(extra)[:5]
        raise RuntimeError(
            f"sense_route has unexpected sense_refs: {sample} "
            f"(and {len(extra) - len(sample)} more)"
        )
    for sense_ref, owner_lemma_id in sense_owner_by_ref.items():
        lemma_ref, expected_bucket = routed[sense_ref]
        if lemma_refs_by_id.get(owner_lemma_id) != lemma_ref:
            raise RuntimeError(
                f"sense_route bucket={expected_bucket} sense_ref={sense_ref!r} "
                f"routes to {lemma_ref!r} but authoritative lemma_ref is "
                f"{lemma_refs_by_id.get(owner_lemma_id)!r}"
            )


def _partition_lookup_shards(
    lemmas: Sequence[tuple[Any, ...]],
    surface_forms: Sequence[tuple[str, int]],
    senses: Sequence[tuple[int, int, str, str, str, int, str | None, str | None, str | None]],
) -> tuple[
    dict[int, list[tuple[Any, ...]]],
    dict[int, list[tuple[str, int]]],
    dict[int, list[tuple[str, str]]],
]:
    """Partition lookup-shard rows into 256 buckets using the closure rule.

    Returns:

    * ``lemma_partitions``: ``bucket -> lemma_rows`` placed for every
      authoritative lemma by ``bucket256_v1(X)`` union
      ``bucket256_v1(sqlite_ascii_lower(X))`` (plus the surface-form
      closure buckets, so the surface_form -> lemma join stays locally
      closed in every bucket).
    * ``surface_partitions``: ``bucket -> (form, lemma_id)`` rows where
      each authoritative surface row appears ONLY in the union of
      ``bucket256_v1(form)`` and
      ``bucket256_v1(sqlite_ascii_lower(form))`` (deduplicated) — never
      duplicated into all 256 buckets.
    * ``sense_route_partitions``: ``bucket -> (sense_ref, lemma_ref)`` rows
      indexed by ``bucket256_v1(sense_ref)``. The sense_route is the
      single bucket-closed routing table that replaces the cross-family
      scan the previous candidate used.

    The full lemma row tuple is preserved; the lookup-shard writer reads
    only the columns it needs.

    Runs in approximately linear time in the number of authoritative
    rows: ``lemma_ref_by_id`` is built once and sense ownership resolves
    by O(1) map lookup instead of nested full-list ``next()`` scans.
    """
    surface_by_lemma: dict[int, list[tuple[int, str]]] = {}
    for form, lemma_id in surface_forms:
        surface_by_lemma.setdefault(lemma_id, []).append((lemma_id, form))
    lemma_partitions: dict[int, list[tuple[Any, ...]]] = {}
    for row in lemmas:
        lemma_id = row[0]
        lemma_text = row[2]
        targets = _compute_bucket_targets_for_lookup(
            lemma_text=lemma_text,
            lemma_id=lemma_id,
            surface_form_lookup=surface_by_lemma.get(lemma_id, []),
        )
        for bucket in targets:
            lemma_partitions.setdefault(bucket, []).append(row)

    # Surface-form partitions: each distinct authoritative (form,
    # lemma_id) row lands only in its own closure buckets.
    surface_partitions: dict[int, list[tuple[str, int]]] = {}
    seen_surface_pairs: set[tuple[str, int]] = set()
    for form, lemma_id in surface_forms:
        pair = (str(form), int(lemma_id))
        if pair in seen_surface_pairs:
            continue
        seen_surface_pairs.add(pair)
        closure_buckets = {
            bucket256_v1(pair[0]),
            bucket256_v1(_sqlite_ascii_lower(pair[0])),
        }
        for bucket in closure_buckets:
            surface_partitions.setdefault(bucket, []).append(pair)

    lemma_ref_by_id: dict[int, str] = {
        int(row[0]): str(row[1]) for row in lemmas
    }
    sense_route_partitions: dict[int, list[tuple[str, str]]] = {}
    seen_routes: set[str] = set()
    for sense_row in senses:
        sense_id, lemma_id, sense_ref, _, _, _, _, _, _ = sense_row
        lemma_ref = lemma_ref_by_id.get(int(lemma_id))
        if lemma_ref is None:
            raise RuntimeError(
                f"sense_id={sense_id} references unknown lemma_id={lemma_id}"
            )
        bucket = bucket256_v1(str(sense_ref))
        if not 0 <= bucket < LOOKUP_FAMILY_SIZE:
            raise RuntimeError(
                f"sense_ref={sense_ref!r} routed to out-of-range bucket {bucket}"
            )
        if sense_ref in seen_routes:
            raise RuntimeError(f"duplicate sense_route for sense_ref={sense_ref!r}")
        seen_routes.add(str(sense_ref))
        sense_route_partitions.setdefault(bucket, []).append((str(sense_ref), lemma_ref))
    return lemma_partitions, surface_partitions, sense_route_partitions


def _partition_entry_shards(
    lemmas: Sequence[tuple[Any, ...]],
    senses: Sequence[tuple[int, int, str, str, str, int, str | None, str | None, str | None]],
    meanings: Sequence[tuple[int, int, str, str, int, str, str, str]],
    surface_forms: Sequence[tuple[str, int]],
    example_lemma: Sequence[tuple[int, int]],
    examples: Sequence[tuple[Any, ...]],
) -> dict[int, dict[str, list[Any]]]:
    """Partition lemma-driven rows by ``bucket256_v1(lemma_semantic_ref)``.

    The entry shard owns the lemma row, its senses, the meanings attached
    to those senses, the surface forms and the ``example_lemma`` join.
    It deliberately does **not** carry the example payload: example rows
    live in the example family keyed by ``example.id % 64``.

    Every ``example_lemma.example_id`` is validated against the
    authoritative example-id set before writing; a dangling reference is
    a fatal builder error. Example routing itself stays
    ``example.id % 64``.
    """
    buckets: dict[int, dict[str, list[Any]]] = {}
    lemma_bucket: dict[int, int] = {}
    for row in lemmas:
        lemma_id, semantic_ref = int(row[0]), str(row[1])
        bucket = bucket256_v1(semantic_ref)
        lemma_bucket[lemma_id] = bucket
        bucket_state = buckets.setdefault(bucket, {
            "lemmas": [],
            "senses": [],
            "meanings": [],
            "surface_forms": [],
            "example_lemma": [],
        })
        bucket_state["lemmas"].append(row)
    sense_by_id: dict[int, tuple[int, int]] = {}
    for row in senses:
        sense_id, lemma_id = int(row[0]), int(row[1])
        sense_by_id[sense_id] = (sense_id, lemma_id)
        sense_bucket_for_lemma = lemma_bucket.get(int(lemma_id))
        if sense_bucket_for_lemma is None:
            raise RuntimeError(f"sense references unknown lemma_id={lemma_id}")
        bucket_for_sense = sense_bucket_for_lemma
        bucket_state = buckets[bucket_for_sense]
        bucket_state["senses"].append(row)
    sense_bucket: dict[int, int] = {}
    for sense_id, pair in sense_by_id.items():
        sense_bucket[sense_id] = lemma_bucket[int(pair[1])]
    for row in meanings:
        sense_id = int(row[1])
        meaning_bucket = sense_bucket.get(int(sense_id))
        if meaning_bucket is None:
            raise RuntimeError(f"meaning references unknown sense_id={sense_id}")
        buckets[meaning_bucket]["meanings"].append(row)
    for form, lemma_id in surface_forms:
        surface_bucket = lemma_bucket.get(int(lemma_id))
        if surface_bucket is None:
            raise RuntimeError(f"surface_form references unknown lemma_id={lemma_id}")
        buckets[surface_bucket]["surface_forms"].append((form, lemma_id))
    example_ids = {int(row[0]) for row in examples}
    for lemma_id, example_id in example_lemma:
        el_bucket = lemma_bucket.get(int(lemma_id))
        if el_bucket is None:
            raise RuntimeError(
                f"example_lemma references unknown lemma_id={lemma_id}"
            )
        if int(example_id) not in example_ids:
            raise RuntimeError(
                f"example_lemma references unknown example_id={example_id}"
            )
        buckets[el_bucket]["example_lemma"].append((lemma_id, example_id))
    return buckets


def _partition_example_shards(
    examples: Sequence[
        tuple[int, str, str | None, str | None, str | None, str | None, int | None, int]
    ],
) -> dict[int, list[
    tuple[int, str, str | None, str | None, str | None, str | None, int | None, int]
]]:
    """Partition authoritative examples into 64 buckets by ``id % 64``."""
    buckets: dict[int, list[tuple[Any, ...]]] = {b: [] for b in range(EXAMPLE_FAMILY_SIZE)}
    for row in examples:
        bucket = example_bucket(int(row[0]))
        buckets[bucket].append(row)
    return buckets


def _write_lookup_shard(
    connection: sqlite3.Connection,
    bucket: int,
    lemma_rows: Sequence[tuple[int, str, str, str | None, int | None, str, str]],
    surface_rows: Sequence[tuple[str, int]],
    sense_route_rows: Sequence[tuple[str, str]] = (),
) -> None:
    """Populate a single lookup shard.

    The lookup shard carries the lemma rows the runtime predicate reads,
    ONLY the surface-form rows whose closure bucket is this bucket, and
    the ``sense_route`` rows whose ``sense_ref`` falls in
    ``bucket256_v1(sense_ref) == bucket``. The sense_route table is
    bucket-closed: every authoritative ``sense_ref`` appears in exactly
    one lookup shard and points to its real parent ``lemma_ref``.
    """
    _init_lookup_shard(connection)
    lemma_rows_sorted = sorted(
        lemma_rows,
        key=lambda r: (
            int(r[5]) if r[5] is not None else 1,
            str(r[3]),
            str(r[4]) if r[4] is not None else "",
            str(r[1]),
            int(r[0]),
        ),
    )
    connection.executemany(
        "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, freq_rank) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (r[0], r[1], r[2], r[3], r[4], r[5])
            for r in lemma_rows_sorted
        ],
    )
    seen: set[tuple[int, str]] = set()
    surface_rows_sorted = sorted(
        ((int(lemma_id), str(form)) for form, lemma_id in surface_rows)
    )
    ordered_surface_rows: list[tuple[str, int]] = []
    for lemma_id, form in surface_rows_sorted:
        key = (lemma_id, form)
        if key in seen:
            continue
        seen.add(key)
        ordered_surface_rows.append((form, lemma_id))
    connection.executemany(
        "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
        ordered_surface_rows,
    )
    if sense_route_rows:
        deduped_routes: dict[str, str] = {}
        for sense_ref, lemma_ref in sense_route_rows:
            if sense_ref in deduped_routes:
                if deduped_routes[sense_ref] != lemma_ref:
                    raise RuntimeError(
                        f"sense_route bucket {bucket} has conflicting "
                        f"lemma_ref for sense_ref={sense_ref!r}"
                    )
                continue
            deduped_routes[sense_ref] = lemma_ref
        connection.executemany(
            "INSERT INTO sense_route (sense_ref, lemma_ref) VALUES (?, ?)",
            [(sense_ref, lemma_ref) for sense_ref, lemma_ref in sorted(deduped_routes.items())],
        )
    connection.commit()
    connection.execute("VACUUM")
    connection.commit()


def _write_entry_shard(
    connection: sqlite3.Connection,
    bucket: int,
    lemma_rows: Sequence[tuple[Any, ...]],
    sense_rows: Sequence[tuple[Any, ...]],
    meaning_rows: Sequence[tuple[Any, ...]],
    surface_rows: Sequence[tuple[str, int]],
    example_lemma_rows: Sequence[tuple[int, int]],
) -> None:
    """Populate a single entry shard.

    The entry shard carries the lemma row, its senses, the meanings
    attached to those senses, the surface forms and the ``example_lemma``
    join. It does not carry the authoritative ``example`` payload: that
    lives in the example family keyed by ``example.id % 64``.
    """
    _init_entry_shard(connection)
    connection.executemany(
        "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, freq_rank, plural, "
        "plural_none, genitive_sg, aux, separable, particle, reflexive, praesens_3sg, "
        "praeteritum_3sg, partizip_ii, governs, comparative, superlative, ipa, source, "
        "license) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        lemma_rows,
    )
    connection.executemany(
        "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord, "
        "register, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        sense_rows,
    )
    connection.executemany(
        "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, "
        "license) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        meaning_rows,
    )
    connection.executemany(
        "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
        surface_rows,
    )
    connection.executemany(
        "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)",
        example_lemma_rows,
    )
    connection.commit()
    connection.execute("VACUUM")
    connection.commit()


def _write_example_shard(
    connection: sqlite3.Connection,
    bucket: int,
    example_rows: Sequence[tuple[Any, ...]],
) -> None:
    """Populate a single example shard."""
    _init_example_shard(connection)
    connection.executemany(
        "INSERT INTO example (id, de, en, source, source_ref, license, token_count, "
        "has_proper) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        example_rows,
    )
    connection.commit()
    connection.execute("VACUUM")
    connection.commit()


def _validate_lookup_surface_closure(
    lemma_partitions: Mapping[int, Sequence[tuple[Any, ...]]],
    surface_partitions: Mapping[int, Sequence[tuple[str, int]]],
) -> None:
    """Prove the surface_form -> lemma join is locally closed per bucket.

    Every ``(form, lemma_id)`` surface row must share its bucket with the
    corresponding lemma row, so the runtime join never needs another
    bucket. Runs in approximately linear time in the partitioned rows.
    """
    for bucket, rows in surface_partitions.items():
        lemma_ids = {int(row[0]) for row in lemma_partitions.get(bucket, ())}
        for form, lemma_id in rows:
            if int(lemma_id) not in lemma_ids:
                raise RuntimeError(
                    f"surface_form {form!r} for lemma_id={lemma_id} in "
                    f"lookup bucket {bucket} has no lemma row in that bucket"
                )


def _canonicalize_blob(blob: bytes) -> bytes:
    """Return an exact blob unchanged; placeholder for future canonicalization."""
    return blob


def build_corpus(
    inputs: BuildInputs,
) -> tuple[OnlineManifest, bytes]:
    """Build the deterministic Online corpus from one verified Local asset.

    Returns the validated :class:`OnlineManifest` and the membership
    filter bytes.
    """
    _validate_local_input(inputs.source_path)
    source = sqlite3.connect(
        f"file:{inputs.source_path.as_posix()}?mode=ro", uri=True
    )
    source.row_factory = sqlite3.Row
    try:
        lemmas = _read_authoritative_lemmas(source)
        senses = _read_authoritative_senses(source)
        meanings = _read_authoritative_meanings(source)
        surface_forms = _read_authoritative_surface_forms(source)
        examples = _read_authoritative_examples(source)
        example_lemma = _read_authoritative_example_lemma(source)
    finally:
        source.close()

    lemma_refs_by_id: dict[int, str] = {
        int(row[0]): str(row[1]) for row in lemmas
    }

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = inputs.output_dir / ".tmp"
    if tmp_dir.exists():
        for child in tmp_dir.iterdir():
            if child.is_file():
                child.unlink()
    tmp_dir.mkdir(parents=True, exist_ok=True)

    lookup_partitions, surface_partitions, sense_route_partitions = (
        _partition_lookup_shards(lemmas, surface_forms, senses)
    )
    _validate_sense_route_partitions(
        senses=senses,
        sense_route_partitions=sense_route_partitions,
        lemma_refs_by_id=lemma_refs_by_id,
    )
    _validate_lookup_surface_closure(lookup_partitions, surface_partitions)
    entry_partitions = _partition_entry_shards(
        lemmas, senses, meanings, surface_forms, example_lemma, examples
    )
    example_partitions = _partition_example_shards(examples)

    assets: list[ManifestAsset] = []
    for bucket in range(LOOKUP_FAMILY_SIZE):
        canonical = inputs.output_dir / _asset_name(SHARD_FAMILY_LOOKUP, bucket)
        connection = sqlite3.connect(
            f"file:{tmp_dir.as_posix()}/lookup-{bucket:03d}.sqlite?mode=rwc",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            _write_lookup_shard(
                connection,
                bucket,
                lookup_partitions.get(bucket, []),
                surface_partitions.get(bucket, []),
                sense_route_partitions.get(bucket, ()),
            )
            connection.commit()
            connection.close()
            tmp_source = tmp_dir / f"lookup-{bucket:03d}.sqlite"
            payload = tmp_source.read_bytes()
            _atomic_install(tmp_source, canonical)
        finally:
            try:
                connection.close()
            except Exception:
                pass
        digest = sha256(canonical.read_bytes()).hexdigest()
        assets.append(
            ManifestAsset(
                family=SHARD_FAMILY_LOOKUP,
                bucket=bucket,
                name=_asset_name(SHARD_FAMILY_LOOKUP, bucket),
                path=_asset_path(SHARD_FAMILY_LOOKUP, bucket),
                byte_size=canonical.stat().st_size,
                sha256=digest,
                schema_version="lookup-shard-v1",
            )
        )

    for bucket in range(ENTRY_FAMILY_SIZE):
        canonical = inputs.output_dir / _asset_name(SHARD_FAMILY_ENTRY, bucket)
        state = entry_partitions.get(bucket, {
            "lemmas": [],
            "senses": [],
            "meanings": [],
            "surface_forms": [],
            "example_lemma": [],
        })
        connection = sqlite3.connect(
            f"file:{tmp_dir.as_posix()}/entry-{bucket:03d}.sqlite?mode=rwc",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            _write_entry_shard(
                connection,
                bucket,
                state["lemmas"],
                state["senses"],
                state["meanings"],
                state["surface_forms"],
                state["example_lemma"],
            )
            connection.close()
            tmp_source = tmp_dir / f"entry-{bucket:03d}.sqlite"
            _atomic_install(tmp_source, canonical)
        finally:
            try:
                connection.close()
            except Exception:
                pass
        digest = sha256(canonical.read_bytes()).hexdigest()
        assets.append(
            ManifestAsset(
                family=SHARD_FAMILY_ENTRY,
                bucket=bucket,
                name=_asset_name(SHARD_FAMILY_ENTRY, bucket),
                path=_asset_path(SHARD_FAMILY_ENTRY, bucket),
                byte_size=canonical.stat().st_size,
                sha256=digest,
                schema_version="entry-shard-v1",
            )
        )

    for bucket in range(EXAMPLE_FAMILY_SIZE):
        canonical = inputs.output_dir / _asset_name(SHARD_FAMILY_EXAMPLE, bucket)
        connection = sqlite3.connect(
            f"file:{tmp_dir.as_posix()}/example-{bucket:03d}.sqlite?mode=rwc",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            _write_example_shard(connection, bucket, example_partitions[bucket])
            connection.close()
            tmp_source = tmp_dir / f"example-{bucket:03d}.sqlite"
            _atomic_install(tmp_source, canonical)
        finally:
            try:
                connection.close()
            except Exception:
                pass
        digest = sha256(canonical.read_bytes()).hexdigest()
        assets.append(
            ManifestAsset(
                family=SHARD_FAMILY_EXAMPLE,
                bucket=bucket,
                name=_asset_name(SHARD_FAMILY_EXAMPLE, bucket),
                path=_asset_path(SHARD_FAMILY_EXAMPLE, bucket),
                byte_size=canonical.stat().st_size,
                sha256=digest,
                schema_version="example-shard-v1",
            )
        )

    # Build the membership filter over authoritative lemmas using dynamic
    # sizing (m = -n ln p / (ln 2)^2, k = round((m/n) ln 2)). The closure
    # rule inserts both ``X`` and ``sqlite_ascii_lower(X)`` per lemma.
    closure_keys: list[str] = []
    seen_keys: set[str] = set()
    for row in lemmas:
        lemma_text = str(row[2])
        for variant in (lemma_text, _sqlite_ascii_lower(lemma_text)):
            if variant in seen_keys:
                continue
            seen_keys.add(variant)
            closure_keys.append(variant)
    filter_payload = BloomFilter.from_closure_keys(closure_keys).to_bytes()
    payload = _canonicalize_blob(filter_payload)
    tmp_filter = tmp_dir / "membership-filter.bin"
    tmp_filter.write_bytes(payload)
    filter_canonical = inputs.output_dir / _filter_name()
    _install_blob(tmp_filter, filter_canonical)
    digest = sha256(filter_canonical.read_bytes()).hexdigest()
    assets.append(
        ManifestAsset(
            family=SHARD_FAMILY_FILTER,
            bucket=0,
            name=_filter_name(),
            path=_filter_path(),
            byte_size=filter_canonical.stat().st_size,
            sha256=digest,
            schema_version="membership-filter-v1",
        )
    )

    # Clean up the temporary directory once everything is canonicalized.
    for child in tmp_dir.iterdir():
        try:
            child.unlink()
        except OSError:
            pass
    try:
        tmp_dir.rmdir()
    except OSError:
        pass

    manifest = OnlineManifest(
        dataset_token=inputs.dataset_token,
        schema_version=MANIFEST_SCHEMA_VERSION,
        distribution=TrustedDistribution(
            base_origin=inputs.base_origin,
            release_tag=inputs.release_tag,
            redirect_policy="github_release_redirect_only",
        ),
        assets=tuple(assets),
    )
    return manifest, filter_canonical.read_bytes()


def write_manifest(
    manifest: OnlineManifest, target_path: Path | str
) -> None:
    """Write one validated manifest as canonical JSON."""
    payload = json.dumps(
        {
            "dataset_token": manifest.dataset_token,
            "schema_version": manifest.schema_version,
            "distribution": {
                "base_origin": manifest.distribution.base_origin,
                "release_tag": manifest.distribution.release_tag,
                "redirect_policy": manifest.distribution.redirect_policy,
            },
            "assets": sorted(
                (
                    {
                        "family": a.family,
                        "bucket": a.bucket,
                        "name": a.name,
                        "path": a.path,
                        "byte_size": a.byte_size,
                        "sha256": a.sha256,
                        "schema_version": a.schema_version,
                    }
                    for a in manifest.assets
                ),
                key=lambda item: (item["family"], item["bucket"]),
            ),
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload + "\n")


def main(argv: Iterable[str] | None = None) -> int:
    """Entry point used by the Slice 11 builder CLI."""
    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the verified Local dictionary asset",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where shard files, the filter, and the manifest are written",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Output path for the canonical manifest JSON",
    )
    args = parser.parse_args(arguments)

    inputs = BuildInputs(
        source_path=args.source.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    manifest, _filter = build_corpus(inputs)
    write_manifest(manifest, args.manifest.resolve())
    digest = manifest_hash(manifest)
    sys.stdout.write(
        json.dumps(
            {
                "manifest_hash": digest,
                "asset_count": len(manifest.assets),
                "filter_size": next(
                    a.byte_size for a in manifest.assets
                    if a.family == SHARD_FAMILY_FILTER
                ),
            }
        )
        + "\n"
    )
    return 0


__all__ = [
    "BuildInputs",
    "build_corpus",
    "main",
    "write_manifest",
]