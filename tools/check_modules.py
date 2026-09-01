"""Validator for MODULES.toml.

Ensures the canonical machine-readable module map is internally consistent
and that every tracked source file under the inventory roots
(`app/`, `tools/`, `frontend/src/`, `reference/`, plus `Dockerfile`) is
claimed by exactly one module. Wired into the authoritative `make gate`
via the `check-modules` Makefile target; standalone-invokable for
maintainers and CI.

All checks fail closed: any inconsistency prints a numbered diagnostic
to stderr and exits 1. Success prints a single concise line to stdout.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path

REPO_ROOT_DEFAULT: Path = Path(__file__).resolve().parent.parent
MODULES_FILENAME: str = "MODULES.toml"

REQUIRED_FIELDS: tuple[str, ...] = (
    "owned_paths",
    "dependencies",
    "focused_tests",
    "agents_rules",
)

OPTIONAL_FIELDS: tuple[str, ...] = (
    "id",
    "focused_commands",
    "adrs",
)

ALLOWED_FIELDS: frozenset[str] = frozenset(REQUIRED_FIELDS) | frozenset(OPTIONAL_FIELDS)

INVENTORY_ROOTS: tuple[str, ...] = (
    "app",
    "tools",
    "reference",
    "frontend/src",
)
INVENTORY_FILES: tuple[str, ...] = ("Dockerfile",)

EXCLUDED_TOP_DIRS: frozenset[str] = frozenset({
    ".git",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
    "handoff",
    "tmp",
    "frontend/test-results",
    "frontend/playwright-report",
})

VALID_GLOB_CHARS: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_./*?\[\]!+\-]+$")


def _print_diagnostics(prefix: str, items: Iterable[str]) -> None:
    for idx, item in enumerate(items, start=1):
        sys.stderr.write(f"  {prefix} {idx:>3}. {item}\n")


def _load_modules(modules_path: Path) -> tuple[dict[str, object] | None, str | None]:
    """Return (data, error). On any failure, data is None and error explains."""
    if not modules_path.is_file():
        return None, f"MODULES.toml not found at {modules_path}"
    try:
        with modules_path.open("rb") as fh:
            return tomllib.load(fh), None
    except tomllib.TOMLDecodeError as exc:
        return None, f"malformed MODULES.toml at {modules_path}: {exc}"
    except OSError as exc:
        return None, f"failed to read MODULES.toml at {modules_path}: {exc}"


def _validate_module_schema(
    modules: dict[str, object],
) -> tuple[list[str], dict[str, dict[str, object]]]:
    """Validate every module entry's type and required fields.

    Returns (violations, valid_modules) keyed by table-key (the implicit
    id). On any per-module violation, that module is omitted from the
    returned dict so the rest of the validator does not raise on absent
    fields. Duplicate table keys are caught by the underlying TOML parser
    before this is reached; the defensive check is on a per-table
    explicit ``id`` field that collides with another module's id.
    """
    violations: list[str] = []
    valid: dict[str, dict[str, object]] = {}

    if not isinstance(modules, dict):
        violations.append("MODULES.toml: top-level [modules] table is missing or not a table")
        return violations, valid

    seen_ids: dict[str, str] = {}
    for raw_id, raw_mod in modules.items():
        if not isinstance(raw_mod, dict):
            violations.append(
                f"MODULES.toml: module '{raw_id}' must be a table, got {type(raw_mod).__name__}"
            )
            continue

        mod = dict(raw_mod)

        explicit_id_obj = mod.get("id")
        if explicit_id_obj is None:
            effective_id = raw_id
        elif isinstance(explicit_id_obj, str):
            effective_id = explicit_id_obj
            if explicit_id_obj != raw_id:
                violations.append(
                    f"MODULES.toml: module table key '{raw_id}' does not match "
                    f"its explicit 'id' field '{explicit_id_obj}'"
                )
        else:
            violations.append(
                f"MODULES.toml: module '{raw_id}' field 'id' must be a string"
            )
            effective_id = raw_id

        if effective_id in seen_ids:
            violations.append(
                f"MODULES.toml: duplicate module id '{effective_id}' "
                f"(first declared under table key '{seen_ids[effective_id]}', "
                f"also under '{raw_id}')"
            )
        else:
            seen_ids[effective_id] = raw_id

        mod["id"] = effective_id

        extra = set(mod) - ALLOWED_FIELDS
        if extra:
            violations.append(
                f"MODULES.toml: module '{raw_id}' has unknown field(s): "
                + ", ".join(sorted(extra))
            )

        missing = [f for f in REQUIRED_FIELDS if f not in mod]
        if missing:
            violations.append(
                f"MODULES.toml: module '{raw_id}' missing required field(s): "
                + ", ".join(missing)
            )
            continue

        for field in REQUIRED_FIELDS:
            value = mod.get(field)
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                violations.append(
                    f"MODULES.toml: module '{raw_id}' field '{field}' must be a list of strings"
                )

        for opt in OPTIONAL_FIELDS:
            if opt in mod and opt != "id":
                value = mod[opt]
                if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                    violations.append(
                        f"MODULES.toml: module '{raw_id}' field '{opt}' must be a list of strings"
                    )

        valid[raw_id] = mod

    return violations, valid


def _check_glob_pattern(pattern: str) -> str | None:
    """Return an error message if the glob pattern is invalid; None if OK."""
    if not pattern:
        return "empty pattern"
    if pattern.startswith("/"):
        return "absolute path patterns are forbidden"
    if "\\" in pattern:
        return "patterns must use forward slashes"
    segments = pattern.split("/")
    if any(seg == ".." for seg in segments):
        return "patterns must not contain '..' segments"
    if not VALID_GLOB_CHARS.match(pattern):
        return "pattern contains characters outside the allowed glob grammar"
    return None


def _check_dependencies(
    modules: dict[str, dict[str, object]],
) -> list[str]:
    """Validate cross-references and structure of the dependency graph."""
    violations: list[str] = []
    ids = set(modules)

    for mod_id, mod in modules.items():
        deps: list[str] = mod.get("dependencies", [])  # type: ignore[assignment]
        seen_dep: set[str] = set()
        for dep in deps:
            if dep not in ids:
                violations.append(
                    f"module '{mod_id}' has unknown dependency '{dep}'"
                )
            elif dep == mod_id:
                violations.append(
                    f"module '{mod_id}' has self-dependency '{dep}'"
                )
            elif dep in seen_dep:
                violations.append(
                    f"module '{mod_id}' has duplicate dependency '{dep}'"
                )
            seen_dep.add(dep)

    return violations


def _detect_cycles(
    modules: dict[str, dict[str, object]],
) -> list[str]:
    """Detect cycles in the dependency graph using DFS colouring."""
    violations: list[str] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    colour: dict[str, int] = {mid: WHITE for mid in modules}

    def dfs(node: str, stack: list[str]) -> None:
        colour[node] = GRAY
        stack.append(node)
        deps: list[str] = modules[node].get("dependencies", [])  # type: ignore[assignment]
        for dep in deps:
            if dep not in colour:
                continue
            if colour[dep] == GRAY:
                idx = stack.index(dep)
                cycle: list[str] = stack[idx:] + [dep]
                violations.append(
                    "module dependency cycle: " + " -> ".join(cycle)
                )
                continue
            if colour[dep] == WHITE:
                dfs(dep, stack)
        stack.pop()
        colour[node] = BLACK

    for mid in modules:
        if colour[mid] == WHITE:
            dfs(mid, [])

    return violations


def _is_escaping(repo_root: Path, rel: str) -> bool:
    """True if the relative path resolves outside the repo root."""
    if not rel:
        return True
    if rel.startswith("/"):
        return True
    if "\\" in rel:
        return True
    if ".." in Path(rel).parts:
        return True
    try:
        (repo_root / rel).resolve().relative_to(repo_root.resolve())
        return False
    except ValueError:
        return True


def _check_focused_tests(
    modules: dict[str, dict[str, object]],
    repo_root: Path,
) -> list[str]:
    """Validate every focused_tests path exists and stays under repo root."""
    violations: list[str] = []
    for mod_id, mod in modules.items():
        tests: list[str] = mod.get("focused_tests", [])  # type: ignore[assignment]
        for test_path in tests:
            err = _check_glob_pattern(test_path)
            if err is not None:
                violations.append(
                    f"module '{mod_id}' focused_tests path invalid: {test_path}: {err}"
                )
                continue
            if _is_escaping(repo_root, test_path):
                violations.append(
                    f"module '{mod_id}' focused-test path escapes repository root: {test_path}"
                )
                continue
            if not (repo_root / test_path).exists():
                violations.append(
                    f"module '{mod_id}' focused-test path does not exist on disk: {test_path}"
                )
    return violations


def _enumerate_tracked_inventory(repo_root: Path) -> list[str]:
    """Return repo-relative paths under inventory roots/files."""
    repo_root = repo_root.resolve()
    inventory: set[str] = set()

    for root in INVENTORY_ROOTS:
        root_path = repo_root / root
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(repo_root).as_posix()
            if "__pycache__" in rel:
                continue
            parts = set(rel.split("/"))
            if parts & EXCLUDED_TOP_DIRS:
                continue
            inventory.add(rel)

    for top in INVENTORY_FILES:
        top_path = repo_root / top
        if top_path.is_file():
            inventory.add(top)

    return sorted(inventory)


def _check_ownership(
    modules: dict[str, dict[str, object]],
    repo_root: Path,
) -> list[str]:
    """Ensure every inventory file is owned by exactly one module."""
    violations: list[str] = []

    patterns_by_module: dict[str, list[str]] = {}
    for mid, mod in modules.items():
        raw = mod.get("owned_paths", [])
        if isinstance(raw, list):
            patterns_by_module[mid] = [str(p) for p in raw if isinstance(p, str)]
        else:
            patterns_by_module[mid] = []

    for mid, patterns in patterns_by_module.items():
        for pat in patterns:
            err = _check_glob_pattern(pat)
            if err is not None:
                violations.append(
                    f"module '{mid}' owned_paths pattern invalid: {pat}: {err}"
                )

    inventory = _enumerate_tracked_inventory(repo_root)
    for rel in inventory:
        matched: list[str] = []
        for mid, patterns in patterns_by_module.items():
            if any(fnmatch.fnmatch(rel, pat) for pat in patterns):
                matched.append(mid)
        if len(matched) > 1:
            violations.append(
                f"ambiguous ownership for '{rel}': matched modules "
                + ", ".join(sorted(matched))
            )
        elif len(matched) == 0:
            violations.append(
                f"unowned inventory path: '{rel}' is not in any module's owned_paths"
            )

    return violations


def _check_module_metadata_self(
    modules: dict[str, dict[str, object]],
) -> list[str]:
    """The module-metadata tooling is part of the inventory it describes."""
    violations: list[str] = []
    expected: dict[str, str] = {
        "tools/check_modules.py": "module_metadata",
        "tools/affected_tests.py": "module_metadata",
        "MODULES.toml": "module_metadata",
    }
    for rel, expected_mid in expected.items():
        owners: list[str] = []
        for mid, mod in modules.items():
            raw = mod.get("owned_paths", [])
            patterns: list[str] = []
            if isinstance(raw, list):
                patterns = [str(p) for p in raw if isinstance(p, str)]
            if any(fnmatch.fnmatch(rel, p) for p in patterns):
                owners.append(mid)
        if len(owners) != 1 or owners[0] != expected_mid:
            violations.append(
                f"validator consistency: '{rel}' must be owned solely by "
                f"'{expected_mid}'; owners: {owners or '(none)'}"
            )
    return violations


def check_all(modules_path: Path) -> tuple[list[str], int]:
    """Run all MODULES.toml validations.

    Returns (violations, module_count). On file-not-found / parse error,
    the violations list contains a single explanatory entry and the count
    is 0 so the CLI can still emit a non-zero exit and a single
    diagnostic line.
    """
    repo_root = modules_path.resolve().parent

    data, err = _load_modules(modules_path)
    if err is not None or data is None:
        return ([err or "failed to load MODULES.toml"], 0)

    modules_raw = data.get("modules")
    if modules_raw is None:
        return (["MODULES.toml: missing [modules] table"], 0)
    if not isinstance(modules_raw, dict):
        return (["MODULES.toml: [modules] must be a table"], 0)

    schema_violations, valid = _validate_module_schema(modules_raw)
    if schema_violations:
        return (schema_violations, 0)

    violations: list[str] = []
    violations.extend(_check_dependencies(valid))
    violations.extend(_detect_cycles(valid))
    violations.extend(_check_focused_tests(valid, repo_root))
    violations.extend(_check_ownership(valid, repo_root))
    violations.extend(_check_module_metadata_self(valid))
    return (violations, len(valid))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint. Exits 0 on success, 1 on any violation."""
    parser = argparse.ArgumentParser(
        description="Validate MODULES.toml against the repository's tracked source.",
    )
    parser.add_argument(
        "modules_path",
        nargs="?",
        default=str(REPO_ROOT_DEFAULT / MODULES_FILENAME),
        help=f"Path to MODULES.toml (default: {REPO_ROOT_DEFAULT / MODULES_FILENAME})",
    )
    args = parser.parse_args(argv)

    modules_path = Path(args.modules_path).resolve()

    violations, module_count = check_all(modules_path)
    if violations:
        sys.stderr.write("MODULES validation failed:\n")
        _print_diagnostics("E", violations)
        sys.stderr.write(
            f"\n{len(violations)} violation(s) in {modules_path}\n"
        )
        return 1

    sys.stdout.write(f"MODULES validation passed: {module_count} modules\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
