"""Standalone runtime bootstrap, XDG path resolution, and user-database init.

Provides the small boundary that makes ``create_app`` usable from a single
launcher without any user-supplied path arguments:

* ``default_data_dir`` — XDG-compliant per-user data directory.
* ``ensure_user_db`` — Idempotent PART-B schema initialisation that never
  touches an existing user database (AGENTS R9 / dictionary separation).
* ``build_standalone_app`` — Convenience wrapper that computes XDG-style
  paths, ensures the user database, and constructs the FastAPI app with
  the loopback-only CORS allowlist required by AGENTS R12. Dictionary
  validation is delegated to ``DictionaryRuntime`` so the ~945 MB asset
  is streamed through SHA-256 / schema validation exactly once.

Nothing here writes to the dictionary file (AGENTS R9) and nothing here
adds a runtime LLM dependency (AGENTS R1).
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT: Path = Path(__file__).resolve().parent.parent
SCHEMA_FILENAME: str = "schema.sql"


class StandaloneError(ValueError):
    """Raised when the standalone bootstrap cannot produce a usable state."""


@dataclass(frozen=True)
class StandalonePaths:
    """Resolved per-user data layout for the standalone launch."""

    data_dir: Path
    dictionary_dir: Path
    dictionary_path: Path
    user_db_path: Path
    media_dir: Path
    cache_dir: Path


def default_data_dir() -> Path:
    """Return the per-user data directory following XDG conventions on Linux.

    ``$XDG_DATA_HOME`` is honoured when set; otherwise
    ``$HOME/.local/share/flashcard`` is used. A leading tilde in the
    environment value is also expanded.
    """
    raw = os.environ.get("XDG_DATA_HOME", "").strip()
    if raw:
        return Path(os.path.expanduser(raw)) / "flashcard"
    home = os.environ.get("HOME", "").strip()
    if not home:
        raise StandaloneError("HOME is not set; cannot resolve default data directory")
    return Path(home) / ".local" / "share" / "flashcard"


def resolve_standalone_paths(
    *,
    data_dir: Path | str | None = None,
    dict_path: Path | str | None = None,
    user_db_path: Path | str | None = None,
    media_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
) -> StandalonePaths:
    """Compute the standalone paths, falling back to per-user defaults.

    Every optional override wins over its derived default. The returned
    paths are absolute and resolved; the user data directory is created
    on demand so callers do not have to mkdir before constructing the
    app.
    """
    base = Path(data_dir).resolve() if data_dir is not None else default_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    dictionary_dir = base / "dictionary"
    dictionary_dir.mkdir(parents=True, exist_ok=True)
    if dict_path is None:
        resolved_dict = dictionary_dir / "dictionary.sqlite"
    else:
        resolved_dict = Path(dict_path).resolve()
    if user_db_path is None:
        resolved_user_db = base / "flashcards.sqlite"
    else:
        resolved_user_db = Path(user_db_path).resolve()
    resolved_user_db.parent.mkdir(parents=True, exist_ok=True)
    resolved_media = (
        Path(media_dir).resolve() if media_dir is not None else base / "media"
    )
    resolved_media.mkdir(parents=True, exist_ok=True)
    resolved_cache = (
        Path(cache_dir).resolve() if cache_dir is not None else base / "cache"
    )
    resolved_cache.mkdir(parents=True, exist_ok=True)
    return StandalonePaths(
        data_dir=base,
        dictionary_dir=dictionary_dir,
        dictionary_path=resolved_dict,
        user_db_path=resolved_user_db,
        media_dir=resolved_media,
        cache_dir=resolved_cache,
    )


def _read_part_b_schema() -> str:
    """Return the PART-B schema section, sourced from ``reference/schema.sql``.

    Imported lazily so the file path is resolved relative to the repo
    root even when the package is installed elsewhere; if the schema
    cannot be located the bootstrap fails closed rather than silently
    building a divergent schema (ADR-0001 / AGENTS R6).
    """
    candidates: list[Path] = []
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "reference" / SCHEMA_FILENAME)
    candidates.append(Path.cwd() / "reference" / SCHEMA_FILENAME)
    for candidate in candidates:
        if candidate.is_file():
            schema_text = candidate.read_text(encoding="utf-8")
            _, marker, part_b = schema_text.partition("-- PART B")
            if not marker:
                raise StandaloneError(
                    f"reference schema at {candidate} is missing the PART B section"
                )
            return "-- PART B" + part_b
    raise StandaloneError(
        "reference/schema.sql not found; cannot bootstrap user database"
    )


def ensure_user_db(user_db_path: Path | str) -> Path:
    """Idempotently create the PART-B user database if absent.

    The dictionary file is never opened or modified (AGENTS R9). An
    existing database is detected by ``stat``; it is never truncated,
    recreated, or migrated by this function. A fresh database is
    initialised with PART-B tables only, with foreign keys enabled and
    the WAL journal mode set so multi-process access from the FastAPI
    app and the SQLite reader is safe.
    """
    target = Path(user_db_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        return target
    schema_sql = _read_part_b_schema()
    conn = sqlite3.connect(target)
    try:
        conn.executescript(schema_sql)
        conn.execute("PRAGMA foreign_keys = ON")
        wal_row = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        if wal_row is None or str(wal_row[0]).lower() != "wal":
            raise StandaloneError(
                "failed to establish WAL journal mode on the new user database"
            )
        conn.commit()
    finally:
        conn.close()
    return target


def verify_dictionary_asset(dict_path: Path | str) -> str:
    """Validate an existing dictionary file against the standalone PART-A contract.

    Returns the SHA-256 fingerprint of the dictionary bytes. The
    validation opens the database read-only via the candidate validator
    so a corrupt PART-A schema or a tampered-with file fails closed
    before the FastAPI app tries to read it.

    Kept for tests and other callers that need an explicit fail-closed
    check, but the standalone launcher no longer invokes it: full-file
    validation is delegated to ``DictionaryRuntime`` so the asset is
    streamed through SHA-256 / schema validation exactly once at
    activation (Repair G).
    """
    target = Path(dict_path).resolve()
    if not target.is_file():
        raise StandaloneError(f"dictionary file not found: {target}")
    try:
        raw_bytes = target.read_bytes()
    except OSError as exc:
        raise StandaloneError(f"dictionary file cannot be read: {target}") from exc
    digest = hashlib.sha256(raw_bytes).hexdigest()
    from app.dictionary import (  # noqa: PLC0415
        DictionaryAssetError,
        validate_candidate_dictionary,
    )

    try:
        asset = validate_candidate_dictionary(target)
    except DictionaryAssetError as exc:
        raise StandaloneError(
            f"dictionary PART-A validation failed: {exc}"
        ) from exc
    try:
        if asset.sha256 != digest:
            raise StandaloneError(
                "dictionary SHA-256 mismatch between read and validated snapshot"
            )
    finally:
        asset.close()
    return digest


def build_standalone_app(
    *,
    data_dir: Path | str | None = None,
    dict_path: Path | str | None = None,
    user_db_path: Path | str | None = None,
    media_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
    cors_origins: Sequence[str] | None = None,
    port: int | None = None,
    tts_remote_url: str | None = None,
    expected_dictionary_sha256: str | None = None,
    expected_dictionary_version: str = "v1",
) -> Any:
    """Construct a FastAPI app using the standalone XDG path layout.

    The user database is initialised on demand; the dictionary file is
    not modified and not created (the dictionary is a read-only
    distributable asset, AGENTS R9 / ADR-0001). Full-file dictionary
    validation is delegated to ``DictionaryRuntime`` so the asset is
    streamed and SHA-256-checked exactly once at activation. The CORS
    allowlist defaults to the loopback endpoints used by the bundled
    frontend; when ``port`` is provided, both the ``127.0.0.1`` and
    ``localhost`` origins are constructed for that port so the bundled
    browser frontend's same-origin ``Origin`` header is accepted at
    non-default ports (Repair C).
    """
    paths = resolve_standalone_paths(
        data_dir=data_dir,
        dict_path=dict_path,
        user_db_path=user_db_path,
        media_dir=media_dir,
        cache_dir=cache_dir,
    )
    ensure_user_db(paths.user_db_path)
    if not paths.dictionary_path.is_file():
        raise StandaloneError(
            "dictionary asset is missing; place the verified dictionary.sqlite at "
            f"{paths.dictionary_path} or pass --dict-path"
        )
    port_value = 8000 if port is None else int(port)
    if cors_origins is None:
        cors_origins = (
            f"http://127.0.0.1:{port_value}",
            f"http://localhost:{port_value}",
        )
    from app.api import create_app  # noqa: PLC0415

    return create_app(
        dict_path=paths.dictionary_path,
        user_db_path=paths.user_db_path,
        cors_origins=cors_origins,
        service_port=port_value,
        tts_remote_url=tts_remote_url,
        media_dir=paths.media_dir,
        cache_dir=paths.cache_dir,
        expected_dictionary_sha256=expected_dictionary_sha256,
        expected_dictionary_version=expected_dictionary_version,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Tiny CLI used by the launcher to print the resolved standalone paths."""
    args = list(argv) if argv is not None else sys.argv[1:]
    data_dir_arg: str | None = None
    dict_arg: str | None = None
    user_arg: str | None = None
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--data-dir" and i + 1 < len(args):
            data_dir_arg = args[i + 1]
            i += 2
            continue
        if token == "--dict-path" and i + 1 < len(args):
            dict_arg = args[i + 1]
            i += 2
            continue
        if token == "--user-db" and i + 1 < len(args):
            user_arg = args[i + 1]
            i += 2
            continue
        if token in {"-h", "--help"}:
            sys.stdout.write(
                "Usage: python -m app.standalone [--data-dir DIR] [--dict-path PATH] "
                "[--user-db PATH]\n"
            )
            return 0
        sys.stderr.write(f"unknown argument: {token}\n")
        return 2
    paths = resolve_standalone_paths(
        data_dir=Path(data_dir_arg) if data_dir_arg else None,
        dict_path=Path(dict_arg) if dict_arg else None,
        user_db_path=Path(user_arg) if user_arg else None,
    )
    ensure_user_db(paths.user_db_path)
    sys.stdout.write(f"data_dir={paths.data_dir}\n")
    sys.stdout.write(f"dictionary_path={paths.dictionary_path}\n")
    sys.stdout.write(f"user_db_path={paths.user_db_path}\n")
    sys.stdout.write(f"media_dir={paths.media_dir}\n")
    sys.stdout.write(f"cache_dir={paths.cache_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
