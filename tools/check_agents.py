"""Executable AGENTS rule checker for project gate.

Enforces:
- R1: Runtime LLM SDK prohibition (pyproject.toml runtime deps and app/ imports)
- R7: Zero lecture-app coupling (no imports or dependencies on lecture app)
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import Final, Sequence

# Canonical forbidden LLM package names (normalized with hyphens and lowercase)
FORBIDDEN_LLM_PACKAGES: Final[frozenset[str]] = frozenset({
    "anthropic",
    "cohere",
    "google-genai",
    "google-generativeai",
    "groq",
    "huggingface-hub",
    "instructor",
    "langchain",
    "litellm",
    "llama-index",
    "mistralai",
    "ollama",
    "openai",
    "transformers",
    "vllm",
})

# Canonical forbidden LLM Python module import prefixes
FORBIDDEN_LLM_MODULES: Final[frozenset[str]] = frozenset({
    "anthropic",
    "cohere",
    "google.genai",
    "google.generativeai",
    "google_genai",
    "groq",
    "huggingface_hub",
    "instructor",
    "langchain",
    "litellm",
    "llama_index",
    "mistralai",
    "ollama",
    "openai",
    "transformers",
    "vllm",
})

# Canonical forbidden lecture app package names (normalized)
FORBIDDEN_LECTURE_PACKAGES: Final[frozenset[str]] = frozenset({
    "curriculum",
    "german-lecture",
    "lecture",
    "lecture-app",
    "lecture-engine",
})

# Canonical forbidden lecture app Python module import prefixes
FORBIDDEN_LECTURE_MODULES: Final[frozenset[str]] = frozenset({
    "curriculum",
    "german_lecture",
    "lecture",
    "lecture_app",
    "lecture_engine",
})


def normalize_package_name(dep: str) -> str:
    """Extract and normalize base package name from a PEP 508 dependency string."""
    # Match leading package name before version/specifier/marker
    match = re.match(r"^([a-zA-Z0-9_.-]+)", dep.strip())
    if not match:
        return dep.strip().lower().replace("_", "-")
    return match.group(1).lower().replace("_", "-")


def is_forbidden_llm_package(dep: str) -> bool:
    """Check if dependency string matches any forbidden LLM package name or prefix."""
    pkg = normalize_package_name(dep)
    if pkg in FORBIDDEN_LLM_PACKAGES:
        return True
    return any(pkg.startswith(f"{p}-") or pkg.startswith(f"{p}_") for p in FORBIDDEN_LLM_PACKAGES)


def is_forbidden_llm_module(mod: str) -> bool:
    """Check if imported module matches any forbidden LLM module prefix."""
    top = mod.split(".")[0]
    for forbidden in FORBIDDEN_LLM_MODULES:
        if mod == forbidden or mod.startswith(f"{forbidden}.") or top == forbidden:
            return True
    return False


def is_forbidden_lecture_package(dep: str) -> bool:
    """Check if dependency string matches any forbidden lecture app package name or prefix."""
    pkg = normalize_package_name(dep)
    if pkg in FORBIDDEN_LECTURE_PACKAGES:
        return True
    return any(
        pkg.startswith(f"{p}-") or pkg.startswith(f"{p}_") for p in FORBIDDEN_LECTURE_PACKAGES
    )


def is_forbidden_lecture_module(mod: str) -> bool:
    """Check if imported module matches any forbidden lecture app module prefix."""
    top = mod.split(".")[0]
    for forbidden in FORBIDDEN_LECTURE_MODULES:
        if mod == forbidden or mod.startswith(f"{forbidden}.") or top == forbidden:
            return True
    return False


def parse_pyproject(repo_root: Path) -> dict[str, object]:
    """Parse pyproject.toml at repo_root, failing closed on missing or malformed file."""
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"Missing required configuration: {pyproject_path}")
    try:
        content = pyproject_path.read_text(encoding="utf-8")
        return tomllib.loads(content)
    except Exception as e:
        raise ValueError(f"Failed to parse {pyproject_path}: {e}") from e


def get_runtime_dependencies(pyproject_data: dict[str, object]) -> list[str]:
    """Extract runtime dependencies from parsed pyproject.toml."""
    project_table = pyproject_data.get("project")
    if not isinstance(project_table, dict):
        raise ValueError("pyproject.toml is missing [project] table")
    deps = project_table.get("dependencies", [])
    if not isinstance(deps, list):
        raise ValueError("[project.dependencies] must be a list")
    for item in deps:
        if not isinstance(item, str):
            raise ValueError(f"Invalid dependency entry: {item}")
    return list(deps)


def get_app_python_files(repo_root: Path) -> list[Path]:
    """Find all .py files in app/ directory if it exists."""
    app_dir = repo_root / "app"
    if not app_dir.exists():
        return []
    if not app_dir.is_dir():
        raise ValueError(f"Expected app to be a directory, but found: {app_dir}")
    return sorted(app_dir.rglob("*.py"))


def collect_imports_from_file(file_path: Path) -> list[str]:
    """Parse AST of a python file and return all imported module paths.

    Fails closed on syntax errors or read errors.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except Exception as e:
        raise ValueError(f"Failed to read/parse Python file {file_path}: {e}") from e

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")
    return imports


def check_r1(repo_root: Path) -> list[str]:
    """Check AGENTS Rule R1: No LLM at runtime.

    Scans pyproject.toml runtime dependencies and app/ imports.
    """
    violations: list[str] = []

    # 1. Check runtime dependencies in pyproject.toml
    try:
        pyproject_data = parse_pyproject(repo_root)
        runtime_deps = get_runtime_dependencies(pyproject_data)
        for dep in runtime_deps:
            if is_forbidden_llm_package(dep):
                violations.append(
                    f"R1 violation: Forbidden runtime LLM dependency '{dep}' in pyproject.toml"
                )
    except Exception as e:
        violations.append(f"R1 fail-closed: {e}")

    # 2. Check imports in app/
    try:
        app_files = get_app_python_files(repo_root)
        for py_file in app_files:
            try:
                imported_modules = collect_imports_from_file(py_file)
                for mod in imported_modules:
                    if is_forbidden_llm_module(mod):
                        violations.append(
                            f"R1 violation: Forbidden LLM import '{mod}' in {py_file}"
                        )
            except Exception as e:
                violations.append(f"R1 fail-closed: {e}")
    except Exception as e:
        violations.append(f"R1 fail-closed: {e}")

    return violations


def check_r7(repo_root: Path) -> list[str]:
    """Check AGENTS Rule R7: Zero coupling to the lecture app.

    Scans pyproject.toml runtime dependencies and app/ imports.
    """
    violations: list[str] = []

    # 1. Check runtime dependencies in pyproject.toml
    try:
        pyproject_data = parse_pyproject(repo_root)
        runtime_deps = get_runtime_dependencies(pyproject_data)
        for dep in runtime_deps:
            if is_forbidden_lecture_package(dep):
                violations.append(
                    f"R7 violation: Forbidden lecture-app dependency '{dep}' in pyproject.toml"
                )
    except Exception as e:
        violations.append(f"R7 fail-closed: {e}")

    # 2. Check imports in app/
    try:
        app_files = get_app_python_files(repo_root)
        for py_file in app_files:
            try:
                imported_modules = collect_imports_from_file(py_file)
                for mod in imported_modules:
                    if is_forbidden_lecture_module(mod):
                        violations.append(
                            f"R7 violation: Forbidden lecture-app import '{mod}' in {py_file}"
                        )
            except Exception as e:
                violations.append(f"R7 fail-closed: {e}")
    except Exception as e:
        violations.append(f"R7 fail-closed: {e}")

    return violations


def check_all(repo_root: Path) -> list[str]:
    """Run all scaffolded executable rule checks (R1, R7)."""
    violations: list[str] = []
    violations.extend(check_r1(repo_root))
    violations.extend(check_r7(repo_root))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for executable AGENTS checks."""
    args = sys.argv[1:] if argv is None else list(argv)
    repo_root = Path(args[0]) if args else Path.cwd()

    violations = check_all(repo_root)
    if violations:
        sys.stderr.write("AGENTS check failed with the following violations:\n")
        for v in violations:
            sys.stderr.write(f"  - {v}\n")
        return 1

    sys.stdout.write("AGENTS checks passed: R1 (runtime LLM), R7 (lecture coupling)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
