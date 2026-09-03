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
    """Create the lookup-shard schema."""
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
        """
    )


def _init_entry_shard(connection: sqlite3.Connection) -> None:
    """Create the entry-shard schema."""
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


def _partition_lookup_shards(
    lemmas: Sequence[tuple[Any, ...]],
    surface_forms: Sequence[tuple[str, int]],
) -> dict[int, list[tuple[Any, ...]]]:
    """Partition lemmas into 256 lookup buckets using the closure rule.

    The full lemma row tuple is preserved; the lookup-shard writer reads
    only the first six columns it needs.
    """
    surface_by_lemma: dict[int, list[tuple[int, str]]] = {}
    for form, lemma_id in surface_forms:
        surface_by_lemma.setdefault(lemma_id, []).append((lemma_id, form))
    buckets: dict[int, list[tuple[Any, ...]]] = {}
    for row in lemmas:
        lemma_id = row[0]
        lemma_text = row[2]
        targets = _compute_bucket_targets_for_lookup(
            lemma_text=lemma_text,
            lemma_id=lemma_id,
            surface_form_lookup=surface_by_lemma.get(lemma_id, []),
        )
        for bucket in targets:
            buckets.setdefault(bucket, []).append(row)
    return buckets


def _partition_entry_shards(
    lemmas: Sequence[tuple[Any, ...]],
    senses: Sequence[tuple[int, int, str, str, str, int, str | None, str | None, str | None]],
    meanings: Sequence[tuple[int, int, str, str, int, str, str, str]],
    surface_forms: Sequence[tuple[str, int]],
    examples: Sequence[
        tuple[int, str, str | None, str | None, str | None, str | None, int | None, int]
    ],
    example_lemma: Sequence[tuple[int, int]],
) -> dict[int, dict[str, list[Any]]]:
    """Partition lemma-driven rows by ``bucket256_v1(lemma_semantic_ref)``.

    The entry shard owns the lemma row, its senses, the meanings attached
    to those senses, the surface forms and the example_lemma + example
    rows that reference the lemma's examples. Each entry shard has all
    data needed to satisfy provider reads without a follow-up remote
    fetch.
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
            "examples": [],
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
    example_by_id: dict[int, tuple[Any, ...]] = {int(r[0]): r for r in examples}
    examples_per_bucket: dict[int, list[tuple[Any, ...]]] = {}
    for lemma_id, example_id in example_lemma:
        el_bucket = lemma_bucket.get(int(lemma_id))
        if el_bucket is None:
            raise RuntimeError(
                f"example_lemma references unknown lemma_id={lemma_id}"
            )
        buckets[el_bucket]["example_lemma"].append((lemma_id, example_id))
        example_value = example_by_id.get(int(example_id))
        if example_value is not None:
            examples_per_bucket.setdefault(el_bucket, []).append(example_value)
    for bucket, rows in examples_per_bucket.items():
        seen_ids: set[int] = set()
        for row in rows:
            if row is None:
                continue
            example_id = int(row[0])
            if example_id in seen_ids:
                continue
            seen_ids.add(example_id)
            buckets[bucket]["examples"].append(row)
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
    surface_by_lemma: Mapping[int, list[str]],
) -> None:
    """Populate a single lookup shard."""
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
    surface_rows: list[tuple[str, int]] = []
    for lemma_id, forms in sorted(surface_by_lemma.items()):
        for form in sorted(forms):
            key = (lemma_id, form)
            if key in seen:
                continue
            seen.add(key)
            surface_rows.append((form, lemma_id))
    connection.executemany(
        "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
        surface_rows,
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
    example_rows: Sequence[tuple[Any, ...]],
    example_lemma_rows: Sequence[tuple[int, int]],
) -> None:
    """Populate a single entry shard."""
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
    connection.executemany(
        "INSERT INTO example (id, de, en, source, source_ref, license, token_count, "
        "has_proper) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        example_rows,
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

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = inputs.output_dir / ".tmp"
    if tmp_dir.exists():
        for child in tmp_dir.iterdir():
            if child.is_file():
                child.unlink()
    tmp_dir.mkdir(parents=True, exist_ok=True)

    surface_by_lemma: dict[int, list[str]] = {}
    for form, lemma_id in surface_forms:
        surface_by_lemma.setdefault(lemma_id, []).append(form)

    lookup_partitions = _partition_lookup_shards(lemmas, surface_forms)
    entry_partitions = _partition_entry_shards(
        lemmas, senses, meanings, surface_forms, examples, example_lemma
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
                surface_by_lemma,
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
            "examples": [],
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
                state["examples"],
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

    # Build the membership filter over authoritative lemmas
    filter_canonical = inputs.output_dir / _filter_name()
    filter_payload = BloomFilter.from_authoritative_lemmas(
        (row[2] for row in lemmas),
        size_bits=512,
    ).to_bytes()
    payload = _canonicalize_blob(filter_payload)
    tmp_filter = tmp_dir / "membership-filter.bin"
    tmp_filter.write_bytes(payload)
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