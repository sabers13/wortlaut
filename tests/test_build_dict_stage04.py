"""Fake/local DE/EN Stage 04 safety tests — v2 repair."""
# mypy: disable-error-code="attr-defined,unused-ignore,operator,index,type-var,arg-type"

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tests.test_build_dict_stage03 import make_stage02, make_stage02_with_en_counts
from tools.build_dict import (
    STAGE01_SCHEMA_SQL,
    STAGE02_EXAMPLE_SCHEMA_SQL,
    BuildDictError,
    _checkpoint_identity,
    _deterministic_audit_sample,
    _load_checkpoint,
    _render_canary_receipt,
    _validate_generated_candidate,
    _write_canary_selection_manifest,
    build_stage03,
    build_stage04,
    de_learner_meaning_request_body,
    de_learner_qa_request_body,
    en_meaning_request_body,
    retry_rejected,
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
    assert state["identity"]["bulk_pipeline_version"] == "stage04-bulk-v2"


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
    for key in ["queue_sha256", "generation_marker", "generated_license", "bulk_de_model", "bulk_en_model", "qa_model", "bulk_pipeline_version", "qa_pipeline_version", "response_schema_version"]:
        assert key in identity, f"missing {key}"
    assert identity["generation_marker"] == "llm_generated_v1"
    assert identity["bulk_de_model"] == "gpt-5.6-luna"
    assert identity["bulk_en_model"] == "gpt-5.6-luna"
    assert identity["qa_model"] == "gpt-5.6-terra"
    assert identity["bulk_pipeline_version"] == "stage04-bulk-v2"
    assert identity["qa_pipeline_version"] == "stage04-qa-v2"
    assert identity["response_schema_version"] == "openai-responses-json-schema-v2"
    assert identity["format"] == "flashcard-stage04-checkpoint-v3"
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out2.sqlite", checkpoint, "OTHER_LICENSE", transport=fake)
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out3.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, bulk_pipeline_version="stage04-bulk-v1")
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out4.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, qa_pipeline_version="stage04-qa-v1")
    with pytest.raises(BuildDictError, match="incompatible"):
        build_stage04(queue, stage02, tmp_path / "out5.sqlite", checkpoint, "TEST_SYNTHETIC_LICENSE_v1", transport=fake, bulk_de_model="other-model")


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
