"""Tests for tools/check_modules.py validation."""

# ruff: noqa: E501

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tools.check_modules import check_all
from tools.check_modules import main as check_modules_main

REPO_ROOT = Path(__file__).resolve().parent.parent


def _synthetic_base(tmp_path: Path) -> None:
    """Create minimal inventory files required by the validator."""
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reference").mkdir(parents=True, exist_ok=True)
    (tmp_path / "frontend" / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    # Inventory files
    (tmp_path / "app" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tools" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "reference" / "schema.sql").write_text("select 1;\n", encoding="utf-8")
    (tmp_path / "reference" / "smoke_test.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "frontend" / "src" / "app.ts").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    # Dummy focused tests
    (tmp_path / "tests" / "test_dummy.py").write_text("def test_dummy(): pass\n", encoding="utf-8")


def test_valid_real_modules_toml(capsys: pytest.CaptureFixture[str]) -> None:
    code = check_modules_main([str(REPO_ROOT / "MODULES.toml")])
    assert code == 0
    out = capsys.readouterr().out
    assert "MODULES validation passed:" in out


def test_malformed_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "MODULES.toml").write_text("invalid toml [[[", encoding="utf-8")
    code = check_modules_main([str(tmp_path / "MODULES.toml")])
    assert code != 0
    err = capsys.readouterr().err
    assert "failed" in err.lower() or "malformed" in err.lower()


def test_unknown_dependency(tmp_path: Path) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py", "app/dummy.py", "tools/dummy.py", "reference/schema.sql", "reference/smoke_test.py", "frontend/src/app.ts", "Dockerfile"]
        dependencies = ["nonexistent"]
        focused_tests = ["tests/test_a.py"]
        agents_rules = []

        [modules.b]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_dummy.py"]
        agents_rules = []
    """)
    # Ensure module_metadata files exist for that check
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    violations, _ = check_all(tmp_path / "MODULES.toml")
    assert any("unknown dependency" in v.lower() for v in violations)


def test_missing_focused_test(tmp_path: Path) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py", "app/dummy.py", "tools/dummy.py", "reference/schema.sql", "reference/smoke_test.py", "frontend/src/app.ts", "Dockerfile"]
        dependencies = []
        focused_tests = ["tests/missing.py"]
        agents_rules = []

        [modules.b]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_dummy.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    violations, _ = check_all(tmp_path / "MODULES.toml")
    assert any("focused-test" in v.lower() and "does not exist" in v.lower() for v in violations)


def test_duplicate_ambiguous_ownership(tmp_path: Path) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "dup.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_b.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    # Need to also ensure other inventory files are covered uniquely
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/dup.py"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []

        [modules.b]
        owned_paths = ["app/dup.py"]
        dependencies = []
        focused_tests = ["tests/test_b.py"]
        agents_rules = []

        [modules.c]
        owned_paths = ["app/dummy.py", "tools/dummy.py", "reference/schema.sql", "reference/smoke_test.py", "frontend/src/app.ts", "Dockerfile", "MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_dummy.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    violations, _ = check_all(tmp_path / "MODULES.toml")
    assert any("ambiguous" in v.lower() for v in violations)


def test_dependency_cycle(tmp_path: Path) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_b.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py"]
        dependencies = ["b"]
        focused_tests = ["tests/test_a.py"]
        agents_rules = []

        [modules.b]
        owned_paths = ["app/b.py"]
        dependencies = ["a"]
        focused_tests = ["tests/test_b.py"]
        agents_rules = []

        [modules.c]
        owned_paths = ["app/dummy.py", "tools/dummy.py", "reference/schema.sql", "reference/smoke_test.py", "frontend/src/app.ts", "Dockerfile", "MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_dummy.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    violations, _ = check_all(tmp_path / "MODULES.toml")
    assert any("cycle" in v.lower() for v in violations)


def test_cli_subprocess() -> None:
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_modules.py"), str(REPO_ROOT / "MODULES.toml")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "MODULES validation passed" in res.stdout
