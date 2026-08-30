"""Seed and serve the compiled FastAPI product for Playwright.

This launcher deliberately has no network or Vite dependency. It creates the
small PART-A/PART-B fixtures in a worktree-local directory, then starts the
same ``create_app`` factory used in production. No Piper runner or remote TTS
URL is configured, which makes automatic-pronunciation fallback deterministic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.api import _get_nlp, create_app  # noqa: E402


def lemma_ref(lemma: str, pos: str, gender: str | None) -> str:
    payload = json.dumps(
        ["de", unicodedata.normalize("NFC", lemma), pos, gender or "<null>"],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return f"lemma:v1:{hashlib.sha256(payload).hexdigest()}"


def sense_ref(lemma: str, pos: str, gender: str | None, source_ref: str) -> str:
    lemma_semantic_ref = lemma_ref(lemma, pos, gender)
    payload = json.dumps(
        [lemma_semantic_ref, "wiktextract:enwiktionary", source_ref],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return f"sense:v1:{hashlib.sha256(payload).hexdigest()}"


def part_a_schema() -> str:
    schema = (REPO_ROOT / "reference" / "schema.sql").read_text(encoding="utf-8")
    part_a, marker, _ = schema.partition("-- PART B")
    if not marker:
        raise RuntimeError("reference/schema.sql has no PART B marker")
    return part_a


def reset_state(state_dir: Path) -> None:
    """Remove only deterministic artifacts owned by this E2E launcher."""
    state_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("dictionary.sqlite", "replacement.sqlite", "user.sqlite"):
        (state_dir / filename).unlink(missing_ok=True)
    for dirname in ("media", "cache"):
        candidate = state_dir / dirname
        if candidate.exists():
            shutil.rmtree(candidate)


def build_dictionary(path: Path, *, include_tisch: bool) -> None:
    entries = [
        (
            1,
            "Haus",
            "NOUN",
            "das",
            "Häuser",
            "Hauses",
            0,
            None,
            None,
            None,
            "house, building",
            "Das Haus ist alt.",
            "The house is old.",
        ),
        (
            2,
            "See",
            "NOUN",
            "der",
            "Seen",
            "Sees",
            0,
            None,
            None,
            None,
            "lake",
            "Der See ist tief.",
            "The lake is deep.",
        ),
        (
            3,
            "See",
            "NOUN",
            "die",
            "Seen",
            None,
            0,
            None,
            None,
            None,
            "sea, ocean",
            "Die See ist stürmisch.",
            "The sea is stormy.",
        ),
        (
            4,
            "anrufen",
            "VERB",
            None,
            None,
            None,
            1,
            "an",
            "rief an",
            "angerufen",
            "to call, phone",
            "Ich rufe dich morgen an.",
            "I will call you tomorrow.",
        ),
        (
            5,
            "Tisch",
            "NOUN",
            "der",
            "Tische",
            "Tisches",
            0,
            None,
            None,
            None,
            "table",
            "Der Tisch ist rund.",
            "The table is round.",
        ),
    ]
    if not include_tisch:
        entries = entries[:-1]
    conn = sqlite3.connect(path)
    try:
        conn.executescript(part_a_schema())
        for entry in entries:
            (
                ident,
                word,
                pos,
                gender,
                plural,
                genitive,
                separable,
                particle,
                past,
                participle,
                gloss,
                example_de,
                example_en,
            ) = entry
            lref = lemma_ref(word, pos, gender)
            sref = sense_ref(word, pos, gender, f"e2e:{ident}")
            conn.execute(
                """INSERT INTO lemma (
                   id, semantic_ref, lemma, pos, gender, plural, genitive_sg,
                   separable, particle, praeteritum_3sg, partizip_ii, ipa,
                   ipa_source, freq_rank, source, license
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ident,
                    lref,
                    word,
                    pos,
                    gender,
                    plural,
                    genitive,
                    separable,
                    particle,
                    past,
                    participle,
                    "test",
                    "fixture",
                    ident * 10,
                    "fixture",
                    "CC0",
                ),
            )
            conn.execute(
                "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, "
                "source_ref, ord, source, license) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (ident, ident, sref, "wiktextract:enwiktionary", f"e2e:{ident}", "fixture", "CC0"),
            )
            conn.execute(
                "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, "
                "source, license) VALUES (?, ?, 'en', 'translation', 0, ?, 'fixture', 'CC0')",
                (ident, ident, gloss),
            )
            conn.execute(
                "INSERT INTO example (id, de, en, source, source_ref, license, "
                "token_count) VALUES (?, ?, ?, 'fixture', ?, 'CC0', 5)",
                (ident, example_de, example_en, f"e2e:{ident}"),
            )
            conn.execute(
                "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)", (ident, ident)
            )
        conn.executemany(
            "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
            [("Häuser", 1), ("ruft an", 4), ("rief an", 4)],
        )
        conn.commit()
    finally:
        conn.close()


def build_user_db(path: Path) -> None:
    schema = (REPO_ROOT / "reference" / "schema.sql").read_text(encoding="utf-8")
    _, marker, part_b = schema.partition("-- PART B")
    if not marker:
        raise RuntimeError("reference/schema.sql has no PART B marker")
    conn = sqlite3.connect(path)
    try:
        conn.executescript("-- PART B" + part_b)
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("E2E_PORT", "8817")))
    args = parser.parse_args()
    state_dir = Path(os.environ.get("E2E_STATE_DIR", REPO_ROOT / ".e2e-state")).resolve()
    reset_state(state_dir)
    build_dictionary(state_dir / "dictionary.sqlite", include_tisch=False)
    build_dictionary(state_dir / "replacement.sqlite", include_tisch=True)
    build_user_db(state_dir / "user.sqlite")
    app = create_app(
        state_dir / "dictionary.sqlite",
        state_dir / "user.sqlite",
        cors_origins=(f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"),
    )
    _get_nlp()
    import uvicorn

    print(f"[e2e-server] FastAPI state: {state_dir}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
