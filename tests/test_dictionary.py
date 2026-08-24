"""Tests for app/dictionary.py read-only dictionary asset reader (ADR-0004 PART A alignment)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

import pytest

from app.dictionary import (
    Dictionary,
    DictionaryAssetError,
    DictionaryEntry,
    _build_lemma_ref_maps,
    validate_candidate_dictionary,
)
from app.resolve import Ref


def _stable_ref(prefix: str, fields: list[str]) -> str:
    """Build a D47 ref from exact test fields without normalizing them."""
    payload = json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f"{prefix}:v1:{sha256(payload).hexdigest()}"


def _make_candidate_asset(
    tmp_path: Path,
    part_a_schema: str,
    *,
    lemma: str = "See",
    source_ref: str = "senseid:en-see-1",
    schema: str | None = None,
) -> Path:
    """Create a minimal, internally consistent PART-A candidate asset."""
    path = tmp_path / f"candidate-{source_ref.replace(':', '-')}.sqlite"
    lemma_ref = _stable_ref("lemma", ["de", lemma, "NOUN", "der"])
    sense_ref = _stable_ref("sense", [lemma_ref, "wiktextract:enwiktionary", source_ref])
    connection = sqlite3.connect(path)
    try:
        connection.executescript(schema if schema is not None else part_a_schema)
        connection.execute(
            "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender) VALUES (1, ?, ?, ?, ?)",
            (lemma_ref, lemma, "NOUN", "der"),
        )
        connection.execute(
            """
            INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref)
            VALUES (1, 1, ?, ?, ?)
            """,
            (sense_ref, "wiktextract:enwiktionary", source_ref),
        )
        connection.commit()
    finally:
        connection.close()
    return path


# --- S2a: candidate assets remain bound to one validated byte snapshot ---


def test_candidate_validation_binds_sha_and_handle_to_original_bytes(
    tmp_path: Path, part_a_schema: str
) -> None:
    """Replacing the source after validation cannot change the retained snapshot."""
    path = _make_candidate_asset(tmp_path, part_a_schema)
    expected_bytes = path.read_bytes()
    expected_sha256 = sha256(expected_bytes).hexdigest()
    original_ref = _stable_ref("lemma", ["de", "See", "NOUN", "der"])

    asset = validate_candidate_dictionary(path)
    try:
        # Replace rather than edit in place: a close-and-reopen implementation
        # would now serve Meer and fail this bytes-bound evidence.
        replacement = _make_candidate_asset(
            tmp_path,
            part_a_schema,
            lemma="Meer",
            source_ref="senseid:replacement",
        )
        replacement.replace(path)

        assert asset.sha256 == expected_sha256
        assert sha256(path.read_bytes()).hexdigest() != expected_sha256
        assert asset.connection.execute("SELECT lemma FROM lemma").fetchone()[0] == "See"
        assert dict(asset.lemma_ids) == {original_ref: 1}
    finally:
        asset.close()


def test_candidate_validation_rejects_corrupt_or_incomplete_assets(tmp_path: Path) -> None:
    """Bad SQLite content and a database missing PART-A structures fail closed."""
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"not a sqlite database")
    with pytest.raises(DictionaryAssetError):
        validate_candidate_dictionary(corrupt)

    incomplete = tmp_path / "incomplete.sqlite"
    sqlite3.connect(incomplete).close()
    with pytest.raises(DictionaryAssetError):
        validate_candidate_dictionary(incomplete)


def test_candidate_validation_rejects_whitespace_padded_identity_field(
    tmp_path: Path, part_a_schema: str
) -> None:
    """Validation never silently strips a non-canonical persisted identity value."""
    path = _make_candidate_asset(tmp_path, part_a_schema)
    connection = sqlite3.connect(path)
    try:
        connection.execute("UPDATE lemma SET lemma = 'See '")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(DictionaryAssetError):
        validate_candidate_dictionary(path)


def test_candidate_validation_rejects_wrong_shape_and_recomputation_mismatch(
    tmp_path: Path, part_a_schema: str
) -> None:
    """A versioned namespace and matching exact D47 hash are both mandatory."""
    wrong_shape = _make_candidate_asset(tmp_path, part_a_schema, source_ref="senseid:wrong-shape")
    connection = sqlite3.connect(wrong_shape)
    try:
        connection.execute("UPDATE lemma SET semantic_ref = 'lemma:v1:not-a-sha'")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(DictionaryAssetError):
        validate_candidate_dictionary(wrong_shape)

    mismatch = _make_candidate_asset(
        tmp_path, part_a_schema, source_ref="senseid:recomputation-mismatch"
    )
    connection = sqlite3.connect(mismatch)
    try:
        connection.execute("UPDATE lemma SET semantic_ref = ?", ("lemma:v1:" + "0" * 64,))
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(DictionaryAssetError):
        validate_candidate_dictionary(mismatch)


def test_candidate_validation_rejects_duplicate_stable_ref(
    tmp_path: Path, part_a_schema: str
) -> None:
    """A schema lacking ref uniqueness cannot make a duplicate candidate eligible."""
    non_unique_schema = part_a_schema.replace(
        "semantic_ref  TEXT NOT NULL UNIQUE,", "semantic_ref  TEXT NOT NULL,"
    )
    path = _make_candidate_asset(tmp_path, part_a_schema, schema=non_unique_schema)
    connection = sqlite3.connect(path)
    try:
        original = connection.execute("SELECT semantic_ref FROM lemma").fetchone()[0]
        connection.execute(
            "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender) VALUES (2, ?, ?, ?, ?)",
            (original, "Meer", "NOUN", "das"),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(DictionaryAssetError):
        validate_candidate_dictionary(path)


def test_internal_lemma_map_rejects_duplicate_stable_ref_rows() -> None:
    """Exercise defense in depth: public assets cannot contain these duplicate rows.

    The public flow requires UNIQUE semantic_ref and D47's namespaced ref shape,
    so an in-asset duplicate is rejected by schema validation first. This direct
    test keeps the map-builder branch mandatory for malformed/internal row input.
    """
    ref = _stable_ref("lemma", ["de", "See", "NOUN", "der"])
    rows = (
        (1, ref, "See", "NOUN", "der"),
        (2, ref, "See", "NOUN", "der"),
    )
    with pytest.raises(DictionaryAssetError, match="duplicate or ambiguous"):
        _build_lemma_ref_maps(rows)


def test_candidate_identity_fingerprints_preserve_trivial_source_differences(
    tmp_path: Path, part_a_schema: str
) -> None:
    """The later swap owner can compare exact D47 source identities across assets."""
    first = validate_candidate_dictionary(
        _make_candidate_asset(tmp_path, part_a_schema, source_ref="senseid:one")
    )
    second = validate_candidate_dictionary(
        _make_candidate_asset(tmp_path, part_a_schema, source_ref="senseid:two")
    )
    try:
        assert set(first.sense_identity_fingerprints.values()).isdisjoint(
            second.sense_identity_fingerprints.values()
        )
    finally:
        first.release()
        second.release()


def test_released_candidate_handle_closes_cleanly(
    tmp_path: Path, part_a_schema: str
) -> None:
    """Discarded candidates free their retained read-only snapshot idempotently."""
    asset = validate_candidate_dictionary(_make_candidate_asset(tmp_path, part_a_schema))
    asset.release()
    asset.close()
    with pytest.raises(sqlite3.ProgrammingError):
        asset.connection.execute("SELECT 1")


def test_missing_db_raises_file_not_found(tmp_path: Path) -> None:
    """Opening nonexistent database file raises FileNotFoundError."""
    missing_path = tmp_path / "nonexistent.sqlite"
    with pytest.raises(FileNotFoundError):
        Dictionary(missing_path)


def test_read_only_enforcement(create_test_db: Callable[[], Path]) -> None:
    """Database is opened in read-only mode and rejects modifications."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        with pytest.raises(sqlite3.OperationalError):
            d._conn.execute(
                "INSERT INTO lemma (lemma, pos, semantic_ref) VALUES ('Test', 'NOUN', 'test_ref')"
            )


def test_dictionary_implements_lookup_protocol(create_test_db: Callable[[], Path]) -> None:
    """Dictionary satisfies LookupProtocol interface."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        assert hasattr(d, "lookup_exact")
        assert hasattr(d, "lookup_surface_form")
        assert hasattr(d, "lookup_senses")


# --- Step 1: Exact Matches and Gender Disambiguation ---


def test_exact_lookup_and_gender_disambiguation(create_test_db: Callable[[], Path]) -> None:
    """Dictionary distinguishes der See (lake) from die See (sea) by gender."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        # Both records when gender is unspecified
        both = d.lookup_exact("See", pos="NOUN")
        assert len(both) == 2
        assert {b.gender for b in both} == {"der", "die"}

        # Exact masculine match
        der_see = d.lookup_exact("See", pos="NOUN", gender="der")
        assert len(der_see) == 1
        assert der_see[0].id == 1
        assert der_see[0].lemma == "See"
        assert der_see[0].gender == "der"
        assert der_see[0].ipa == "zeː"
        assert der_see[0].ipa_source == "wiktionary"
        assert der_see[0].semantic_ref is not None

        # Exact feminine match
        die_see = d.lookup_exact("See", pos="NOUN", gender="die")
        assert len(die_see) == 1
        assert die_see[0].id == 2
        assert die_see[0].lemma == "See"
        assert die_see[0].gender == "die"


# --- Step 2: Surface Form Lookup ---


def test_surface_form_lookup(create_test_db: Callable[[], Path]) -> None:
    """Dictionary resolves inflected surface forms to base lemma entries."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        # Häuser -> Haus
        matches = d.lookup_surface_form("Häuser")
        assert len(matches) == 1
        assert matches[0].id == 7
        assert matches[0].lemma == "Haus"
        assert matches[0].gender == "das"

        # Multi-word separable inflection: 'rief an' -> 'anrufen'
        verb_matches = d.lookup_surface_form("rief an")
        assert len(verb_matches) == 1
        assert verb_matches[0].id == 11
        assert verb_matches[0].lemma == "anrufen"
        assert verb_matches[0].separable == 1
        assert verb_matches[0].particle == "an"


# --- Resolution Ladder Through Dictionary Oracle ---


def test_resolution_ladder_exact(create_test_db: Callable[[], Path]) -> None:
    """Ladder Step 1 through Dictionary: exact hit returns status='resolved'."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        refs = d.resolve("Bank", pos="NOUN")
        assert len(refs) == 1
        assert refs[0] == Ref(
            lemma="Bank",
            pos="NOUN",
            gender="die",
            status="resolved",
            lemma_id=3,
        )


def test_resolution_ladder_surface_form(create_test_db: Callable[[], Path]) -> None:
    """Ladder Step 2 through Dictionary: surface form returns status='resolved'."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        refs = d.resolve("Häuser")
        assert len(refs) == 1
        assert refs[0].lemma == "Haus"
        assert refs[0].gender == "das"
        assert refs[0].status == "resolved"
        assert refs[0].lemma_id == 7


def test_resolution_ladder_compound_split(create_test_db: Callable[[], Path]) -> None:
    """Ladder Step 3 through Dictionary: compound splitter with D46 bindings."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        refs = d.resolve("Krankenversicherungskarte")
        assert len(refs) == 1
        ref = refs[0]
        assert ref.lemma == "Krankenversicherungskarte"
        assert ref.pos == "NOUN"
        assert ref.gender == "die"
        assert ref.status == "derived_compound"
        assert ref.lemma_id is None
        assert ref.components == ["kranken", "versicherung", "karte"]
        assert ref.head_lemma == "Karte"
        assert ref.component_bindings is not None
        assert len(ref.component_bindings) == 3

        b0, b1, b2 = ref.component_bindings
        assert b0.lemma == "kranken"
        assert b0.lemma_id == 4
        assert b0.lemma_ref.startswith("lemma:v1:")
        assert b0.sense_ref.startswith("sense:v1:")

        assert b1.lemma == "Versicherung"
        assert b1.lemma_id == 5
        assert b1.lemma_ref.startswith("lemma:v1:")

        assert b2.lemma == "Karte"
        assert b2.lemma_id == 6
        assert b2.lemma_ref.startswith("lemma:v1:")


def test_resolution_ladder_stub_fallthrough(create_test_db: Callable[[], Path]) -> None:
    """Ladder Step 4 through Dictionary: unknown word returns status='needs_gloss'."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        refs = d.resolve("NeologismusUnbekannt", pos="NOUN", gender="das")
        assert len(refs) == 1
        assert refs[0] == Ref(
            lemma="NeologismusUnbekannt",
            pos="NOUN",
            gender="das",
            status="needs_gloss",
            lemma_id=None,
            components=None,
            head_lemma=None,
            component_bindings=None,
        )


# --- Senses, Meanings, Examples, and Composite Entries ---


def test_get_senses_and_meanings(create_test_db: Callable[[], Path]) -> None:
    """Dictionary retrieves senses and deterministic localized meanings for a lemma."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        # Senses for der See (id=1)
        senses_1 = d.get_senses_for_lemma(1)
        assert len(senses_1) == 1
        assert senses_1[0].id is not None
        assert senses_1[0].semantic_ref == "sense:v1:see_der_0"
        assert senses_1[0].source_namespace == "wiktextract:enwiktionary"
        assert senses_1[0].source_ref == "senseid:en-see-1"

        meanings_1 = d.get_meanings_for_sense(senses_1[0].id)
        assert len(meanings_1) == 1
        assert meanings_1[0].text == "lake"
        assert meanings_1[0].language == "en"

        # Senses for die See (id=2)
        senses_2 = d.get_senses_for_lemma(2)
        assert len(senses_2) == 1
        assert senses_2[0].id is not None
        assert senses_2[0].semantic_ref == "sense:v1:see_die_0"

        meanings_2 = d.get_meanings_for_sense(senses_2[0].id)
        assert len(meanings_2) == 1
        assert meanings_2[0].text == "sea, ocean"

        # Examples for anrufen (id=11)
        examples = d.get_examples_for_lemma(11)
        assert len(examples) == 1
        assert examples[0].de == "Ich rufe dich morgen an."
        assert examples[0].en == "I will call you tomorrow."


def test_get_entry_composite(create_test_db: Callable[[], Path]) -> None:
    """Dictionary.get_entry returns full composite entry with all PART A fields."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        entry = d.get_entry(7)  # Haus
        assert entry is not None
        assert isinstance(entry, DictionaryEntry)
        assert entry.lemma.lemma == "Haus"
        assert entry.lemma.gender == "das"
        assert entry.lemma.semantic_ref is not None
        assert len(entry.senses) == 1
        assert len(entry.meanings) == 1
        assert entry.meanings[0].text == "house, building"
        assert "Häuser" in entry.surface_forms or "häuser" in entry.surface_forms


def test_get_entry_nonexistent_returns_none(create_test_db: Callable[[], Path]) -> None:
    """Dictionary.get_entry returns None for nonexistent lemma_id."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        assert d.get_entry(9999) is None


def test_suggest_lemmas_prefix(create_test_db: Callable[[], Path]) -> None:
    """Dictionary.suggest_lemmas performs prefix autocomplete."""
    db_path = create_test_db()
    with Dictionary(db_path) as d:
        suggestions = d.suggest_lemmas("Se", limit=5)
        lemmas = [s.lemma for s in suggestions]
        assert "See" in lemmas


def test_no_part_b_table_references() -> None:
    """Acceptance B5: app/dictionary.py must never touch, query, or reference PART B tables."""
    import app.dictionary
    source_file = app.dictionary.__file__
    assert source_file is not None
    with open(source_file, encoding="utf-8") as f:
        code = f.read()

    forbidden_part_b = [
        "note",
        "card",
        "review_log",
        "deck",
        "note_deck",
        "gloss_contribution",
    ]
    for table in forbidden_part_b:
        assert f"FROM {table}" not in code
        assert f"INTO {table}" not in code
        assert f"UPDATE {table}" not in code
        assert f"JOIN {table}" not in code
