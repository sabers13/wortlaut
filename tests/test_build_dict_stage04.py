"""Fake/local DE/EN Stage 04 safety tests."""

import hashlib
import json
from pathlib import Path

import pytest

from tests.test_build_dict_stage03 import make_stage02
from tools.build_dict import BuildDictError, build_stage03, build_stage04, retry_rejected


class FakeTransport:
    def __init__(self, texts: dict[str, str] | None = None, fail_after: int | None = None) -> None:
        self.texts = texts or {}
        self.fail_after = fail_after
        self.bulk_submitted: list[str] = []
        self.qa_submitted: list[str] = []
        self.items: dict[str, dict[str, object]] = {}

    def send_bulk(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        if self.fail_after is not None and len(self.bulk_submitted) >= self.fail_after:
            raise RuntimeError("deliberate local failure")
        self.bulk_submitted.extend(item_ids)
        return {
            item_id: {
                "text": self.texts.get(
                    item_id,
                    "ein Gebäude" if self.items[item_id]["language"] == "de" else "building",
                ),
                "language": str(self.items[item_id]["language"]),
                "kind": "definition" if self.items[item_id]["language"] == "de" else "translation",
            }
            for item_id in item_ids
        }

    def send_qa(self, item_ids: list[str]) -> dict[str, dict[str, str]]:
        self.qa_submitted.extend(item_ids)
        return self.send_bulk(item_ids)


def queue_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, dict[str, object]]]:
    stage02 = make_stage02(tmp_path / "input.sqlite")
    queue = tmp_path / "queue.json"
    build_stage03(stage02, queue)
    items = json.loads(queue.read_text(encoding="utf-8"))["items"]
    assert isinstance(items, list)
    return stage02, queue, {str(item["item_id"]): item for item in items}


def test_fake_bulk_qa_persists_generated_rows_and_derivations(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    before = hashlib.sha256(stage02.read_bytes()).hexdigest()
    fake = FakeTransport()
    fake.items = items
    output, checkpoint = tmp_path / "enriched.sqlite", tmp_path / "checkpoint.json"
    result = build_stage04(
        queue, stage02, output, checkpoint, "TEST_CLASSIFICATION_v1", transport=fake, batch_size=1
    )
    assert result["bulk_completed"] == 2
    assert result["qa_completed"] == 2
    assert hashlib.sha256(stage02.read_bytes()).hexdigest() == before
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert set(state) >= {"bulk", "qa", "manifests"}
    assert not state["bulk"]["in_flight"]
    manifest = state["manifests"][0]
    assert manifest["state"] == "PREPARED"
    assert manifest["correlation"].startswith("batchcorr:v1:")
    assert manifest["custom_ids"] == [f"batch:{item_id}" for item_id in manifest["item_ids"]]


def test_complete_invalid_result_is_rejected_and_not_resubmitted(tmp_path: Path) -> None:
    stage02, queue, items = queue_fixture(tmp_path)
    bad_id = sorted(items)[0]
    fake = FakeTransport({bad_id: "Haus"})
    fake.items = items
    checkpoint = tmp_path / "checkpoint.json"
    with pytest.raises(BuildDictError, match="rejected"):
        build_stage04(
            queue,
            stage02,
            tmp_path / "out.sqlite",
            checkpoint,
            "TEST_CLASSIFICATION_v1",
            transport=fake,
            batch_size=2,
        )
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert bad_id in state["bulk"]["rejected"]
    assert not state["bulk"]["in_flight"]
    again = FakeTransport()
    again.items = items
    build_stage04(
        queue,
        stage02,
        tmp_path / "out.sqlite",
        checkpoint,
        "TEST_CLASSIFICATION_v1",
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
            "TEST_CLASSIFICATION_v1",
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
            "TEST_CLASSIFICATION_v1",
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
            "TEST_CLASSIFICATION_v1",
            transport=fake,
        )
    with pytest.raises(BuildDictError, match="not rejected"):
        retry_rejected(checkpoint, queue, ["unknown"], "TEST_CLASSIFICATION_v1")
    retry_rejected(checkpoint, queue, [bad_id], "TEST_CLASSIFICATION_v1")
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
            "TEST_CLASSIFICATION_v1",
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
            "TEST_CLASSIFICATION_v1",
            transport=fake,
        )
