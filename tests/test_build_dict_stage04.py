"""Phase-A fake-transport tests for Stage 04 enrichment and provenance."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.build_dict import (
    STAGE02_EXAMPLE_SCHEMA_SQL,
    BuildDictError,
    _audit_item_ids,
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
        conn.execute(
            "DELETE FROM sense_meaning WHERE language='en' AND sense_id=(SELECT MIN(id) FROM sense)"
        )
        conn.execute("DELETE FROM sense_meaning WHERE sense_id=(SELECT MAX(id) FROM sense)")
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


def test_stage04_persists_de_en_fa_with_exact_and_zero_derivations(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    items = read_stage03_queue(queue)
    missing_en = next(item for item in items if item["job_class"] == "missing_en")
    zero_edge = next(item for item in items if not item["derivation_inputs"])
    output = tmp_path / "enriched.sqlite"
    run_stage04(
        database,
        queue,
        output,
        tmp_path / "checkpoint.json",
        "test-only-license",
        transport=_fake_candidates,
        qa_transport=lambda candidates: candidates,
    )
    with sqlite3.connect(output) as conn:
        generated = conn.execute(
            "SELECT language, kind, source, license FROM sense_meaning "
            "WHERE source='llm_generated_v1'"
        ).fetchall()
        assert {row[0] for row in generated} == {"de", "en", "fa"}
        assert all(row[2:] == ("llm_generated_v1", "test-only-license") for row in generated)
        missing_sense = str(missing_en["sense_semantic_ref"])
        assert (
            conn.execute(
                "SELECT count(*) FROM sense_meaning m JOIN sense s ON s.id=m.sense_id "
                "WHERE s.semantic_ref=? AND m.language='en' AND m.kind='definition' "
                "AND m.source='llm_generated_v1'",
                (missing_sense,),
            ).fetchone()[0]
            == 1
        )
        zero_sense = str(zero_edge["sense_semantic_ref"])
        assert (
            conn.execute(
                "SELECT count(*) FROM sense_meaning_derivation d JOIN sense_meaning m "
                "ON m.id=d.generated_meaning_id JOIN sense s ON s.id=m.sense_id "
                "WHERE s.semantic_ref=? AND m.language=?",
                (zero_sense, zero_edge["target_language"]),
            ).fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0] == sum(
            1 for item in items if item["derivation_inputs"]
        )


def test_stage04_rejects_implicit_network_and_secret_bearing_provider_payload(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    with pytest.raises(BuildDictError, match="No Stage 04 transport"):
        run_stage04(
            database,
            queue,
            tmp_path / "no-transport.sqlite",
            tmp_path / "no-transport.json",
            "test-only",
        )

    checkpoint = tmp_path / "checkpoint.json"

    def secret_transport(items: list[dict[str, object]]) -> list[dict[str, object]]:
        response = _fake_candidates(items)
        response[0]["api_key"] = "sk-this-must-not-persist-0123456789"
        return response

    with pytest.raises(BuildDictError, match="structured schema"):
        run_stage04(
            database,
            queue,
            tmp_path / "secret.sqlite",
            checkpoint,
            "test-only",
            transport=secret_transport,
            qa_transport=lambda candidates: candidates,
        )
    assert not checkpoint.exists()
    assert not (tmp_path / "secret.sqlite").exists()


def test_stage04_routes_all_suspicious_and_reproducible_audit_item_ids(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    items = read_stage03_queue(queue)
    selected_runs: list[set[str]] = []

    def suspicious_transport(input_items: list[dict[str, object]]) -> list[dict[str, object]]:
        response = _fake_candidates(input_items)
        for item, candidate in zip(input_items, response, strict=True):
            if item["target_language"] == "de":
                candidate["text"] = (
                    "eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn"
                )
        return response

    def qa_transport(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
        selected_runs.append({str(candidate["item_id"]) for candidate in candidates})
        return candidates

    for index in range(2):
        run_stage04(
            database,
            queue,
            tmp_path / f"run-{index}.sqlite",
            tmp_path / f"checkpoint-{index}.json",
            "test-only",
            transport=suspicious_transport,
            qa_transport=qa_transport,
        )
    item_ids = [str(item["item_id"]) for item in items]
    expected_audit = _audit_item_ids(item_ids, sha256_file(queue))
    suspicious = {str(item["item_id"]) for item in items if item["target_language"] == "de"}
    assert selected_runs[0] == selected_runs[1]
    assert suspicious <= selected_runs[0]
    assert expected_audit <= selected_runs[0]


def test_stage04_rejects_incompatible_checkpoint_and_invalid_persian(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    checkpoint = tmp_path / "checkpoint.json"
    run_stage04(
        database,
        queue,
        tmp_path / "first.sqlite",
        checkpoint,
        "test-only",
        bulk_model="first-bulk",
        transport=_fake_candidates,
        qa_transport=lambda candidates: candidates,
    )
    with pytest.raises(BuildDictError, match="incompatible"):
        run_stage04(
            database,
            queue,
            tmp_path / "second.sqlite",
            checkpoint,
            "test-only",
            bulk_model="second-bulk",
            transport=_fake_candidates,
            qa_transport=lambda candidates: candidates,
        )

    def bad_persian(items: list[dict[str, object]]) -> list[dict[str, object]]:
        response = _fake_candidates(items)
        next(candidate for candidate in response if candidate["language"] == "fa")["text"] = (
            "not Persian"
        )
        return response

    with pytest.raises(BuildDictError, match="lacks Persian script"):
        run_stage04(
            database,
            queue,
            tmp_path / "bad.sqlite",
            tmp_path / "bad-checkpoint.json",
            "test-only",
            transport=bad_persian,
            qa_transport=lambda candidates: candidates,
        )
