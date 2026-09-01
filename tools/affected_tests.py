"""Iteration-time focused-test resolver.

Reads MODULES.toml plus a list of changed paths (or a `git diff` range) and
emits a compact, LLM-friendly focused-validation command. Conservative —
unmapped paths, ambiguous ownership, malformed metadata, missing focused
tests, or invalid dependency graphs force a BROAD/FAIL-CLOSED
recommendation; verification is never silently omitted.

Source semantics:

  changed source
      ↓
  owning module
      ↓
  transitive reverse/dependent closure
      ↓
  union of focused validation

A changed path is resolved in two passes:

1.  Source ownership via `owned_paths` (any matching module is added to
    the direct set; closure is computed over the union of direct
    modules when any source path is involved).
2.  Known focused-test path via `focused_tests`. A known focused-test
    path is FOCUSED for the module(s) it directly tests and does NOT
    expand reverse dependencies solely because the test changed.

If neither pass matches a path, the resolver fails closed to BROAD.
Source-only changes expand the reverse closure; test-only changes do
not.

This module does NOT re-implement MODULES validation. It delegates
schema and graph validation to `tools.check_modules.load_and_validate`,
the single authoritative validator. Any violation returned there is
treated as BROAD/pytest -q.

This is iteration tooling only; the authoritative `make gate` is unchanged
(WORKFLOW.md §16.4).
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Allow `python tools/affected_tests.py ...` (the documented CLI form)
# and `python -m tools.affected_tests` to resolve `tools.check_modules`.
_PKG_PARENT = Path(__file__).resolve().parent.parent
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from tools.check_modules import load_and_validate  # noqa: E402

REPO_ROOT_DEFAULT: Path = Path(__file__).resolve().parent.parent
MODULES_FILENAME: str = "MODULES.toml"
FRONTEND_PATH_PREFIX: str = "frontend/"
PYTHON_TEST_SUFFIX: str = ".py"
PYTHON_TEST_PREFIX: str = "tests/"


def _load_valid_modules(
    repo_root: Path,
) -> tuple[dict[str, dict[str, object]] | None, str | None]:
    """Load MODULES.toml via the authoritative validator.

    Returns (modules, error). modules is None on any violation (including
    malformed TOML, missing/invalid id, unknown dependency, cycle,
    missing focused test, invalid path, ambiguous ownership, unowned
    inventory path, or git inventory failure).
    """
    modules_path = repo_root / MODULES_FILENAME
    result = load_and_validate(modules_path)
    if result.modules is None:
        summary = "; ".join(result.violations[:3])
        if len(result.violations) > 3:
            summary += f" (+{len(result.violations) - 3} more)"
        return None, f"invalid MODULES.toml: {summary}"
    return result.modules, None


def _find_owning_module(
    rel_path: str,
    modules: dict[str, dict[str, object]],
) -> tuple[str | None, str | None]:
    """Return (module_id, error_message) for a concrete changed path.

    Specificity: longer literal (non-wildcard) characters win; ties are
    ambiguous and produce a single error.
    """
    best_specificity: tuple[int, int] | None = None
    best_modules: list[str] = []
    best_patterns: list[str] = []

    for mid, mod in modules.items():
        owned = mod.get("owned_paths", [])
        if not isinstance(owned, list):
            continue
        mod_best: tuple[int, int] | None = None
        mod_pat: str | None = None
        for pat in owned:
            if not isinstance(pat, str):
                continue
            if fnmatch.fnmatch(rel_path, pat):
                literal_len = sum(1 for c in pat if c not in "*?[]!")
                spec = (literal_len, len(pat))
                if mod_best is None or spec > mod_best:
                    mod_best = spec
                    mod_pat = pat
        if mod_best is not None and mod_pat is not None:
            if best_specificity is None or mod_best > best_specificity:
                best_specificity = mod_best
                best_modules = [mid]
                best_patterns = [mod_pat]
            elif mod_best == best_specificity:
                best_modules.append(mid)
                best_patterns.append(mod_pat)

    if not best_modules:
        return None, "unmapped"
    if len(best_modules) > 1:
        return None, (
            f"ambiguous ownership for '{rel_path}': matched modules "
            + ", ".join(sorted(set(best_modules)))
        )
    return best_modules[0], None


def _find_focused_test_modules(
    rel_path: str,
    modules: dict[str, dict[str, object]],
) -> list[str]:
    """Return module ids whose `focused_tests` include this path.

    A focused-test path is "known" if it matches any module's
    `focused_tests` entry. A focused-test change selects its
    directly associated module(s) and does NOT cause reverse closure
    expansion.
    """
    matched: list[str] = []
    for mid, mod in modules.items():
        focused = mod.get("focused_tests", [])
        if not isinstance(focused, list):
            continue
        for t in focused:
            if isinstance(t, str) and fnmatch.fnmatch(rel_path, t):
                if mid not in matched:
                    matched.append(mid)
                break
    return sorted(matched)


def _build_reverse_graph(
    modules: dict[str, dict[str, object]],
) -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = {mid: [] for mid in modules}
    for mid, mod in modules.items():
        deps = mod.get("dependencies", [])
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if isinstance(dep, str) and dep in reverse:
                reverse[dep].append(mid)
    for k in reverse:
        reverse[k] = sorted(set(reverse[k]))
    return reverse


def _reverse_closure(
    direct: set[str],
    reverse_graph: dict[str, list[str]],
) -> set[str]:
    affected: set[str] = set(direct)
    stack: list[str] = sorted(direct)
    while stack:
        cur = stack.pop()
        for dependent in reverse_graph.get(cur, []):
            if dependent not in affected:
                affected.add(dependent)
                stack.append(dependent)
    return affected


def _get_git_changed(
    repo_root: Path, base: str, head: str
) -> tuple[list[str] | None, str | None]:
    """Run `git diff --name-only <base>...<head>` (falling back to two-dot)."""
    for sep in ("...", ".."):
        cmd = ["git", "diff", "--name-only", f"{base}{sep}{head}"]
        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode == 0:
                files = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
                return files, None
        except (OSError, subprocess.SubprocessError) as exc:
            return None, f"git diff failed: {exc}"
    return None, f"git diff failed for {base}...{head}"


def _emit_broad(reason: str, is_frontend_sensitive: bool = False) -> str:
    lines = [
        "MODE=BROAD",
        f"REASON={reason}",
        "PYTEST=pytest -q",
    ]
    if is_frontend_sensitive:
        lines.append(
            "FRONTEND=npm test --prefix frontend && "
            "npm run --prefix frontend typecheck && "
            "npm run --prefix frontend build"
        )
        lines.append("NOTE=frontend authoritative checks may be required")
    return "\n".join(lines)


def _normalise_paths(paths: Sequence[str]) -> list[str]:
    out: list[str] = []
    for raw in paths:
        cleaned = raw.strip()
        if not cleaned:
            continue
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if cleaned:
            out.append(cleaned)
    return out


def _resolve_emit(
    modules: dict[str, dict[str, object]],
    changed_paths: Sequence[str],
) -> str:
    if not changed_paths:
        return (
            "MODE=FOCUSED\n"
            "MODULES=\n"
            "PYTEST=NONE\n"
        )

    direct: set[str] = set()
    has_source: bool = False

    for rel in changed_paths:
        is_frontend = rel.startswith(FRONTEND_PATH_PREFIX)

        owner, err = _find_owning_module(rel, modules)
        if owner is not None:
            direct.add(owner)
            has_source = True
            continue
        if err is not None and err != "unmapped":
            return _emit_broad(err, is_frontend)

        test_modules = _find_focused_test_modules(rel, modules)
        if test_modules:
            for mid in test_modules:
                direct.add(mid)
            continue

        return _emit_broad(f"unmapped path: {rel}", is_frontend)

    if has_source:
        reverse = _build_reverse_graph(modules)
        affected = _reverse_closure(direct, reverse)
    else:
        affected = set(direct)

    py_tests: set[str] = set()
    frontend_tests: set[str] = set()
    commands: set[str] = set()
    for mid in affected:
        mod = modules[mid]
        ftests = mod.get("focused_tests", [])
        if isinstance(ftests, list):
            for t in ftests:
                if isinstance(t, str):
                    if t.startswith(PYTHON_TEST_PREFIX) and t.endswith(PYTHON_TEST_SUFFIX):
                        py_tests.add(t)
                    else:
                        frontend_tests.add(t)
        fcmds = mod.get("focused_commands", [])
        if isinstance(fcmds, list):
            for c in fcmds:
                if isinstance(c, str):
                    commands.add(c)

    sorted_modules = sorted(affected)
    sorted_py = sorted(py_tests)
    sorted_frontend = sorted(frontend_tests)
    sorted_cmds = sorted(commands)

    lines: list[str] = ["MODE=FOCUSED", f"MODULES={','.join(sorted_modules)}"]

    if sorted_py:
        lines.append(f"PYTEST=pytest -q {' '.join(sorted_py)}")
    else:
        lines.append("PYTEST=NONE")

    if sorted_frontend:
        lines.append(f"FRONTEND_TESTS={' '.join(sorted_frontend)}")
    if sorted_cmds:
        lines.append(f"COMMANDS={' && '.join(sorted_cmds)}")

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint. Exits 0 on FOCUSED, 2 on BROAD/FAIL-CLOSED, 1 on CLI error."""
    parser = argparse.ArgumentParser(
        description=(
            "Resolve changed paths to focused pytest/frontend commands "
            "via MODULES.toml + reverse-dependency closure."
        ),
    )
    parser.add_argument(
        "--base",
        help="git base ref for `git diff --name-only <base>...<head>`",
    )
    parser.add_argument(
        "--head",
        help="git head ref for `git diff --name-only <base>...<head>`",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT_DEFAULT),
        help=f"Path to the repository root (default: {REPO_ROOT_DEFAULT})",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Explicit changed paths (relative to repo root). Overrides --base/--head.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        sys.stderr.write(f"ERROR: --repo-root is not a directory: {repo_root}\n")
        return 1

    modules, err = _load_valid_modules(repo_root)
    if err is not None or modules is None:
        sys.stdout.write(_emit_broad(err or "invalid MODULES.toml") + "\n")
        return 2

    changed: list[str]
    if args.paths:
        changed = _normalise_paths(args.paths)
    elif args.base is not None and args.head is not None:
        git_files, git_err = _get_git_changed(repo_root, args.base, args.head)
        if git_err is not None or git_files is None:
            sys.stdout.write(_emit_broad(f"git diff failed: {git_err}") + "\n")
            return 2
        changed = _normalise_paths(git_files)
    else:
        sys.stdout.write(
            _emit_broad("no changed paths provided; supply --base/--head or explicit paths")
            + "\n"
        )
        return 2

    output = _resolve_emit(modules, changed)
    sys.stdout.write(output + "\n")
    if output.startswith("MODE=BROAD"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
