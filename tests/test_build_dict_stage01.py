"""Tests for tools/build_dict.py build stage 01 (ADR-0004 PART A alignment)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from app.dictionary import Dictionary
from tools.build_dict import (
    BuildDictError,
    build_stage01,
    canonicalize_pos,
    compute_lemma_semantic_ref,
    compute_sense_fallback_ref,
    compute_sense_semantic_ref,
    compute_sense_source_ref,
    main,
    validate_sense_meaning_derivations,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EN_FIXTURE_PATH = FIXTURES_DIR / "wiktextract_stage01_en.jsonl"
DE_FIXTURE_PATH = FIXTURES_DIR / "wiktextract_stage01_de.jsonl"


def test_pos_canonicalization() -> None:
    """Verify canonical POS mappings match C2 specification."""
    assert canonicalize_pos("noun") == "NOUN"
    assert canonicalize_pos("proper_noun") == "PROPN"
    assert canonicalize_pos("name") == "PROPN"
    assert canonicalize_pos("verb") == "VERB"
    assert canonicalize_pos("aux") == "AUX"
    assert canonicalize_pos("adj") == "ADJ"
    assert canonicalize_pos("adv") == "ADV"
    assert canonicalize_pos("prep") == "ADP"
    assert canonicalize_pos("postp") == "ADP"
    assert canonicalize_pos("pron") == "PRON"
    assert canonicalize_pos("det") == "DET"
    assert canonicalize_pos("num") == "NUM"
    assert canonicalize_pos("conj") == "CCONJ"
    assert canonicalize_pos("particle") == "PART"
    assert canonicalize_pos("intj") == "INTJ"
    assert canonicalize_pos("abbreviation") == "ABBREVIATION"


def test_stage01_build_and_dictionary_compatibility(tmp_path: Path) -> None:
    """Stage 01 build output is fully compatible with app.dictionary.Dictionary (A15)."""
    out_db = tmp_path / "dict_test.sqlite"

    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, out_db)
    assert out_db.exists()

    # Open with app.dictionary.Dictionary in read-only mode
    with Dictionary(out_db) as d:
        # Exact lookup: Haus (noun, neuter)
        haus_entries = d.lookup_exact("Haus", pos="NOUN", gender="das")
        assert len(haus_entries) == 1
        haus = haus_entries[0]
        assert haus.lemma == "Haus"
        assert haus.pos == "NOUN"
        assert haus.gender == "das"
        assert haus.plural == "Häuser"
        assert haus.plural_none == 0
        assert haus.genitive_sg == "Hauses"
        assert haus.ipa == "/haʊ̯s/"
        assert haus.ipa_source == "wiktionary"
        assert haus.source == "wiktionary"
        assert haus.license == "CC BY-SA"
        assert haus.separable == 0
        assert haus.aux is None
        assert haus.semantic_ref == (
            "lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436"
        )

        # Senses for Haus: exactly 1 sense with 3 meanings (A6 / A7)
        senses = d.get_senses_for_lemma(haus.id)
        assert len(senses) == 1
        sense_haus = senses[0]
        assert sense_haus.id is not None
        assert sense_haus.ord == 0
        assert sense_haus.source_namespace == "wiktextract:enwiktionary"
        assert sense_haus.source == "wiktionary"
        assert sense_haus.license == "CC BY-SA"
        assert sense_haus.semantic_ref is not None
        assert sense_haus.semantic_ref.startswith("sense:v1:")

        meanings = d.get_meanings_for_sense(sense_haus.id)
        assert len(meanings) == 3
        assert [m.text for m in meanings] == ["house", "building", "home"]
        assert [m.ord for m in meanings] == [0, 1, 2]
        for m in meanings:
            assert m.language == "en"
            assert m.kind == "translation"
            assert m.source == "wiktionary"
            assert m.license == "CC BY-SA"

        # Tri-state plural checks
        # 1. Known plural: Haus (plural="Häuser", plural_none=0)
        assert haus.plural == "Häuser"
        assert haus.plural_none == 0

        # 2. Explicit no-plural: Milch (plural=None, plural_none=1)
        milch_entries = d.lookup_exact("Milch", pos="NOUN")
        assert len(milch_entries) == 1
        milch = milch_entries[0]
        assert milch.plural is None
        assert milch.plural_none == 1

        # 3. Unknown plural: Berlin (plural=None, plural_none=0)
        berlin_entries = d.lookup_exact("Berlin", pos="PROPN")
        assert len(berlin_entries) == 1
        berlin = berlin_entries[0]
        assert berlin.plural is None
        assert berlin.plural_none == 0

        # Gender disambiguation: See (der) vs See (die)
        der_see = d.lookup_exact("See", pos="NOUN", gender="der")
        assert len(der_see) == 1
        assert der_see[0].gender == "der"
        assert der_see[0].genitive_sg == "Sees"
        assert der_see[0].plural == "Seen"

        die_see = d.lookup_exact("See", pos="NOUN", gender="die")
        assert len(die_see) == 1
        assert die_see[0].gender == "die"

        # Surface form lookups (including multi-word separable forms)
        assert len(d.lookup_surface_form("Häuser")) == 1
        assert d.lookup_surface_form("Häuser")[0].lemma == "Haus"
        assert len(d.lookup_surface_form("Hause")) == 1
        assert d.lookup_surface_form("Hause")[0].lemma == "Haus"

        # Literal 'rief an' and 'ruft an' for anrufen
        anrufen_entries = d.lookup_exact("anrufen", pos="VERB")
        assert len(anrufen_entries) == 1
        anrufen = anrufen_entries[0]
        assert anrufen.praesens_3sg == "ruft an"
        assert anrufen.praeteritum_3sg == "rief an"
        assert anrufen.partizip_ii == "angerufen"
        assert anrufen.semantic_ref == (
            "lemma:v1:0694906fb1cb9a54d2a100d341607d922446d187b0bb250546f06c755a229c8b"
        )

        ruft_matches = d.lookup_surface_form("ruft an")
        assert len(ruft_matches) == 1
        assert ruft_matches[0].lemma == "anrufen"

        rief_matches = d.lookup_surface_form("rief an")
        assert len(rief_matches) == 1
        assert rief_matches[0].lemma == "anrufen"

        # Adjective form-derived fields: schnell
        schnell_entries = d.lookup_exact("schnell", pos="ADJ")
        assert len(schnell_entries) == 1
        schnell = schnell_entries[0]
        assert schnell.comparative == "schneller"
        assert schnell.superlative == "schnellste"

        # Preposition mapping: mit (prep -> ADP)
        mit_entries = d.lookup_exact("mit", pos="ADP")
        assert len(mit_entries) == 1
        assert mit_entries[0].lemma == "mit"

        # Prefix suggest
        suggestions = d.suggest_lemmas("Ha")
        assert any(s.lemma == "Haus" for s in suggestions)


def test_no_part_b_or_example_tables(tmp_path: Path) -> None:
    """Stage 01 output contains only stage-01 PART A tables (no PART B/examples, A15 #34)."""
    out_db = tmp_path / "dict_tables.sqlite"
    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, out_db)

    conn = sqlite3.connect(out_db)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()

    assert set(tables) == {
        "lemma",
        "surface_form",
        "sense",
        "sense_meaning",
        "sense_meaning_derivation",
    }
    assert "example" not in tables
    assert "example_lemma" not in tables
    assert "note" not in tables
    assert "card" not in tables
    assert "review_log" not in tables


def test_no_gloss_en_column_in_sense_table(tmp_path: Path) -> None:
    """Acceptance A7/A15 #17: sense.gloss_en is removed as normative meaning carrier."""
    out_db = tmp_path / "dict_nogloss.sqlite"
    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, out_db)

    conn = sqlite3.connect(out_db)
    cur = conn.execute("PRAGMA table_info(sense)")
    columns = [row[1] for row in cur.fetchall()]
    conn.close()

    assert "gloss_en" not in columns
    assert "semantic_ref" in columns
    assert "source_namespace" in columns
    assert "source_ref" in columns


def test_language_column_has_no_closed_list_check(tmp_path: Path) -> None:
    """Acceptance A7/A15 #18: sense_meaning.language has no closed-list database CHECK."""
    out_db = tmp_path / "dict_lang.sqlite"
    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, out_db)

    conn = sqlite3.connect(out_db)
    # Inserting Persian 'fa' or French 'fr' localized meanings is allowed at schema level
    conn.execute(
        """
        INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license)
        VALUES (9999, 1, 'fa', 'translation', 0, 'خانه', 'manual', 'CC BY-SA')
        """
    )
    conn.commit()
    row = conn.execute("SELECT language, text FROM sense_meaning WHERE id = 9999").fetchone()
    assert row == ("fa", "خانه")
    conn.close()


def test_determinism_and_order_independence(tmp_path: Path) -> None:
    """Reversing source lines produces identical queried rows, IDs, and orderings."""
    db1 = tmp_path / "db1.sqlite"
    db2 = tmp_path / "db2.sqlite"

    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, db1)

    # Create reversed fixture files
    en_reversed_path = tmp_path / "en_reversed.jsonl"
    de_reversed_path = tmp_path / "de_reversed.jsonl"

    en_lines = [line for line in EN_FIXTURE_PATH.read_text(encoding="utf-8").splitlines() if line]
    de_lines = [line for line in DE_FIXTURE_PATH.read_text(encoding="utf-8").splitlines() if line]

    en_reversed_path.write_text("\n".join(reversed(en_lines)) + "\n", encoding="utf-8")
    de_reversed_path.write_text("\n".join(reversed(de_lines)) + "\n", encoding="utf-8")

    build_stage01(en_reversed_path, de_reversed_path, db2)

    conn1 = sqlite3.connect(db1)
    conn2 = sqlite3.connect(db2)

    for table in ("lemma", "surface_form", "sense", "sense_meaning", "sense_meaning_derivation"):
        rows1 = conn1.execute(f"SELECT * FROM {table}").fetchall()
        rows2 = conn2.execute(f"SELECT * FROM {table}").fetchall()
        assert rows1 == rows2, f"Discrepancy in table {table} between runs"

    conn1.close()
    conn2.close()


def test_refuse_existing_output_path(tmp_path: Path) -> None:
    """Attempting to build to an existing path raises BuildDictError and does not overwrite."""
    out_db = tmp_path / "existing.sqlite"
    out_db.write_text("existing content", encoding="utf-8")

    with pytest.raises(BuildDictError, match="Output path already exists"):
        build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, out_db)

    assert out_db.read_text(encoding="utf-8") == "existing content"


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    """Invalid JSON line fails closed with path and line number, leaving no output."""
    bad_en = tmp_path / "bad.jsonl"
    bad_en.write_text(
        '{"word": "Haus", "pos": "noun", "lang_code": "de"}\n{invalid json}\n', encoding="utf-8"
    )
    out_db = tmp_path / "out.sqlite"

    with pytest.raises(BuildDictError, match="Malformed JSON in .*bad.jsonl:2"):
        build_stage01(bad_en, DE_FIXTURE_PATH, out_db)

    assert not out_db.exists()


def test_wrong_field_type_fails_closed(tmp_path: Path) -> None:
    """Participating record with wrong field type fails closed with field name."""
    bad_en = tmp_path / "bad_tags.jsonl"
    bad_en.write_text(
        '{"word": "Haus", "pos": "noun", "lang_code": "de", "tags": 12345}\n', encoding="utf-8"
    )
    out_db = tmp_path / "out.sqlite"

    with pytest.raises(BuildDictError, match="Invalid type for field 'tags' in .*bad_tags.jsonl:1"):
        build_stage01(bad_en, DE_FIXTURE_PATH, out_db)

    assert not out_db.exists()


def test_conflicting_gender_tags_fails_closed(tmp_path: Path) -> None:
    """Record with conflicting gender tags fails closed."""
    bad_en = tmp_path / "conflict_gender.jsonl"
    bad_en.write_text(
        '{"word": "Zwitter", "pos": "noun", "lang_code": "de",'
        ' "tags": ["masculine", "feminine"]}\n',
        encoding="utf-8",
    )
    out_db = tmp_path / "out.sqlite"

    with pytest.raises(BuildDictError, match="Conflicting gender tags"):
        build_stage01(bad_en, DE_FIXTURE_PATH, out_db)

    assert not out_db.exists()


def test_ignored_records_with_malformed_fields_do_not_fail_build(tmp_path: Path) -> None:
    """Non-German or non-participating records with invalid tags are safely ignored."""
    en_file = tmp_path / "ignored.jsonl"
    record1 = {"word": "Haus", "pos": "noun", "lang_code": "de", "tags": ["neuter"]}
    record2 = {"word": "dog", "pos": "noun", "lang_code": "en", "tags": 12345}  # non-German
    record3 = {"word": "redirect", "lang_code": "de", "tags": "invalid"}  # no pos

    en_file.write_text(
        f"{json.dumps(record1)}\n{json.dumps(record2)}\n{json.dumps(record3)}\n",
        encoding="utf-8",
    )
    out_db = tmp_path / "out.sqlite"

    build_stage01(en_file, DE_FIXTURE_PATH, out_db)
    assert out_db.exists()


def test_cli_invocation_in_process(tmp_path: Path) -> None:
    """CLI entrypoint main() executes stage01 successfully and returns exit code 0."""
    out_db = tmp_path / "cli_out.sqlite"
    exit_code = main([
        "stage01",
        "--en-jsonl",
        str(EN_FIXTURE_PATH),
        "--de-jsonl",
        str(DE_FIXTURE_PATH),
        "--output",
        str(out_db),
    ])
    assert exit_code == 0
    assert out_db.exists()


def test_cli_invocation_subprocess(tmp_path: Path) -> None:
    """Subprocess execution of python tools/build_dict.py stage01 matches contract."""
    out_db = tmp_path / "subp_out.sqlite"
    cmd = [
        sys.executable,
        "tools/build_dict.py",
        "stage01",
        "--en-jsonl",
        str(EN_FIXTURE_PATH),
        "--de-jsonl",
        str(DE_FIXTURE_PATH),
        "--output",
        str(out_db),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert out_db.exists()


# --- A15: Golden Vectors & Deterministic Identity Tests ---


def test_golden_lemma_semantic_refs() -> None:
    """Assert exact payload bytes and golden hashes for lemma semantic refs (A2 / A15 #5)."""
    # Vector 1: Haus
    payload1 = json.dumps(
        ["de", "Haus", "NOUN", "das"], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    assert payload1 == b'["de","Haus","NOUN","das"]'
    ref1 = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    assert ref1 == "lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436"

    # Vector 2: anrufen
    payload2 = json.dumps(
        ["de", "anrufen", "VERB", "<null>"], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    assert payload2 == b'["de","anrufen","VERB","<null>"]'
    ref2 = compute_lemma_semantic_ref("anrufen", "VERB", None)
    assert ref2 == "lemma:v1:0694906fb1cb9a54d2a100d341607d922446d187b0bb250546f06c755a229c8b"


def test_golden_sense_semantic_ref() -> None:
    """Assert exact payload bytes and golden hash for sense semantic ref (A5 / A15 #6)."""
    lemma_ref = "lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436"
    source_namespace = "wiktextract:enwiktionary"
    source_ref = "senseid:en-house-1"

    payload = json.dumps(
        [lemma_ref, source_namespace, source_ref],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    assert payload == (
        b'["lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436",'
        b'"wiktextract:enwiktionary","senseid:en-house-1"]'
    )

    ref = compute_sense_semantic_ref(lemma_ref, source_namespace, source_ref)
    assert ref == "sense:v1:2fdd041adad74df1dfcd67a3ed5245c54bb03c20e373f989829e30dc755a70e6"


def test_nfc_equivalent_lemma_identity(tmp_path: Path) -> None:
    """Acceptance A2 / A15 #7: NFC-equivalent Unicode spellings produce identical semantic refs."""
    # Composed vs Decomposed 'Häuser'
    composed = "Häuser"
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed  # different byte sequence

    ref_comp = compute_lemma_semantic_ref(composed, "NOUN", "das")
    ref_decomp = compute_lemma_semantic_ref(decomposed, "NOUN", "das")
    assert ref_comp == ref_decomp


def test_source_ref_senseid_and_multiple_senseids() -> None:
    """Acceptance A4 / A15 #8: senseid and multiple senseids paths."""
    # Single senseid
    s1 = {"senseid": "en-house-1"}
    assert compute_sense_source_ref(s1) == "senseid:en-house-1"

    # Multiple senseids sorted & hashed
    s2 = {"senseids": ["en-house-2", "en-house-1"]}
    expected_payload = json.dumps(
        ["en-house-1", "en-house-2"], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    expected_ref = f"senseids:v1:{hashlib.sha256(expected_payload).hexdigest()}"
    assert compute_sense_source_ref(s2) == expected_ref


def test_source_ref_wikidata_and_multiple_wikidata() -> None:
    """Acceptance A4: wikidata and multiple wikidata paths."""
    # Single QID
    s1 = {"wikidata": "Q11569"}
    assert compute_sense_source_ref(s1) == "wikidata:Q11569"

    # Multiple QIDs
    s2 = {"wikidata": ["Q200", "Q100"]}
    expected_payload = json.dumps(
        ["Q100", "Q200"], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    expected_ref = f"wikidata-set:v1:{hashlib.sha256(expected_payload).hexdigest()}"
    assert compute_sense_source_ref(s2) == expected_ref


def test_fallback_fingerprint_cosmetic_stability() -> None:
    """Acceptance A4 / A15 #9-#12: Fallback fingerprint cosmetic stability and sensitivity."""
    # Whitespace changes do not alter fingerprint
    s_base = {"glosses": ["house, building"]}
    s_ws = {"glosses": ["   house, \n  building   "]}
    assert compute_sense_fallback_ref(s_base) == compute_sense_fallback_ref(s_ws)

    # Punctuation-only changes do not alter fingerprint
    s_punct = {"glosses": ["house; building!"]}
    assert compute_sense_fallback_ref(s_base) == compute_sense_fallback_ref(s_punct)

    # Key order and unordered container order do not alter fingerprint
    s_order1 = {"glosses": ["house"], "tags": ["neuter", "architecture"]}
    s_order2 = {"tags": ["architecture", "neuter"], "glosses": ["house"]}
    assert compute_sense_fallback_ref(s_order1) == compute_sense_fallback_ref(s_order2)

    # Real lexical change DOES alter fingerprint
    s_diff = {"glosses": ["castle, fortress"]}
    assert compute_sense_fallback_ref(s_base) != compute_sense_fallback_ref(s_diff)


def test_duplicate_stable_semantic_refs_fail_closed(tmp_path: Path) -> None:
    """Acceptance A4 / A15 #13: Duplicate semantic refs fail closed."""
    # Duplicate sense semantic refs for the same lemma
    en_file = tmp_path / "dup_sense.jsonl"
    record = {
        "word": "Haus",
        "pos": "noun",
        "lang_code": "de",
        "tags": ["neuter"],
        "senses": [
            {"senseid": "same-id", "glosses": ["house"]},
            {"senseid": "same-id", "glosses": ["building"]},
        ],
    }
    en_file.write_text(f"{json.dumps(record)}\n", encoding="utf-8")
    out_db = tmp_path / "out_dup.sqlite"

    with pytest.raises(BuildDictError, match="Duplicate sense semantic_ref"):
        build_stage01(en_file, DE_FIXTURE_PATH, out_db)


def test_max_three_english_meanings_and_single_sense_multiple_glosses(tmp_path: Path) -> None:
    """Acceptance A6 / A15 #14-#15: Multiple glosses become 1 sense and multiple meanings, max 3."""
    en_file = tmp_path / "multi_gloss.jsonl"
    record = {
        "word": "Haus",
        "pos": "noun",
        "lang_code": "de",
        "tags": ["neuter"],
        "senses": [
            {"senseid": "s1", "glosses": ["house", "building", "home", "dwelling", "residence"]},
        ],
    }
    en_file.write_text(f"{json.dumps(record)}\n", encoding="utf-8")
    out_db = tmp_path / "out_multi.sqlite"

    build_stage01(en_file, DE_FIXTURE_PATH, out_db)

    with Dictionary(out_db) as d:
        haus_entries = d.lookup_exact("Haus", pos="NOUN")
        assert len(haus_entries) == 1
        senses = d.get_senses_for_lemma(haus_entries[0].id)
        assert len(senses) == 1
        assert senses[0].id is not None
        meanings = d.get_meanings_for_sense(senses[0].id)
        assert len(meanings) == 3
        assert [m.text for m in meanings] == ["house", "building", "home"]


def test_derivation_edge_validation(tmp_path: Path) -> None:
    """Acceptance A8 / A15 #19-#23: D45 derivation edge rules validation."""
    db_path = tmp_path / "deriv_test.sqlite"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sense_meaning (
          id        INTEGER PRIMARY KEY,
          sense_id  INTEGER NOT NULL,
          language  TEXT NOT NULL,
          kind      TEXT NOT NULL,
          ord       INTEGER NOT NULL DEFAULT 0,
          text      TEXT NOT NULL,
          source    TEXT NOT NULL,
          license   TEXT NOT NULL
        );
        CREATE TABLE sense_meaning_derivation (
          generated_meaning_id INTEGER NOT NULL,
          source_meaning_id INTEGER NOT NULL,
          PRIMARY KEY (generated_meaning_id, source_meaning_id)
        );
        """
    )

    # Insert valid meanings
    conn.execute(
        "INSERT INTO sense_meaning VALUES (1, 100, 'en', 'translation', 0, "
        "'source text', 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense_meaning VALUES (2, 100, 'de', 'definition', 0, "
        "'generated text', 'llm_generated_v1', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense_meaning VALUES (3, 200, 'fa', 'translation', 0, "
        "'other sense text', 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense_meaning VALUES (4, 100, 'fa', 'translation', 0, "
        "'gen2 text', 'llm_generated_v2', 'CC BY-SA')"
    )

    # 1. Valid derivation edge (2 -> 1)
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (2, 1)")
    validate_sense_meaning_derivations(conn)

    # 2. Nonexistent generated meaning fails
    conn.execute("DELETE FROM sense_meaning_derivation")
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (999, 1)")
    with pytest.raises(BuildDictError, match="nonexistent generated meaning"):
        validate_sense_meaning_derivations(conn)

    # 3. Nonexistent source meaning fails
    conn.execute("DELETE FROM sense_meaning_derivation")
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (2, 999)")
    with pytest.raises(BuildDictError, match="nonexistent source meaning"):
        validate_sense_meaning_derivations(conn)

    # 4. Self-edge fails
    conn.execute("DELETE FROM sense_meaning_derivation")
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (2, 2)")
    with pytest.raises(BuildDictError, match="self-edge forbidden"):
        validate_sense_meaning_derivations(conn)

    # 5. Generated marker violation on generated side
    conn.execute("DELETE FROM sense_meaning_derivation")
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (1, 2)")
    with pytest.raises(BuildDictError, match="does not match versioned generated marker"):
        validate_sense_meaning_derivations(conn)

    # 6. Source side is generated (generated -> generated forbidden)
    conn.execute("DELETE FROM sense_meaning_derivation")
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (4, 2)")
    with pytest.raises(BuildDictError, match="generated->generated forbidden"):
        validate_sense_meaning_derivations(conn)

    # 7. Cross-sense derivation forbidden
    conn.execute("DELETE FROM sense_meaning_derivation")
    conn.execute("INSERT INTO sense_meaning_derivation VALUES (2, 3)")
    with pytest.raises(BuildDictError, match="Cross-sense derivation forbidden"):
        validate_sense_meaning_derivations(conn)

    conn.close()


def test_tri_state_noun_plural(tmp_path: Path) -> None:
    """Acceptance A9 / A15 #24-#27: Known, no-plural, unknown, and contradictory plural."""
    # 1. Contradictory plural fails closed
    bad_plural_file = tmp_path / "bad_plural.jsonl"
    record = {
        "word": "Wasser",
        "pos": "noun",
        "lang_code": "de",
        "tags": ["neuter", "no-plural"],
        "forms": [{"form": "Wässer", "tags": ["plural"]}],
    }
    bad_plural_file.write_text(f"{json.dumps(record)}\n", encoding="utf-8")
    out_db = tmp_path / "out_bad_plural.sqlite"

    with pytest.raises(BuildDictError, match="Contradictory plural evidence"):
        build_stage01(bad_plural_file, DE_FIXTURE_PATH, out_db)
