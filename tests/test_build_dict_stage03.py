"""Contract tests for deterministic, offline Stage-03 enrichment queues."""

from __future__ import annotations

import socket
import sqlite3
from pathlib import Path

import pytest

from tools.build_dict import (
    STAGE02_EXAMPLE_SCHEMA_SQL,
    BuildDictError,
    build_stage01,
    build_stage03,
    read_stage03_queue,
    sha256_file,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def stage02_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "stage02.sqlite"
    build_stage01(
        FIXTURES / "wiktextract_stage01_en.jsonl", FIXTURES / "wiktextract_stage01_de.jsonl", path
    )
    with sqlite3.connect(path) as conn:
        conn.executescript(STAGE02_EXAMPLE_SCHEMA_SQL)
        conn.execute(
            "DELETE FROM sense_meaning WHERE language='en' AND sense_id=(SELECT MIN(id) FROM sense)"
        )
    return path


def test_stage03_is_deterministic_semantic_and_read_only(
    stage02_fixture: Path, tmp_path: Path
) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    before_hash, before_size = sha256_file(stage02_fixture), stage02_fixture.stat().st_size

    first_counts = build_stage03(stage02_fixture, first)
    second_counts = build_stage03(stage02_fixture, second)
    records = read_stage03_queue(first)

    assert first.read_bytes() == second.read_bytes()
    assert first_counts == second_counts
    assert before_hash == sha256_file(stage02_fixture)
    assert before_size == stage02_fixture.stat().st_size
    assert records == sorted(records, key=lambda item: str(item["item_id"]))
    assert {str(item["target_language"]) for item in records} == {"de", "en", "fa"}
    assert {str(item["job_class"]) for item in records} >= {
        "missing_en",
        "de_learner_meaning",
        "fa_translation",
    }
    assert all("sense_id" not in item and "lemma_id" not in item for item in records)
    assert all(str(item["sense_semantic_ref"]).startswith("sense:") for item in records)


def test_stage03_refuses_overwrite_and_tampered_queue(
    stage02_fixture: Path, tmp_path: Path
) -> None:
    output = tmp_path / "queue.jsonl"
    build_stage03(stage02_fixture, output)
    with pytest.raises(BuildDictError, match="already exists"):
        build_stage03(stage02_fixture, output)
    lines = output.read_text(encoding="utf-8").splitlines()
    output.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
    with pytest.raises(BuildDictError, match="ordering"):
        read_stage03_queue(output)


def test_stage03_is_independent_of_numeric_id_and_insertion_order(
    stage02_fixture: Path, tmp_path: Path
) -> None:
    renumbered = tmp_path / "renumbered.sqlite"
    renumbered.write_bytes(stage02_fixture.read_bytes())
    with sqlite3.connect(renumbered) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("UPDATE surface_form SET lemma_id=lemma_id+10000")
        conn.execute("UPDATE example_lemma SET lemma_id=lemma_id+10000")
        conn.execute("UPDATE sense_meaning SET sense_id=sense_id+10000")
        conn.execute("UPDATE sense SET lemma_id=lemma_id+10000")
        conn.execute("UPDATE sense SET id=id+10000")
        conn.execute("UPDATE lemma SET id=id+10000")
    first, second = tmp_path / "original.jsonl", tmp_path / "renumbered.jsonl"
    build_stage03(stage02_fixture, first)
    build_stage03(renumbered, second)
    assert first.read_bytes() == second.read_bytes()


def test_stage03_has_no_network_path(
    stage02_fixture: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_socket(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("Stage 03 attempted network access")

    monkeypatch.setattr(socket, "socket", forbidden_socket)
    build_stage03(stage02_fixture, tmp_path / "network-free.jsonl")
