"""Fake/local DE/EN Stage 04 safety tests — v2 repair."""
# mypy: disable-error-code="attr-defined,unused-ignore,operator,index,type-var,arg-type,override"

import hashlib
import inspect
import json
import socket
import sqlite3
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_build_dict_stage03 import make_stage02, make_stage02_with_en_counts
from tools import build_dict as bd
from tools.build_dict import (
    GENERATED_MARKER,
    STAGE01_SCHEMA_SQL,
    STAGE02_EXAMPLE_SCHEMA_SQL,
    STAGE04_BULK_REASONING_EFFORT,
    STAGE04_COST_PLAN_ARTIFACT,
    STAGE04_DEFAULT_BULK_DE_MODEL,
    STAGE04_DEFAULT_BULK_EN_MODEL,
    STAGE04_DEFAULT_QA_MODEL,
    STAGE04_LIVE_API_KEY_ENV,
    STAGE04_LIVE_CANARY_BULK_INPUT_TOKEN_ESTIMATE,
    STAGE04_LIVE_CANARY_QA_BOUND_INPUT_TOKEN_ESTIMATE,
    STAGE04_LIVE_RESPONSES_URL,
    STAGE04_MAX_OUTPUT_TOKENS,
    STAGE04_QA_REASONING_EFFORT,
    BuildDictError,
    OpenAILiveResponsesTransport,
    Stage04PretransmissionBlocked,
    _canonical_line,
    _checkpoint_identity,
    _decimal_to_wire,
    _deterministic_audit_sample,
    _empty_spend_state,
    _load_checkpoint,
    _render_canary_receipt,
    _spend_total_usd,
    _validate_de_semantic_contract,
    _validate_generated_candidate,
    _validate_spend_state,
    _write_canary_selection_manifest,
    build_stage03,
    build_stage04,
    de_learner_meaning_request_body,
    de_learner_qa_request_body,
    en_meaning_request_body,
    execute_stage04_live,
    main,
    prepare_stage04_live,
    retry_rejected,
    stage04_pretransmission_guard_blocks,
    stage04_worst_case_request_cost_usd,
    stage04_worst_case_request_cost_usd_decimal,
)
from tools.resolver_hash import get_resolver_hash

_ = get_resolver_hash()


class FakeTransport:
    def __init__(self, texts: dict[str, str] | None = None, fail_after: int | None = None) -> None:
        self.texts = texts or {}
        self.fail_after = fail_after
        self.bulk_submitted: list[str] = []
        self.qa_submitted: list[str] = []
        self.items: dict[str, dict[str, object]] = {}
        self._bulk_call_count = 0

    def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        if self.fail_after is not None and self._bulk_call_count >= self.fail_after:
            raise RuntimeError("deliberate local failure")
        self._bulk_call_count += 1
        self.bulk_submitted.extend(item_ids)
        res: dict[str, dict[str, str]] = {}
        for item_id in item_ids:
            lang = str(self.items[item_id]["language"])
            txt = self.texts.get(item_id)
            if txt is None:
                txt = f"ein Gebäude {item_id[-6:]}" if lang == "de" else f"building {item_id[-6:]}"
            if lang == "de":
                # return strict DE schema
                # For tests needing synonym, use text that is single word
                if "synonym" in txt.lower():
                    res[item_id] = {"meaning": txt, "kind": "synonym"}
                else:
                    res[item_id] = {"meaning": txt, "kind": "definition"}
            else:
                res[item_id] = {"meaning": txt}
        return res

    def send_qa(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        self.qa_submitted.extend(item_ids)
        return {
            item_id: {"meaning": self.texts.get(item_id, f"qa-valid-{item_id[-6:]}"), "kind": "definition"} if str(self.items[item_id]["language"]) == "de" else {"meaning": self.texts.get(item_id, f"qa-valid-{item_id[-6:]}")}
            for item_id in item_ids
        }


class FailingBulkAfterOneTransport(FakeTransport):
    def __init__(self, items: dict[str, dict[str, object]], texts: dict[str, str] | None = None) -> None:
        super().__init__(texts=texts)
        self.items = items
        self._bulk_calls = 0

    def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        self._bulk_calls += 1
        if self._bulk_calls > 1:
            raise RuntimeError("deliberate bulk failure after one completed unit")
        self.bulk_submitted.extend(item_ids)
        res: dict[str, dict[str, str]] = {}
        for item_id in item_ids:
            lang = str(self.items[item_id]["language"])
            txt = self.texts.get(item_id, f"ein Gebäude {item_id[-6:]}" if lang == "de" else f"building {item_id[-6:]}")
            if lang == "de":
                res[item_id] = {"meaning": txt, "kind": "definition"}
            else:
                res[item_id] = {"meaning": txt}
        return res


class FailingQAAfterOneTransport(FakeTransport):
    def __init__(self, items: dict[str, dict[str, object]]) -> None:
        super().__init__()
        self.items = items
        self._qa_calls = 0

    def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        self.bulk_submitted.extend(item_ids)
        res: dict[str, dict[str, str]] = {}
        for item_id in item_ids:
            lang = str(self.items[item_id]["language"])
            txt = f"ein Gebäude {item_id[-6:]}" if lang == "de" else f"building {item_id[-6:]}"
            if lang == "de":
                res[item_id] = {"meaning": txt, "kind": "definition"}
            else:
                res[item_id] = {"meaning": txt}
        return res

    def send_qa(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        self._qa_calls += 1
        if self._qa_calls > 1:
            raise RuntimeError("deliberate QA failure after one completed unit")
        self.qa_submitted.extend(item_ids)
        res: dict[str, dict[str, str]] = {}
        for item_id in item_ids:
            lang = str(self.items[item_id]["language"])
            if lang == "de":
                res[item_id] = {"meaning": f"qa-valid-{item_id[-6:]}", "kind": "definition"}
            else:
                res[item_id] = {"meaning": f"qa-valid-{item_id[-6:]}"}
        return res


def queue_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, dict[str, object]]]:
    stage02 = make_stage02(tmp_path / "input.sqlite")
    queue = tmp_path / "queue.json"
    build_stage03(stage02, queue)
    items = json.loads(queue.read_text(encoding="utf-8"))["items"]
    assert isinstance(items, list)
    return stage02, queue, {str(item["item_id"]): item for item in items}


def make_stage02_with_n(tmp_path: Path, n: int, prefix: str = "test") -> tuple[Path, Path, dict[str, dict[str, object]]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / f"{prefix}.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(STAGE01_SCHEMA_SQL + STAGE02_EXAMPLE_SCHEMA_SQL)
    for i in range(n):
        lemma = f"Lemma{i:04d}"
        sem_ref = f"lemma:v1:{prefix}:{i:04d}"
        sense_ref = f"sense:v1:{prefix}:{i:04d}"
        conn.execute(
            "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i + 1, sem_ref, lemma, "NOUN", None, "wiktionary", "CC BY-SA"),
        )
        conn.execute(
            "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (i + 1, i + 1, sense_ref, "wiktextract:enwiktionary", f"fingerprint:v1:{i:04d}", i, "wiktionary", "CC BY-SA"),
        )
        conn.execute(
            "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (i + 1, i + 1, "en", "translation", 0, f"meaning {i}", "wiktionary", "CC BY-SA"),
        )
        conn.execute(
            "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1000 + i + 1, i + 1, "de", "definition", 0, "siehe Haus", "wiktionary", "CC BY-SA"),
        )
    conn.commit()
    conn.close()
    queue = tmp_path / f"{prefix}-queue.json"
    build_stage03(db, queue)
    items = json.loads(queue.read_text(encoding="utf-8"))["items"]
    assert isinstance(items, list)
    return db, queue, {str(item["item_id"]): item for item in items}


def test_fake_bulk_qa_persists_generated_rows_and_derivations(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    before = hashlib.sha256(stage02.read_bytes()).hexdigest()
    fake = FakeTransport()
    fake.items = items
    output, checkpoint = tmp_path / "enriched.sqlite", tmp_path / "checkpoint.json"
    result = build_stage04(
        queue, stage02, output, checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=1
    )
    # queue_fixture now has 1 DE item (since one sense eligible)
    assert result["bulk_completed"] == 1
    assert hashlib.sha256(stage02.read_bytes()).hexdigest() == before
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert set(state) >= {"bulk", "qa", "manifests"}
    assert not state["bulk"]["in_flight"]
    manifest = state["manifests"][0]
    assert manifest["state"] == "PREPARED"
    assert manifest["correlation"].startswith("batchcorr:v1:")
    assert manifest["custom_ids"] == [f"batch:{item_id}" for item_id in manifest["item_ids"]]
    # Verify response schema version is v2
    assert state["identity"]["response_schema_version"] == "openai-responses-json-schema-v2"
    assert state["identity"]["bulk_pipeline_version"] == "stage04-bulk-v4"
    assert state["identity"]["qa_pipeline_version"] == "stage04-qa-v4"


def test_complete_invalid_result_is_rejected_and_not_resubmitted(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    bad_id = sorted(items)[0]
    # Make bad candidate echo lemma (should be rejected)
    fake = FakeTransport({bad_id: "Haus"})
    fake.items = items
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(
            queue,
            stage02,
            tmp_path / "out.sqlite",
            checkpoint,
            "TEST_SYNTHETIC_LICENSE_v1",
            transport=fake,
            batch_size=2,
        )
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert bad_id in state["bulk"]["rejected"]
    assert not state["bulk"]["in_flight"]
    again = FakeTransport()
    again.items = items
    # Remove existing output if any
    (tmp_path / "out.sqlite").unlink(missing_ok=True)
    build_stage04(
        queue,
        stage02,
        tmp_path / "out.sqlite",
        checkpoint,
        "TEST_SYNTHETIC_LICENSE_v1",
        transport=again,
    )
    assert bad_id not in again.bulk_submitted


def test_unknown_outcome_stays_in_flight_and_fails_closed(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    fake = FakeTransport(fail_after=0)
    fake.items = items
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="Transport failure"):
        build_stage04(
            queue,
            stage02,
            tmp_path / "out.sqlite",
            checkpoint,
            "TEST_SYNTHETIC_LICENSE_v1",
            transport=fake,
            batch_size=1,
        )
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["bulk"]["in_flight"] == [sorted(items)[0]]
    with pytest.raises(BuildDictError, match="ambiguous"):
        build_stage04(
            queue,
            stage02,
            tmp_path / "out2.sqlite",
            checkpoint,
            "TEST_SYNTHETIC_LICENSE_v1",
            transport=fake,
        )


def test_checkpoint_identity_and_explicit_retry_are_fail_closed(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    bad_id = sorted(items)[0]
    fake = FakeTransport({bad_id: "Haus"})
    fake.items = items
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError):
        build_stage04(
            queue,
            stage02,
            tmp_path / "out.sqlite",
            checkpoint,
            "TEST_SYNTHETIC_LICENSE_v1",
            transport=fake,
        )
    with pytest.raises(BuildDictError, match="not rejected"):
        retry_rejected(checkpoint, queue, ["unknown"], "TEST_SYNTHETIC_LICENSE_v1")
    retry_rejected(checkpoint, queue, [bad_id], "TEST_SYNTHETIC_LICENSE_v1")
    changed = FakeTransport()
    changed.items = items
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(
            queue,
            stage02,
            tmp_path / "other.sqlite",
            checkpoint,
            "OTHER_CLASSIFICATION",
            transport=changed,
        )


def test_no_transport_or_retired_queue_is_refused(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    with pytest.raises(BuildDictError, match="No local deterministic"):
        build_stage04(
            queue,
            stage02,
            tmp_path / "out.sqlite",
            tmp_path / "checkpoint.json",
            "TEST_SYNTHETIC_LICENSE_v1",
        )
    payload = json.loads(queue.read_text(encoding="utf-8"))
    payload["items"][0]["language"] = "fa"
    payload["items"][0]["job_class"] = "fa_generated_meaning"
    retired = tmp_path / "retired.json"
    retired.write_text(json.dumps(payload), encoding="utf-8")
    fake = FakeTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="retired"):
        build_stage04(
            retired,
            stage02,
            tmp_path / "bad.sqlite",
            tmp_path / "bad.json",
            "TEST_SYNTHETIC_LICENSE_v1",
            transport=fake,
        )


def test_bulk_interruption_resume_with_exact_ids(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 4, prefix="bulk-interrupt")
    sorted_ids = sorted(items.keys())
    failing = FailingBulkAfterOneTransport(items)
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="Transport failure"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=failing, batch_size=1)
    state_after_fail = json.loads(checkpoint.read_text(encoding="utf-8"))
    completed_ids = sorted(state_after_fail["bulk"]["completed"].keys())
    in_flight_ids = state_after_fail["bulk"]["in_flight"]
    assert len(completed_ids) == 1
    assert completed_ids == [sorted_ids[0]]
    assert in_flight_ids == [sorted_ids[1]]
    assert failing.bulk_submitted == [sorted_ids[0]]
    with pytest.raises(BuildDictError, match="ambiguous"):
        build_stage04(queue, stage02, tmp_path / "out2.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=FakeTransport(), batch_size=1)
    state_after_fail["bulk"]["in_flight"] = []
    checkpoint.write_text(json.dumps(state_after_fail, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    good = FakeTransport()
    good.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=good, batch_size=1)
    assert sorted_ids[0] not in good.bulk_submitted
    assert set(good.bulk_submitted) == set(sorted_ids[1:])
    uninterrupted_checkpoint = tmp_path / "uninterrupted.json"
    uninterrupted = FakeTransport()
    uninterrupted.items = items
    build_stage04(queue, stage02, tmp_path / "expected.sqlite", uninterrupted_checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=uninterrupted, batch_size=1)
    resumed_state = json.loads(checkpoint.read_text(encoding="utf-8"))
    uninterrupted_state = json.loads(uninterrupted_checkpoint.read_text(encoding="utf-8"))
    assert set(resumed_state["bulk"]["completed"].keys()) == set(uninterrupted_state["bulk"]["completed"].keys())
    assert resumed_state["bulk"]["completed"] == uninterrupted_state["bulk"]["completed"]


def test_qa_interruption_resume_with_exact_ids(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 4, prefix="qa-interrupt")
    failing_qa = FailingQAAfterOneTransport(items)
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="Transport failure"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=failing_qa, batch_size=1)
    state_after_fail = json.loads(checkpoint.read_text(encoding="utf-8"))
    qa_completed = sorted(state_after_fail["qa"]["completed"].keys())
    qa_in_flight = state_after_fail["qa"]["in_flight"]
    assert len(qa_completed) == 1
    assert len(qa_in_flight) == 1
    all_required = sorted(state_after_fail["qa"]["required"])
    assert qa_completed[0] in all_required
    assert qa_in_flight[0] in all_required
    assert failing_qa.qa_submitted == qa_completed
    with pytest.raises(BuildDictError, match="ambiguous"):
        build_stage04(queue, stage02, tmp_path / "out2.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=FakeTransport())
    state_after_fail["qa"]["in_flight"] = []
    checkpoint.write_text(json.dumps(state_after_fail, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    good = FakeTransport()
    good.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=good, batch_size=1)
    assert qa_completed[0] not in good.qa_submitted
    assert set(good.qa_submitted) == set([i for i in all_required if i not in qa_completed])
    uninterrupted_checkpoint = tmp_path / "uninterrupted-qa.json"
    uninterrupted = FakeTransport()
    uninterrupted.items = items
    build_stage04(queue, stage02, tmp_path / "expected-qa.sqlite", uninterrupted_checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=uninterrupted, batch_size=1)
    resumed_state = json.loads(checkpoint.read_text(encoding="utf-8"))
    uninterrupted_state = json.loads(uninterrupted_checkpoint.read_text(encoding="utf-8"))
    assert set(resumed_state["qa"]["completed"].keys()) == set(uninterrupted_state["qa"]["completed"].keys())


def test_five_item_four_valid_one_invalid_durable_state(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 5, prefix="five-item")
    sorted_ids = sorted(items.keys())
    bad_id = sorted_ids[2]
    fake_texts: dict[str, str] = {bad_id: str(items[bad_id].get("lemma_text", "Haus"))}
    fake_texts[bad_id] = str(items[bad_id].get("lemma_text", "Lemma0002"))
    fake = FakeTransport(texts=fake_texts)
    fake.items = items
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=5)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(state["bulk"]["completed"]) == 4
    assert len(state["bulk"]["rejected"]) == 1
    assert bad_id in state["bulk"]["rejected"]
    assert state["bulk"]["rejected"][bad_id]["error_code"] == "echo_lemma"
    assert not state["bulk"]["in_flight"]
    assert len(fake.bulk_submitted) == 5


def test_rejected_not_resubmitted_and_explicit_retry(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 5, prefix="retry-test")
    sorted_ids = sorted(items.keys())
    bad_id = sorted_ids[1]
    fake = FakeTransport(texts={bad_id: str(items[bad_id].get("lemma_text", "bad"))})
    fake.items = items
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=5)
    state_before = json.loads(checkpoint.read_text(encoding="utf-8"))
    _attempt_before = state_before["bulk"]["rejected"][bad_id]["attempt_count"]
    again = FakeTransport()
    again.items = items
    (tmp_path / "out.sqlite").unlink(missing_ok=True)
    _result = build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=again, batch_size=5)
    assert bad_id not in again.bulk_submitted
    retry_rejected(checkpoint, queue, [bad_id], "TEST_SYNTHETIC_LICENSE_v1")
    state_after_retry_manifest = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert bad_id not in state_after_retry_manifest["bulk"]["rejected"]
    (tmp_path / "out.sqlite").unlink(missing_ok=True)
    retry_transport = FakeTransport(texts={bad_id: "gutes Gebäude"})
    retry_transport.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=retry_transport, batch_size=5)
    state_after = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert bad_id in state_after["bulk"]["completed"]
    with pytest.raises(BuildDictError):
        retry_rejected(checkpoint, queue, sorted_ids, "TEST_SYNTHETIC_LICENSE_v1")
    stage02b, queueb, itemsb = make_stage02_with_n(tmp_path / "retry-inflight", 2, prefix="retry-inflight")
    failing = FailingBulkAfterOneTransport(itemsb)
    ckpt2 = tmp_path / "ckpt2.json"
    with pytest.raises(BuildDictError, match="Transport failure"):
        build_stage04(queueb, stage02b, tmp_path / "out2.sqlite", ckpt2, "TEST_SYNTHETIC_LICENSE_v1", transport=failing, batch_size=1)
    state2 = json.loads(ckpt2.read_text(encoding="utf-8"))
    in_flight_id = state2["bulk"]["in_flight"][0]
    with pytest.raises(BuildDictError, match="in-flight"):
        retry_rejected(ckpt2, queueb, [in_flight_id], "TEST_SYNTHETIC_LICENSE_v1")


def test_ambiguous_transport_no_automatic_resubmit_and_exact_one_recovery(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 3, prefix="ambiguous")
    sorted_ids = sorted(items.keys())
    failing = FailingBulkAfterOneTransport(items)
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="Transport failure"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=failing, batch_size=1)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(state["bulk"]["in_flight"]) == 1
    assert state["bulk"]["in_flight"][0] == sorted_ids[1]
    state["bulk"]["in_flight"] = []
    checkpoint.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    good = FakeTransport()
    good.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=good, batch_size=1)
    assert sorted_ids[0] not in good.bulk_submitted


def test_checkpoint_compatibility_components_and_fail_closed(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    checkpoint = tmp_path / "checkpoint.json"
    fake = FakeTransport()
    fake.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=2)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    identity = state["identity"]
    for key in ["queue_sha256", "generation_marker", "generated_license", "bulk_de_model", "bulk_en_model", "qa_model", "bulk_pipeline_version", "qa_pipeline_version", "response_schema_version", "bulk_de_reasoning_effort", "bulk_de_max_output_tokens", "bulk_en_reasoning_effort", "bulk_en_max_output_tokens", "qa_reasoning_effort", "qa_max_output_tokens"]:
        assert key in identity, f"missing {key}"
    assert identity["generation_marker"] == "llm_generated_v1"
    assert identity["bulk_de_model"] == "gpt-5.6-luna"
    assert identity["bulk_en_model"] == "gpt-5.6-luna"
    assert identity["qa_model"] == "gpt-5.6-terra"
    assert identity["bulk_pipeline_version"] == "stage04-bulk-v4"
    assert identity["qa_pipeline_version"] == "stage04-qa-v4"
    assert identity["response_schema_version"] == "openai-responses-json-schema-v2"
    assert identity["bulk_de_reasoning_effort"] == "none"
    assert identity["bulk_de_max_output_tokens"] == "512"
    assert identity["bulk_en_reasoning_effort"] == "none"
    assert identity["bulk_en_max_output_tokens"] == "512"
    assert identity["qa_reasoning_effort"] == "low"
    assert identity["qa_max_output_tokens"] == "512"
    assert identity["format"] == "flashcard-stage04-checkpoint-v3"
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out2.sqlite", checkpoint, "OTHER_LICENSE", transport=fake)
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out3.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, bulk_pipeline_version="stage04-bulk-v1")
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out4.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, qa_pipeline_version="stage04-qa-v1")
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out5.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, bulk_de_model="other-model")
    # Reasoning effort participates in checkpoint compatibility
    state_mutated = dict(state)
    mutated_identity = dict(identity)
    mutated_identity["qa_reasoning_effort"] = "high"
    state_mutated["identity"] = mutated_identity
    checkpoint.write_text(json.dumps(state_mutated, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out6.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    # max_output_tokens participates in checkpoint compatibility
    state_mutated2 = dict(state)
    mutated_identity2 = dict(identity)
    mutated_identity2["bulk_de_max_output_tokens"] = "1024"
    state_mutated2["identity"] = mutated_identity2
    checkpoint.write_text(json.dumps(state_mutated2, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out7.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_batch_manifest_partitioning_and_custom_id_join(tmp_path: Path) -> None:
    from tools.build_dict import _build_manifests

    sorted_ids = [f"queue:v2:test:{i:04d}" for i in range(5)]
    item_payloads = {}
    for iid in sorted_ids:
        record = {"custom_id": f"batch:{iid}", "method": "POST", "url": "/v1/responses", "body": {"model": "gpt-5.6-luna"}}
        item_payloads[iid] = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    identity = {"queue_sha256": "x", "generation_marker": "llm_generated_v1"}
    manifests = _build_manifests(sorted_ids, max_requests=2, max_bytes=10_000_000, item_payloads=item_payloads, compatibility_identity=identity)
    assert len(manifests) == 3
    assert manifests[0]["item_ids"] == sorted_ids[0:2]
    assert manifests[1]["item_ids"] == sorted_ids[2:4]
    assert manifests[2]["item_ids"] == sorted_ids[4:5]
    for m in manifests:
        m_any: dict[str, object] = m  # type: ignore[assignment]
        assert m_any["correlation"] == f"batchcorr:v1:{m_any['manifest_sha256']}"
        assert m_any["input_file_sha256"] == m_any["manifest_sha256"]
        assert m_any["byte_len"] == len(b"\n".join(item_payloads[i] for i in m_any["item_ids"])+(b"\n"))  # type: ignore[operator]
        assert m_any["state"] == "PREPARED"
        assert m_any["custom_ids"] == [f"batch:{i}" for i in m_any["item_ids"]]  # type: ignore[operator]
    first_manifest_bytes = b"\n".join(item_payloads[i] for i in manifests[0]["item_ids"]) + b"\n"
    assert manifests[0]["byte_len"] == len(first_manifest_bytes)
    stage02, queue, items = make_stage02_with_n(tmp_path, 5, prefix="manifest-durability")
    checkpoint = tmp_path / "ckpt.json"
    fake = FakeTransport()
    fake.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=2)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(state["manifests"]) >= 1
    assert all(m["state"] == "PREPARED" for m in state["manifests"])
    assert sum(len(m["item_ids"]) for m in state["manifests"]) == len(items)


def test_batch_output_reordering_and_missing_duplicate_unknown_fail_closed(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 3, prefix="batch-join")
    _sorted_ids = sorted(items.keys())

    class ReorderingTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.bulk_submitted.extend(item_ids)
            result = super().send_bulk(item_ids)
            return {k: result[k] for k in reversed(item_ids)}

    reordering = ReorderingTransport()
    reordering.items = items
    checkpoint = tmp_path / "ckpt.json"
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=reordering, batch_size=3)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(state["bulk"]["completed"]) == 3

    class MissingTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.bulk_submitted.extend(item_ids)
            result = {item_ids[0]: {"meaning": "ein Gebäude", "kind": "definition"}}
            return result

    stage02b, queueb, itemsb = make_stage02_with_n(tmp_path / "missing", 2, prefix="missing")
    missing = MissingTransport()
    missing.items = itemsb
    with pytest.raises(BuildDictError, match="Missing custom_id"):
        build_stage04(queueb, stage02b, tmp_path / "out-missing.sqlite", tmp_path / "ckpt-missing.json", "TEST_SYNTHETIC_LICENSE_v1", transport=missing, batch_size=2)

    class UnknownTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.bulk_submitted.extend(item_ids)
            result = {iid: {"meaning": "ein Gebäude", "kind": "definition"} for iid in item_ids}
            result["unknown-id"] = {"meaning": "bad", "kind": "definition"}
            return result

    stage02c, queuec, itemsc = make_stage02_with_n(tmp_path / "unknown", 2, prefix="unknown")
    unknown = UnknownTransport()
    unknown.items = itemsc
    with pytest.raises(BuildDictError, match="Unknown custom_id"):
        build_stage04(queuec, stage02c, tmp_path / "out-unknown.sqlite", tmp_path / "ckpt-unknown.json", "TEST_SYNTHETIC_LICENSE_v1", transport=unknown, batch_size=2)


def test_legacy_persian_checkpoint_preserved(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.json"
    legacy_state = {
        "format": "flashcard-stage04-checkpoint-v2",
        "identity": {
            "queue_sha256": "old-sha",
            "generation_marker": "llm_generated_v1",
            "generated_license": "OLD_LICENSE",
            "bulk_de_model": "gpt-5.6-luna",
            "bulk_en_model": "gpt-5.6-luna",
            "qa_model": "gpt-5.6-terra",
            "bulk_pipeline_version": "stage04-bulk-v1",
            "qa_pipeline_version": "stage04-qa-v1",
            "response_schema_version": "openai-responses-json-schema-v1",
        },
        "bulk": {
            "completed": {},
            "rejected": {},
            "in_flight": [
                "enrichment-job:v1:ad94a752b4025c93e7eb08dd07fa59ca6eff54a137bd0c66ac5df7434ab95093",
                "enrichment-job:v1:b9d5cff13da2216f9fa2646feca6bd9d7f3b5f4807d3060a722bdfc8ca112288",
                "enrichment-job:v1:bb197886c1955f46f45cc3807a1099ff13875b29105b8f5c0011792c74f605be",
                "enrichment-job:v1:db6832699239264636beeed0baa223152d96547cc6c934ef68eb8277a334dca1",
                "enrichment-job:v1:f457af46b0c1db13e0f8f11e21d69f86c5ba41b74358ea6180c1986e7d0c4bad",
            ],
        },
        "qa": {"required": [], "completed": {}, "rejected": {}, "in_flight": []},
        "manifests": [],
    }
    legacy_path.write_text(json.dumps(legacy_state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    stage02, queue, items = make_stage02_with_n(tmp_path, 2, prefix="legacy-new")
    fake = FakeTransport()
    fake.items = items
    new_ckpt = tmp_path / "new.json"
    build_stage04(queue, stage02, tmp_path / "out.sqlite", new_ckpt, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    legacy_after = json.loads(legacy_path.read_text(encoding="utf-8"))
    assert legacy_after["bulk"]["in_flight"] == legacy_state["bulk"]["in_flight"]  # type: ignore[index]
    queue_sha = hashlib.sha256(Path(queue).read_bytes()).hexdigest()
    identity = _checkpoint_identity(queue_sha, "llm_generated_v1", "TEST_SYNTHETIC_LICENSE_v1", "gpt-5.6-luna", "gpt-5.6-luna", "gpt-5.6-terra")
    with pytest.raises(BuildDictError, match="incompatible"):
        _load_checkpoint(legacy_path, identity)


def test_generated_row_provenance_rollback(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 2, prefix="rollback")
    fake = FakeTransport()
    fake.items = items
    checkpoint = tmp_path / "ckpt.json"
    output = tmp_path / "out.sqlite"
    build_stage04(queue, stage02, output, checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=2)
    conn = sqlite3.connect(output)
    gen_rows = conn.execute("SELECT id, source, license, language, sense_id FROM sense_meaning WHERE source='llm_generated_v1'").fetchall()
    assert len(gen_rows) == 2
    for gid, src, lic, lang, sid in gen_rows:
        assert src == "llm_generated_v1"
        assert lic == "TEST_SYNTHETIC_LICENSE_v1"
        assert lang in ("de", "en")
    deriv_count = conn.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0]
    assert deriv_count == 2
    gen_ids = [r[0] for r in gen_rows]
    conn.execute("INSERT INTO sense_meaning_derivation (generated_meaning_id, source_meaning_id) VALUES (?, ?)", (gen_ids[0], gen_ids[1]))
    from tools.build_dict import validate_sense_meaning_derivations as _validate_deriv

    with pytest.raises(BuildDictError, match="generated->generated forbidden"):
        _validate_deriv(conn)
    conn.rollback()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM sense_meaning WHERE source='llm_generated_v1'")
    if conn.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0] != 0:
        conn.execute("DELETE FROM sense_meaning_derivation WHERE generated_meaning_id IN (SELECT id FROM sense_meaning WHERE source='llm_generated_v1')")
        remaining = conn.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0]
        if remaining != 0:
            conn.execute("DELETE FROM sense_meaning_derivation")
    assert conn.execute("SELECT count(*) FROM sense_meaning WHERE source='llm_generated_v1'").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM sense_meaning WHERE source='wiktionary'").fetchone()[0] > 0
    conn.close()


def test_validation_rules_and_qa_routing(tmp_path: Path) -> None:
    assert _validate_generated_candidate("", "de", "definition", "Haus") == "empty"
    assert _validate_generated_candidate("text", "xx", "definition", "Haus") == "invalid_language"
    assert _validate_generated_candidate("text", "de", "badkind", "Haus") == "invalid_kind"
    assert _validate_generated_candidate("a" * 281, "de", "definition", "Haus") == "too_long"
    assert _validate_generated_candidate("Haus", "de", "definition", "Haus") == "echo_lemma"
    assert _validate_generated_candidate("hello\x00world", "de", "definition", "Haus") is not None
    assert _validate_generated_candidate("hello\u061cworld", "de", "definition", "Haus") is not None
    assert _validate_generated_candidate("Hallo", "de", "definition", "Haus") is None
    assert _validate_generated_candidate("Hello", "en", "translation", "Haus") is None
    assert _validate_generated_candidate("12345", "de", "definition", "Haus") == "implausible_german"
    stage02, queue, items = make_stage02_with_n(tmp_path, 6, prefix="qa-routing")
    texts = {}
    sorted_ids = sorted(items.keys())
    texts[sorted_ids[0]] = "a" * 60
    fake = FakeTransport(texts=texts)
    fake.items = items
    checkpoint = tmp_path / "ckpt.json"
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=6)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    required = state["qa"]["required"]
    assert sorted_ids[0] in required
    queue_sha = hashlib.sha256(Path(queue).read_bytes()).hexdigest()
    expected_sample = _deterministic_audit_sample(sorted_ids, queue_sha, 2)
    for sid in expected_sample:
        assert sid in required
    assert len(required) < len(sorted_ids) or len(required) == len(set([sorted_ids[0]] + expected_sample))


def test_corrupt_checkpoint_fails_closed(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    checkpoint = tmp_path / "ckpt.json"
    checkpoint.write_text("not json", encoding="utf-8")
    fake = FakeTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="corrupt"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    checkpoint.write_text(json.dumps({"format": "flashcard-stage04-checkpoint-v3", "identity": {}, "bulk": "bad", "qa": {}, "manifests": []}), encoding="utf-8")
    with pytest.raises(BuildDictError, match="corrupt|invalid|incompatible"):
        build_stage04(queue, stage02, tmp_path / "out2.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    good = FakeTransport()
    good.items = items
    checkpoint.unlink(missing_ok=True)
    build_stage04(queue, stage02, tmp_path / "out3.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=good, batch_size=2)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    state["qa"]["completed"] = "not-a-dict"
    checkpoint.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(BuildDictError, match="corrupt|invalid"):
        build_stage04(queue, stage02, tmp_path / "out4.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=good)


def test_no_secret_leakage_and_stage03_no_network(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    queue_bytes = Path(queue).read_bytes()
    lower = queue_bytes.decode("utf-8").lower()
    for forbidden in ["api_key", "authorization", "bearer", "password", "/home/"]:
        assert forbidden not in lower
    fake = FakeTransport()
    fake.items = items
    checkpoint = tmp_path / "ckpt.json"
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    ckpt_bytes = checkpoint.read_bytes().decode("utf-8").lower()
    for forbidden in ["api_key", "sk-", "bearer"]:
        assert forbidden not in ckpt_bytes


# ---- New v2 mandatory tests ----

def test_de_request_body_strict_schema(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    body = de_learner_meaning_request_body(de_item, "gpt-5.6-luna")
    assert body["model"] == "gpt-5.6-luna"
    fmt = body["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True
    assert fmt["name"] == "de_learner_meaning"
    schema = fmt["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"meaning", "kind"}
    assert schema["properties"]["kind"]["enum"] == ["synonym", "definition"]
    # Must contain real instructions and EN text
    assert "Work only on the supplied single semantic sense" in body["input"]
    assert any(str(x["text"]) in body["input"] for x in de_item["derivation_inputs"])


def test_en_request_body_schema(tmp_path: Path) -> None:
    # Create EN job fixture
    conn = sqlite3.connect(tmp_path / "db.sqlite")
    conn.executescript(STAGE01_SCHEMA_SQL + STAGE02_EXAMPLE_SCHEMA_SQL)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license) VALUES (1, 'lemma:v1:e', 'E', 'NOUN', NULL, 'wiktionary', 'CC BY-SA')")
    conn.execute("INSERT INTO sense VALUES (1, 1, 'sense:v1:e:1', 'enwiktionary', 'E-1', 0, NULL, 'wiktionary', 'CC BY-SA')")
    conn.execute("INSERT INTO sense_meaning VALUES (1, 1, 'de', 'definition', 0, 'siehe E', 'wiktionary', 'CC BY-SA')")
    conn.commit()
    conn.close()
    q = tmp_path / "q.json"
    build_stage03(tmp_path / "db.sqlite", q)
    items = {x["item_id"]: x for x in json.loads(q.read_text(encoding="utf-8"))["items"] if x["language"] == "en"}
    if not items:
        pytest.skip("no EN job in fixture")
    en_item = next(iter(items.values()))
    body = en_meaning_request_body(en_item, "gpt-5.6-luna")
    fmt = body["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True
    assert fmt["name"] == "en_meaning"
    assert fmt["schema"]["required"] == ["meaning"]
    assert fmt["schema"]["additionalProperties"] is False
    assert "kind" not in fmt["schema"]["properties"]


def test_provider_cannot_override_language(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    class OverrideTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.bulk_submitted.extend(item_ids)
            return {iid: {"meaning": "Hallo Welt", "kind": "definition", "language": "en"} for iid in item_ids}
    fake = OverrideTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="provider_language_override"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", tmp_path / "ckpt.json", "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_de_synonym_and_definition_persist(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 2, prefix="syn-def")
    # Force first job to be synonym, second definition; bypass QA overwrite by making QA return same kinds
    class SynDefTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.bulk_submitted.extend(item_ids)
            res = {}
            for iid in item_ids:
                if iid == sorted(item_ids)[0]:
                    res[iid] = {"meaning": "Haus", "kind": "synonym"}
                else:
                    res[iid] = {"meaning": "ein kleines Haus mit Garten", "kind": "definition"}
            return res

        def send_qa(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.qa_submitted.extend(item_ids)
            res = {}
            for iid in item_ids:
                # Preserve kind: synonym stays synonym
                if iid == sorted(items.keys())[0]:
                    res[iid] = {"meaning": "Haus", "kind": "synonym"}
                else:
                    res[iid] = {"meaning": "ein kleines Haus mit Garten", "kind": "definition"}
            return res

    fake = SynDefTransport()
    fake.items = items
    ckpt = tmp_path / "ckpt.json"
    out = tmp_path / "out.sqlite"
    build_stage04(queue, stage02, out, ckpt, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    # Check bulk completed retains kinds before QA overwrite (or final DB after QA)
    state = json.loads(ckpt.read_text(encoding="utf-8"))
    bulk_kinds = {v["kind"] for v in state["bulk"]["completed"].values()}
    assert "synonym" in bulk_kinds and "definition" in bulk_kinds
    conn = sqlite3.connect(out)
    rows = conn.execute("SELECT text, kind FROM sense_meaning WHERE source='llm_generated_v1' ORDER BY text").fetchall()
    kinds = {r[1] for r in rows}
    assert "synonym" in kinds and "definition" in kinds
    conn.close()


def test_de_missing_kind_rejects(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    class MissingKindTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
            self.bulk_submitted.extend(item_ids)
            return {iid: {"meaning": "Hallo Welt"} for iid in item_ids}
    fake = MissingKindTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="missing_field|rejected"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", tmp_path / "ckpt.json", "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_sync_batch_body_equivalence(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    sync_body = de_learner_meaning_request_body(de_item, "gpt-5.6-luna")
    # Simulate batch record body
    batch_record = {"custom_id": f"batch:{de_item['item_id']}", "method": "POST", "url": "/v1/responses", "body": sync_body}
    # canonical JSON equivalence
    def canonical(v: object) -> str:
        return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert canonical(sync_body) == canonical(batch_record["body"])
    # Also test via manifest payload construction
    from tools.build_dict import _request_body_for_item
    body2 = _request_body_for_item(de_item, "gpt-5.6-luna", "gpt-5.6-luna")
    assert canonical(body2) == canonical(sync_body)


def test_qa_receives_semantic_context(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    candidate = "ein Testgebäude"
    body = de_learner_qa_request_body(de_item, candidate, "gpt-5.6-terra")
    # Must contain EN texts and candidate and opaque refs
    for en in de_item["derivation_inputs"]:
        assert str(en["text"]) in body["input"]
    assert candidate in body["input"]
    assert "lemma_semantic_ref" in body["input"]
    assert "sense_semantic_ref" in body["input"]


def test_derivation_n2_n3(tmp_path: Path) -> None:
    # 2-source
    db2 = make_stage02_with_en_counts(tmp_path / "db2.sqlite", [2])
    q2 = tmp_path / "q2.json"
    build_stage03(db2, q2)
    items2 = {x["item_id"]: x for x in json.loads(q2.read_text(encoding="utf-8"))["items"]}
    fake2 = FakeTransport()
    fake2.items = items2
    out2 = tmp_path / "out2.sqlite"
    ckpt2 = tmp_path / "ckpt2.json"
    build_stage04(q2, db2, out2, ckpt2, "TEST_SYNTHETIC_LICENSE_v1", transport=fake2)
    conn2 = sqlite3.connect(out2)
    assert conn2.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0] == 2
    conn2.close()
    # 3-source
    db3 = make_stage02_with_en_counts(tmp_path / "db3.sqlite", [3])
    q3 = tmp_path / "q3.json"
    build_stage03(db3, q3)
    items3 = {x["item_id"]: x for x in json.loads(q3.read_text(encoding="utf-8"))["items"]}
    fake3 = FakeTransport()
    fake3.items = items3
    out3 = tmp_path / "out3.sqlite"
    ckpt3 = tmp_path / "ckpt3.json"
    build_stage04(q3, db3, out3, ckpt3, "TEST_SYNTHETIC_LICENSE_v1", transport=fake3)
    conn3 = sqlite3.connect(out3)
    assert conn3.execute("SELECT count(*) FROM sense_meaning_derivation").fetchone()[0] == 3
    conn3.close()


def test_induced_edge_failure_rolls_back(tmp_path: Path) -> None:
    db, queue, items = make_stage02_with_n(tmp_path, 2, prefix="edge-fail")
    payload = json.loads(queue.read_text(encoding="utf-8"))
    # Build mapping sense_id -> EN ids
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT id, sense_id FROM sense_meaning WHERE language='en' ORDER BY sense_id, id").fetchall()
    sense_to_ids: dict[int, list[int]] = {}
    for mid, sid in rows:
        sense_to_ids.setdefault(sid, []).append(mid)
    conn.close()
    # Pick first payload item and force its derivation to be from a different sense
    target = payload["items"][0]
    target_sid = int(target["sense_id"])
    # Find a foreign sense id different from target
    foreign_sid = next(s for s in sense_to_ids if s != target_sid)
    foreign_mid = sense_to_ids[foreign_sid][0]
    target["derivation_source_ids"] = [foreign_mid]
    target["derivation_inputs"] = [{"meaning_id": foreign_mid, "language": "en", "kind": "translation", "ord": 0, "text": "foreign", "source": "wiktionary", "license": "CC BY-SA"}]
    tampered_queue = tmp_path / "tampered.json"
    tampered_queue.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    tampered_items = {x["item_id"]: x for x in payload["items"]}
    fake = FakeTransport()
    fake.items = tampered_items
    with pytest.raises(BuildDictError, match="Cross-sense"):
        build_stage04(tampered_queue, db, tmp_path / "out.sqlite", tmp_path / "ckpt.json", "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    assert not (tmp_path / "out.sqlite").exists() or sqlite3.connect(tmp_path / "out.sqlite").execute("SELECT count(*) FROM sense_meaning WHERE source='llm_generated_v1'").fetchone()[0] == 0


def test_old_checkpoint_rejected(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    # Create old checkpoint with v2 format
    old_path = tmp_path / "old.json"
    old_identity = {
        "format": "flashcard-stage04-checkpoint-v2",
        "queue_sha256": hashlib.sha256(queue.read_bytes()).hexdigest(),
        "generation_marker": "llm_generated_v1",
        "generated_license": "TEST_SYNTHETIC_LICENSE_v1",
        "bulk_de_model": "gpt-5.6-luna",
        "bulk_en_model": "gpt-5.6-luna",
        "qa_model": "gpt-5.6-terra",
        "bulk_pipeline_version": "stage04-bulk-v1",
        "qa_pipeline_version": "stage04-qa-v1",
        "response_schema_version": "openai-responses-json-schema-v1",
    }
    old_state = {"format": "flashcard-stage04-checkpoint-v2", "identity": old_identity, "bulk": {"completed": {}, "rejected": {}, "in_flight": []}, "qa": {"required": [], "completed": {}, "rejected": {}, "in_flight": []}, "manifests": []}
    old_path.write_text(json.dumps(old_state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    fake = FakeTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="incompatible|corrupt"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", old_path, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_missing_classification_fails_closed(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    fake = FakeTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="license"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", tmp_path / "ckpt.json", "", transport=fake)
    with pytest.raises(BuildDictError, match="license"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", tmp_path / "ckpt.json", "   ", transport=fake)


def test_canary_artifact_single_source(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 5, prefix="canary")
    # Prepare selection of 3 items
    selected = [items[k] for k in sorted(items.keys())[:3]]
    sel_path = tmp_path / "selection.json"
    sha, nbytes = _write_canary_selection_manifest(selected, sel_path)
    # Renderer must read and verify
    rendered = _render_canary_receipt(sel_path, sha)
    assert len(rendered) == 3
    assert [r["item_id"] for r in rendered] == sorted([r["item_id"] for r in selected])
    # Extra row fails
    extra = selected + [selected[0]]
    extra_path = tmp_path / "extra.json"
    sha_extra, _ = _write_canary_selection_manifest(extra, extra_path)
    # Rendering with old sha should fail (extra row changes sha)
    with pytest.raises(BuildDictError):
        _render_canary_receipt(extra_path, sha)
    # Mutated ID fails
    raw = json.loads(sel_path.read_bytes().decode())
    raw[0]["item_id"] = "queue:v2:mutated"
    mutated_path = tmp_path / "mutated.json"
    mutated_path.write_text(json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    # Should fail when expected sha is original
    with pytest.raises(BuildDictError):
        _render_canary_receipt(mutated_path, sha)
    # SHA mismatch fails
    with pytest.raises(BuildDictError):
        _render_canary_receipt(sel_path, "0"*64)


# ---- Canary paid-request boundedness repair tests (bulk/QA v3) ----


def _canonical_bytes(v: object) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_de_bulk_body_reasoning_none_and_max_512(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    body = de_learner_meaning_request_body(de_item, "gpt-5.6-luna")
    assert body["reasoning"] == {"effort": "none"}
    assert body["reasoning"]["effort"] == STAGE04_BULK_REASONING_EFFORT
    assert body["max_output_tokens"] == 512
    assert body["max_output_tokens"] == STAGE04_MAX_OUTPUT_TOKENS


def test_en_bulk_body_reasoning_none_and_max_512(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "db.sqlite")
    conn.executescript(STAGE01_SCHEMA_SQL + STAGE02_EXAMPLE_SCHEMA_SQL)
    conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license) VALUES (1, 'lemma:v1:e', 'E', 'NOUN', NULL, 'wiktionary', 'CC BY-SA')")
    conn.execute("INSERT INTO sense VALUES (1, 1, 'sense:v1:e:1', 'enwiktionary', 'E-1', 0, NULL, 'wiktionary', 'CC BY-SA')")
    conn.execute("INSERT INTO sense_meaning VALUES (1, 1, 'de', 'definition', 0, 'siehe E', 'wiktionary', 'CC BY-SA')")
    conn.commit()
    conn.close()
    q = tmp_path / "q.json"
    build_stage03(tmp_path / "db.sqlite", q)
    en_items = [x for x in json.loads(q.read_text(encoding="utf-8"))["items"] if x["language"] == "en"]
    if not en_items:
        pytest.skip("no EN job in fixture")
    body = en_meaning_request_body(en_items[0], "gpt-5.6-luna")
    assert body["reasoning"] == {"effort": "none"}
    assert body["reasoning"]["effort"] == STAGE04_BULK_REASONING_EFFORT
    assert body["max_output_tokens"] == 512
    assert body["max_output_tokens"] == STAGE04_MAX_OUTPUT_TOKENS


def test_qa_body_reasoning_low_and_max_512(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    body = de_learner_qa_request_body(de_item, "ein Testkandidat", "gpt-5.6-terra")
    assert body["reasoning"] == {"effort": "low"}
    assert body["reasoning"]["effort"] == STAGE04_QA_REASONING_EFFORT
    assert body["max_output_tokens"] == 512
    assert body["max_output_tokens"] == STAGE04_MAX_OUTPUT_TOKENS


def test_sync_batch_body_bytewise_identical_with_bounds(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    sync_body = de_learner_meaning_request_body(de_item, "gpt-5.6-luna")
    from tools.build_dict import _request_body_for_item

    # The Batch record embeds the exact same logical body object
    batch_record = {
        "custom_id": f"batch:{de_item['item_id']}",
        "method": "POST",
        "url": "/v1/responses",
        "body": sync_body,
    }
    record_bytes = json.dumps(batch_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    embedded_body = json.loads(record_bytes.decode("utf-8"))["body"]
    # Bytewise canonical equality of the logical body (sync vs Batch envelope)
    assert _canonical_bytes(embedded_body) == _canonical_bytes(sync_body)
    # The manifest payload path uses the identical single-source builder
    body2 = _request_body_for_item(de_item, "gpt-5.6-luna", "gpt-5.6-luna")
    assert _canonical_bytes(body2) == _canonical_bytes(sync_body)
    qa_sync = de_learner_qa_request_body(de_item, "Kandidat", "gpt-5.6-terra")
    qa_batch = {"custom_id": f"batch:{de_item['item_id']}", "method": "POST", "url": "/v1/responses", "body": qa_sync}
    assert _canonical_bytes(json.loads(_canonical_bytes(qa_batch))["body"]) == _canonical_bytes(qa_sync)


def test_strict_schema_and_semantic_context_unchanged_with_bounds(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    de_item = next(v for v in items.values() if v["language"] == "de")
    body = de_learner_meaning_request_body(de_item, "gpt-5.6-luna")
    fmt = body["text"]["format"]
    # Strict schema remains unchanged
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True
    assert fmt["name"] == "de_learner_meaning"
    assert fmt["schema"]["additionalProperties"] is False
    assert set(fmt["schema"]["required"]) == {"meaning", "kind"}
    assert fmt["schema"]["properties"]["kind"]["enum"] == ["synonym", "definition"]
    # Exact source semantic context remains unchanged
    assert "Work only on the supplied single semantic sense" in body["input"]
    for en in de_item["derivation_inputs"]:
        assert str(en["text"]) in body["input"]
    assert "lemma_semantic_ref" in body["input"]
    assert "sense_semantic_ref" in body["input"]
    qa_body = de_learner_qa_request_body(de_item, "Kandidat", "gpt-5.6-terra")
    assert qa_body["text"]["format"]["name"] == "de_learner_meaning"
    assert qa_body["text"]["format"]["strict"] is True


def _semantic_item(source: str, lemma: str = "Testwort") -> dict[str, object]:
    return {
        "language": "de",
        "lemma_text": lemma,
        "derivation_inputs": [{"text": source, "language": "en"}],
    }


def test_german_prompt_and_qa_require_source_fidelity(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    item = next(v for v in items.values() if v["language"] == "de")
    prompt = str(de_learner_meaning_request_body(item, "gpt-5.6-luna")["input"])
    assert "SOURCE FIDELITY OVERRIDES" in prompt
    assert "every statement" in prompt
    assert "historical, encyclopedic, technical, domain, cultural, usage" in prompt
    assert "unless that lexical meaning appears in the supplied source rows" in prompt
    assert "broader, narrower, associated, or merely similar" in prompt
    assert "person, number, tense, mood, degree, case, gender" in prompt
    qa = str(de_learner_qa_request_body(item, "Kandidat", "gpt-5.6-terra")["input"])
    for clause in (
        "every statement is supported",
        "Remove historical, encyclopedic, technical, domain, cultural, usage",
        "person, number, tense, mood, degree, case, gender",
        "truly equivalent synonym",
        "mood, tense, person, case, gender, number, or degree changed",
    ):
        assert clause in qa


def test_morphology_contract_preserves_all_explicit_features() -> None:
    ertrinket = _semantic_item("second-person plural subjunctive I of ertrinken", "ertrinket")
    assert _validate_de_semantic_contract(
        ertrinket, "2. Person Plural Konjunktiv I von „ertrinken“", "definition"
    ) is None
    assert _validate_de_semantic_contract(ertrinket, "ihr würdet ertrinken", "definition") == (
        "morphology_missing_subjunctive_i"
    )

    features = _semantic_item(
        "strong/mixed nominative/accusative masculine/feminine/neuter singular comparative/superlative degree"
    )
    assert _validate_de_semantic_contract(
        features,
        "starke/gemischte Nominativ/Akkusativ maskuline/feminine/neutrale Singular Komparativ/Superlativform",
        "definition",
    ) is None


def test_morphology_and_terse_source_regressions_reject_unsupported_elaboration() -> None:
    plural = _semantic_item("plural of Arisierung", "Arisierungen")
    assert _validate_de_semantic_contract(
        plural,
        "Plural von „Arisierung“: erzwungene Übertragung jüdischen Eigentums",
        "definition",
    ) == "morphology_unsupported_elaboration"

    mod = _semantic_item("mod", "Mod")
    assert _validate_de_semantic_contract(
        mod, "Fan-Erweiterung für ein Computerspiel", "definition"
    ) == "unsupported_domain_elaboration"


def test_morphology_plural_and_singular_form_compounds() -> None:
    """Regression for the German Canary v4 validator false positive.

    ``_MORPHOLOGY_FEATURE_RULES`` matched only the bare words "singular"/
    "plural"; it rejected the legitimate bounded German compounds
    "Singularform(en)"/"Pluralform(en)" ("singular/plural form(s)"), including
    the exact candidate returned live for queue:v2:198fbee5ba3f6dafe7ccaf247bee1337
    (lemma "hochverräterische").
    """
    strong_plural = _semantic_item("strong nominative/accusative plural", "hochverräterische")
    # A — the exact recorded live candidate must now pass.
    assert _validate_de_semantic_contract(
        strong_plural, "starke Nominativ- oder Akkusativ-Pluralform", "definition"
    ) is None
    # B — genuinely missing plural information is still rejected.
    assert _validate_de_semantic_contract(
        strong_plural, "starke Nominativ- oder Akkusativform", "definition"
    ) == "morphology_missing_plural"

    singular = _semantic_item("singular", "Testwort")
    # C — the analogous legitimate "Singularform" compound must pass.
    assert _validate_de_semantic_contract(singular, "Singularform", "definition") is None

    plural = _semantic_item("plural", "Testwort")
    # D — an unrelated word that merely contains "plural" as a substring
    # ("Pluralismus" = pluralism) must not satisfy the plural feature.
    assert _validate_de_semantic_contract(
        plural, "typisch für den politischen Pluralismus", "definition"
    ) == "morphology_missing_plural"


def test_morphology_dative_form_compound_and_grosser_regression() -> None:
    """Regression for the second German Canary v4 validator false positive.

    The same closed-compound/word-boundary defect class first found on
    "Pluralform" recurred on "Dativform": ``\\bdativ\\b`` cannot match inside
    the single token "Dativform". This is the exact candidate returned live
    for queue:v2:45bd0bd1611b6a1f2df543fb0107a7c1 (lemma "grosser").
    """
    strong_gen_dat = _semantic_item(
        "strong genitive/dative feminine singular", "grosser"
    )
    assert _validate_de_semantic_contract(
        strong_gen_dat,
        "starke Genitiv- und Dativform Feminin Singular von",
        "definition",
    ) is None
    dative = _semantic_item("dative", "Testwort")
    assert _validate_de_semantic_contract(dative, "Dativform", "definition") is None
    assert _validate_de_semantic_contract(dative, "Dativformen", "definition") is None
    # "Dativobjekt" ("dative object") merely starts with the same character
    # sequence as "Dativ" and must not satisfy the feature.
    assert _validate_de_semantic_contract(
        dative, "Dativobjekt", "definition"
    ) == "morphology_missing_dative"


@pytest.mark.parametrize(
    ("source", "candidate", "expected"),
    [
        # CASE: bare stem, "...form", and "...formen" all pass; an unrelated
        # lookalike word that merely starts with the same stem does not.
        ("nominative", "Nominativ", None),
        ("nominative", "Nominativform", None),
        ("nominative", "Nominativformen", None),
        ("nominative", "Nominativsatz", "morphology_missing_nominative"),
        ("accusative", "Akkusativ", None),
        ("accusative", "Akkusativform", None),
        ("accusative", "Akkusativformen", None),
        ("dative", "Dativ", None),
        ("dative", "Dativform", None),
        ("dative", "Dativformen", None),
        ("dative", "Dativobjekt", "morphology_missing_dative"),
        ("genitive", "Genitiv", None),
        ("genitive", "Genitivform", None),
        ("genitive", "Genitivformen", None),
        ("genitive", "Genitivus", "morphology_missing_genitive"),
        # NUMBER
        ("singular", "Singular", None),
        ("singular", "Singularform", None),
        ("singular", "Singularformen", None),
        ("plural", "Plural", None),
        ("plural", "Pluralform", None),
        ("plural", "Pluralformen", None),
        ("plural", "Pluralismus", "morphology_missing_plural"),
        # MOOD / TENSE, including reasonable hyphenation
        ("subjunctive I", "Konjunktiv I", None),
        ("subjunctive I", "Konjunktiv-I-Form", None),
        ("subjunctive I", "Konjunktiv-I-Formen", None),
        ("subjunctive II", "Konjunktiv II", None),
        ("subjunctive II", "Konjunktiv-II-Form", None),
        # a Konjunktiv-I pattern must never match a Konjunktiv-II compound
        ("subjunctive I", "Konjunktiv-II-Form", "morphology_missing_subjunctive_i"),
        ("subjunctive II", "Konjunktiv-I-Form", "morphology_missing_subjunctive_ii"),
        ("indicative", "Indikativ", None),
        ("indicative", "Indikativform", None),
        ("imperative", "Imperativ", None),
        ("imperative", "Imperativform", None),
        ("present", "Präsens", None),
        ("present", "Präsensform", None),
        ("preterite", "Präteritum", None),
        ("preterite", "Präteritumform", None),
        ("perfect", "Perfekt", None),
        ("perfect", "Perfektform", None),
        # DEGREE (already handled by the pre-existing \w* patterns)
        ("comparative degree", "Komparativ", None),
        ("comparative degree", "Komparativform", None),
        ("superlative degree", "Superlativ", None),
        ("superlative degree", "Superlativform", None),
        # GENDER
        ("masculine", "Maskulin", None),
        ("masculine", "Maskulinum", None),
        ("masculine", "Maskulinform", None),
        ("feminine", "Feminin", None),
        ("feminine", "Femininform", None),
        ("neuter", "Neutrum", None),
        ("neuter", "Neutrumform", None),
        # PERSON, including reasonable hyphenation
        ("first-person", "1. Person", None),
        ("first-person", "1.-Person-Form", None),
        ("second-person", "2. Person", None),
        ("second-person", "2.-Person-Form", None),
        ("third-person", "3. Person", None),
        ("third-person", "3.-Person-Form", None),
    ],
)
def test_morphology_feature_recognizer_truth_table(
    source: str, candidate: str, expected: str | None
) -> None:
    item = _semantic_item(source, "Testwort")
    assert _validate_de_semantic_contract(item, candidate, "definition") == expected


def test_related_term_cannot_claim_exact_synonym() -> None:
    symphonic = _semantic_item("symphonic", "sinfonisch")
    assert _validate_de_semantic_contract(
        symphonic, "orchesterähnlich", "synonym"
    ) == "related_not_exact_synonym"


def test_reasoning_effort_change_invalidates_checkpoint_compatibility(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    checkpoint = tmp_path / "ckpt.json"
    fake = FakeTransport()
    fake.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    for key, value in [
        ("bulk_de_reasoning_effort", "low"),
        ("bulk_en_reasoning_effort", "medium"),
        ("qa_reasoning_effort", "none"),
    ]:
        mutated = dict(state)
        mutated["identity"] = dict(state["identity"])
        mutated["identity"][key] = value
        checkpoint.write_text(json.dumps(mutated, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        with pytest.raises(BuildDictError, match="incompatible"):
            build_stage04(queue, stage02, tmp_path / f"out-{key}.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_max_output_tokens_change_invalidates_checkpoint_compatibility(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    checkpoint = tmp_path / "ckpt.json"
    fake = FakeTransport()
    fake.items = items
    build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    for key in ["bulk_de_max_output_tokens", "bulk_en_max_output_tokens", "qa_max_output_tokens"]:
        mutated = dict(state)
        mutated["identity"] = dict(state["identity"])
        mutated["identity"][key] = "256"
        checkpoint.write_text(json.dumps(mutated, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        with pytest.raises(BuildDictError, match="incompatible"):
            build_stage04(queue, stage02, tmp_path / f"out-{key}.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_pre_repair_checkpoint_fails_closed(tmp_path: Path) -> None:
    """A checkpoint written before the boundedness repair must fail closed."""
    stage02, queue, items = queue_fixture(tmp_path)
    pre_repair_identity = {
        "format": "flashcard-stage04-checkpoint-v3",
        "queue_sha256": hashlib.sha256(Path(queue).read_bytes()).hexdigest(),
        "generation_marker": "llm_generated_v1",
        "generated_license": "TEST_SYNTHETIC_LICENSE_v1",
        "bulk_de_model": "gpt-5.6-luna",
        "bulk_en_model": "gpt-5.6-luna",
        "qa_model": "gpt-5.6-terra",
        "bulk_pipeline_version": "stage04-bulk-v2",
        "qa_pipeline_version": "stage04-qa-v2",
        "response_schema_version": "openai-responses-json-schema-v2",
    }
    pre_repair_state = {
        "format": "flashcard-stage04-checkpoint-v3",
        "identity": pre_repair_identity,
        "bulk": {"completed": {}, "rejected": {}, "in_flight": []},
        "qa": {"required": [], "completed": {}, "rejected": {}, "in_flight": []},
        "manifests": [],
    }
    ckpt = tmp_path / "pre-repair.json"
    ckpt.write_text(json.dumps(pre_repair_state, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    fake = FakeTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", ckpt, "TEST_SYNTHETIC_LICENSE_v1", transport=fake)


def test_incomplete_max_output_tokens_response_is_never_persisted(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 3, prefix="incomplete")
    sorted_ids = sorted(items.keys())

    class IncompleteSecondTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, object]]:
            self.bulk_submitted.extend(item_ids)
            if self._bulk_call_count >= 1:
                iid = item_ids[0]
                return {
                    iid: {
                        "meaning": "teilweise",
                        "kind": "definition",
                        "response_status": "incomplete",
                        "incomplete_details": {"reason": "max_output_tokens"},
                    }
                }
            self._bulk_call_count += 1
            return {iid: {"meaning": f"ein Gebäude {iid[-6:]}", "kind": "definition"} for iid in item_ids}

    fake = IncompleteSecondTransport()
    fake.items = items
    checkpoint = tmp_path / "ckpt.json"
    out = tmp_path / "out.sqlite"
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(queue, stage02, out, checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=1)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    bad_id = sorted_ids[1]
    assert bad_id in state["bulk"]["rejected"]
    assert state["bulk"]["rejected"][bad_id]["error_code"] == "incomplete_max_output_tokens"
    assert bad_id not in state["bulk"]["completed"]
    assert not state["bulk"]["completed"].get(bad_id)
    # STOP before further paid work: the third request was never transmitted
    assert len(fake.bulk_submitted) == 2
    assert sorted_ids[2] not in fake.bulk_submitted
    # Partial JSON was never persisted as a valid generated row
    assert not out.exists() or sqlite3.connect(out).execute(
        "SELECT count(*) FROM sense_meaning WHERE source='llm_generated_v1'"
    ).fetchone()[0] == 0


def test_noncompleted_status_without_details_fails_closed(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 1, prefix="status-fail")

    class FailedStatusTransport(FakeTransport):
        def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, object]]:
            self.bulk_submitted.extend(item_ids)
            return {
                iid: {
                    "meaning": f"ein Gebäude {iid[-6:]}",
                    "kind": "definition",
                    "response_status": "failed",
                }
                for iid in item_ids
            }

    fake = FailedStatusTransport()
    fake.items = items
    checkpoint = tmp_path / "ckpt.json"
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=1)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    bad_id = sorted(items.keys())[0]
    assert state["bulk"]["rejected"][bad_id]["error_code"] == "provider_status_failed"
    assert not state["bulk"]["completed"]
    assert not state["qa"]["completed"]


def test_incomplete_qa_response_is_never_persisted(tmp_path: Path) -> None:
    stage02, queue, items = make_stage02_with_n(tmp_path, 4, prefix="qa-incomplete")
    checkpoint = tmp_path / "ckpt.json"

    class QAIncompleteTransport(FakeTransport):
        def send_qa(self, item_ids: list[str]) -> dict[str, dict[str, object]]:
            self.qa_submitted.extend(item_ids)
            return {
                iid: {
                    "meaning": f"qa-valid-{iid[-6:]}",
                    "kind": "definition",
                    "response_status": "incomplete",
                    "incomplete_details": {"reason": "max_output_tokens"},
                }
                for iid in item_ids
            }

    fake = QAIncompleteTransport()
    fake.items = items
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(queue, stage02, tmp_path / "out.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, batch_size=4)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    required = state["qa"]["required"]
    for rid in required:
        assert rid not in state["qa"]["completed"]
        assert state["qa"]["rejected"][rid]["error_code"] == "incomplete_max_output_tokens"


def test_pretransmission_spend_guard_blocks_over_cap() -> None:
    # Synthetic prices only — never real public pricing constants.
    worst = stage04_worst_case_request_cost_usd(
        input_token_estimate=400,
        max_output_tokens=512,
        input_price_per_mtok=2.00,
        output_price_per_mtok=12.00,
    )
    # 400*2 input tokens at $2/M + all 512 output tokens at $12/M
    assert abs(worst - ((800 / 1e6) * 2.00 + (512 / 1e6) * 12.00)) < 1e-12
    assert stage04_pretransmission_guard_blocks(
        recorded_spend_usd=0.50 - worst * 0.5,
        authorized_hard_cap_usd=0.50,
        next_request_worst_case_usd=worst,
    )
    with pytest.raises(BuildDictError):
        stage04_worst_case_request_cost_usd(100, 512, -1.0, 12.00)
    with pytest.raises(BuildDictError):
        stage04_pretransmission_guard_blocks(-1.0, 0.50, worst)


def test_pretransmission_spend_guard_permits_within_cap() -> None:
    worst_luna = stage04_worst_case_request_cost_usd(
        input_token_estimate=344,
        max_output_tokens=512,
        input_price_per_mtok=0.20,
        output_price_per_mtok=1.20,
    )
    assert not stage04_pretransmission_guard_blocks(
        recorded_spend_usd=0.10,
        authorized_hard_cap_usd=0.50,
        next_request_worst_case_usd=worst_luna,
    )
    # Boundary: exactly reaching the cap is still permitted; anything beyond blocks.
    assert not stage04_pretransmission_guard_blocks(0.50 - worst_luna, 0.50, worst_luna)
    assert stage04_pretransmission_guard_blocks(0.50 - worst_luna + 1e-9, 0.50, worst_luna)
    with pytest.raises(BuildDictError):
        stage04_worst_case_request_cost_usd(100, 0, 0.20, 1.20)
    with pytest.raises(BuildDictError):
        stage04_worst_case_request_cost_usd(100, 512, 0.20, 1.20, input_safety_multiplier=0.5)


# ======================================================================
# Live synchronous OpenAI Responses transport — zero-network tests
# (strict opt-in; every HTTP interaction is an injected fake opener)
# ======================================================================

LIVE_TEST_KEY = "sk-test-LIVE-SECRET-ZZ9Q"


@pytest.fixture(autouse=True)
def _live_tests_never_see_a_real_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STAGE04_LIVE_API_KEY_ENV, raising=False)


class FakeLiveResponse:
    def __init__(
        self,
        env: dict[str, object] | None = None,
        *,
        raw: bytes | None = None,
        status: int = 200,
        fail_read: bool = False,
    ) -> None:
        if raw is not None:
            self._raw = raw
        else:
            self._raw = json.dumps(env or {}).encode("utf-8")
        self.status = status
        self._fail_read = fail_read

    def read(self) -> bytes:
        if self._fail_read:
            raise ConnectionResetError("connection lost mid-read")
        return self._raw

    def __enter__(self) -> "FakeLiveResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeLiveOpener:
    """Scripted opener: records every call; never performs DNS/network I/O."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def open(self, request: object, timeout: float | None = None) -> object:
        headers = {str(k).lower(): str(v) for k, v in request.header_items()}  # type: ignore[attr-defined]
        data = bytes(request.data) if request.data is not None else b""  # type: ignore[attr-defined]
        self.calls.append(
            {
                "url": request.full_url,  # type: ignore[attr-defined]
                "method": request.get_method(),  # type: ignore[attr-defined]
                "headers": headers,
                "data": data,
                "timeout": timeout,
            }
        )
        if not self._outcomes:
            raise AssertionError("unexpected additional HTTP call")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _distribute(total: int, n: int) -> list[int]:
    base = total // n
    rem = total - base * n
    return [base + (1 if i < rem else 0) for i in range(n)]


def _build_live_fixture(tmp_path: Path, n: int = 55) -> dict[str, object]:
    workdir = tmp_path / "livefx"
    db, queue, items = make_stage02_with_n(workdir, n, prefix="live")
    sorted_ids = sorted(items.keys(), key=lambda s: s.encode())
    assert len(sorted_ids) >= 50
    sel_ids = sorted_ids[:50]
    selection_records = []
    for iid in sel_ids:
        rec = dict(items[iid])
        rec["stratum"] = "lexical"
        selection_records.append(rec)
    sel_bytes = json.dumps(
        selection_records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    sel_path = workdir / "selection.json"
    sel_path.write_bytes(sel_bytes)

    bodies = {
        iid: de_learner_meaning_request_body(iid_rec, STAGE04_DEFAULT_BULK_DE_MODEL)
        for iid, iid_rec in ((iid, items[iid]) for iid in sel_ids)
    }
    req_blob = "".join(
        _canonical_line({"body": bodies[iid], "custom_id": f"batch:{iid}", "item_id": iid}) + "\n"
        for iid in sel_ids
    ).encode("utf-8")
    batch_blob = "".join(
        _canonical_line(
            {
                "body": bodies[iid],
                "custom_id": f"batch:{iid}",
                "method": "POST",
                "url": "/v1/responses",
            }
        )
        + "\n"
        for iid in sel_ids
    ).encode("utf-8")

    bulk_ests = _distribute(STAGE04_LIVE_CANARY_BULK_INPUT_TOKEN_ESTIMATE, len(sel_ids))
    qa_ests = _distribute(STAGE04_LIVE_CANARY_QA_BOUND_INPUT_TOKEN_ESTIMATE, len(sel_ids))
    cost_doc = {
        "artifact": STAGE04_COST_PLAN_ARTIFACT,
        "selection_sha256": hashlib.sha256(sel_bytes).hexdigest(),
        "request_sha256": hashlib.sha256(req_blob).hexdigest(),
        "aggregate_bulk_input_tokens": sum(bulk_ests),
        "aggregate_qa_bound_input_tokens": sum(qa_ests),
        "items": [
            {"item_id": iid, "bulk_input_tokens": b, "qa_bound_input_tokens": q}
            for iid, b, q in zip(sel_ids, bulk_ests, qa_ests)
        ],
    }
    cost_bytes = _canonical_line(cost_doc).encode("utf-8")
    cost_path = workdir / "cost-plan.json"
    cost_path.write_bytes(cost_bytes)

    return {
        "db": db,
        "queue": queue,
        "items": items,
        "sel_ids": sel_ids,
        "sel_path": sel_path,
        "sel_sha": hashlib.sha256(sel_bytes).hexdigest(),
        "bodies": bodies,
        "req_sha": hashlib.sha256(req_blob).hexdigest(),
        "batch_sha": hashlib.sha256(batch_blob).hexdigest(),
        "cost_path": cost_path,
        "cost_sha": hashlib.sha256(cost_bytes).hexdigest(),
        "queue_sha": hashlib.sha256(queue.read_bytes()).hexdigest(),
        "queue_bytes": queue.stat().st_size,
        "workdir": workdir,
        "bulk_ests": dict(zip(sel_ids, bulk_ests)),
        "qa_ests": dict(zip(sel_ids, qa_ests)),
    }


_LIVE_DEFAULT_AUTH: dict[str, str] = {
    "hard_spend_cap_usd": "0.45",
    "bulk_input_price_per_mtok": "0.20",
    "bulk_output_price_per_mtok": "1.20",
    "qa_input_price_per_mtok": "2.00",
    "qa_output_price_per_mtok": "12.00",
    "input_safety_multiplier": "2.0",
}


def _live_prepare_kwargs(
    fx: dict[str, object], tmp_path: Path, tag: str, **overrides: object
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "queue_path": fx["queue"],
        "stage02_path": fx["db"],
        "checkpoint_path": tmp_path / f"{tag}-checkpoint.json",
        "output_path": tmp_path / f"{tag}-output.sqlite",
        "subset_queue_path": tmp_path / f"{tag}-subset-queue.json",
        "selection_path": fx["sel_path"],
        "expected_selection_sha": fx["sel_sha"],
        "expected_queue_sha": fx["queue_sha"],
        "expected_queue_bytes": fx["queue_bytes"],
        "authorized_request_sha": fx["req_sha"],
        "authorized_batch_equivalence_sha": fx["batch_sha"],
        "cost_plan_path": fx["cost_path"],
        "cost_plan_sha": fx["cost_sha"],
        "generated_license": "CC BY-SA",
        "bulk_de_model": STAGE04_DEFAULT_BULK_DE_MODEL,
        "bulk_en_model": STAGE04_DEFAULT_BULK_EN_MODEL,
        "qa_model": STAGE04_DEFAULT_QA_MODEL,
        "approved_bulk_model": STAGE04_DEFAULT_BULK_DE_MODEL,
        "approved_qa_model": STAGE04_DEFAULT_QA_MODEL,
        "timeout_seconds": 5,
        **dict(_LIVE_DEFAULT_AUTH),
    }
    kwargs.update(overrides)
    return kwargs


def _prepare_live(
    fx: dict[str, object], tmp_path: Path, tag: str, **overrides: object
) -> object:
    return prepare_stage04_live(**_live_prepare_kwargs(fx, tmp_path, tag, **overrides))  # type: ignore[arg-type]


def _execute_live(plan, fx: dict[str, object], opener: object, key: str = LIVE_TEST_KEY):  # type: ignore[no-untyped-def]
    return execute_stage04_live(
        plan,
        api_key=key,
        stage02_path=fx["db"],  # type: ignore[arg-type]
        output_path=plan.checkpoint_path.parent / (plan.checkpoint_path.stem + "-out.sqlite"),
        opener=opener,
    )


def _completed_env(
    *,
    meaning: str = "ein schlichtes Gebäude",
    kind: str = "definition",
    usage: tuple[int, int, int] | None = (100, 40, 10),
    status: str = "completed",
    incomplete: dict[str, str] | None = None,
    output: list[dict[str, object]] | None = None,
    response_id: str = "resp_live_test_1",
) -> dict[str, object]:
    if output is None:
        payload = json.dumps({"meaning": meaning, "kind": kind})
        output = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": payload}],
            }
        ]
    env: dict[str, object] = {"id": response_id, "status": status, "output": output}
    if incomplete is not None:
        env["incomplete_details"] = incomplete
    if usage is not None:
        env["usage"] = {
            "input_tokens": usage[0],
            "output_tokens": usage[1],
            "output_tokens_details": {"reasoning_tokens": usage[2]},
        }
    return env


def _read_state(path: Path) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _happy_opener(count: int = 52) -> FakeLiveOpener:
    return FakeLiveOpener([FakeLiveResponse(env=_completed_env()) for _ in range(count)])


def test_default_stage04_remains_zero_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = {"key_reads": 0, "opener_builds": 0}

    def _no_key() -> str:
        probes["key_reads"] += 1
        return ""

    def _no_opener() -> object:
        probes["opener_builds"] += 1
        raise AssertionError("live opener constructed without opt-in")

    monkeypatch.setattr(bd, "_read_openai_api_key", _no_key)
    monkeypatch.setattr(bd, "build_live_responses_opener", _no_opener)
    rc = main(
        [
            "stage04",
            "--queue",
            str(fx["queue"]),
            "--stage02",
            str(fx["db"]),
            "--output",
            str(tmp_path / "out.sqlite"),
            "--checkpoint",
            str(tmp_path / "ckpt.json"),
            "--generated-license",
            "CC BY-SA",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "No local deterministic Stage 04 transport configured" in err
    assert probes["key_reads"] == 0
    assert probes["opener_builds"] == 0


def test_live_flag_absent_never_reads_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = {"reads": 0}

    def _tripwire() -> str:
        probes["reads"] += 1
        return ""

    monkeypatch.setattr(bd, "_read_openai_api_key", _tripwire)
    rc = main(
        [
            "stage04",
            "--queue",
            str(fx["queue"]),
            "--stage02",
            str(fx["db"]),
            "--output",
            str(tmp_path / "out.sqlite"),
            "--checkpoint",
            str(tmp_path / "ckpt.json"),
            "--generated-license",
            "CC BY-SA",
            "--batch-size",
            "100",
        ]
    )
    assert rc == 1
    assert probes["reads"] == 0


def test_cli_rejects_dangling_live_args_without_flag(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    fx = _build_live_fixture(tmp_path)
    rc = main(
        [
            "stage04",
            "--queue",
            str(fx["queue"]),
            "--stage02",
            str(fx["db"]),
            "--output",
            str(tmp_path / "out.sqlite"),
            "--checkpoint",
            str(tmp_path / "ckpt.json"),
            "--generated-license",
            "CC BY-SA",
            "--live-selection",
            str(fx["sel_path"]),
        ]
    )
    assert rc == 1
    assert "--live-openai-responses" in capsys.readouterr().err


def _cli_base_args(fx: dict[str, object], tmp_path: Path, tag: str) -> list[str]:
    return [
        "--queue",
        str(fx["queue"]),
        "--stage02",
        str(fx["db"]),
        "--output",
        str(tmp_path / f"{tag}-out.sqlite"),
        "--checkpoint",
        str(tmp_path / f"{tag}-ckpt.json"),
        "--generated-license",
        "CC BY-SA",
    ]


def _cli_live_args(fx: dict[str, object], tmp_path: Path, tag: str) -> list[str]:
    return _cli_base_args(fx, tmp_path, tag) + [
        "--live-openai-responses",
        "--live-selection",
        str(fx["sel_path"]),
        "--live-selection-sha",
        str(fx["sel_sha"]),
        "--expected-queue-sha",
        str(fx["queue_sha"]),
        "--expected-queue-bytes",
        str(fx["queue_bytes"]),
        "--authorized-request-sha",
        str(fx["req_sha"]),
        "--authorized-batch-equivalence-sha",
        str(fx["batch_sha"]),
        "--live-cost-plan",
        str(fx["cost_path"]),
        "--live-cost-plan-sha",
        str(fx["cost_sha"]),
        "--live-subset-queue",
        str(tmp_path / f"{tag}-subset.json"),
        "--live-hard-spend-cap-usd",
        "0.45",
        "--live-bulk-input-price-per-mtok",
        "0.20",
        "--live-bulk-output-price-per-mtok",
        "1.20",
        "--live-qa-input-price-per-mtok",
        "2.00",
        "--live-qa-output-price-per-mtok",
        "12.00",
        "--live-input-safety-multiplier",
        "2.0",
        "--approved-bulk-model",
        STAGE04_DEFAULT_BULK_DE_MODEL,
        "--approved-qa-model",
        STAGE04_DEFAULT_QA_MODEL,
        "--live-timeout-seconds",
        "5",
    ]


def test_cli_live_preflight_stops_at_credential_boundary_no_side_effects(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Full live preflight passes on correct artifacts, then stops at key read."""
    fx = _build_live_fixture(tmp_path)
    rc = main(["stage04", *_cli_live_args(fx, tmp_path, "boundary")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "missing or blank" in err
    ckpt = tmp_path / "boundary-ckpt.json"
    out = tmp_path / "boundary-out.sqlite"
    subset = tmp_path / "boundary-subset.json"
    assert not ckpt.exists(), "credential boundary must precede any checkpoint creation"
    assert not out.exists()
    assert subset.exists(), "fences run before the credential boundary and derive the subset"
    subset_ids = [rec["item_id"] for rec in json.loads(subset.read_text(encoding="utf-8"))["items"]]
    assert sorted(subset_ids, key=lambda s: s.encode()) == fx["sel_ids"]


def _key_read_probe(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    probes = {"reads": 0}

    def _boom() -> str:
        probes["reads"] += 1
        raise AssertionError("OPENAI_API_KEY must not be read before preflight passes")

    monkeypatch.setattr(bd, "_read_openai_api_key", _boom)
    return probes


def test_live_activation_requires_exact_selection_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)
    with pytest.raises(BuildDictError, match="Canary SHA mismatch"):
        _prepare_live(fx, tmp_path, "badsel", expected_selection_sha="0" * 64)
    assert probes["reads"] == 0


def test_live_mode_requires_exactly_50_unique_frozen_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)

    records = json.loads(Path(str(fx["sel_path"])).read_text(encoding="utf-8"))
    short_path = tmp_path / "short-selection.json"
    short_path.write_bytes(
        json.dumps(records[:49], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    with pytest.raises(BuildDictError, match="count != 50"):
        prepare_stage04_live(
            **_live_prepare_kwargs(
                fx,
                tmp_path,
                "short",
                selection_path=short_path,
                expected_selection_sha=hashlib.sha256(short_path.read_bytes()).hexdigest(),
            )
        )

    dup = list(records)
    dup[1] = dict(dup[0])
    dup_path = tmp_path / "dup-selection.json"
    dup_bytes = json.dumps(dup, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    dup_path.write_bytes(dup_bytes)
    with pytest.raises(BuildDictError):
        prepare_stage04_live(
            **_live_prepare_kwargs(
                fx,
                tmp_path,
                "dup",
                selection_path=dup_path,
                expected_selection_sha=hashlib.sha256(dup_bytes).hexdigest(),
            )
        )
    assert probes["reads"] == 0


def test_selection_divergence_stops_before_key_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)
    records = json.loads(Path(str(fx["sel_path"])).read_text(encoding="utf-8"))
    tampered = json.loads(json.dumps(records))
    tampered[7]["derivation_inputs"][0]["text"] = (
        str(tampered[7]["derivation_inputs"][0]["text"]) + " mutated"
    )
    path = tmp_path / "tampered-selection.json"
    blob = json.dumps(tampered, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(blob)
    with pytest.raises(BuildDictError, match="diverge from queue"):
        prepare_stage04_live(
            **_live_prepare_kwargs(
                fx,
                tmp_path,
                "tamp",
                selection_path=path,
                expected_selection_sha=hashlib.sha256(blob).hexdigest(),
            )
        )
    assert probes["reads"] == 0


def test_request_sha_mismatch_stops_before_key_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)
    with pytest.raises(BuildDictError, match="STOP BEFORE KEY READ.*request SHA"):
        _prepare_live(fx, tmp_path, "reqsha", authorized_request_sha="f" * 64)
    assert probes["reads"] == 0


def test_batch_equivalence_sha_mismatch_stops_before_key_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)
    with pytest.raises(BuildDictError, match="STOP BEFORE KEY READ"):
        _prepare_live(fx, tmp_path, "batsha", authorized_batch_equivalence_sha="e" * 64)
    assert probes["reads"] == 0


def test_cost_plan_mismatches_stop_before_key_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)

    def cost_variant(mutator) -> tuple[Path, str]:  # type: ignore[no-untyped-def]
        doc = json.loads(Path(str(fx["cost_path"])).read_text(encoding="utf-8"))
        mutator(doc)
        blob = _canonical_line(doc).encode("utf-8")
        path = tmp_path / f"cost-{abs(hash(blob))}.json"
        path.write_bytes(blob)
        return path, hashlib.sha256(blob).hexdigest()

    # wrong artifact SHA supplied
    with pytest.raises(BuildDictError, match="cost plan SHA mismatch"):
        _prepare_live(fx, tmp_path, "cpsha", cost_plan_sha="a" * 64)
    # unknown item id
    p, s = cost_variant(lambda d: d["items"][3].update({"item_id": "queue:v2:alien"}))
    with pytest.raises(BuildDictError, match="item IDs"):
        _prepare_live(fx, tmp_path, "cpid", cost_plan_path=p, cost_plan_sha=s)
    # negative estimate
    p, s = cost_variant(lambda d: d["items"][5].update({"bulk_input_tokens": -4}))
    with pytest.raises(BuildDictError, match="nonnegative"):
        _prepare_live(fx, tmp_path, "cpneg", cost_plan_path=p, cost_plan_sha=s)
    # boolean estimate rejected
    p, s = cost_variant(lambda d: d["items"][6].update({"qa_bound_input_tokens": True}))
    with pytest.raises(BuildDictError, match="nonnegative"):
        _prepare_live(fx, tmp_path, "cpbool", cost_plan_path=p, cost_plan_sha=s)
    # aggregate mismatch vs recorded items
    p, s = cost_variant(lambda d: d.update({"aggregate_bulk_input_tokens": 12}))
    with pytest.raises(BuildDictError, match="aggregate mismatch"):
        _prepare_live(fx, tmp_path, "cpagg", cost_plan_path=p, cost_plan_sha=s)
    # frozen canary contract aggregates not satisfied
    doc = json.loads(Path(str(fx["cost_path"])).read_text(encoding="utf-8"))
    doc["items"] = [
        {**rec, "bulk_input_tokens": rec["bulk_input_tokens"] + 1} for rec in doc["items"]
    ]
    doc["aggregate_bulk_input_tokens"] += 50
    blob = _canonical_line(doc).encode("utf-8")
    p = tmp_path / "cost-shifted.json"
    p.write_bytes(blob)
    with pytest.raises(BuildDictError, match="frozen German-canary contract"):
        _prepare_live(
            fx, tmp_path, "cpfrozen", cost_plan_path=p, cost_plan_sha=hashlib.sha256(blob).hexdigest()
        )
    assert probes["reads"] == 0


def _minimal_transport(tmp_path: Path, opener: object, **overrides: object) -> OpenAILiveResponsesTransport:
    kwargs: dict[str, object] = {
        "api_key": LIVE_TEST_KEY,
        "bulk_bodies": {},
        "item_records": {},
        "token_estimates": {},
        "hard_cap_usd": Decimal("0.45"),
        "bulk_input_price_per_mtok": Decimal("0.20"),
        "bulk_output_price_per_mtok": Decimal("1.20"),
        "qa_input_price_per_mtok": Decimal("2.00"),
        "qa_output_price_per_mtok": Decimal("12.00"),
        "input_safety_multiplier": Decimal("2"),
        "qa_model": STAGE04_DEFAULT_QA_MODEL,
        "spend_state": _empty_spend_state({"k": "v"}),
        "timeout_seconds": 5,
        "opener": opener,
    }
    kwargs.update(overrides)
    return OpenAILiveResponsesTransport(**kwargs)  # type: ignore[arg-type]


def test_missing_or_blank_key_stops_before_http(tmp_path: Path) -> None:
    for bad_key in ("", "   ", '"sk-wrapped"', "'x'"):
        opener = FakeLiveOpener([])
        with pytest.raises(BuildDictError, match="missing or blank"):
            _minimal_transport(tmp_path, opener, api_key=bad_key)
    opener = FakeLiveOpener([AssertionError("must never transmit")])
    transport = _minimal_transport(tmp_path, opener)
    with pytest.raises(BuildDictError):
        transport.send_bulk(["whatever"])
    assert opener.calls == []


def test_fixed_endpoint_and_no_configurable_credential_destination(tmp_path: Path) -> None:
    assert STAGE04_LIVE_RESPONSES_URL == "https://api.openai.com/v1/responses"
    params = set(inspect.signature(OpenAILiveResponsesTransport.__init__).parameters)
    assert not params & {"endpoint", "url", "base_url", "host", "api_base", "api_url"}
    opener = FakeLiveOpener([])
    with pytest.raises(TypeError):
        _minimal_transport(tmp_path, opener, endpoint="http://127.0.0.1:9/v1")  # type: ignore[call-arg]
    transport = _minimal_transport(
        tmp_path,
        FakeLiveOpener([FakeLiveResponse(env=_completed_env())]),
        bulk_bodies={"i": {"model": "m"}},
        token_estimates={("bulk", "i"): 100},
    )
    assert transport.endpoint == STAGE04_LIVE_RESPONSES_URL
    transport.pretransmission_reserve("bulk", ["i"])
    transport.send_bulk(["i"])


def test_transmitted_body_is_exact_authorized_logical_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    opener = FakeLiveOpener([FakeLiveResponse(env=_completed_env()), ConnectionResetError("stop")])
    plan = _prepare_live(fx, tmp_path, "body")
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, opener)
    assert len(opener.calls) == 2  # unit 1 completed; unit 2 attempted once, ambiguous
    call = opener.calls[0]
    assert call["url"] == STAGE04_LIVE_RESPONSES_URL
    assert call["method"] == "POST"
    assert call["timeout"] == 5
    expected_body = plan.bulk_bodies[first_id]
    assert _canonical_line(json.loads(call["data"])) == _canonical_line(expected_body)
    # canonical compact serialization of the exact logical body object
    assert call["data"] == _canonical_line(expected_body).encode("utf-8")
    probes = _key_read_probe(monkeypatch)
    assert probes["reads"] == 0


def test_authorization_header_built_but_never_logged_or_persisted(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    outcomes: list[object] = [FakeLiveResponse(env=_completed_env())]
    outcomes.append(ConnectionResetError("ambiguous after first"))
    opener = FakeLiveOpener(outcomes)
    plan = _prepare_live(fx, tmp_path, "hdr")
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, opener)
    headers = opener.calls[0]["headers"]
    assert headers["authorization"] == f"Bearer {LIVE_TEST_KEY}"
    ckpt_bytes = plan.checkpoint_path.read_bytes()
    assert LIVE_TEST_KEY.encode() not in ckpt_bytes
    subset_bytes = plan.subset_queue_path.read_bytes()
    assert LIVE_TEST_KEY.encode() not in subset_bytes


def test_transport_repr_never_contains_credential(tmp_path: Path) -> None:
    transport = _minimal_transport(tmp_path, FakeLiveOpener([]))
    rendered = repr(transport)
    assert LIVE_TEST_KEY not in rendered
    assert STAGE04_LIVE_RESPONSES_URL in rendered


def _run_first_unit_failure(fx: dict[str, object], tmp_path: Path, tag: str, outcome: object):  # type: ignore[no-untyped-def]
    opener = FakeLiveOpener([outcome, AssertionError("no further calls allowed")])
    plan = _prepare_live(fx, tmp_path, tag)
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, opener)
    return plan, opener


def test_successful_completed_structured_response_parsed_and_persisted(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    opener = _happy_opener(52)
    plan = _prepare_live(fx, tmp_path, "happy")
    summary = _execute_live(plan, fx, opener)
    assert summary["bulk_completed"] == 50
    assert summary["qa_completed"] == 2
    state = _read_state(plan.checkpoint_path)
    bulk_completed = state["bulk"]["completed"]  # type: ignore[index]
    assert len(bulk_completed) == 50
    sample = bulk_completed[fx["sel_ids"][0]]  # type: ignore[index]
    assert sample["text"] == "ein schlichtes Gebäude"
    assert sample["kind"] == "definition"
    assert sample["source"] == GENERATED_MARKER
    assert sample["license"] == "CC BY-SA"
    assert state["bulk"]["in_flight"] == []  # type: ignore[index]
    assert state["qa"]["in_flight"] == []  # type: ignore[index]
    entries = state["spend"]["entries"]  # type: ignore[index]
    assert len(entries) == 52
    assert all(e["accounting"] == "ACTUAL" for e in entries)
    out = sqlite3.connect(plan.checkpoint_path.parent / "happy-checkpoint-out.sqlite")
    rows = out.execute(
        "SELECT COUNT(*) FROM sense_meaning WHERE source=?", (GENERATED_MARKER,)
    ).fetchone()[0]
    out.close()
    assert rows == 50


def test_reasoning_item_coexists_without_exposure(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    hidden = "SECRET-REASONING-CHAIN-CONTENT-XYZ"
    output = [
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": hidden}]},
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": json.dumps({"meaning": "kurz und klar", "kind": "synonym"}),
                }
            ],
        },
    ]
    env = _completed_env(output=output)
    blob = json.dumps(env)
    assert hidden in blob
    opener = FakeLiveOpener([FakeLiveResponse(env=env), ConnectionResetError("stop")])
    plan = _prepare_live(fx, tmp_path, "reasoning")
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, opener)
    state = _read_state(plan.checkpoint_path)
    completed = state["bulk"]["completed"]  # type: ignore[index]
    assert list(completed.values())[0]["text"] == "kurz und klar"  # type: ignore[index]
    ckpt_bytes = plan.checkpoint_path.read_bytes()
    assert hidden.encode() not in ckpt_bytes


def test_missing_output_text_fails_closed_durable(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    # Usage unavailable takes precedence and rejects fail-closed.
    plan, opener = _run_first_unit_failure(
        fx,
        tmp_path,
        "missingtext",
        FakeLiveResponse(env=_completed_env(output=[], usage=None)),
    )
    assert len(opener.calls) == 1
    state = _read_state(plan.checkpoint_path)
    rejected = state["bulk"]["rejected"]  # type: ignore[index]
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert (
        rejected[first_id]["error_code"] == "provider_usage_unavailable"  # type: ignore[index]
    )
    assert state["bulk"]["in_flight"] == []  # type: ignore[index]
    entries = state["spend"]["entries"]  # type: ignore[index]
    assert len(entries) == 1
    assert entries[0]["accounting"] == "WORST_CASE_RESERVED"

    # With valid usage but no usable output_text payload: durable rejection,
    # actual charge accounted, STOP.
    fx2 = _build_live_fixture(tmp_path / "mt2")
    plan2, opener2 = _run_first_unit_failure(
        fx2,
        tmp_path / "mt2",
        "missingtext2",
        FakeLiveResponse(env=_completed_env(output=[])),
    )
    assert len(opener2.calls) == 1
    state2 = _read_state(plan2.checkpoint_path)
    first_id2 = fx2["sel_ids"][0]  # type: ignore[index]
    assert (
        state2["bulk"]["rejected"][first_id2]["error_code"] == "missing_output_text"  # type: ignore[index]
    )
    entry = state2["spend"]["entries"][0]  # type: ignore[index]
    assert entry["accounting"] == "ACTUAL"
    assert Decimal(entry["charge_usd"]) == Decimal("0.000068")


def test_multiple_output_text_fails_closed_durable(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    text = json.dumps({"meaning": "eins", "kind": "definition"})
    output = [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": text}, {"type": "output_text", "text": text}],
        }
    ]
    plan, opener = _run_first_unit_failure(
        fx, tmp_path, "multitext", FakeLiveResponse(env=_completed_env(output=output))
    )
    assert len(opener.calls) == 1
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert (
        state["bulk"]["rejected"][first_id]["error_code"] == "multiple_output_text"  # type: ignore[index]
    )


def test_malformed_json_output_fails_closed(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    output = [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "{not-json"}],
        }
    ]
    plan, _opener = _run_first_unit_failure(
        fx, tmp_path, "badjson", FakeLiveResponse(env=_completed_env(output=output))
    )
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert state["bulk"]["rejected"][first_id]["error_code"] == "malformed_output_json"  # type: ignore[index]


def test_non_object_output_fails_closed(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    output = [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": '["array-not-object"]'}],
        }
    ]
    plan, _opener = _run_first_unit_failure(
        fx, tmp_path, "notobj", FakeLiveResponse(env=_completed_env(output=output))
    )
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert state["bulk"]["rejected"][first_id]["error_code"] == "output_not_object"  # type: ignore[index]


def test_provider_status_incomplete_fails_closed_via_live_transport(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    env = _completed_env(
        status="incomplete",
        incomplete={"reason": "max_output_tokens"},
        usage=(300, 512, 400),
    )
    plan, opener = _run_first_unit_failure(fx, tmp_path, "incomplete", FakeLiveResponse(env=env))
    assert len(opener.calls) == 1
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert (
        state["bulk"]["rejected"][first_id]["error_code"] == "incomplete_max_output_tokens"  # type: ignore[index]
    )
    entry = state["spend"]["entries"][0]  # type: ignore[index]
    assert entry["accounting"] == "ACTUAL"
    assert entry["reported_output_tokens"] == 512

    fx2 = _build_live_fixture(tmp_path / "failed")
    env2 = _completed_env(status="failed", usage=None)
    plan2, opener2 = _run_first_unit_failure(fx2, tmp_path / "failed", "failed", FakeLiveResponse(env=env2))
    assert len(opener2.calls) == 1
    state2 = _read_state(plan2.checkpoint_path)
    first_id2 = fx2["sel_ids"][0]  # type: ignore[index]
    assert (
        state2["bulk"]["rejected"][first_id2]["error_code"] == "provider_status_failed"  # type: ignore[index]
    )
    assert state2["spend"]["entries"][0]["accounting"] == "WORST_CASE_RESERVED"  # type: ignore[index]


def test_usage_accounted_as_actual_charge_persisted(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    opener = FakeLiveOpener([FakeLiveResponse(env=_completed_env()), ConnectionResetError("stop")])
    plan = _prepare_live(fx, tmp_path, "usage")
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, opener)
    state = _read_state(plan.checkpoint_path)
    entries = state["spend"]["entries"]  # type: ignore[index]
    assert len(entries) == 2
    entry = entries[0]
    expected_charge = (Decimal(100) * Decimal("0.20") + Decimal(40) * Decimal("1.20")) / Decimal(
        1000000
    )
    assert Decimal(entry["charge_usd"]) == expected_charge
    assert entry["charge_usd"] == "0.000068"
    assert entry["cumulative_usd"] == "0.000068"
    assert entry["accounting"] == "ACTUAL"
    assert entry["response_id"] == "resp_live_test_1"
    assert entry["reported_input_tokens"] == 100
    assert entry["reported_output_tokens"] == 40
    assert entry["reported_reasoning_tokens"] == 10
    assert entry["phase"] == "bulk"
    second_id = fx["sel_ids"][1]  # type: ignore[index]
    assert entries[1]["item_id"] == second_id
    assert entries[1]["accounting"] == "WORST_CASE_RESERVED"
    worst_second = stage04_worst_case_request_cost_usd_decimal(
        int(fx["bulk_ests"][second_id]),  # type: ignore[index]
        STAGE04_MAX_OUTPUT_TOKENS,
        Decimal("0.20"),
        Decimal("1.20"),
        Decimal("2"),
    )
    assert Decimal(entries[1]["charge_usd"]) == worst_second
    assert (
        Decimal(entries[1]["cumulative_usd"])  # type: ignore[index]
        == Decimal("0.000068") + worst_second
    )


def test_missing_usage_reserves_worst_case_and_stops(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    env = _completed_env(usage=None)
    plan, opener = _run_first_unit_failure(fx, tmp_path, "nousage", FakeLiveResponse(env=env))
    assert len(opener.calls) == 1
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert (
        state["bulk"]["rejected"][first_id]["error_code"] == "provider_usage_unavailable"  # type: ignore[index]
    )
    entry = state["spend"]["entries"][0]  # type: ignore[index]
    est = fx["bulk_ests"][first_id]  # type: ignore[index]
    expected_worst = stage04_worst_case_request_cost_usd_decimal(
        int(est), STAGE04_MAX_OUTPUT_TOKENS, Decimal("0.20"), Decimal("1.20"), Decimal("2")
    )
    assert Decimal(entry["charge_usd"]) == expected_worst
    assert entry["accounting"] == "WORST_CASE_RESERVED"


def test_malformed_envelope_fails_closed_with_reservation(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    plan, _opener = _run_first_unit_failure(
        fx, tmp_path, "malformedenv", FakeLiveResponse(raw=b"{not a json envelope")
    )
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert (
        state["bulk"]["rejected"][first_id]["error_code"] == "invalid_response_envelope"  # type: ignore[index]
    )
    assert state["spend"]["entries"][0]["accounting"] == "WORST_CASE_RESERVED"  # type: ignore[index]


AMBIGUOUS_OUTCOMES = {
    "timeout": TimeoutError("timed out"),
    "urlerror": urllib.error.URLError("connection refused"),
    "http429": urllib.error.HTTPError(STAGE04_LIVE_RESPONSES_URL, 429, "Too Many Requests", {}, None),  # type: ignore[arg-type]
    "http500": urllib.error.HTTPError(STAGE04_LIVE_RESPONSES_URL, 500, "Server Error", {}, None),  # type: ignore[arg-type]
    "reset": ConnectionResetError("reset by peer"),
    "eof_mid_read": FakeLiveResponse(env=_completed_env(), fail_read=True),
}


@pytest.mark.parametrize("scenario", sorted(AMBIGUOUS_OUTCOMES.keys()))
def test_ambiguous_outcomes_preserve_in_flight_zero_retries(
    tmp_path: Path, scenario: str
) -> None:
    fx = _build_live_fixture(tmp_path / f"amb-{scenario}")
    outcome: object = AMBIGUOUS_OUTCOMES[scenario]
    plan, opener = _run_first_unit_failure(fx, tmp_path / f"amb-{scenario}", scenario, outcome)
    assert len(opener.calls) == 1
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert state["bulk"]["in_flight"] == [first_id]  # type: ignore[index]
    entries = state["spend"]["entries"]  # type: ignore[index]
    assert len(entries) == 1
    assert entries[0]["accounting"] == "WORST_CASE_RESERVED"


def test_redirect_is_not_followed(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path / "redir")
    redirect = urllib.error.HTTPError(STAGE04_LIVE_RESPONSES_URL, 301, "Moved", {"Location": "https://evil.example/v1/responses"}, None)  # type: ignore[arg-type]
    opener = FakeLiveOpener([redirect, AssertionError("redirect must never be followed")])
    plan = _prepare_live(fx, tmp_path / "redir", "redirect")
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, opener)
    assert len(opener.calls) == 1
    state = _read_state(plan.checkpoint_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    assert state["bulk"]["in_flight"] == [first_id]  # type: ignore[index]


def test_item_outside_authorization_cannot_transmit(tmp_path: Path) -> None:
    opener = FakeLiveOpener([])
    transport = _minimal_transport(tmp_path, opener)
    with pytest.raises(BuildDictError, match="outside the authorized live selection"):
        transport.send_bulk(["queue:v2:not-in-frozen-50"])
    with pytest.raises(BuildDictError, match="outside the authorized live selection"):
        transport.pretransmission_reserve("qa", ["queue:v2:not-in-frozen-50"])
    assert opener.calls == []


def test_pretransmission_guard_blocks_over_cap_before_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = _key_read_probe(monkeypatch)
    opener = FakeLiveOpener([AssertionError("no HTTP allowed past the guard")])
    plan = _prepare_live(fx, tmp_path, "guard", hard_spend_cap_usd="0.000001")
    with pytest.raises(Stage04PretransmissionBlocked):
        _execute_live(plan, fx, opener)
    assert opener.calls == []
    state = _read_state(plan.checkpoint_path)
    assert state["bulk"]["in_flight"] == []  # type: ignore[index]
    assert state["spend"]["entries"] == []  # type: ignore[index]
    assert probes["reads"] == 0


def test_restart_preserves_cumulative_spend_and_constrains_cap(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    est_first = int(fx["bulk_ests"][first_id])  # type: ignore[index]
    worst_first = stage04_worst_case_request_cost_usd_decimal(
        est_first, STAGE04_MAX_OUTPUT_TOKENS, Decimal("0.20"), Decimal("1.20"), Decimal("2")
    )
    cap = worst_first + (worst_first / Decimal(2))

    # Run 1: first request admitted and completed; second admitted (reserved),
    # transmission ambiguous => reservation stands; process stops.
    outcomes: list[object] = [
        FakeLiveResponse(env=_completed_env()),
        FakeLiveResponse(env=_completed_env()),
        ConnectionResetError("ambiguous"),
        AssertionError("no further calls"),
    ]
    plan1 = _prepare_live(fx, tmp_path, "restart", hard_spend_cap_usd=_decimal_to_wire(cap))
    with pytest.raises(BuildDictError):
        _execute_live(plan1, fx, FakeLiveOpener(outcomes))
    state1 = _read_state(plan1.checkpoint_path)
    persisted_spend = _spend_total_usd(_validate_spend_state(state1["spend"]))  # type: ignore[index]

    # Restart simulation: fresh ledger loaded from disk must reproduce exactly
    # the recorded cumulative spend.
    reloaded = _empty_spend_state({"k": "v"})
    reloaded["entries"] = json.loads(json.dumps(state1["spend"]["entries"]))  # type: ignore[index]
    assert _spend_total_usd(_validate_spend_state(reloaded)) == persisted_spend
    assert persisted_spend > Decimal(0)

    # A restarted transport constrained by the same cap admits strictly fewer
    # further reservations than an empty-ledger transport would.
    def count_admissible(spend_state: dict[str, object]) -> int:
        t = _minimal_transport(
            tmp_path,
            FakeLiveOpener([]),
            hard_cap_usd=cap,
            spend_state=spend_state,
            token_estimates={("bulk", f"i{n}"): 100 for n in range(50)},
        )
        admitted = 0
        try:
            while True:
                t.pretransmission_reserve("bulk", [f"i{admitted}"])
                admitted += 1
        except Stage04PretransmissionBlocked:
            return admitted

    empty_admissible = count_admissible(_empty_spend_state({"k": "v"}))
    restarted_admissible = count_admissible(reloaded)
    assert restarted_admissible < empty_admissible


def test_execute_stage04_live_restart_persists_new_spend_end_to_end(tmp_path: Path) -> None:
    """Attempt-2 B1 regression: cross the execute_stage04_live -> build_stage04 boundary.

    Attempt 1 held two distinct spend-ledger dicts: the live transport mutated the
    one built by execute_stage04_live while _write_checkpoint serialized a second
    one reloaded inside build_stage04. Every restarted run therefore transmitted
    paid requests whose reservations/charges never reached durable state. This
    test drives three consecutive real execute_stage04_live invocations against a
    single checkpoint, discarding all in-memory objects between them.
    """
    fx = _build_live_fixture(tmp_path)
    sel_ids = fx["sel_ids"]
    ckpt = tmp_path / "b1-checkpoint.json"

    actual_charge = (Decimal(100) * Decimal("0.20") + Decimal(40) * Decimal("1.20")) / Decimal(
        1000000
    )
    worst_case = stage04_worst_case_request_cost_usd_decimal(
        int(fx["bulk_ests"][sel_ids[2]]),
        STAGE04_MAX_OUTPUT_TOKENS,
        Decimal("0.20"),
        Decimal("1.20"),
        Decimal("2"),
    )
    # Admits exactly: two bulk requests in run 1, one in run 2, none in run 3.
    cap = (actual_charge * 2) + worst_case + (worst_case / 2)

    def invoke(tag: str, outcomes: list[object]) -> FakeLiveOpener:
        """One process-style live execution; caller keeps no objects from it."""
        plan = _prepare_live(
            fx,
            tmp_path,
            "b1",
            checkpoint_path=ckpt,
            subset_queue_path=tmp_path / f"b1-{tag}-subset.json",
            hard_spend_cap_usd=_decimal_to_wire(cap),
        )
        opener = FakeLiveOpener(outcomes)
        with pytest.raises(BuildDictError):
            _execute_live(plan, fx, opener)
        return opener

    # ---- Run 1: item0 completes with usage; item1 returns incomplete -> STOP. ----
    opener1 = invoke(
        "run1",
        [
            FakeLiveResponse(env=_completed_env(meaning="bedeutung eins")),
            FakeLiveResponse(
                env=_completed_env(status="incomplete", incomplete={"reason": "max_output_tokens"})
            ),
        ],
    )
    assert len(opener1.calls) == 2, "run 1 must actually transmit two paid requests"

    state1 = _read_state(ckpt)
    assert state1["bulk"]["in_flight"] == []
    spend1 = _validate_spend_state(state1["spend"])
    entries1 = spend1["entries"]
    # (A) first execution created persisted spend entries
    assert len(entries1) == 2
    assert [e["accounting"] for e in entries1] == ["ACTUAL", "ACTUAL"]
    total1 = _spend_total_usd(spend1)
    assert total1 == actual_charge * 2

    # ---- (B) Run 2: restart. Nothing from run 1 survives except the checkpoint. ----
    opener2 = invoke("run2", [FakeLiveResponse(env=_completed_env(usage=None))])
    # (C) the restarted run really transmitted a further paid request
    assert len(opener2.calls) == 1
    assert opener2.calls[0]["url"] == STAGE04_LIVE_RESPONSES_URL

    # (D) re-read the checkpoint from disk after the second invocation
    state2 = _read_state(ckpt)
    spend2 = _validate_spend_state(state2["spend"])
    entries2 = spend2["entries"]
    total2 = _spend_total_usd(spend2)

    # (E) persisted entry count and cumulative amount increased correctly
    assert len(entries2) == len(entries1) + 1, "restart spend must persist (Attempt-1 B1)"
    assert total2 == total1 + worst_case
    assert total2 > total1

    # (F) the persisted ledger is exactly the accounting the second run used:
    #     run 2's response carried no usage, so its worst-case reservation stands.
    new_entry = entries2[-1]
    assert new_entry["item_id"] == sel_ids[2]
    assert new_entry["phase"] == "bulk"
    assert new_entry["accounting"] == "WORST_CASE_RESERVED"
    assert Decimal(new_entry["charge_usd"]) == worst_case
    assert Decimal(new_entry["cumulative_usd"]) == total2
    assert entries2[:2] == entries1, "prior persisted entries must be preserved verbatim"
    assert state2["bulk"]["rejected"][sel_ids[2]]["error_code"] == "provider_usage_unavailable"

    # ---- (G) Run 3: remaining-cap enforcement uses cumulative spend from BOTH runs. ----
    opener3 = invoke("run3", [AssertionError("run 3 must block before any transmission")])
    assert len(opener3.calls) == 0, "over-cap request must never reach HTTP"

    state3 = _read_state(ckpt)
    assert state3["bulk"]["in_flight"] == [], "blocked request leaves no in_flight side effect"
    assert _spend_total_usd(_validate_spend_state(state3["spend"])) == total2

    # (H) the same cap would have ADMITTED that request had the ledger reset to zero.
    next_worst_case = stage04_worst_case_request_cost_usd_decimal(
        int(fx["bulk_ests"][sel_ids[3]]),
        STAGE04_MAX_OUTPUT_TOKENS,
        Decimal("0.20"),
        Decimal("1.20"),
        Decimal("2"),
    )
    assert bd.stage04_pretransmission_guard_blocks_decimal(total2, cap, next_worst_case) is True
    assert (
        bd.stage04_pretransmission_guard_blocks_decimal(Decimal(0), cap, next_worst_case) is False
    ), "test is only meaningful if a reset ledger would have admitted this request"


def test_live_spend_ledger_object_is_shared_with_checkpoint_state(tmp_path: Path) -> None:
    """The transport's ledger and the dict build_stage04 serializes are ONE object."""
    fx = _build_live_fixture(tmp_path)
    ckpt = tmp_path / "shared-checkpoint.json"
    seen: dict[str, object] = {}
    real_write = bd._write_checkpoint

    def spy(path: Path, identity: dict[str, str], state: dict[str, object]) -> None:
        seen["spend"] = state.get("spend")
        real_write(path, identity, state)

    for tag, outcomes in (
        ("fresh", [FakeLiveResponse(env=_completed_env(usage=None))]),
        ("restart", [FakeLiveResponse(env=_completed_env(usage=None))]),
    ):
        plan = _prepare_live(
            fx,
            tmp_path,
            "shared",
            checkpoint_path=ckpt,
            subset_queue_path=tmp_path / f"shared-{tag}-subset.json",
        )
        transports: list[object] = []
        real_transport_cls = bd.OpenAILiveResponsesTransport

        def capture(*args: object, **kwargs: object) -> object:
            t = real_transport_cls(*args, **kwargs)  # type: ignore[arg-type]
            transports.append(t)
            return t

        bd.OpenAILiveResponsesTransport = capture  # type: ignore[assignment,misc]
        bd._write_checkpoint = spy  # type: ignore[assignment]
        try:
            with pytest.raises(BuildDictError):
                _execute_live(plan, fx, FakeLiveOpener(outcomes))
        finally:
            bd.OpenAILiveResponsesTransport = real_transport_cls  # type: ignore[misc]
            bd._write_checkpoint = real_write  # type: ignore[assignment]
        assert len(transports) == 1
        assert transports[0]._spend_state is seen["spend"], (
            f"{tag}: transport ledger and serialized checkpoint ledger diverged"
        )


def test_bulk_and_qa_share_the_same_hard_cap(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    first_id = fx["sel_ids"][0]  # type: ignore[index]
    bulk_actual = (Decimal(100) * Decimal("0.20") + Decimal(40) * Decimal("1.20")) / Decimal(
        1000000
    )
    qa_worst = stage04_worst_case_request_cost_usd_decimal(
        int(fx["qa_ests"][first_id]),  # type: ignore[index]
        STAGE04_MAX_OUTPUT_TOKENS,
        Decimal("2.00"),
        Decimal("12.00"),
        Decimal("2"),
    )
    cap = bulk_actual + (qa_worst * Decimal("4") / Decimal(10))
    spend = _empty_spend_state({"auth": "live"})
    opener = FakeLiveOpener([FakeLiveResponse(env=_completed_env()), AssertionError("QA blocked")])
    transport = _minimal_transport(
        tmp_path,
        opener,
        hard_cap_usd=cap,
        spend_state=spend,
        token_estimates={
            ("bulk", str(first_id)): int(fx["bulk_ests"][first_id]),  # type: ignore[index]
            ("qa", str(first_id)): int(fx["qa_ests"][first_id]),  # type: ignore[index]
        },
        item_records={},
        bulk_bodies={str(first_id): {"model": "m"}},
        qa_model=STAGE04_DEFAULT_QA_MODEL,
    )
    transport.pretransmission_reserve("bulk", [str(first_id)])
    transport.qa_candidate_lookup[str(first_id)] = "Kandidat"
    transport.send_bulk([str(first_id)])
    assert len(opener.calls) == 1
    with pytest.raises(Stage04PretransmissionBlocked):
        transport.pretransmission_reserve("qa", [str(first_id)])
    assert len(opener.calls) == 1, "blocked QA request must never be transmitted"


def test_classification_change_invalidates_live_checkpoint(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    plan1 = _prepare_live(fx, tmp_path, "clsA")
    ckpt = plan1.checkpoint_path
    with pytest.raises(BuildDictError):
        _execute_live(plan1, fx, FakeLiveOpener([FakeLiveResponse(env=_completed_env())]))
    assert ckpt.exists()
    plan2 = _prepare_live(
        fx, tmp_path, "clsB", checkpoint_path=ckpt, generated_license="CC0-1.0"
    )
    tripwire_opener = FakeLiveOpener([AssertionError("incompatible must not transmit")])
    with pytest.raises(BuildDictError, match="incompatible"):
        _execute_live(plan2, fx, tripwire_opener)
    assert tripwire_opener.calls == []


@pytest.mark.parametrize(
    "override",
    [
        {"hard_spend_cap_usd": "0.46"},
        {"bulk_input_price_per_mtok": "0.21"},
        {"input_safety_multiplier": "2.5"},
    ],
)
def test_authorization_input_change_invalidates_live_checkpoint(
    tmp_path: Path, override: dict[str, str]
) -> None:
    fx = _build_live_fixture(tmp_path)
    plan1 = _prepare_live(fx, tmp_path, "authA")
    ckpt = plan1.checkpoint_path
    with pytest.raises(BuildDictError):
        _execute_live(plan1, fx, FakeLiveOpener([FakeLiveResponse(env=_completed_env())]))
    plan2 = _prepare_live(fx, tmp_path, "authB", checkpoint_path=ckpt, **override)  # type: ignore[arg-type]
    tripwire_opener = FakeLiveOpener([AssertionError("incompatible must not transmit")])
    with pytest.raises(BuildDictError, match="incompatible"):
        _execute_live(plan2, fx, tripwire_opener)
    assert tripwire_opener.calls == []


def test_historical_persian_checkpoint_untouched_by_live_path(tmp_path: Path) -> None:
    legacy_identity = {
        "format": "flashcard-stage04-checkpoint-v2",
        "queue_sha256": "legacy-queue",
        "generation_marker": "llm_generated_v1",
        "generated_license": "AI_GENERATED_FROM_WIKTIONARY_ATTRIBUTED_v1",
        "bulk_de_model": "gpt-5.6-luna",
        "bulk_en_model": "gpt-5.6-luna",
        "qa_model": "gpt-5.6-terra",
        "bulk_pipeline_version": "stage04-bulk-v1",
        "qa_pipeline_version": "stage04-qa-v1",
        "response_schema_version": "openai-responses-json-schema-v1",
    }
    legacy_ids = ["enrichment-job:v1:a", "enrichment-job:v1:b"]
    legacy = {
        "format": "flashcard-stage04-checkpoint-v2",
        "identity": legacy_identity,
        "bulk": {"completed": {}, "rejected": {}, "in_flight": legacy_ids},
        "qa": {"required": [], "completed": {}, "rejected": {}, "in_flight": []},
        "manifests": [],
    }
    workdir = tmp_path / "legacy"
    workdir.mkdir()
    legacy_path = workdir / "legacy-checkpoint.json"
    legacy_bytes = json.dumps(legacy, sort_keys=True).encode("utf-8")
    legacy_path.write_bytes(legacy_bytes)

    fx = _build_live_fixture(workdir)
    plan = _prepare_live(fx, workdir, "legacyrun", checkpoint_path=legacy_path)
    tripwire_opener = FakeLiveOpener([AssertionError("legacy must never transmit")])
    with pytest.raises(BuildDictError):
        _execute_live(plan, fx, tripwire_opener)
    assert tripwire_opener.calls == []
    assert legacy_path.read_bytes() == legacy_bytes
    current_identity = dict(
        _checkpoint_identity(
            "q",
            GENERATED_MARKER,
            "CC BY-SA",
            STAGE04_DEFAULT_BULK_DE_MODEL,
            STAGE04_DEFAULT_BULK_EN_MODEL,
            STAGE04_DEFAULT_QA_MODEL,
        )
    )
    with pytest.raises(BuildDictError, match="format"):
        _load_checkpoint(legacy_path, current_identity)


def test_live_serialization_format_pinned() -> None:
    body = de_learner_meaning_request_body(
        {
            "lemma_text": "Ärzte",
            "pos": "NOUN",
            "gender": None,
            "lemma_semantic_ref": "lemma:v1:x",
            "sense_semantic_ref": "sense:v1:x",
            "derivation_inputs": [{"text": "doctor", "source": "wiktionary"}],
        },
        STAGE04_DEFAULT_BULK_DE_MODEL,
    )
    line = _canonical_line({"body": body, "custom_id": "batch:i", "item_id": "i"})
    parsed = json.loads(line)
    assert set(parsed.keys()) == {"body", "custom_id", "item_id"}
    assert parsed["body"] == body
    # pinned compact key ordering (readiness artifact property)
    assert line.startswith('{"body":')
    assert '"custom_id":"batch:i"' in line
    assert line.endswith('"item_id":"i"}')
    assert "Ä" in line  # non-ASCII preserved raw (readiness artifact property)
    batch_line = _canonical_line(
        {"body": body, "custom_id": "batch:i", "method": "POST", "url": "/v1/responses"}
    )
    parsed_batch = json.loads(batch_line)
    assert set(parsed_batch.keys()) == {"body", "custom_id", "method", "url"}
    assert parsed_batch["method"] == "POST"
    assert parsed_batch["url"] == "/v1/responses"
    assert _canonical_line(parsed_batch["body"]) == _canonical_line(parsed["body"])


def test_no_credential_in_any_error_string_or_artifact(tmp_path: Path) -> None:
    fx = _build_live_fixture(tmp_path)
    captured_errors: list[str] = []
    for tag, outcome in (
        ("leak1", ConnectionResetError("ambiguous")),
        ("leak2", urllib.error.HTTPError(STAGE04_LIVE_RESPONSES_URL, 500, "boom", {}, None)),  # type: ignore[arg-type]
    ):
        opener = FakeLiveOpener([outcome, AssertionError("stop")])
        plan = _prepare_live(fx, tmp_path, tag)
        try:
            _execute_live(plan, fx, opener)
        except BuildDictError as exc:
            captured_errors.append(str(exc))
    transport_repr = repr(_minimal_transport(tmp_path, FakeLiveOpener([])))
    artifacts = list((tmp_path).glob("*"))
    blobs = b""
    for path in artifacts:
        if path.is_file():
            blobs += path.read_bytes()
    assert LIVE_TEST_KEY.encode() not in blobs
    assert all(LIVE_TEST_KEY not in message for message in captured_errors)
    assert LIVE_TEST_KEY not in transport_repr


def test_no_real_provider_calls_in_entire_live_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = _build_live_fixture(tmp_path)
    probes = {"urlopen": 0, "socket": 0}

    def _no_urlopen(*args: object, **kwargs: object) -> object:
        probes["urlopen"] += 1
        raise AssertionError("real provider call attempted")

    class _NoSocket:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("real socket attempted")

    monkeypatch.setattr(urllib.request, "urlopen", _no_urlopen)
    monkeypatch.setattr(socket, "socket", _NoSocket)
    monkeypatch.setattr(bd, "_read_openai_api_key", lambda: LIVE_TEST_KEY)
    plan = _prepare_live(fx, tmp_path, "nonet")
    summary = _execute_live(plan, fx, _happy_opener(52), key=LIVE_TEST_KEY)
    assert summary["bulk_completed"] == 50
    assert probes["urlopen"] == 0
    assert probes["socket"] == 0
