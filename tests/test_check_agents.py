"""Unit and integration tests for tools/check_agents.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.check_agents import (
    check_all,
    check_r1,
    check_r7,
    main,
    normalize_package_name,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_normalize_package_name() -> None:
    assert normalize_package_name("openai>=1.0.0") == "openai"
    assert normalize_package_name("Google_Genai~=0.1") == "google-genai"
    assert normalize_package_name("anthropic[extra]<=0.5") == "anthropic"
    assert normalize_package_name("german_lecture==1.0") == "german-lecture"


def test_clean_repo_passes() -> None:
    """The repository tree must pass all rule checks cleanly."""
    violations = check_all(REPO_ROOT)
    assert violations == []


def test_r1_clean_subproject(tmp_path: Path) -> None:
    """A clean subproject without LLM deps or imports passes R1."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["fastapi", "pydantic"]\n',
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text(
        "import json\nfrom pathlib import Path\n\ndef run():\n    return 42\n",
        encoding="utf-8",
    )
    assert check_r1(tmp_path) == []


@pytest.mark.parametrize(
    "forbidden_dep",
    [
        "openai>=1.0",
        "anthropic==0.20.0",
        "google-genai",
        "google_generativeai>=0.3",
        "langchain",
        "llama-index-core",
    ],
)
def test_r1_rejects_forbidden_runtime_dependencies(tmp_path: Path, forbidden_dep: str) -> None:
    """R1 rejects any forbidden LLM SDK in pyproject.toml runtime dependencies."""
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["{forbidden_dep}"]\n',
        encoding="utf-8",
    )
    violations = check_r1(tmp_path)
    assert len(violations) >= 1
    assert any("R1 violation" in v and "Forbidden runtime LLM dependency" in v for v in violations)


@pytest.mark.parametrize(
    "forbidden_code",
    [
        "import openai\n",
        "from anthropic import Anthropic\n",
        "import google.genai\n",
        "import google_genai\n",
        "from google import genai\n",
        "from google import generativeai\n",
        "from langchain.chains import LLMChain\n",
        "import litellm\n",
    ],
)
def test_r1_rejects_forbidden_imports_in_app(tmp_path: Path, forbidden_code: str) -> None:
    """R1 rejects forbidden LLM imports in any file under app/."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    app_dir = tmp_path / "app" / "submodule"
    app_dir.mkdir(parents=True)
    (app_dir / "service.py").write_text(forbidden_code, encoding="utf-8")

    violations = check_r1(tmp_path)
    assert len(violations) >= 1
    assert any("R1 violation" in v and "Forbidden LLM import" in v for v in violations)


@pytest.mark.parametrize(
    "forbidden_dep",
    [
        "german-lecture",
        "lecture-app>=0.1",
        "lecture_engine",
        "curriculum",
    ],
)
def test_r7_rejects_forbidden_runtime_dependencies(tmp_path: Path, forbidden_dep: str) -> None:
    """R7 rejects lecture-app runtime dependencies in pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["{forbidden_dep}"]\n',
        encoding="utf-8",
    )
    violations = check_r7(tmp_path)
    assert len(violations) >= 1
    assert any("R7 violation" in v and "Forbidden lecture-app dependency" in v for v in violations)


@pytest.mark.parametrize(
    "forbidden_code",
    [
        "import german_lecture\n",
        "from lecture_app.models import Lesson\n",
        "from lecture_engine import audio\n",
        "import lecture\n",
        "from curriculum import vocab\n",
    ],
)
def test_r7_rejects_forbidden_imports_in_app(tmp_path: Path, forbidden_code: str) -> None:
    """R7 rejects lecture-app imports in any file under app/."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "adapter.py").write_text(forbidden_code, encoding="utf-8")

    violations = check_r7(tmp_path)
    assert len(violations) >= 1
    assert any("R7 violation" in v and "Forbidden lecture-app import" in v for v in violations)


def test_fail_closed_on_missing_pyproject(tmp_path: Path) -> None:
    """Missing pyproject.toml causes rule checks to fail closed."""
    violations = check_all(tmp_path)
    assert len(violations) >= 1
    assert any("fail-closed" in v for v in violations)


def test_fail_closed_on_malformed_pyproject(tmp_path: Path) -> None:
    """Unparseable pyproject.toml causes rule checks to fail closed."""
    (tmp_path / "pyproject.toml").write_text(
        "[project\nname = invalid toml",
        encoding="utf-8",
    )
    violations = check_all(tmp_path)
    assert len(violations) >= 1
    assert any("fail-closed" in v and "Failed to parse" in v for v in violations)


def test_fail_closed_on_missing_project_table(tmp_path: Path) -> None:
    """pyproject.toml without [project] table fails closed."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.other]\nkey = "value"\n',
        encoding="utf-8",
    )
    violations = check_all(tmp_path)
    assert len(violations) >= 1
    assert any("missing [project] table" in v for v in violations)


def test_fail_closed_on_syntax_error_in_app(tmp_path: Path) -> None:
    """Syntax error in app/ python file causes rule checks to fail closed."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "broken.py").write_text("def broken_func(\n", encoding="utf-8")

    violations = check_all(tmp_path)
    assert len(violations) >= 1
    assert any("fail-closed" in v and "broken.py" in v for v in violations)


def test_cli_success(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI returns 0 on clean repository."""
    exit_code = main([str(REPO_ROOT)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "AGENTS checks passed" in captured.out


def test_cli_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI returns 1 on repository with violations."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "bad"\nversion = "0.1.0"\ndependencies = ["openai"]\n',
        encoding="utf-8",
    )
    exit_code = main([str(tmp_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "AGENTS check failed" in captured.err


def test_cli_subprocess_invocation() -> None:
    """Subprocess execution of tools/check_agents.py against the repository root succeeds."""
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_agents.py"), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "AGENTS checks passed" in res.stdout
