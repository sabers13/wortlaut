"""Tests for tools/affected_tests.py resolver — direct-owner semantics only."""

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


# ---------------------------------------------------------------------------
# Direct-owner examples — must match the repair spec exactly
# ---------------------------------------------------------------------------


def test_audio_direct_owner_only(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/audio.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=audio" in out
    assert "tests/test_audio.py" in out
    # Must NOT expand to reverse dependents (e.g. runtime_api depends on audio)
    assert "runtime_api" not in out
    assert "test_api.py" not in out
    assert "test_build_dict" not in out
    # Exactly one module, exactly its focused tests
    assert out.count("test_audio.py") >= 1
    # PYTEST line must contain only that test
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            assert line.strip() == "PYTEST=pytest -q tests/test_audio.py"


def test_resolve_direct_owner_only_no_closure(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/resolve.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=resolve" in out
    assert "tests/test_resolve.py" in out
    assert "tests/test_resolve_spacy.py" in out
    # Must NOT pull transitive reverse dependents
    assert "dictionary" not in out
    assert "test_dictionary" not in out
    assert "test_render" not in out
    assert "test_deck" not in out
    assert "runtime_api" not in out
    assert "test_api" not in out
    assert "build_dict" not in out
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            # Sorted deterministic: test_resolve.py before test_resolve_spacy.py
            assert line.strip() == "PYTEST=pytest -q tests/test_resolve.py tests/test_resolve_spacy.py"
        if line.startswith("MODULES="):
            assert line.strip() == "MODULES=resolve"


def test_api_direct_owner_only(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/api.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=runtime_api" in out
    assert "tests/test_api.py" in out
    assert "tests/test_capture.py" in out
    assert "tests/test_smoke_baseline.py" in out
    # Must NOT invoke unrelated modules
    assert "test_build_dict" not in out
    assert "test_audio" not in out
    assert "test_resolve" not in out
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            assert line.strip() == "PYTEST=pytest -q tests/test_api.py tests/test_capture.py tests/test_smoke_baseline.py"
        if line.startswith("MODULES="):
            assert line.strip() == "MODULES=runtime_api"


def test_build_dict_direct_owner_only(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["tools/build_dict.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=build_dict" in out
    for stage in ["stage01", "stage02", "stage03", "stage04", "stage05"]:
        assert stage in out
    # Must not include non-direct tests
    assert "test_audio" not in out
    assert "test_api" not in out
    # Verify exact sorted PYTEST line
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            assert line.strip() == (
                "PYTEST=pytest -q tests/test_build_dict_stage01.py tests/test_build_dict_stage02.py "
                "tests/test_build_dict_stage03.py tests/test_build_dict_stage04.py tests/test_build_dict_stage05.py"
            )


def test_frontend_api_direct_owner_only(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["frontend/src/api/client.ts"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=frontend_api" in out
    # frontend_api focused_tests and commands only
    assert "frontend/src/api/client.test.ts" in out
    # Must NOT include frontend_shell
    assert "frontend_shell" not in out
    assert "product.spec.ts" not in out
    assert "npm run --prefix frontend build" not in out
    # Should contain frontend_api commands, sorted deterministically
    assert "npm test --prefix frontend" in out
    assert "npm run --prefix frontend typecheck" in out
    # Pure frontend must NOT emit PYTEST fallback; no runtime Python tests
    assert "PYTEST=" not in out
    assert "tests/test_" not in out
    assert "runtime_api" not in out
    for line in out.splitlines():
        if line.startswith("MODULES="):
            assert line.strip() == "MODULES=frontend_api"
        if line.startswith("FRONTEND_TESTS="):
            assert "frontend/src/api/client.test.ts" in line
        if line.startswith("COMMANDS="):
            assert "npm test --prefix frontend" in line


def test_frontend_shell_direct_owner_only(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["frontend/src/app.ts"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=frontend_shell" in out
    # Pure frontend must NOT emit PYTEST fallback
    assert "PYTEST=" not in out
    assert "tests/test_" not in out
    # Must NOT include frontend_api expansion (direct-owner only)
    for line in out.splitlines():
        if line.startswith("MODULES="):
            assert line.strip() == "MODULES=frontend_shell"
    assert "frontend_api" not in out
    # Audit-required iteration validation for frontend_shell
    assert "npm run --prefix frontend typecheck" in out
    assert "npm run --prefix frontend test:e2e" in out
    # Must contain e2e frontend test
    assert "frontend/tests/e2e/product.spec.ts" in out
    # Should not contain generic npm test for api (that's frontend_api only)
    # but ensure at least typecheck + e2e are present in COMMANDS
    for line in out.splitlines():
        if line.startswith("FRONTEND_TESTS="):
            assert "frontend/tests/e2e/product.spec.ts" in line
        if line.startswith("COMMANDS="):
            assert "npm run --prefix frontend typecheck" in line
            assert "npm run --prefix frontend test:e2e" in line


# ---------------------------------------------------------------------------
# Multiple paths — union of direct owners, no closure
# ---------------------------------------------------------------------------


def test_multiple_direct_union_audio_resolve(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/audio.py", "app/resolve.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    # Sorted union
    assert "MODULES=audio,resolve" in out
    assert "tests/test_audio.py" in out
    assert "tests/test_resolve.py" in out
    assert "tests/test_resolve_spacy.py" in out
    # Must not include transitive dependents
    assert "test_dictionary" not in out
    assert "test_api" not in out
    # Deterministic ordering check via PYTEST sort
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            assert line.strip() == "PYTEST=pytest -q tests/test_audio.py tests/test_resolve.py tests/test_resolve_spacy.py"


def test_multiple_direct_union_api_audio(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/api.py", "app/audio.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=audio,runtime_api" in out
    assert "tests/test_audio.py" in out
    assert "tests/test_api.py" in out
    assert "tests/test_capture.py" in out
    assert "tests/test_smoke_baseline.py" in out
    # No closure spillover
    assert "test_resolve" not in out
    assert "test_dictionary" not in out


def test_multiple_direct_union_frontend_and_audio(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["frontend/src/api/client.ts", "app/audio.py"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=audio,frontend_api" in out
    assert "tests/test_audio.py" in out
    assert "frontend/src/api/client.test.ts" in out
    # Mixed must emit focused Python PYTEST for audio only and frontend validation
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            assert line.strip() == "PYTEST=pytest -q tests/test_audio.py"
        if line.startswith("MODULES="):
            assert line.strip() == "MODULES=audio,frontend_api"
        if line.startswith("FRONTEND_TESTS="):
            assert "frontend/src/api/client.test.ts" in line
        if line.startswith("COMMANDS="):
            assert "npm test --prefix frontend" in line
    # Must NOT expand to non-direct owners
    assert "runtime_api" not in out
    assert "frontend_shell" not in out
    assert "product.spec.ts" not in out
    assert "test_capture" not in out


def test_mixed_audio_frontend_exact_shape(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_affected(capsys, ["app/audio.py", "frontend/src/api/client.ts"])
    assert code == 0
    assert "MODE=FOCUSED" in out
    # Order independence: both orderings must produce same sorted output
    code2, out2, _ = _run_affected(capsys, ["frontend/src/api/client.ts", "app/audio.py"])
    assert code2 == 0
    assert out == out2
    assert "MODULES=audio,frontend_api" in out
    for line in out.splitlines():
        if line.startswith("PYTEST="):
            assert line.strip() == "PYTEST=pytest -q tests/test_audio.py"
        if line.startswith("MODULES="):
            assert line.strip() == "MODULES=audio,frontend_api"
    assert "frontend/src/api/client.test.ts" in out
    assert "npm test --prefix frontend" in out
    assert "runtime_api" not in out
    assert "frontend_shell" not in out


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_deterministic_ordering(capsys: pytest.CaptureFixture[str]) -> None:
    code1, out1, _ = _run_affected(capsys, ["app/resolve.py"])
    assert code1 == 0
    code2, out2, _ = _run_affected(capsys, ["app/resolve.py"])
    assert code2 == 0
    assert out1 == out2
    code3, out3, _ = _run_affected(capsys, ["app/audio.py", "app/resolve.py"])
    code4, out4, _ = _run_affected(capsys, ["app/resolve.py", "app/audio.py"])
    assert out3 == out4
    code5, out5, _ = _run_affected(capsys, ["app/api.py", "app/audio.py", "app/resolve.py"])
    code6, out6, _ = _run_affected(capsys, ["app/resolve.py", "app/api.py", "app/audio.py"])
    assert out5 == out6


def test_deterministic_repeated_frontend(capsys: pytest.CaptureFixture[str]) -> None:
    code1, out1, _ = _run_affected(capsys, ["frontend/src/api/client.ts"])
    code2, out2, _ = _run_affected(capsys, ["frontend/src/api/client.ts"])
    assert code1 == 0 and code2 == 0
    assert out1 == out2


def test_deterministic_repeated_frontend_shell(capsys: pytest.CaptureFixture[str]) -> None:
    code1, out1, _ = _run_affected(capsys, ["frontend/src/app.ts"])
    code2, out2, _ = _run_affected(capsys, ["frontend/src/app.ts"])
    assert code1 == 0 and code2 == 0
    assert out1 == out2
    # Deterministic sorted output: repeated mixed ordering same result
    code3, out3, _ = _run_affected(capsys, ["app/audio.py", "frontend/src/api/client.ts"])
    code4, out4, _ = _run_affected(capsys, ["frontend/src/api/client.ts", "app/audio.py"])
    assert out3 == out4


def test_deterministic_mixed_and_broad(capsys: pytest.CaptureFixture[str]) -> None:
    code1, out1, _ = _run_affected(capsys, ["app/audio.py", "frontend/src/api/client.ts"])
    code2, out2, _ = _run_affected(capsys, ["frontend/src/api/client.ts", "app/audio.py"])
    assert out1 == out2
    # Frontend unmapped broad should be deterministic as well (synthetic check via real repo)
    # Repeated frontend_api call already verified; ensure shell repeatability
    code3, out3, _ = _run_affected(capsys, ["frontend/src/app.ts"])
    code4, out4, _ = _run_affected(capsys, ["frontend/src/app.ts"])
    assert out3 == out4


# ---------------------------------------------------------------------------
# BROAD fallback — conservative
# ---------------------------------------------------------------------------


def test_unmapped_path_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
    code, out, _ = _run_affected(capsys, ["unmapped/random.txt"], repo_root=tmp_path)
    assert code == 2
    assert "MODE=BROAD" in out
    assert "REASON" in out
    assert "pytest -q" in out


def test_ambiguous_ownership_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "dup.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_b.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
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
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    # Ensure inventory files exist
    (tmp_path / "app" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tools" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "reference" / "smoke_test.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_dummy.py").write_text("", encoding="utf-8")
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/dup.py"], repo_root=tmp_path)
    assert code == 2
    assert "MODE=BROAD" in out
    assert "ambiguous" in out.lower()


def test_malformed_metadata_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "MODULES.toml").write_text("invalid toml [[[", encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/audio.py"], repo_root=tmp_path)
    assert code == 2
    assert "MODE=BROAD" in out
    assert "pytest -q" in out


def test_invalid_dependency_metadata_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tools" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "reference" / "smoke_test.py").write_text("x=1\n", encoding="utf-8")
    content = textwrap.dedent("""
        [modules.a]
        owned_paths = ["app/a.py"]
        dependencies = ["nonexistent"]
        focused_tests = ["tests/test_a.py"]
        agents_rules = []

        [modules.b]
        owned_paths = ["app/dummy.py", "tools/dummy.py", "reference/schema.sql", "reference/smoke_test.py", "frontend/src/app.ts", "Dockerfile", "MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/a.py"], repo_root=tmp_path)
    assert code == 2
    assert "MODE=BROAD" in out
    assert "unknown dependency" in out.lower()


def test_dependency_cycle_gives_broad(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _synthetic_base(tmp_path)
    (tmp_path / "app" / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_b.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "check_modules.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "affected_tests.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "tools" / "dummy.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "reference" / "smoke_test.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
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
        focused_tests = ["tests/test_a.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/a.py"], repo_root=tmp_path)
    assert code == 2
    assert "MODE=BROAD" in out
    assert "cycle" in out.lower()


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
    assert code == 2
    assert "MODE=BROAD" in out
    assert "frontend" in out.lower()
    # BROAD must keep conservative guidance: PYTEST and FRONTEND present
    assert "PYTEST=pytest -q" in out
    assert "FRONTEND=" in out
    assert "npm test --prefix frontend" in out
    assert "NOTE=" in out

    # Also verify real repo BROAD frontend-unmapped keeps same behavior
    code2, out2, _ = _run_affected(capsys, ["frontend/src/does-not-exist.ts"])
    assert code2 == 2
    assert "MODE=BROAD" in out2
    assert "PYTEST=pytest -q" in out2
    assert "FRONTEND=" in out2


def test_broad_frontend_unmapped_conservative(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
    code, out, _ = _run_affected(capsys, ["frontend/unmapped/random.ts"], repo_root=tmp_path)
    assert code == 2
    assert "MODE=BROAD" in out
    assert "REASON=" in out
    assert "PYTEST=pytest -q" in out
    assert "FRONTEND=npm test --prefix frontend" in out
    assert "NOTE=frontend authoritative checks may be required" in out


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
    assert code == 2
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
    assert "MODULES=audio" in res.stdout
    assert "test_audio.py" in res.stdout
    assert "runtime_api" not in res.stdout


def test_no_reverse_closure_synthetic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Synthetic graph a→b→c must NOT expand c into a,b."""
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
    # Changing leaf c must NOT pull a,b
    code, out, _ = _run_affected(capsys, ["app/c.py"], repo_root=tmp_path)
    assert code == 0
    assert "MODE=FOCUSED" in out
    assert "MODULES=c" in out
    assert "test_c.py" in out
    assert "test_a.py" not in out
    assert "test_b.py" not in out
    # Changing a must NOT pull b,c
    code2, out2, _ = _run_affected(capsys, ["app/a.py"], repo_root=tmp_path)
    assert code2 == 0
    assert "MODULES=a" in out2
    assert "test_b.py" not in out2 and "test_c.py" not in out2
    # Changing b must NOT pull a,c
    code3, out3, _ = _run_affected(capsys, ["app/b.py"], repo_root=tmp_path)
    assert code3 == 0
    assert "MODULES=b" in out3
    assert "test_a.py" not in out3 and "test_c.py" not in out3
    # Multiple leaves union must be exact, no transitive spill
    code4, out4, _ = _run_affected(capsys, ["app/b.py", "app/c.py"], repo_root=tmp_path)
    assert code4 == 0
    assert "MODULES=b,c" in out4
    assert "test_b.py" in out4 and "test_c.py" in out4
    assert "test_a.py" not in out4


def test_direct_union_does_not_chain_through_dependencies(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Even when changed paths include both ends of a dependency chain,
    result must be union of direct modules only, not closure of intermediates."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    for name in ["x", "y", "z"]:
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
        [modules.x]
        owned_paths = ["app/x.py"]
        dependencies = ["y"]
        focused_tests = ["tests/test_x.py"]
        agents_rules = []

        [modules.y]
        owned_paths = ["app/y.py"]
        dependencies = ["z"]
        focused_tests = ["tests/test_y.py"]
        agents_rules = []

        [modules.z]
        owned_paths = ["app/z.py", "tools/a.py", "frontend/src/app.ts", "reference/schema.sql", "Dockerfile"]
        dependencies = []
        focused_tests = ["tests/test_z.py"]
        agents_rules = []

        [modules.meta]
        owned_paths = ["MODULES.toml", "tools/check_modules.py", "tools/affected_tests.py"]
        dependencies = []
        focused_tests = ["tests/test_x.py"]
        agents_rules = []
    """)
    (tmp_path / "MODULES.toml").write_text(content, encoding="utf-8")
    code, out, _ = _run_affected(capsys, ["app/x.py", "app/z.py"], repo_root=tmp_path)
    assert code == 0
    assert "MODULES=x,z" in out
    assert "test_x.py" in out and "test_z.py" in out
    assert "test_y.py" not in out
