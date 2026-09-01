"""Tests for tools/affected_tests.py resolver."""

# ruff: noqa: E501

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tools.affected_tests import main as affected_main

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_affected(
    capsys: pytest.CaptureFixture[str],
    paths: list[str],
    repo_root: Path = REPO_ROOT,
) -> tuple[int, str, str]:
    args = ["--repo-root", str(repo_root)] + paths
    code = affected_main(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _synthetic_base(tmp_path: Path) -> None:
    (tmp_path / "frontend" / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "frontend" / "src" / "app.ts").write_text("", encoding="utf-8")
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reference").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reference" / "schema.sql").write_text("", encoding="utf-8")


def test_audio_only_direct_change(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/audio.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "audio" in out
    assert "test_audio.py" in out
    assert "test_build_dict" not in out


def test_resolver_change_expands_through_reverse_closure(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/resolve.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "resolve" in out
    assert "dictionary" in out
    assert any(name in out for name in ["deck", "render", "export", "runtime_api"])
    assert "test_resolve" in out
    assert "test_dictionary" in out


def test_api_only_does_not_invoke_build_dict(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/api.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "runtime_api" in out
    assert "test_api" in out
    assert "test_build_dict" not in out


def test_build_dict_only_selects_stage_tests(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["tools/build_dict.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    # New MODULES.toml uses build_dict id
    assert "build_dict" in out
    for stage in ["stage01", "stage02", "stage03", "stage04", "stage05"]:
        assert stage in out


def test_frontend_api_change_selects_frontend_validation(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["frontend/src/api/client.ts"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "frontend_api" in out
    assert ("client.test.ts" in out) or ("npm test" in out) or ("FRONTEND" in out) or ("COMMANDS" in out)


def test_deterministic_ordering(capsys: pytest.CaptureFixture[str]) -> None:
    code1, out1, _ = _run_affected(capsys, ["app/resolve.py"])
    assert code1 == 0
    code2, out2, _ = _run_affected(capsys, ["app/resolve.py"])
    assert code2 == 0
    assert out1 == out2
    code3, out3, _ = _run_affected(capsys, ["app/audio.py", "app/resolve.py"])
    code4, out4, _ = _run_affected(capsys, ["app/resolve.py", "app/audio.py"])
    assert out3 == out4


def test_unmapped_path_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    # Create minimal MODULES covering inventory
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py", "tools/a.py", "frontend/src/app.ts", "reference/schema.sql", "Dockerfile"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []

        [modules.meta]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["unmapped/random.txt"], repo_root=tmp_path)
    assert code != 0
    assert "MODE=BROAD" in out
    assert "REASON" in out
    assert "pytest -q" in out


def test_malformed_metadata_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "MODULES.toml").write_text("invalid toml [[[", encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/audio.py"], repo_root=tmp_path)
    assert code != 0
    assert "MODE=BROAD" in out
    assert "pytest -q" in out


def test_frontend_unmapped_includes_frontend_note(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py", "tools/a.py", "frontend/src/app.ts", "reference/schema.sql", "Dockerfile"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []

        [modules.meta]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["frontend/src/unmapped.ts"], repo_root=tmp_path)
    assert code != 0
    assert "MODE=BROAD" in out
    assert "frontend" in out.lower()


def test_missing_focused_test_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py", "tools/a.py", "frontend/src/app.ts", "reference/schema.sql", "Dockerfile"]
        dependencies = []
        focused_tests = ["tests/missing.py"]
        agents_rules = []

        [modules.meta]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/a.py"], repo_root=tmp_path)
    assert code != 0
    assert "MODE=BROAD" in out


def test_git_diff_mode_with_real_repo(capsys: pytest.CaptureFixture[str]) -> None:
    _ = affected_main(["--repo-root", str(REPO_ROOT), "--base", "main", "--head", "HEAD"])
    captured = capsys.readouterr()
    assert "MODE=" in captured.out
    assert captured.out.strip() != ""


def test_cli_subprocess_with_explicit_path() -> None:
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "affected_tests.py"), "--repo-root", str(REPO_ROOT), "app/audio.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "MODE=FOCUSED" in res.stdout
    assert "test_audio.py" in res.stdout


def test_reverse_closure_with_synthetic_graph(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    for name in ["a", "b", "c"]:
        (tmp_path / "tests" / f"test_{name}.py").write_text("", encoding="utf-8")
        (tmp_path / "app").mkdir(parents=True, exist_ok=True)
        (tmp_path / "app" / f"{name}.py").write_text("", encoding="utf-8")
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "frontend" / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "frontend" / "src" / "app.ts").write_text("", encoding="utf-8")
    (tmp_path / "reference").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reference" / "schema.sql").write_text("", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
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
        dependencies = ["c"]
        focused_tests = ["tests/test_b.py"]
        agents_rules = []

        [modules.c]
        owned_paths = ["app/c.py", "tools/a.py", "frontend/src/app.ts", "reference/schema.sql", "Dockerfile"]
        dependencies = []
        focused_tests = ["tests/test_c.py"]
        agents_rules = []

        [modules.meta]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/c.py"], repo_root=tmp_path)
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "a" in out and "b" in out and "c" in out
    assert "test_a.py" in out and "test_b.py" in out and "test_c.py" in out
    code2, out2, _ = _run_affected(capsys, ["app/a.py"], repo_root=tmp_path)
    assert code2 == 0
    assert "MODULES=a" in out2
    assert "test_b.py" not in out2 and "test_c.py" not in out2
