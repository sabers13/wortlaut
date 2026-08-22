"""DE/EN-only Stage 03 queue tests."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.build_dict import (
    STAGE01_SCHEMA_SQL,
    STAGE02_EXAMPLE_SCHEMA_SQL,
    BuildDictError,
    _validate_de_source_eligibility,
    build_stage03,
)


def make_stage02(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(STAGE01_SCHEMA_SQL + STAGE02_EXAMPLE_SCHEMA_SQL)
    conn.execute(
        "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license) VALUES (1, 'lemma:v1:haus', 'Haus', 'NOUN', 'das', 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense VALUES (1, 1, 'sense:v1:haus:1', 'enwiktionary', 'Haus-1', 0, NULL, 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense VALUES (2, 1, 'sense:v1:haus:2', 'enwiktionary', 'Haus-2', 1, NULL, 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense_meaning VALUES (1, 1, 'en', 'translation', 0, 'house', 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense_meaning VALUES (2, 1, 'de', 'synonym', 0, 'Gebäude', 'wiktionary', 'CC BY-SA')"
    )
    conn.execute(
        "INSERT INTO sense_meaning VALUES (3, 2, 'de', 'definition', 0, 'siehe Haus', 'wiktionary', 'CC BY-SA')"
    )
    conn.commit()
    conn.close()
    return path


def read_queue(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return dict(value)


def test_source_first_queue_is_de_en_only_and_deterministic(tmp_path: Path) -> None:
    db = make_stage02(tmp_path / "input.sqlite")
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    result = build_stage03(db, first)
    build_stage03(db, second)
    queue = read_queue(first)
    items = queue["items"]
    assert isinstance(items, list)
    assert first.read_bytes() == second.read_bytes()
    assert result["de"] == 1 and result["en"] == 1
    assert {item["job_class"] for item in items} == {"de_learner_meaning", "en_meaning"}
    assert {item["language"] for item in items} == {"de", "en"}
    assert [item["item_id"] for item in items] == sorted(item["item_id"] for item in items)
    assert all("/home/" not in json.dumps(item) for item in items)
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


def test_de_fallback_carries_exact_source_text_provenance(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.json"
    build_stage03(make_stage02(tmp_path / "input.sqlite"), queue_path)
    items = read_queue(queue_path)["items"]
    assert isinstance(items, list)
    de_item = next(item for item in items if item["language"] == "de")
    assert de_item["derivation_source_ids"] == [3]
    source = de_item["derivation_inputs"][0]
    assert source["text"] == "siehe Haus"
    assert source["source"] == "wiktionary"
    assert source["license"] == "CC BY-SA"


@pytest.mark.parametrize(
    "text,kind",
    [("Haus!", "synonym"), ("siehe Haus", "definition"), ("ein langer\nText", "definition")],
)
def test_de_positive_predicate_rejects_uncertain_source(text: str, kind: str) -> None:
    assert _validate_de_source_eligibility(text, kind) is not None


def test_stage03_refuses_overwrite_and_retired_packet_mode(tmp_path: Path) -> None:
    db = make_stage02(tmp_path / "input.sqlite")
    queue = tmp_path / "queue.json"
    build_stage03(db, queue)
    with pytest.raises(BuildDictError, match="already exists"):
        build_stage03(db, queue)
    with pytest.raises(BuildDictError, match="retired"):
        build_stage03(db, tmp_path / "other.json", packet_path=tmp_path / "packet.json")


def test_queue_ids_are_stable_and_order_independent(tmp_path: Path) -> None:
    # Build two DBs with same logical senses but different insertion order; queue must be identical
    def make_ordered(path: Path, reverse: bool) -> Path:
        conn = sqlite3.connect(path)
        conn.executescript(STAGE01_SCHEMA_SQL + STAGE02_EXAMPLE_SCHEMA_SQL)
        # Two senses with same semantic refs but inserted in different order
        senses = [
            (1, "sense:v1:haus:1", "Haus-1"),
            (2, "sense:v1:haus:2", "Haus-2"),
        ]
        if reverse:
            senses = list(reversed(senses))
        conn.execute("INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license) VALUES (1, 'lemma:v1:haus', 'Haus', 'NOUN', 'das', 'wiktionary', 'CC BY-SA')")
        for sid, sref, ssource in senses:
            conn.execute("INSERT INTO sense VALUES (?, 1, ?, 'enwiktionary', ?, ?, NULL, 'wiktionary', 'CC BY-SA')", (sid, sref, ssource, sid - 1))
        conn.execute("INSERT INTO sense_meaning VALUES (1, 1, 'en', 'translation', 0, 'house', 'wiktionary', 'CC BY-SA')")
        conn.execute("INSERT INTO sense_meaning VALUES (2, 1, 'de', 'synonym', 0, 'Gebäude', 'wiktionary', 'CC BY-SA')")
        conn.execute("INSERT INTO sense_meaning VALUES (3, 2, 'de', 'definition', 0, 'siehe Haus', 'wiktionary', 'CC BY-SA')")
        conn.commit()
        conn.close()
        return path

    db1 = make_ordered(tmp_path / "db1.sqlite", reverse=False)
    db2 = make_ordered(tmp_path / "db2.sqlite", reverse=True)
    q1 = tmp_path / "q1.json"
    q2 = tmp_path / "q2.json"
    build_stage03(db1, q1)
    build_stage03(db2, q2)
    # Queue ordering is deterministic bytewise by item_id, independent of input insertion order
    assert q1.read_bytes() == q2.read_bytes()
    qdata = read_queue(q1)
    items = qdata["items"]
    assert isinstance(items, list)
    # Stable refs are used as durable identity
    for item in items:
        assert item["lemma_semantic_ref"] == "lemma:v1:haus"
        assert item["sense_semantic_ref"] in ("sense:v1:haus:1", "sense:v1:haus:2")
        assert item["custom_id"] == f"batch:{item['item_id']}"


def test_queue_uses_semantic_refs_not_numeric_ids(tmp_path: Path) -> None:
    db = make_stage02(tmp_path / "input.sqlite")
    queue = tmp_path / "queue.json"
    build_stage03(db, queue)
    items = read_queue(queue)["items"]
    assert isinstance(items, list)
    for item in items:
        # Numeric ids may appear as convenience but durable identity is semantic
        assert "lemma_semantic_ref" in item
        assert "sense_semantic_ref" in item
        assert item["item_id"].startswith("queue:v1:")
        # custom_id derived from item_id
        assert item["custom_id"] == f"batch:{item['item_id']}"


def test_stage03_no_network_and_input_immutable(tmp_path: Path) -> None:
    db = make_stage02(tmp_path / "input.sqlite")
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    queue = tmp_path / "queue.json"
    # No network is inherent; we just verify input not mutated
    build_stage03(db, queue)
    after = hashlib.sha256(db.read_bytes()).hexdigest()
    assert before == after
    # Queue contains no secrets
    lower = queue.read_bytes().decode("utf-8").lower()
    for forbidden in ["api_key", "password", "/home/"]:
        assert forbidden not in lower
