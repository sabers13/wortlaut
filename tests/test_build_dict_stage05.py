"""Tests for copy-on-write Stage-05 dictionary packaging."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from tools.build_dict import (
    STAGE02_EXAMPLE_SCHEMA_SQL,
    BuildDictError,
    build_stage01,
    build_stage03,
    package_stage05,
    run_stage04,
    sha256_file,
    validate_stage05_database,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fake(items: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for item in items:
        language = str(item["target_language"])
        output.append(
            {
                "item_id": item["item_id"],
                "language": language,
                "kind": "translation" if language == "fa" else "definition",
                "text": {"de": "kurze Erklärung", "en": "short meaning", "fa": "معنی کوتاه"}[
                    language
                ],
                "derivation_input_ids": [],
            }
        )
    return output


def _fake_qa(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    return candidates


@pytest.fixture
def enriched(tmp_path: Path) -> Path:
    source = tmp_path / "stage02.sqlite"
    build_stage01(
        FIXTURES / "wiktextract_stage01_en.jsonl", FIXTURES / "wiktextract_stage01_de.jsonl", source
    )
    with sqlite3.connect(source) as conn:
        conn.executescript(STAGE02_EXAMPLE_SCHEMA_SQL)
    queue = tmp_path / "queue.jsonl"
    build_stage03(source, queue)
    target = tmp_path / "enriched.sqlite"
    run_stage04(
        source,
        queue,
        target,
        tmp_path / "checkpoint.json",
        "test-only",
        transport=_fake,
        qa_transport=_fake_qa,
    )
    return target


def test_stage05_packages_without_mutating_input(enriched: Path, tmp_path: Path) -> None:
    before = sha256_file(enriched)
    metadata = package_stage05(enriched, tmp_path / "package", "v1")
    package = tmp_path / "package" / "dictionary_v1.sqlite"
    assert package.exists()
    assert sha256_file(enriched) == before
    assert metadata["sha256"] == sha256_file(package)
    assert metadata["bytes"] == package.stat().st_size
    assert (
        json.loads((tmp_path / "package" / "dictionary_v1.metadata.json").read_text()) == metadata
    )
    with pytest.raises(BuildDictError, match="already exists"):
        package_stage05(enriched, tmp_path / "package", "v1")


def test_stage05_rejects_bad_attribution(enriched: Path) -> None:
    with sqlite3.connect(enriched) as conn:
        conn.execute(
            "UPDATE sense_meaning SET license='' WHERE id=(SELECT id FROM sense_meaning LIMIT 1)"
        )
    with pytest.raises(BuildDictError, match="bad localized attributions"):
        validate_stage05_database(enriched)


def _copy_without_semantic_ref_uniques(source: Path, target: Path) -> None:
    with sqlite3.connect(source) as conn:
        dump = "\n".join(conn.iterdump())
    with sqlite3.connect(target) as conn:
        conn.executescript(
            re.sub(r"semantic_ref\s+TEXT NOT NULL UNIQUE", "semantic_ref TEXT NOT NULL", dump)
        )


@pytest.mark.parametrize("table", ["lemma", "sense"])
def test_stage05_rejects_duplicate_semantic_refs_through_package_validation(
    enriched: Path, tmp_path: Path, table: str
) -> None:
    malformed = tmp_path / f"duplicate-{table}.sqlite"
    _copy_without_semantic_ref_uniques(enriched, malformed)
    with sqlite3.connect(malformed) as conn:
        first, second = conn.execute(
            f"SELECT id, semantic_ref FROM {table} ORDER BY id LIMIT 2"
        ).fetchall()
        conn.execute(f"UPDATE {table} SET semantic_ref=? WHERE id=?", (first[1], second[0]))
    with pytest.raises(BuildDictError, match="duplicate semantic refs"):
        package_stage05(malformed, tmp_path / f"package-{table}", "v1")


def test_stage05_rejects_blank_ref_and_malformed_generated_provenance(
    enriched: Path, tmp_path: Path
) -> None:
    malformed = tmp_path / "malformed.sqlite"
    malformed.write_bytes(enriched.read_bytes())
    with sqlite3.connect(malformed) as conn:
        generated_id, source_id = conn.execute(
            "SELECT g.id, s.id FROM sense_meaning g JOIN sense_meaning s ON s.sense_id=g.sense_id "
            "WHERE g.source='llm_generated_v1' AND s.source!='llm_generated_v1' LIMIT 1"
        ).fetchone()
        conn.execute(
            "INSERT INTO sense_meaning_derivation "
            "(generated_meaning_id, source_meaning_id) VALUES (?, ?)",
            (generated_id, source_id),
        )
        conn.execute("UPDATE sense_meaning SET source='llm_generated_v1' WHERE id=?", (source_id,))
        assert generated_id != source_id
    with pytest.raises(BuildDictError, match="invalid edges"):
        package_stage05(malformed, tmp_path / "bad-provenance", "v1")

    blank = tmp_path / "blank.sqlite"
    blank.write_bytes(enriched.read_bytes())
    with sqlite3.connect(blank) as conn:
        conn.execute("UPDATE lemma SET semantic_ref=' ' WHERE id=(SELECT MIN(id) FROM lemma)")
    with pytest.raises(BuildDictError, match="blank semantic refs"):
        package_stage05(blank, tmp_path / "blank-package", "v1")


def test_dockerfile_has_pinned_piper_prerequisite() -> None:
    dockerfile = (Path(__file__).parent.parent / "Dockerfile").read_text(encoding="utf-8")
    assert "piper-tts==1.6.0" in dockerfile
    assert "de_DE-thorsten-high" in dockerfile
    assert "8aaa3c9839d2b669cb57a94e1ec92ae0928897e8" in dockerfile
    assert "9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1" in dockerfile
    assert "sha256sum --check --status" in dockerfile
    assert "GPL-3.0-or-later" in dockerfile and "CC0" in dockerfile and "MIT" in dockerfile
    assert "importlib.metadata" in dockerfile
    assert "api/models/rhasspy/piper-voices/revision/${PIPER_VOICE_REV}" in dockerfile
