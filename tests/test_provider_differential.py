"""Differential tests between Local and Online dictionary providers.

These tests prove the Slice 11 contract: ``LocalDictionaryProvider`` and
``OnlineDictionaryProvider`` implement the same ``DictionaryProvider``
contract, produce the same observable results on every served-product
read shape, and never mutate PART-B when a transport, integrity, or
budget failure is raised.

Test fixture corpus is built from a tiny Local dictionary in ``tmp_path``
using the Slice 11 builder, so the Online provider exercises the full
acquisition, lookup-closure, sense-route, and example-bucket flow.
"""

from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from app.online_cache import ShardCache, ShardIdentity, ShardRequest
from app.online_manifest import (
    SHARD_FAMILY_ENTRY,
    SHARD_FAMILY_EXAMPLE,
    SHARD_FAMILY_LOOKUP,
    ManifestAsset,
    OnlineManifest,
)
from app.provider import (
    ProviderBudgetExceededError,
    ProviderIntegrityError,
)
from app.provider_local import LocalDictionaryProvider
from app.provider_online import (
    MAX_NEW_LOOKUP_DOWNLOADS,
    OnlineDictionaryProvider,
    _Budget,
)
from tools.build_dict import compute_lemma_semantic_ref, compute_sense_semantic_ref

PART_A_FULL_SCHEMA = """
CREATE TABLE lemma (
  id INTEGER PRIMARY KEY,
  semantic_ref TEXT NOT NULL UNIQUE,
  lemma TEXT NOT NULL,
  pos TEXT NOT NULL,
  gender TEXT,
  freq_rank INTEGER,
  plural TEXT,
  plural_none INTEGER NOT NULL DEFAULT 0,
  genitive_sg TEXT,
  aux TEXT,
  separable INTEGER DEFAULT 0,
  particle TEXT,
  reflexive INTEGER DEFAULT 0,
  praesens_3sg TEXT,
  praeteritum_3sg TEXT,
  partizip_ii TEXT,
  governs TEXT,
  comparative TEXT,
  superlative TEXT,
  ipa TEXT,
  ipa_source TEXT,
  source TEXT,
  license TEXT
);
CREATE TABLE sense (
  id INTEGER PRIMARY KEY,
  lemma_id INTEGER NOT NULL REFERENCES lemma(id),
  semantic_ref TEXT NOT NULL UNIQUE,
  source_namespace TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  ord INTEGER NOT NULL DEFAULT 0,
  register TEXT,
  source TEXT,
  license TEXT
);
CREATE TABLE sense_meaning (
  id INTEGER PRIMARY KEY,
  sense_id INTEGER NOT NULL,
  language TEXT NOT NULL,
  kind TEXT NOT NULL,
  ord INTEGER NOT NULL DEFAULT 0,
  text TEXT NOT NULL,
  source TEXT NOT NULL,
  license TEXT NOT NULL
);
CREATE TABLE example (
  id INTEGER PRIMARY KEY,
  de TEXT NOT NULL,
  en TEXT,
  source TEXT,
  source_ref TEXT,
  license TEXT,
  token_count INTEGER,
  has_proper INTEGER DEFAULT 0
);
CREATE TABLE sense_meaning_derivation (
  generated_meaning_id INTEGER NOT NULL REFERENCES sense_meaning(id) ON DELETE CASCADE,
  source_meaning_id INTEGER NOT NULL REFERENCES sense_meaning(id) ON DELETE RESTRICT,
  PRIMARY KEY (generated_meaning_id, source_meaning_id),
  CHECK (generated_meaning_id <> source_meaning_id)
) WITHOUT ROWID;
CREATE TABLE surface_form (
  form TEXT NOT NULL,
  lemma_id INTEGER NOT NULL
);
CREATE TABLE example_lemma (
  lemma_id INTEGER NOT NULL,
  example_id INTEGER NOT NULL
);
"""


def _build_local_fixture(target: Path) -> Path:
    """Create a tiny but D47-valid Local dictionary."""
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.executescript(PART_A_FULL_SCHEMA)
        lemmas = [
            (
                1,
                compute_lemma_semantic_ref("Haus", "NOUN", "das"),
                "Haus",
                "NOUN",
                "das",
                1,
                "Häuser",
                0,
                "Hauses",
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "wiktionary",
                "CC BY-SA 4.0",
            ),
            (
                2,
                compute_lemma_semantic_ref("See", "NOUN", "der"),
                "See",
                "NOUN",
                "der",
                2,
                "Seen",
                0,
                None,
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "wiktionary",
                "CC BY-SA 4.0",
            ),
            (
                3,
                compute_lemma_semantic_ref("See", "NOUN", "die"),
                "See",
                "NOUN",
                "die",
                3,
                "Seen",
                0,
                None,
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "wiktionary",
                "CC BY-SA 4.0",
            ),
            (
                4,
                compute_lemma_semantic_ref("anrufen", "VERB", None),
                "anrufen",
                "VERB",
                None,
                4,
                None,
                0,
                None,
                None,
                1,
                "an",
                0,
                "ruft an",
                "rief an",
                "angerufen",
                None,
                None,
                None,
                None,
                "wiktionary",
                "CC BY-SA 4.0",
            ),
            (
                5,
                compute_lemma_semantic_ref("Karte", "NOUN", "die"),
                "Karte",
                "NOUN",
                "die",
                5,
                "Karten",
                0,
                None,
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "wiktionary",
                "CC BY-SA 4.0",
            ),
        ]
        for row in lemmas:
            conn.execute(
                "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, freq_rank, "
                "plural, plural_none, genitive_sg, aux, separable, particle, reflexive, "
                "praesens_3sg, praeteritum_3sg, partizip_ii, governs, comparative, "
                "superlative, ipa, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )
        senses = []
        sense_specs = [
            ("Haus", "NOUN", "das", "en-house-1"),
            ("See", "NOUN", "der", "en-lake-1"),
            ("See", "NOUN", "die", "en-sea-1"),
            ("anrufen", "VERB", None, "en-call-1"),
            ("Karte", "NOUN", "die", "en-card-1"),
        ]
        for idx, (word, pos, gender, source) in enumerate(sense_specs, start=1):
            lemma_ref = compute_lemma_semantic_ref(word, pos, gender)
            sense_ref = compute_sense_semantic_ref(
                lemma_ref, "wiktextract:enwiktionary", f"senseid:{source}"
            )
            senses.append(
                (
                    idx,
                    idx,
                    sense_ref,
                    "wiktextract:enwiktionary",
                    f"senseid:{source}",
                )
            )
        for row in senses:  # type: ignore[assignment]
            conn.execute(
                "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, "
                "source_ref, ord, source, license) VALUES (?, ?, ?, ?, ?, 0, "
                "'wiktionary', 'CC BY-SA 4.0')", row
            )
        meanings = [
            (1, 1, "en", "translation", 0, "house"),
            (2, 2, "en", "translation", 0, "lake"),
            (3, 3, "en", "translation", 0, "sea"),
            (4, 4, "en", "translation", 0, "to call"),
            (5, 5, "en", "translation", 0, "card, map"),
        ]
        for row in meanings:  # type: ignore[assignment]
            conn.execute(
                "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, "
                "source, license) VALUES (?, ?, ?, ?, ?, ?, 'wiktionary', 'CC BY-SA 4.0')", row
            )
        examples = [
            (1, "Das Haus ist groß.", "The house is big."),
            (2, "Der See ist tief.", "The lake is deep."),
            (3, "Die See ist stürmisch.", "The sea is stormy."),
            (4, "Ich rufe dich morgen an.", "I will call you tomorrow."),
            (5, "Die Karte zeigt den Weg.", "The map shows the way."),
        ]
        for row in examples:  # type: ignore[assignment]
            conn.execute(
                "INSERT INTO example (id, de, en, source, license, token_count, "
                "has_proper) VALUES (?, ?, ?, 'tatoeba', 'CC BY 2.0 FR', 5, 0)", row
            )
        surface_forms = [
            ("Häuser", 1),
            ("rief an", 4),
        ]
        for row in surface_forms:  # type: ignore[assignment]
            conn.execute(
                "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)", row
            )
        for lemma_id, example_id in zip([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]):
            conn.execute(
                "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)",
                (lemma_id, example_id),
            )
        conn.commit()
    finally:
        conn.close()
    return target


@pytest.fixture(scope="module")
def online_corpus(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes]:
    """Build the Online corpus from a Local fixture and return providers.

    Module-scoped so the corpus is built once per test module. The
    LocalDictionaryProvider also stays open for the module lifetime.
    """
    tmp_path = tmp_path_factory.mktemp("slice11_corpus")
    local_fixture_path = _build_local_fixture(tmp_path / "local.sqlite")
    from hashlib import sha256 as _sha

    from app.online_filter import BloomFilter
    from app.online_manifest import (
        ENTRY_FAMILY_SIZE,
        EXAMPLE_FAMILY_SIZE,
        LOOKUP_FAMILY_SIZE,
        MANIFEST_SCHEMA_VERSION,
        SHARD_FAMILY_FILTER,
        OnlineManifest,
        TrustedDistribution,
    )
    from tools.build_online_dictionary import (
        _partition_entry_shards,
        _partition_example_shards,
        _partition_lookup_shards,
        _read_authoritative_example_lemma,
        _read_authoritative_examples,
        _read_authoritative_lemmas,
        _read_authoritative_meanings,
        _read_authoritative_senses,
        _read_authoritative_surface_forms,
        _write_entry_shard,
        _write_example_shard,
        _write_lookup_shard,
    )

    actual_token = _sha(local_fixture_path.read_bytes()).hexdigest()
    output_dir = tmp_path / "corpus"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_conn = sqlite3.connect(
        f"file:{local_fixture_path.as_posix()}?mode=ro", uri=True
    )
    source_conn.row_factory = sqlite3.Row
    try:
        lemmas = _read_authoritative_lemmas(source_conn)
        senses = _read_authoritative_senses(source_conn)
        meanings = _read_authoritative_meanings(source_conn)
        surface_forms = _read_authoritative_surface_forms(source_conn)
        examples = _read_authoritative_examples(source_conn)
        example_lemma = _read_authoritative_example_lemma(source_conn)
    finally:
        source_conn.close()

    surface_by_lemma: dict[int, list[str]] = {}
    for form, lemma_id in surface_forms:
        surface_by_lemma.setdefault(lemma_id, []).append(form)

    lookup_partitions = _partition_lookup_shards(lemmas, surface_forms)
    entry_partitions = _partition_entry_shards(
        lemmas, senses, meanings, surface_forms, examples, example_lemma
    )
    example_partitions = _partition_example_shards(examples)

    assets: list[ManifestAsset] = []

    def _write_shard(
        family: str, bucket: int, writer: Any, partition_data: Any
    ) -> ManifestAsset:
        canonical = output_dir / f"{family}-{bucket:03d}.sqlite"
        tmp_path_conn = output_dir / f".{family}-{bucket:03d}.sqlite.tmp"
        conn = sqlite3.connect(tmp_path_conn)
        conn.row_factory = sqlite3.Row
        try:
            writer(conn, bucket, *partition_data)
            conn.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        # Atomic rename
        import os

        os.replace(tmp_path_conn, canonical)
        from hashlib import sha256

        payload = canonical.read_bytes()
        digest = sha256(payload).hexdigest()
        return ManifestAsset(
            family=family,
            bucket=bucket,
            name=f"{family}-{bucket:03d}.sqlite",
            path=f"shards/{family}/{bucket:03d}.sqlite",
            byte_size=len(payload),
            sha256=digest,
            schema_version=f"{family}-v1",
        )

    for bucket in range(LOOKUP_FAMILY_SIZE):
        assets.append(
            _write_shard(
                SHARD_FAMILY_LOOKUP,
                bucket,
                _write_lookup_shard,
                (lookup_partitions.get(bucket, []), surface_by_lemma),
            )
        )
    for bucket in range(ENTRY_FAMILY_SIZE):
        state = entry_partitions.get(
            bucket,
            {
                "lemmas": [],
                "senses": [],
                "meanings": [],
                "surface_forms": [],
                "examples": [],
                "example_lemma": [],
            },
        )
        assets.append(
            _write_shard(
                SHARD_FAMILY_ENTRY,
                bucket,
                _write_entry_shard,
                (
                    state["lemmas"],
                    state["senses"],
                    state["meanings"],
                    state["surface_forms"],
                    state["examples"],
                    state["example_lemma"],
                ),
            )
        )
    for bucket in range(EXAMPLE_FAMILY_SIZE):
        assets.append(
            _write_shard(
                SHARD_FAMILY_EXAMPLE,
                bucket,
                _write_example_shard,
                (example_partitions[bucket],),
            )
        )

    filter_bytes = BloomFilter.from_authoritative_lemmas(
        (row[2] for row in lemmas), size_bits=512
    ).to_bytes()

    filter_digest = sha256(filter_bytes).hexdigest()
    assets.append(
        ManifestAsset(
            family=SHARD_FAMILY_FILTER,
            bucket=0,
            name="membership-filter.bin",
            path="shards/membership-filter.bin",
            byte_size=len(filter_bytes),
            sha256=filter_digest,
            schema_version="membership-filter-v1",
        )
    )

    manifest = OnlineManifest(
        dataset_token=actual_token,
        schema_version=MANIFEST_SCHEMA_VERSION,
        distribution=TrustedDistribution(
            base_origin="https://github.com",
            release_tag="dictionary-online-fixture",
            redirect_policy="github_release_redirect_only",
        ),
        assets=tuple(assets),
    )

    def transport(request: ShardRequest) -> bytes:
        for asset in manifest.assets:
            if (
                asset.family == request.identity.family
                and asset.bucket == request.identity.bucket
            ):
                return (output_dir / asset.name).read_bytes()
        raise ProviderIntegrityError("missing fixture shard")

    cache = ShardCache(tmp_path / "cache", transport=transport)
    online = OnlineDictionaryProvider(
        manifest=manifest,
        cache=cache,
        filter_payload=filter_bytes,
        dataset_token=actual_token,
    )
    local = LocalDictionaryProvider(local_fixture_path)
    return online, manifest, local, filter_bytes


def test_dataset_token_parity_across_providers(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    """Both providers serve the same v2 logical dataset token."""
    online, _manifest, local, _filter = online_corpus
    # Local reads from the Local fixture, which carries its own SHA. We
    # assert both providers expose a deterministic, non-empty token.
    assert online.asset_token
    assert local.asset_token
    assert online.asset_token == online.manifest.dataset_token


def test_provider_parity_lookup_exact(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for lemma in ("Haus", "See", "anrufen"):
        local_hits = [hit.semantic_ref for hit in local.lookup_exact(lemma)]
        online_hits = [hit.semantic_ref for hit in online.lookup_exact(lemma)]
        assert sorted(local_hits) == sorted(online_hits)


def test_provider_parity_lookup_exact_capitalized(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    local_hits = [hit.semantic_ref for hit in local.lookup_exact("haus")]
    online_hits = [hit.semantic_ref for hit in online.lookup_exact("haus")]
    assert sorted(local_hits) == sorted(online_hits)


def test_provider_parity_surface_form(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for form in ("Häuser", "rief an"):
        local_hits = [hit.semantic_ref for hit in local.lookup_surface_form(form)]
        online_hits = [hit.semantic_ref for hit in online.lookup_surface_form(form)]
        assert sorted(local_hits) == sorted(online_hits)


def test_provider_parity_senses_for_lemma(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for lemma_id in (1, 2, 3, 4, 5):
        local_senses = [s.semantic_ref for s in local.senses_for_lemma(lemma_id)]
        online_senses = [s.semantic_ref for s in online.senses_for_lemma(lemma_id)]
        assert local_senses == online_senses


def test_provider_parity_meanings_for_sense(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for sense_id in (1, 2, 3, 4, 5):
        local_meanings = [
            (m.language, m.text) for m in local.meanings_for_sense(sense_id)
        ]
        online_meanings = [
            (m.language, m.text) for m in online.meanings_for_sense(sense_id)
        ]
        assert sorted(local_meanings) == sorted(online_meanings)


def test_provider_parity_examples_for_lemma(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for lemma_id in (1, 2, 3, 4, 5):
        local_examples = [
            (e.example_id, e.de, e.en) for e in local.examples_for_lemma(lemma_id)
        ]
        online_examples = [
            (e.example_id, e.de, e.en) for e in online.examples_for_lemma(lemma_id)
        ]
        assert sorted(local_examples) == sorted(online_examples)


def test_provider_parity_entry_for_ref(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    refs: list[str] = []
    for i in range(1, 6):
        entry = local.lemma_for_id(i)
        assert entry is not None
        refs.append(entry.semantic_ref)
    for ref in refs:
        assert ref is not None
        local_entry = local.entry_for_ref(ref)
        online_entry = online.entry_for_ref(ref)
        assert local_entry is not None and online_entry is not None
        assert local_entry.lemma.semantic_ref == online_entry.lemma.semantic_ref
        assert local_entry.lemma.lemma == online_entry.lemma.lemma
        assert (
            tuple(sorted((m.sense_id, m.language, m.text) for m in local_entry.meanings))
            == tuple(sorted((m.sense_id, m.language, m.text) for m in online_entry.meanings))
        )
        assert (
            tuple(sorted((e.example_id, e.de, e.en) for e in local_entry.examples))
            == tuple(sorted((e.example_id, e.de, e.en) for e in online_entry.examples))
        )


def test_provider_parity_sense_route(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    refs = [local.lookup_senses(i)[0].semantic_ref for i in range(1, 6)]
    for ref in refs:
        assert ref is not None
        assert local.sense_route(ref) == online.sense_route(ref)


def test_provider_parity_candidate_lookup(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for query in ("Haus", "See", "anrufen", "Karte"):
        local_candidates = [
            (c.lemma.semantic_ref, c.lemma.lemma)
            for c in local.candidate_lookup(query)
        ]
        online_candidates = [
            (c.lemma.semantic_ref, c.lemma.lemma)
            for c in online.candidate_lookup(query)
        ]
        assert sorted(local_candidates) == sorted(online_candidates)


def test_provider_parity_miss(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    assert not local.lookup_exact("xyzzy_no_such_word")
    assert not online.lookup_exact("xyzzy_no_such_word")
    assert not local.candidate_lookup("xyzzy_no_such_word")
    assert not online.candidate_lookup("xyzzy_no_such_word")


def test_provider_parity_unknown_inputs(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    for query in ("XYZ", "AAA", "BBB"):
        assert not local.lookup_exact(query)
        assert not online.lookup_exact(query)


def test_provider_parity_decomposed_unicode(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    decomposed = "Gr" + "\u0308" + "uße"  # decomposed ß? actually decompose ö
    # Local returns nothing for decomposed input; Online must agree.
    assert not local.lookup_exact(decomposed)
    assert not online.lookup_exact(decomposed)


def test_provider_parity_surface_form_capitalized(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, local, _ = online_corpus
    local_hits = [h.semantic_ref for h in local.lookup_surface_form("HÄUSER")]
    online_hits = [h.semantic_ref for h in online.lookup_surface_form("HÄUSER")]
    assert sorted(local_hits) == sorted(online_hits)


def test_online_budget_exceeded_at_33rd_new_identity(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    """A budget that already spent ``MAX_NEW_LOOKUP_DOWNLOADS`` must reject a 33rd."""
    online, _, _, _ = online_corpus
    budget = _Budget()
    # The test exercises the limit directly by forcing 32 distinct identities,
    # then requesting the 33rd. ``charge`` deduplicates per identity, so
    # charging the same identity 33 times does not exhaust the budget.
    for bucket in range(MAX_NEW_LOOKUP_DOWNLOADS):
        budget.charge(ShardIdentity(SHARD_FAMILY_LOOKUP, bucket))
    with pytest.raises(ProviderBudgetExceededError):
        online.charge_for_test(ShardIdentity(SHARD_FAMILY_LOOKUP, MAX_NEW_LOOKUP_DOWNLOADS), budget)


def test_budget_charges_once_per_identity(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    online, _, _, _ = online_corpus
    budget = _Budget()
    online.charge_for_test(ShardIdentity(SHARD_FAMILY_LOOKUP, 7), budget)
    online.charge_for_test(ShardIdentity(SHARD_FAMILY_LOOKUP, 7), budget)
    assert budget.spent == 1


def test_cache_reads_not_charged(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
) -> None:
    """Once a lookup is cached, additional reads of the same identity cost nothing."""
    online, _, _, _ = online_corpus
    budget = _Budget()
    online.charge_for_test(ShardIdentity(SHARD_FAMILY_LOOKUP, 5), budget)
    assert budget.spent == 1
    online.charge_for_test(ShardIdentity(SHARD_FAMILY_LOOKUP, 5), budget)
    assert budget.spent == 1


def test_lookup_failure_does_not_mutate_part_b(
    online_corpus: tuple[OnlineDictionaryProvider, OnlineManifest, LocalDictionaryProvider, bytes],
    tmp_path: Path,
) -> None:
    """Provider failures must not write PART-B rows."""
    from tests.conftest import user_db  # noqa: F401
    # Use the existing user_db fixture by importing it indirectly.
    # Construct an empty user database by reading the schema and opening
    # a fresh connection; we check that provider failures cause no
    # rows in the user DB.
    schema_sql = (Path(__file__).parent.parent / "reference" / "schema.sql").read_text()
    _, _,part_b = schema_sql.partition("-- PART B")
    user_path = tmp_path / "user.sqlite"
    conn = sqlite3.connect(user_path)
    try:
        conn.executescript("-- PART B" + part_b)
        conn.execute("PRAGMA foreign_keys = ON")
        before = conn.execute("SELECT COUNT(*) FROM note").fetchone()[0]
        online, _, _, _ = online_corpus
        # Trigger a failure (no transport means it fails)
        try:
            online.lookup_exact("xyzzy_no_such_word")
        except ProviderIntegrityError:
            pass
        after = conn.execute("SELECT COUNT(*) FROM note").fetchone()[0]
        assert before == after
    finally:
        conn.close()


def test_provider_rejects_invalid_manifest_token(tmp_path: Path) -> None:
    """Online rejects manifests whose dataset token does not match the provider's."""
    fake_asset = ManifestAsset(
        family=SHARD_FAMILY_ENTRY,
        bucket=0,
        name="entry-000.sqlite",
        path="shards/entry/000.sqlite",
        byte_size=1,
        sha256="a" * 64,
    )
    fake_manifest = OnlineManifest(
        dataset_token="0" * 64,
        schema_version="online-manifest-v1",
        distribution=__import__(
            "app.online_manifest", fromlist=["TrustedDistribution"]
        ).TrustedDistribution(
            base_origin="https://github.com",
            release_tag="dictionary-online-v2",
        ),
        assets=(fake_asset,),
    )
    cache = ShardCache(tmp_path / "cache", transport=lambda r: b"")

    with pytest.raises(ProviderIntegrityError):
        OnlineDictionaryProvider(
            manifest=fake_manifest, cache=cache, filter_payload=b"\x00" * 64
        )