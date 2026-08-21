"""Phase-A fake-transport tests for Stage 04 enrichment and provenance."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast
from urllib import request as urllib_request

import pytest

import tools.build_dict as build_dict
from tools.build_dict import (
    STAGE02_EXAMPLE_SCHEMA_SQL,
    STAGE04_CHECKPOINT_FORMAT,
    BuildDictError,
    _audit_item_ids,
    _checkpoint_identity,
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
        response[0]["api_key"] = "test-secret-must-not-persist"
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
    checkpoint_state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert checkpoint_state["bulk"]["completed"] == {}
    assert checkpoint_state["bulk"]["in_flight"]
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


def _logical_generated_rows(path: Path) -> list[tuple[str, str, str, str, str]]:
    with sqlite3.connect(path) as conn:
        return conn.execute(
            "SELECT s.semantic_ref, m.language, m.kind, m.text, m.license "
            "FROM sense_meaning m JOIN sense s ON s.id=m.sense_id "
            "WHERE m.source='llm_generated_v1' "
            "ORDER BY s.semantic_ref, m.language, m.kind, m.ord"
        ).fetchall()


def test_stage04_bulk_partial_checkpoint_resume_and_equivalence(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    checkpoint = tmp_path / "checkpoint.json"
    submitted: list[list[str]] = []
    calls = 0

    def interrupted(items: list[dict[str, object]]) -> list[dict[str, object]]:
        nonlocal calls
        calls += 1
        submitted.append([str(item["item_id"]) for item in items])
        if calls == 2:
            raise RuntimeError("deliberate interruption after first bounded unit")
        return _fake_candidates(items)

    with pytest.raises(RuntimeError, match="deliberate interruption"):
        run_stage04(
            database,
            queue,
            tmp_path / "interrupted.sqlite",
            checkpoint,
            "test-only",
            transport=interrupted,
            qa_transport=lambda candidates: candidates,
            batch_size=1,
        )
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    first_id, second_id = submitted[0][0], submitted[1][0]
    assert set(state["bulk"]["completed"]) == {first_id}
    assert state["bulk"]["in_flight"] == [second_id]
    with pytest.raises(BuildDictError, match="unresolved bulk"):
        run_stage04(
            database,
            queue,
            tmp_path / "must-not-resubmit.sqlite",
            checkpoint,
            "test-only",
            transport=lambda _items: pytest.fail("unresolved paid work was resubmitted"),
            qa_transport=lambda candidates: candidates,
            batch_size=1,
        )

    # A process can be interrupted immediately after its first atomic completion
    # checkpoint. That valid partial state is safely resumable and skips its ID.
    state["bulk"]["in_flight"] = []
    checkpoint.write_text(json.dumps(state), encoding="utf-8")
    resumed_submitted: list[str] = []

    def resumed_transport(items: list[dict[str, object]]) -> list[dict[str, object]]:
        resumed_submitted.extend(str(item["item_id"]) for item in items)
        return _fake_candidates(items)

    resumed = tmp_path / "resumed.sqlite"
    run_stage04(
        database,
        queue,
        resumed,
        checkpoint,
        "test-only",
        transport=resumed_transport,
        qa_transport=lambda candidates: candidates,
        batch_size=1,
    )
    assert first_id not in resumed_submitted

    uninterrupted = tmp_path / "uninterrupted.sqlite"
    run_stage04(
        database,
        queue,
        uninterrupted,
        tmp_path / "uninterrupted-checkpoint.json",
        "test-only",
        transport=_fake_candidates,
        qa_transport=lambda candidates: candidates,
        batch_size=3,
    )
    assert _logical_generated_rows(resumed) == _logical_generated_rows(uninterrupted)


def test_stage04_qa_partial_checkpoint_resume_and_independent_state(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    checkpoint = tmp_path / "checkpoint.json"
    submitted_qa: list[list[str]] = []
    qa_calls = 0

    def interrupted_qa(items: list[dict[str, object]]) -> list[dict[str, object]]:
        nonlocal qa_calls
        qa_calls += 1
        submitted_qa.append([str(item["item_id"]) for item in items])
        if qa_calls == 2:
            raise RuntimeError("deliberate QA interruption")
        return items

    def flagged_bulk(items: list[dict[str, object]]) -> list[dict[str, object]]:
        candidates = _fake_candidates(items)
        for candidate in candidates:
            if candidate["language"] == "de":
                candidate["text"] = (
                    "eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn"
                )
        return candidates

    with pytest.raises(RuntimeError, match="deliberate QA interruption"):
        run_stage04(
            database,
            queue,
            tmp_path / "interrupted.sqlite",
            checkpoint,
            "test-only",
            transport=flagged_bulk,
            qa_transport=interrupted_qa,
            batch_size=1,
        )
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    first_id, second_id = submitted_qa[0][0], submitted_qa[1][0]
    assert state["bulk"]["completed"]
    assert state["qa"]["required"]
    assert set(state["qa"]["completed"]) == {first_id}
    assert state["qa"]["in_flight"] == [second_id]
    with pytest.raises(BuildDictError, match="unresolved QA"):
        run_stage04(
            database,
            queue,
            tmp_path / "must-not-resubmit.sqlite",
            checkpoint,
            "test-only",
            transport=lambda _items: pytest.fail("bulk should already be complete"),
            qa_transport=lambda _items: pytest.fail("unresolved QA was resubmitted"),
            batch_size=1,
        )

    state["qa"]["in_flight"] = []
    checkpoint.write_text(json.dumps(state), encoding="utf-8")
    resumed_qa: list[str] = []

    def resumed_transport(items: list[dict[str, object]]) -> list[dict[str, object]]:
        resumed_qa.extend(str(item["item_id"]) for item in items)
        return items

    resumed = tmp_path / "resumed.sqlite"
    run_stage04(
        database,
        queue,
        resumed,
        checkpoint,
        "test-only",
        transport=lambda _items: pytest.fail("completed bulk was resubmitted"),
        qa_transport=resumed_transport,
        batch_size=1,
    )
    assert first_id not in resumed_qa

    uninterrupted = tmp_path / "uninterrupted.sqlite"
    run_stage04(
        database,
        queue,
        uninterrupted,
        tmp_path / "uninterrupted-checkpoint.json",
        "test-only",
        transport=flagged_bulk,
        qa_transport=lambda candidates: candidates,
        batch_size=2,
    )
    assert _logical_generated_rows(resumed) == _logical_generated_rows(uninterrupted)


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("generated_license", "other-classification"),
        ("bulk_pipeline_version", "bulk-v2"),
        ("qa_pipeline_version", "qa-v2"),
        ("provider_response_schema_version", "schema-v2"),
    ],
)
def test_stage04_checkpoint_identity_changes_fail_closed(
    queue_and_input: tuple[Path, Path], tmp_path: Path, keyword: str, value: str
) -> None:
    database, queue = queue_and_input
    checkpoint = tmp_path / "checkpoint.json"
    run_stage04(
        database,
        queue,
        tmp_path / "first.sqlite",
        checkpoint,
        "test-only",
        transport=_fake_candidates,
        qa_transport=lambda candidates: candidates,
    )
    with pytest.raises(BuildDictError, match="incompatible"):
        if keyword == "generated_license":
            run_stage04(
                database, queue, tmp_path / "second.sqlite", checkpoint, value,
                transport=_fake_candidates, qa_transport=lambda candidates: candidates,
            )
        elif keyword == "bulk_pipeline_version":
            run_stage04(
                database, queue, tmp_path / "second.sqlite", checkpoint, "test-only",
                transport=_fake_candidates, qa_transport=lambda candidates: candidates,
                bulk_pipeline_version=value,
            )
        elif keyword == "qa_pipeline_version":
            run_stage04(
                database, queue, tmp_path / "second.sqlite", checkpoint, "test-only",
                transport=_fake_candidates, qa_transport=lambda candidates: candidates,
                qa_pipeline_version=value,
            )
        else:
            run_stage04(
                database, queue, tmp_path / "second.sqlite", checkpoint, "test-only",
                transport=_fake_candidates, qa_transport=lambda candidates: candidates,
                provider_response_schema_version=value,
            )


def test_stage04_rejects_corrupt_partial_phase_state(
    queue_and_input: tuple[Path, Path], tmp_path: Path
) -> None:
    database, queue = queue_and_input
    queue_sha = sha256_file(queue)
    identity = _checkpoint_identity(
        queue_sha,
        "llm_generated_v1",
        "test-only",
        build_dict.STAGE04_DEFAULT_BULK_MODEL,
        build_dict.STAGE04_DEFAULT_QA_MODEL,
        build_dict.STAGE04_BULK_PIPELINE_VERSION,
        build_dict.STAGE04_QA_PIPELINE_VERSION,
        build_dict.STAGE04_PROVIDER_RESPONSE_SCHEMA_VERSION,
    )
    for phase in ("bulk", "qa"):
        checkpoint = tmp_path / f"corrupt-{phase}.json"
        state: dict[str, Any] = {
            "format": STAGE04_CHECKPOINT_FORMAT,
            "identity": identity,
            **build_dict._empty_checkpoint(),
        }
        state[phase]["in_flight"] = [123]
        checkpoint.write_text(json.dumps(state), encoding="utf-8")
        with pytest.raises(BuildDictError, match="invalid in-flight"):
            run_stage04(
                database,
                queue,
                tmp_path / f"{phase}.sqlite",
                checkpoint,
                "test-only",
                transport=_fake_candidates,
                qa_transport=lambda candidates: candidates,
            )


def test_stage04_fixture_mode_is_explicit_and_never_reads_openai_key(
    queue_and_input: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, queue = queue_and_input
    responses = tmp_path / "responses.json"
    responses.write_text(json.dumps(_fake_candidates(read_stage03_queue(queue))), encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-secret-must-not-be-read")
    monkeypatch.setattr(
        build_dict,
        "make_openai_transport",
        lambda *_args: pytest.fail("fixture mode constructed a live transport"),
    )
    assert build_dict.main(
        [
            "stage04", "--stage02", str(database), "--queue", str(queue), "--output",
            str(tmp_path / "fixture.sqlite"), "--checkpoint", str(tmp_path / "fixture.json"),
            "--generated-license", "test-only", "--bulk-model", "fixture-bulk", "--qa-model",
            "fixture-qa", "--responses", str(responses), "--qa-responses", str(responses),
        ]
    ) == 0
    assert (tmp_path / "fixture.sqlite").exists()
    monkeypatch.delenv("OPENAI_API_KEY")
    assert build_dict.main(
        [
            "stage04", "--transport", "openai", "--stage02", str(database), "--queue", str(queue),
            "--output", str(tmp_path / "no-live.sqlite"), "--checkpoint",
            str(tmp_path / "no-live.json"), "--generated-license", "test-only", "--bulk-model",
            "live-bulk", "--qa-model", "live-qa",
        ]
    ) == 1

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


def test_stage04_mocked_openai_live_mode_uses_structured_store_false_without_secret_leak(
    queue_and_input: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database, queue = queue_and_input
    observed_requests: list[tuple[urllib_request.Request, dict[str, Any]]] = []

    class FakeResponse:
        def __init__(self, body: dict[str, object]) -> None:
            self._body = json.dumps(body).encode("utf-8")

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self._body

    def fake_urlopen(request: urllib_request.Request, timeout: int) -> FakeResponse:
        assert timeout == 120
        body = request.data
        assert isinstance(body, bytes)
        payload = cast(dict[str, Any], json.loads(body.decode("utf-8")))
        observed_requests.append((request, payload))
        prompt = cast(dict[str, Any], json.loads(str(payload["input"])))
        records = prompt["items"]
        candidates = _fake_candidates(
            [cast(dict[str, object], record["queue_item"]) for record in records]
        )
        return FakeResponse({"output_text": json.dumps({"candidates": candidates})})

    secret = "test-secret-never-persist-or-report"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)
    output = tmp_path / "live-mocked.sqlite"
    checkpoint = tmp_path / "live-mocked.json"
    assert build_dict.main(
        [
            "stage04", "--transport", "openai", "--stage02", str(database), "--queue", str(queue),
            "--output", str(output), "--checkpoint", str(checkpoint), "--generated-license",
            "test-only", "--bulk-model", "configured-bulk", "--qa-model", "configured-qa",
            "--batch-size", "2", "--bulk-pipeline-version", "test-bulk-v1",
            "--qa-pipeline-version", "test-qa-v1", "--provider-response-schema-version",
            "test-schema-v1",
        ]
    ) == 0
    captured = capsys.readouterr()
    assert observed_requests
    assert all(payload["store"] is False for _request, payload in observed_requests)
    assert {str(payload["model"]) for _request, payload in observed_requests} == {
        "configured-bulk", "configured-qa"
    }
    for request, payload in observed_requests:
        assert request.get_header("Authorization") == f"Bearer {secret}"
        assert payload["text"]["format"]["type"] == "json_schema"
        assert payload["text"]["format"]["strict"] is True
    assert secret not in checkpoint.read_text(encoding="utf-8")
    assert secret not in output.read_bytes().decode("latin1")
    assert secret not in captured.out and secret not in captured.err
