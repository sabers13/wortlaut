"""Tests for tools/build_dict.py build stage 01."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.dictionary import Dictionary
from tools.build_dict import BuildDictError, build_stage01, canonicalize_pos, main

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
    """Stage 01 build output is fully compatible with app.dictionary.Dictionary."""
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
        assert haus.genitive_sg == "Hauses"
        assert haus.ipa == "/haʊ̯s/"
        assert haus.ipa_source == "wiktionary"
        assert haus.source == "wiktionary"
        assert haus.license == "CC BY-SA"
        assert haus.separable == 0
        assert haus.aux is None

        # Senses for Haus: max 3 senses, English only, R11 attribution
        senses = d.get_senses_for_lemma(haus.id)
        assert len(senses) == 3
        assert [s.gloss_en for s in senses] == ["house", "building", "home"]
        assert [s.ord for s in senses] == [0, 1, 2]
        for s in senses:
            assert s.source == "wiktionary"
            assert s.license == "CC BY-SA"

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

        # Merged POS mapping: Berlin (name -> PROPN, proper_noun -> PROPN)
        berlin_entries = d.lookup_exact("Berlin", pos="PROPN")
        assert len(berlin_entries) == 1
        assert berlin_entries[0].lemma == "Berlin"
        assert berlin_entries[0].gender == "das"

        # Preposition mapping: mit (prep -> ADP)
        mit_entries = d.lookup_exact("mit", pos="ADP")
        assert len(mit_entries) == 1
        assert mit_entries[0].lemma == "mit"

        # Prefix suggest
        suggestions = d.suggest_lemmas("Ha")
        assert any(s.lemma == "Haus" for s in suggestions)


def test_no_part_b_or_example_tables(tmp_path: Path) -> None:
    """Stage 01 output contains only stage-01 PART A tables (no PART B / example tables)."""
    out_db = tmp_path / "dict_tables.sqlite"
    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, out_db)

    conn = sqlite3.connect(out_db)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    conn.close()

    assert set(tables) == {"lemma", "surface_form", "sense"}
    assert "example" not in tables
    assert "example_lemma" not in tables
    assert "note" not in tables
    assert "card" not in tables
    assert "review_log" not in tables


def test_determinism_and_order_independence(tmp_path: Path) -> None:
    """Reversing source lines produces identical queried rows, IDs, and orderings."""
    db1 = tmp_path / "db1.sqlite"
    db2 = tmp_path / "db2.sqlite"

    # Build DB 1 with standard fixtures
    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, db1)

    # Create reversed fixture files
    en_reversed_path = tmp_path / "en_reversed.jsonl"
    de_reversed_path = tmp_path / "de_reversed.jsonl"

    en_lines = [line for line in EN_FIXTURE_PATH.read_text(encoding="utf-8").splitlines() if line]
    de_lines = [line for line in DE_FIXTURE_PATH.read_text(encoding="utf-8").splitlines() if line]

    en_reversed_path.write_text("\n".join(reversed(en_lines)) + "\n", encoding="utf-8")
    de_reversed_path.write_text("\n".join(reversed(de_lines)) + "\n", encoding="utf-8")

    # Build DB 2 with reversed fixtures
    build_stage01(en_reversed_path, de_reversed_path, db2)

    conn1 = sqlite3.connect(db1)
    conn2 = sqlite3.connect(db2)

    for table in ("lemma", "surface_form", "sense"):
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

    # Content unchanged
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
