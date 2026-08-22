"""Fixture-only Stage 05 packaging tests."""

import hashlib
import json
from pathlib import Path

import pytest

from tests.test_build_dict_stage03 import make_stage02
from tools.build_dict import BuildDictError, build_stage05


def test_stage05_copies_verified_fixture_and_metadata(tmp_path: Path) -> None:
    source = make_stage02(tmp_path / "fixture.sqlite")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    output, metadata = tmp_path / "dictionary_v1.sqlite", tmp_path / "release.json"
    result = build_stage05(source, output, "v1", metadata)
    assert result == json.loads(metadata.read_text(encoding="utf-8"))
    assert result["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert result["bytes"] == output.stat().st_size
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_stage05_refuses_overwrite_and_bad_attribution(tmp_path: Path) -> None:
    source = make_stage02(tmp_path / "fixture.sqlite")
    output = tmp_path / "dictionary_v1.sqlite"
    build_stage05(source, output)
    with pytest.raises(BuildDictError, match="already exists"):
        build_stage05(source, output)
    bad = make_stage02(tmp_path / "bad.sqlite")
    import sqlite3

    conn = sqlite3.connect(bad)
    conn.execute("UPDATE sense_meaning SET license='' WHERE id=1")
    conn.commit()
    conn.close()
    with pytest.raises(BuildDictError, match="attribution"):
        build_stage05(bad, tmp_path / "bad-output.sqlite")
