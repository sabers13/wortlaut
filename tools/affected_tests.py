"""Iteration-time focused-test resolver.

Reads MODULES.toml plus a list of changed paths (or a `git diff` range) and
emits a compact, LLM-friendly focused-validation command. Conservative —
unmapped paths, ambiguous ownership, malformed metadata, missing focused
tests, or invalid dependency graphs force a BROAD/FAIL-CLOSED
recommendation; verification is never silently omitted.

Direct-owner semantics only: each changed path resolves to exactly one
directly owning module; focused tests/commands are the union of those
direct modules only. No automatic reverse-dependency expansion.

This is iteration tooling only; the authoritative `make gate` is unchanged
(WORKFLOW.md §16.4).
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT_DEFAULT: Path = Path(__file__).resolve().parent.parent
MODULES_FILENAME: str = "MODULES.toml"
FRONTEND_PATH_PREFIX: str = "frontend/"

VALID_GLOB_CHARS: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_./*?\[\]!+\-]+$")


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


def _load_modules(repo_root: Path) -> tuple[dict[str, dict[str, object]] | None, str | None]:
    """Return (modules_by_id, error_message). modules_by_id is keyed by id."""
    modules_path = repo_root / MODULES_FILENAME
    if not modules_path.is_file():
        return None, f"missing MODULES.toml at {modules_path}"
    try:
        with modules_path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        return None, f"malformed TOML: {exc}"
    except OSError as exc:
        return None, f"failed to read MODULES.toml: {exc}"

    raw = data.get("modules")
    if not isinstance(raw, dict):
        return None, "MODULES.toml: top-level [modules] table is missing or not a table"

    by_id: dict[str, dict[str, object]] = {}
    seen: set[str] = set()
    for raw_id, raw_mod in raw.items():
        if not isinstance(raw_mod, dict):
            return None, f"MODULES.toml: module '{raw_id}' must be a table"
        if raw_id in seen:
            return None, f"MODULES.toml: duplicate module id '{raw_id}'"
        seen.add(raw_id)
        by_id[raw_id] = dict(raw_mod)
        by_id[raw_id]["id"] = raw_id

    return by_id, None


def _validate_graph(
    modules: dict[str, dict[str, object]],
    repo_root: Path,
) -> list[str]:
    """Static checks that don't require the resolver's input data."""
    violations: list[str] = []
    ids = set(modules)

    for mod_id, mod in modules.items():
        for field in ("owned_paths", "dependencies", "focused_tests"):
            value = mod.get(field)
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                violations.append(
                    f"module '{mod_id}' field '{field}' must be a list of strings"
                )

        deps = mod.get("dependencies", [])
        if isinstance(deps, list):
            seen: set[str] = set()
            for dep in deps:
                if not isinstance(dep, str):
                    continue
                if dep == mod_id:
                    violations.append(f"module '{mod_id}' has self-dependency '{dep}'")
                elif dep in seen:
                    violations.append(f"module '{mod_id}' has duplicate dependency '{dep}'")
                elif dep not in ids:
                    violations.append(
                        f"module '{mod_id}' has unknown dependency '{dep}'"
                    )
                seen.add(dep)

        owned = mod.get("owned_paths", [])
        if isinstance(owned, list):
            for pat in owned:
                if not isinstance(pat, str):
                    continue
                err = _check_glob_pattern(pat)
                if err is not None:
                    violations.append(
                        f"module '{mod_id}' owned_paths pattern invalid: {pat}: {err}"
                    )

        ftests = mod.get("focused_tests", [])
        if isinstance(ftests, list):
            for tpath in ftests:
                if not isinstance(tpath, str):
                    continue
                if _is_escaping(repo_root, tpath):
                    violations.append(
                        f"module '{mod_id}' focused-test path escapes repo root: {tpath}"
                    )
                    continue
                if not (repo_root / tpath).exists():
                    violations.append(
                        f"module '{mod_id}' focused-test path does not exist on disk: {tpath}"
                    )

    violations.extend(_detect_cycles(modules))
    return violations


def _detect_cycles(
    modules: dict[str, dict[str, object]],
) -> list[str]:
    """Detect cycles in the dependency graph using DFS colouring."""
    violations: list[str] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    colour: dict[str, int] = {mid: WHITE for mid in modules}
    deps_by: dict[str, list[str]] = {}
    for mid, mod in modules.items():
        raw = mod.get("dependencies", [])
        if isinstance(raw, list):
            deps_by[mid] = [str(d) for d in raw if isinstance(d, str)]
        else:
            deps_by[mid] = []

    def dfs(node: str, stack: list[str]) -> None:
        colour[node] = GRAY
        stack.append(node)
        for dep in deps_by.get(node, []):
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
            "PYTEST=pytest -q\n"
        )

    direct: set[str] = set()
    for rel in changed_paths:
        owner, err = _find_owning_module(rel, modules)
        if err is not None:
            is_frontend = rel.startswith(FRONTEND_PATH_PREFIX)
            if err == "unmapped":
                return _emit_broad(f"unmapped path: {rel}", is_frontend)
            return _emit_broad(err, is_frontend)
        assert owner is not None
        direct.add(owner)

    # Direct-owner only: no reverse-dependency closure.
    affected = direct

    py_tests: set[str] = set()
    frontend_tests: set[str] = set()
    commands: set[str] = set()
    for mid in affected:
        mod = modules[mid]
        ftests = mod.get("focused_tests", [])
        if isinstance(ftests, list):
            for t in ftests:
                if not isinstance(t, str):
                    continue
                if t.startswith("tests/") and t.endswith(".py"):
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
            "via MODULES.toml direct-owner mapping only."
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

    modules, err = _load_modules(repo_root)
    if err is not None or modules is None:
        sys.stdout.write(_emit_broad(f"malformed MODULES.toml: {err or 'load failed'}") + "\n")
        return 2

    graph_violations = _validate_graph(modules, repo_root)
    if graph_violations:
        summary = "; ".join(graph_violations[:3])
        if len(graph_violations) > 3:
            summary += f" (+{len(graph_violations) - 3} more)"
        sys.stdout.write(_emit_broad(f"invalid MODULES.toml: {summary}") + "\n")
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
