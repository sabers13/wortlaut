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
