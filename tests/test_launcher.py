"""Subprocess smoke test for the standalone launcher.

Drives the ``./flashcard`` launcher through argparse, a missing
dictionary error, and the install-dictionary path. The test never
launches a long-running server — it verifies the launcher's
fail-closed error paths and CLI plumbing so a regression in the
single-command UX is caught.
"""

from __future__ import annotations

import http.server
import json
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from app.dict_install import compute_sha256
from tools.build_dict import compute_lemma_semantic_ref, compute_sense_semantic_ref

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "reference" / "schema.sql"
LAUNCHER = Path(__file__).resolve().parents[1] / "flashcard"
PYTHON = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python"


def _part_a_sql() -> str:
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    part_a, marker, _ = text.partition("-- PART B")
    assert marker
    return part_a


@pytest.fixture
def synthetic_dict(tmp_path: Path) -> Path:
    db_path = tmp_path / "tiny.sqlite"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(_part_a_sql())
        lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
        sense_ref = compute_sense_semantic_ref(
            lemma_ref, "wiktextract:enwiktionary", "senseid:en-haus-1"
        )
        conn.execute(
            """
            INSERT INTO lemma (id, semantic_ref, lemma, pos, gender,
                plural_none, source, license)
            VALUES (?, ?, ?, ?, ?, 0, 'wiktionary', 'CC BY-SA')
            """,
            (1, lemma_ref, "Haus", "NOUN", "das"),
        )
        conn.execute(
            """
            INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace,
                source_ref, ord, source, license)
            VALUES (?, ?, ?, ?, ?, 0, 'wiktionary', 'CC BY-SA')
            """,
            (1, 1, sense_ref, "wiktextract:enwiktionary", "senseid:en-haus-1"),
        )
        conn.execute(
            """
            INSERT INTO sense_meaning (id, sense_id, language, kind, ord,
                text, source, license)
            VALUES (?, ?, 'en', 'translation', 0, 'house',
                'wiktionary', 'CC BY-SA')
            """,
            (1, 1),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _run_launcher(
    *args: str,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, str(LAUNCHER), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    return proc


def test_launcher_help_prints_expected_text(tmp_path: Path) -> None:
    proc = _run_launcher("--help", cwd=tmp_path)
    assert proc.returncode == 0
    assert "Run the Flashcard standalone web app" in proc.stdout
    assert "--data-dir" in proc.stdout
    assert "--install-dictionary" in proc.stdout


def test_launcher_fails_closed_when_dictionary_missing(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path), "XDG_DATA_HOME": str(tmp_path / "xdg")}
    proc = _run_launcher(
        "--data-dir",
        str(tmp_path / "data"),
        "--no-browser",
        cwd=tmp_path,
        env=env,
        timeout=10,
    )
    assert proc.returncode != 0
    assert "dictionary asset is missing" in proc.stderr


def test_launcher_fails_closed_on_dictionary_verify_error(
    tmp_path: Path, synthetic_dict: Path
) -> None:
    # Write a non-dictionary file at the expected slot
    fake = synthetic_dict.parent / "dictionary.sqlite"
    fake.write_bytes(b"NOT A SQLITE FILE")
    env = {"HOME": str(tmp_path), "XDG_DATA_HOME": str(tmp_path / "xdg")}
    proc = _run_launcher(
        "--data-dir",
        str(tmp_path / "data"),
        "--dict-path",
        str(fake),
        "--no-browser",
        cwd=tmp_path,
        env=env,
        timeout=10,
    )
    assert proc.returncode != 0
    assert "verification failed" in proc.stderr or "PART-A" in proc.stderr


def test_launcher_fails_closed_with_exit_code_on_missing_dict(
    tmp_path: Path,
) -> None:
    """Missing dictionary must fail closed with a clear exit code, not
    silently start a half-configured server.
    """
    env = {"HOME": str(tmp_path), "XDG_DATA_HOME": str(tmp_path / "xdg")}
    data_dir = tmp_path / "data"
    proc = _run_launcher(
        "--data-dir",
        str(data_dir),
        "--no-browser",
        cwd=tmp_path,
        env=env,
        timeout=5,
    )
    assert proc.returncode != 0
    assert "dictionary asset is missing" in proc.stderr


def test_launcher_install_dictionary_then_fail_server(
    tmp_path: Path, synthetic_dict: Path
) -> None:
    """End-to-end: ``--install-dictionary`` over a local HTTP URL places
    the verified dictionary in the user data directory. The server then
    fails for an unrelated reason (the test harness does not bind a
    port) but the install path has succeeded.
    """
    served_bytes = synthetic_dict.read_bytes()

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Length", str(len(served_bytes)))
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(served_bytes)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    _, port = server.server_address  # type: ignore[misc]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        manifest_payload = {
            "version": "v1",
            "filename": "dictionary_v1.sqlite",
            "sha256": compute_sha256(synthetic_dict),
            "bytes": synthetic_dict.stat().st_size,
            "classification": "source-backed-stage02",
            "attribution": "ATTRIBUTION.md",
            "download_url": f"http://127.0.0.1:{port}/dict.sqlite",
        }
        manifest_path = tmp_path / "dictionary-manifest-v1.json"
        manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")

        env = {"HOME": str(tmp_path), "XDG_DATA_HOME": str(tmp_path / "xdg")}
        # Run the install path: the launcher verifies the manifest,
        # downloads, verifies SHA + quick_check, and atomically renames.
        proc = _run_launcher(
            "--data-dir",
            str(tmp_path / "data"),
            "--manifest",
            str(manifest_path),
            "--install-dictionary",
            "--no-browser",
            cwd=tmp_path,
            env=env,
            timeout=10,
        )
        # The install succeeds, but uvicorn then tries to bind a port
        # we don't actually claim — the test only cares that the
        # dictionary landed.
        installed = (
            tmp_path / "data" / "dictionary" / "dictionary_v1.sqlite"
        )
        assert installed.is_file()
        assert installed.read_bytes() == served_bytes
        # The launcher may exit nonzero when uvicorn fails to bind, but
        # the dictionary must have been installed before that.
        assert proc.returncode != 0
    finally:
        server.shutdown()
        thread.join(timeout=2)
