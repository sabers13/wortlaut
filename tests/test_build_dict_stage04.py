"""Phase-A fake-transport tests for Stage 04 enrichment and provenance."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.build_dict import (
    STAGE02_EXAMPLE_SCHEMA_SQL,
    BuildDictError,
    build_stage01,
    build_stage03,
    read_stage03_queue,
    run_stage04,
    sha256_file,
    validate_generated_derivations,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def queue_and_input(tmp_path: Path) -> tuple[Path, Path]:
    database = tmp_path / "stage02.sqlite"
    build_stage01(
        FIXTURES / "wiktextract_stage01_en.jsonl",
        FIXTURES / "wiktextract_stage01_de.jsonl",
        database,
    )
    with sqlite3.connect(database) as conn:
        conn.executescript(STAGE02_EXAMPLE_SCHEMA_SQL)
    queue = tmp_path / "queue.jsonl"
    build_stage03(database, queue)
    return database, queue


def _fake_candidates(items: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for item in items:
        language = str(item["target_language"])
        text = {"de": "einfache Erklärung", "en": "simple meaning", "fa": "معنی ساده"}[language]
        kind = {"de": "definition", "en": "definition", "fa": "translation"}[language]
        inputs = item["derivation_inputs"]
        if not isinstance(inputs, list):
            raise AssertionError("fixture queue has invalid derivation inputs")
        first_input: list[str] = []
        if inputs:
            if not isinstance(inputs[0], dict):
                raise AssertionError("fixture queue has invalid derivation input")
            first_input = [str(inputs[0]["input_id"])]
        result.append(
            {
                "item_id": item["item_id"],
                "language": language,
                "kind": kind,
                "text": text,
                "derivation_input_ids": first_input,
            }
        )
    return result


def test_stage04_fake_e2e_checkpoint_resume_and_rollback(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    before = sha256_file(database)
    calls: list[int] = []

    def transport(items: list[dict[str, object]]) -> list[dict[str, object]]:
        calls.append(len(items))
        return _fake_candidates(items)

    output = tmp_path / "enriched.sqlite"
    checkpoint = tmp_path / "ignored" / "checkpoint.json"

    def qa_transport(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
        return candidates

    results = run_stage04(
        database,
        queue,
        output,
        checkpoint,
        "test-only",
        transport=transport,
        qa_transport=qa_transport,
    )

    assert results["completed"] == len(read_stage03_queue(queue))
    assert results["qa_selected"] >= results["audit_selected"] >= 1
    assert calls[0] == results["completed"]
    assert sha256_file(database) == before
    with sqlite3.connect(output) as conn:
        generated = conn.execute(
            "SELECT count(*) FROM sense_meaning WHERE source='llm_generated_v1'"
        ).fetchone()[0]
        source_before = conn.execute(
            "SELECT count(*) FROM sense_meaning WHERE source!='llm_generated_v1'"
        ).fetchone()[0]
        assert generated == results["completed"]
        validate_generated_derivations(conn)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM sense_meaning WHERE source='llm_generated_v1'")
        assert conn.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT count(*) FROM sense_meaning WHERE source!='llm_generated_v1'"
            ).fetchone()[0]
            == source_before
        )

    resumed = tmp_path / "resumed.sqlite"
    run_stage04(
        database,
        queue,
        resumed,
        checkpoint,
        "test-only",
        transport=transport,
        qa_transport=qa_transport,
    )
    assert calls == [results["completed"]]


def test_stage04_fails_closed_on_corrupt_checkpoint_and_generated_lineage(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text("not json", encoding="utf-8")
    with pytest.raises(BuildDictError, match="checkpoint is corrupt"):
        run_stage04(
            database,
            queue,
            tmp_path / "out.sqlite",
            checkpoint,
            "test-only",
            transport=_fake_candidates,
        )

    enriched = tmp_path / "enriched.sqlite"
    checkpoint.unlink()
    run_stage04(
        database,
        queue,
        enriched,
        checkpoint,
        "test-only",
        transport=_fake_candidates,
        qa_transport=lambda candidates: candidates,
    )
    with sqlite3.connect(enriched) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        generated_id = conn.execute(
            "SELECT id FROM sense_meaning WHERE source='llm_generated_v1' LIMIT 1"
        ).fetchone()[0]
        conn.execute(
            "UPDATE sense_meaning SET source='llm_generated_v2' WHERE id=?", (generated_id,)
        )
        source_id = conn.execute(
            "SELECT source_meaning_id FROM sense_meaning_derivation LIMIT 1"
        ).fetchone()[0]
        conn.execute("UPDATE sense_meaning SET source='llm_generated_v1' WHERE id=?", (source_id,))
        with pytest.raises(BuildDictError, match="invalid edges"):
            validate_generated_derivations(conn)
