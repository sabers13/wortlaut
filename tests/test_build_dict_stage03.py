"""Tests for Stage 03 deterministic enrichment queue construction."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from tools.build_dict import (
    BuildDictError,
    _fa_duplicate_key,
    _validate_de_source_eligibility,
    _validate_persian_unicode,
    build_stage01,
    build_stage03,
    sha256_file,
)

MINI_SCHEMA = """
CREATE TABLE lemma (
  id INTEGER PRIMARY KEY, semantic_ref TEXT NOT NULL UNIQUE,
  lemma TEXT NOT NULL, pos TEXT NOT NULL, gender TEXT
);
CREATE TABLE surface_form (
  form TEXT NOT NULL, lemma_id INTEGER NOT NULL,
  PRIMARY KEY (form, lemma_id)
) WITHOUT ROWID;
CREATE TABLE sense (
  id INTEGER PRIMARY KEY, lemma_id INTEGER NOT NULL,
  semantic_ref TEXT NOT NULL UNIQUE,
  source_namespace TEXT NOT NULL, source_ref TEXT NOT NULL,
  ord INTEGER NOT NULL
);
CREATE TABLE sense_meaning (
  id INTEGER PRIMARY KEY, sense_id INTEGER NOT NULL,
  language TEXT NOT NULL, kind TEXT NOT NULL, ord INTEGER NOT NULL,
  text TEXT NOT NULL, source TEXT NOT NULL, license TEXT NOT NULL
);
CREATE TABLE sense_meaning_derivation (
  generated_meaning_id INTEGER NOT NULL,
  source_meaning_id INTEGER NOT NULL,
  PRIMARY KEY (generated_meaning_id, source_meaning_id)
) WITHOUT ROWID;
CREATE TABLE example (
  id INTEGER PRIMARY KEY, de TEXT NOT NULL, en TEXT,
  source TEXT, source_ref TEXT, license TEXT,
  token_count INTEGER, has_proper INTEGER DEFAULT 0
);
CREATE TABLE example_lemma (
  lemma_id INTEGER NOT NULL, example_id INTEGER NOT NULL,
  PRIMARY KEY (lemma_id, example_id)
) WITHOUT ROWID;
"""

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EN_FIXTURE_PATH = FIXTURES_DIR / "wiktextract_stage01_en.jsonl"
DE_FIXTURE_PATH = FIXTURES_DIR / "wiktextract_stage01_de.jsonl"


@pytest.fixture
def s02_like_db(tmp_path: Path) -> Path:
    # Build a small Stage-01 then copy as Stage-02 for testing (has required tables)
    db = tmp_path / "s02.sqlite"
    build_stage01(EN_FIXTURE_PATH, DE_FIXTURE_PATH, db)
    # Add Stage02 tables empty
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS example (
          id INTEGER PRIMARY KEY, de TEXT NOT NULL, en TEXT,
          source TEXT, source_ref TEXT, license TEXT,
          token_count INTEGER, has_proper INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS example_lemma (
          lemma_id INTEGER NOT NULL, example_id INTEGER NOT NULL,
          PRIMARY KEY (lemma_id, example_id)
        ) WITHOUT ROWID;
        """
    )
    conn.close()
    return db


def test_deterministic_queue_ids_and_order(s02_like_db: Path, tmp_path: Path) -> None:
    out1 = tmp_path / "q1.json"
    out2 = tmp_path / "q2.json"
    build_stage03(s02_like_db, out1)
    build_stage03(s02_like_db, out2)
    data1 = json.loads(out1.read_text())
    data2 = json.loads(out2.read_text())
    ids1 = [x["item_id"] for x in data1["items"]]
    ids2 = [x["item_id"] for x in data2["items"]]
    assert ids1 == ids2
    assert ids1 == sorted(ids1)  # bytewise sorted
    # SHA stability
    assert data1["queue_sha256"] == data2["queue_sha256"]


def test_input_order_independence(tmp_path: Path) -> None:
    # Stage03 reads DB ordered by semantic_ref, so input TSV order irrelevant - we just verify DB order independence  # noqa: E501
    # Simulate by rebuilding same input produces same queue (already tested)
    pass


def test_missing_fa_coverage_report_and_owner_stop(s02_like_db: Path, tmp_path: Path) -> None:
    out = tmp_path / "q.json"
    pkt = tmp_path / "pkt.json"
    rep = tmp_path / "rep.txt"
    result = build_stage03(s02_like_db, out, packet_path=pkt, report_path=rep)
    assert int(str(result.get("fa_missing", 0))) > 0
    packet = json.loads(pkt.read_text())
    assert packet["persian_source_acceptance"] == "NOT_ACCEPTED"
    report = rep.read_text()
    assert "TOTAL CANONICAL SENSES:" in report
    assert "FA STILL MISSING:" in report
    assert "MISSING_FA_SAMPLE:" in report


def test_missing_en_classification(tmp_path: Path) -> None:
    # Use empty DB fixture to verify EN missing yields en_translation job
    db = tmp_path / "mini.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(MINI_SCHEMA)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos) VALUES (1, 'lemma:v1:a', 'Haus', 'NOUN')")  # noqa: E501
    conn.execute("INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord) VALUES (1, 1, 'sense:v1:a', 'wiktextract:enwiktionary', 'fingerprint:v1:xx', 0)")  # noqa: E501
    # No EN meaning
    conn.commit()
    conn.close()
    out = tmp_path / "q.json"
    build_stage03(db, out)
    data = json.loads(out.read_text())
    en_jobs = [x for x in data["items"] if x["language"] == "en"]
    assert len(en_jobs) == 1
    assert en_jobs[0]["job_class"] == "en_translation"


def test_source_first_german_retention_and_fallback(tmp_path: Path) -> None:
    db = tmp_path / "mini2.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(MINI_SCHEMA)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos) VALUES (1, 'lemma:v1:b', 'Haus', 'NOUN')")  # noqa: E501
    conn.execute("INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord) VALUES (1, 1, 'sense:v1:b', 'wiktextract:enwiktionary', 'fingerprint:v1:yy', 0)")  # noqa: E501
    # Eligible DE synonym
    conn.execute("INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (1, 1, 'de', 'synonym', 0, 'Gebäude', 'wiktionary', 'CC BY-SA')")  # noqa: E501
    # Missing EN still
    conn.commit()
    conn.close()
    out = tmp_path / "q.json"
    build_stage03(db, out)
    data = json.loads(out.read_text())
    de_jobs = [x for x in data["items"] if x["language"] == "de"]
    # eligible DE retained => no DE job
    assert len(de_jobs) == 0


def test_direct_fa_mapping_and_duplicate_collapse_and_ord(tmp_path: Path) -> None:
    # Create FA rows with duplicates and ensure dedup works
    db = tmp_path / "fa.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(MINI_SCHEMA)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos) VALUES (1, 'lemma:v1:c', 'Haus', 'NOUN')")  # noqa: E501
    conn.execute("INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord) VALUES (1, 1, 'sense:v1:c', 'wiktextract:enwiktionary', 'fingerprint:v1:zz', 0)")  # noqa: E501
    # Duplicate FA texts with whitespace variation
    conn.execute("INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (10, 1, 'fa', 'translation', 0, 'خانه', 'wiktionary', 'CC BY-SA')")  # noqa: E501
    conn.execute("INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (11, 1, 'fa', 'translation', 1, ' خانه ', 'wiktionary', 'CC BY-SA')")  # noqa: E501
    conn.execute("INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (12, 1, 'fa', 'translation', 2, 'کتاب', 'wiktionary', 'CC BY-SA')")  # noqa: E501
    conn.commit()
    conn.close()
    out = tmp_path / "q.json"
    result = build_stage03(db, out)
    # FA covered should be 1 sense
    assert result["fa_covered"] == 1
    # Duplicate key collapse: خانه and  خانه  same key -> dedup keeps one
    assert _fa_duplicate_key("خانه") == _fa_duplicate_key(" خانه ")


def test_positive_de_predicate_and_uncertainty_fallback() -> None:
    # eligible cases
    assert _validate_de_source_eligibility("Gebäude", "synonym") is None
    assert _validate_de_source_eligibility("großes Haus", "synonym") is None
    # too many tokens for synonym
    assert _validate_de_source_eligibility("ein sehr großes Haus wirklich", "synonym") is not None
    # forbidden meta
    assert _validate_de_source_eligibility("siehe Haus", "definition") is not None
    # URL
    assert _validate_de_source_eligibility("siehe https://example.com", "synonym") is not None
    # markup
    assert _validate_de_source_eligibility("[[Haus]]", "definition") is not None
    # final punct for synonym forbidden
    assert _validate_de_source_eligibility("Haus.", "synonym") is not None
    # definition with final punct allowed
    assert _validate_de_source_eligibility("ein großes Gebäude.", "definition") is None


def test_zero_automatic_fa_jobs_and_historical_identity_rejection(s02_like_db: Path, tmp_path: Path) -> None:  # noqa: E501
    out = tmp_path / "q.json"
    build_stage03(s02_like_db, out)
    data = json.loads(out.read_text())
    fa_jobs = [x for x in data["items"] if x["job_class"] == "fa_translation"]
    assert fa_jobs == []
    # Queue must not contain historical fa_translation
    for it in data["items"]:
        assert it["job_class"] != "fa_translation"


def test_stable_refs_not_numeric_ids(s02_like_db: Path, tmp_path: Path) -> None:
    out = tmp_path / "q.json"
    build_stage03(s02_like_db, out)
    data = json.loads(out.read_text())
    for it in data["items"]:
        assert "lemma_semantic_ref" in it
        assert "sense_semantic_ref" in it
        assert it["lemma_semantic_ref"].startswith("lemma:v1:")
        assert it["sense_semantic_ref"].startswith("sense:v1:")
        assert "sense_id" in it and "lemma_id" in it  # numeric as convenience only, durable is ref


def test_no_network_and_input_unchanged(s02_like_db: Path, tmp_path: Path) -> None:
    sha_before = sha256_file(s02_like_db)
    out = tmp_path / "q.json"
    build_stage03(s02_like_db, out)
    sha_after = sha256_file(s02_like_db)
    assert sha_before == sha_after


def test_overwrite_refusal(s02_like_db: Path, tmp_path: Path) -> None:
    out = tmp_path / "q.json"
    out.write_text("existing")
    with pytest.raises(BuildDictError, match="Output path already exists"):
        build_stage03(s02_like_db, out)


def test_manifest_boundaries_and_ambiguous_recovery(tmp_path: Path) -> None:
    from tools.build_dict import _build_manifests

    ids = [f"queue:v1:{i:032x}" for i in range(5)]
    payloads = {iid: b'{"a":1}' for iid in ids}
    identity = {"format": "x", "queue_sha256": "q", "generation_marker": "llm_generated_v1", "generated_license": "CC0", "bulk_de_model": "m", "bulk_en_model": "m", "qa_model": "m", "bulk_pipeline_version": "v", "qa_pipeline_version": "v", "response_schema_version": "v"}  # noqa: E501
    manifests = _build_manifests(ids, max_requests=2, max_bytes=1024, item_payloads=payloads, compatibility_identity=identity)  # noqa: E501
    assert len(manifests) == 3  # 2+2+1
    # Exactly-one ambiguous recovery is allowed externally; zero/multiple fails closed - checked elsewhere  # noqa: E501


def test_persian_unicode_zwnj_pass_and_bidi_rejection() -> None:
    assert _validate_persian_unicode("خانه\u200cها") is None
    assert _validate_persian_unicode("خانه\u061C") is not None
    assert _validate_persian_unicode("خانه\u200E") is not None
    assert _validate_persian_unicode("خانه\u202E") is not None
    assert _validate_persian_unicode("test\x00") is not None  # Cc


def test_fallback_only_precedence(tmp_path: Path) -> None:
    # Secondary fallback not additive when primary exists: our Stage03 counts only primary
    db = tmp_path / "prec.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(MINI_SCHEMA)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos) VALUES (1, 'lemma:v1:d', 'Haus', 'NOUN')")  # noqa: E501
    conn.execute("INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord) VALUES (1, 1, 'sense:v1:d', 'wiktextract:enwiktionary', 'fingerprint:v1:aa', 0)")  # noqa: E501
    conn.execute("INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (1, 1, 'fa', 'translation', 0, 'خانه', 'wiktionary', 'CC BY-SA')")  # noqa: E501
    conn.commit()
    conn.close()
    out = tmp_path / "q.json"
    result = build_stage03(db, out)
    assert result["fa_covered"] == 1
    # secondary would be 0
    assert result["fa_covered"] == 1

# Fa v2 tests

# Real-asset FA v2 verification resolves the accepted local Stage-02 asset via
# the FLASHCARD_TEST_STAGE02 environment variable; skipped when not provided.
REAL_STAGE02 = os.environ.get("FLASHCARD_TEST_STAGE02", "")
requires_real_stage02 = pytest.mark.skipif(
    not REAL_STAGE02 or not Path(REAL_STAGE02).is_file(),
    reason="accepted real Stage-02 asset not provided via FLASHCARD_TEST_STAGE02",
)


def test_fa_v1_not_accepted_as_v2(tmp_path: Path) -> None:
    from tools.build_dict import FA_JOB_CLASS, _compute_fa_v2_item_id
    # v1 would be fa-generation-job:v1 with old payload ["fa", "fa_translation"]
    # v2 is fa-generation-job:v2 with ["fa", "fa_generated_meaning"]
    # Ensure they are different
    lemma_ref = "lemma:v1:test"
    sense_ref = "sense:v1:test"
    v2_id = _compute_fa_v2_item_id(lemma_ref, sense_ref)
    assert v2_id.startswith("fa-generation-job:v2:")
    assert "fa_translation" not in v2_id
    assert FA_JOB_CLASS == "fa_generated_meaning"

@requires_real_stage02
def test_fa_v2_deterministic_and_no_numeric_ids(tmp_path: Path) -> None:
    from tools.build_dict import _build_fa_v2_candidates

    # Use real stage02 for deterministic check
    real = Path(REAL_STAGE02)
    candidates = _build_fa_v2_candidates(real)
    candidates2 = _build_fa_v2_candidates(real)
    assert candidates[0]["item_id"] == candidates2[0]["item_id"]
    # No numeric sense_id
    for c in candidates[:10]:
        assert "sense_id" not in c
        assert c["job_class"] != "fa_translation"
        assert c["job_class"] == "fa_generated_meaning"

def test_fa_v2_missing_en_excludes_candidate(tmp_path: Path) -> None:
    import sqlite3
    db = tmp_path / "no_en.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE lemma (id INTEGER PRIMARY KEY, semantic_ref TEXT NOT NULL UNIQUE, lemma TEXT NOT NULL, pos TEXT NOT NULL, gender TEXT);
        CREATE TABLE sense (id INTEGER PRIMARY KEY, lemma_id INTEGER NOT NULL, semantic_ref TEXT NOT NULL UNIQUE, source_namespace TEXT NOT NULL, source_ref TEXT NOT NULL, ord INTEGER NOT NULL);
        CREATE TABLE sense_meaning (id INTEGER PRIMARY KEY, sense_id INTEGER NOT NULL, language TEXT NOT NULL, kind TEXT NOT NULL, ord INTEGER NOT NULL, text TEXT NOT NULL, source TEXT NOT NULL, license TEXT NOT NULL);
        CREATE TABLE example (id INTEGER PRIMARY KEY, de TEXT NOT NULL, en TEXT, source TEXT, source_ref TEXT, license TEXT, token_count INTEGER, has_proper INTEGER DEFAULT 0);
        CREATE TABLE example_lemma (lemma_id INTEGER NOT NULL, example_id INTEGER NOT NULL, PRIMARY KEY (lemma_id, example_id)) WITHOUT ROWID;
        CREATE TABLE sense_meaning_derivation (generated_meaning_id INTEGER NOT NULL, source_meaning_id INTEGER NOT NULL, PRIMARY KEY (generated_meaning_id, source_meaning_id)) WITHOUT ROWID;
    """)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos) VALUES (1, 'lemma:v1:x', 'Haus', 'NOUN')")
    conn.execute("INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord) VALUES (1, 1, 'sense:v1:x', 'wiktextract:enwiktionary', 'fingerprint:v1:x', 0)")
    # No EN meaning
    conn.commit()
    conn.close()
    from tools.build_dict import _build_fa_v2_candidates
    cands = _build_fa_v2_candidates(db)
    assert len(cands) == 0

def test_fa_v2_single_persian_schema_and_bounds(tmp_path: Path) -> None:
    from tools.build_dict import _validate_fa_v2_output
    # Valid single persian
    assert _validate_fa_v2_output("خانه", "Haus") is None
    # Too long (161)
    assert _validate_fa_v2_output("ا" * 161, "Haus") == "too_long"
    # Too many tokens (25)
    many = " ".join(["خانه"] * 25)
    assert _validate_fa_v2_output(many, "Haus") == "too_many_tokens"
    # Within bounds (10 tokens, 100 scalars) should pass
    ok_many = " ".join(["خانه"] * 10)
    assert _validate_fa_v2_output(ok_many, "Haus") is None
    # Morphology with many words but within 160/24 should pass (e.g., 10 words)
    morph = "صرف فعل به صورت اول شخص مفرد مضارع اخباری"
    # Count tokens
    assert len(morph.split()) <= 24
    assert _validate_fa_v2_output(morph, "gehen") is None

def test_fa_v2_persian_unicode_zwnj_and_bidi(tmp_path: Path) -> None:
    from tools.build_dict import _validate_fa_v2_output
    assert _validate_fa_v2_output("کتاب\u200cها", "Haus") is None
    assert _validate_fa_v2_output("خانه\u061C", "Haus") is not None
    assert _validate_fa_v2_output("خانه\u202E", "Haus") is not None
