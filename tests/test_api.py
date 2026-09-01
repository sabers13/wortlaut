"""Comprehensive unit and integration tests for FastAPI application, routes, and security guards.

Covers:
1. Creation-time wildcard origin rejection (AGENTS R12)
2. Host guard matrix (loopback accepted, external rejected)
3. Origin exact-match matrix (allowed origin, rejected origin, omitted origin, OPTIONS)
4. Missing and wrong X-Flashcards-Request on EVERY non-GET route returning 403 with zero writes
5. Wrong Content-Type on JSON routes returning 400
6. Lookup endpoint returning candidate grammar data + active asset token
7. Note capture happy path, stale-token 409 with zero writes, Persian fa 422 with zero writes
8. Cards/next rendering display-time front and back faces (never stored)
9. Review confidence-only contract rejecting client-supplied rating and out-of-range confidence
10. Gloss set/delete with Persian fa 422 rejection and zero writes
11. Audio upload validation, failure preserving previous audio, streaming, and revert
12. Dictionary activation success, failure paths, and token update
13. Decks CRUD, mastery_percent computation per D30, and orphan preservation (AGENTS R5)
14. Anki TSV export sanitization with embedded tabs, newlines, commas (AGENTS R10)
"""

from __future__ import annotations

import io
import sqlite3
import threading
import wave
from collections.abc import Generator
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import _render_input_from_observation, create_app
from app.render import render_card
from tools.build_dict import compute_lemma_semantic_ref, compute_sense_semantic_ref


def _make_dummy_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate minimal valid PCM WAV bytes for audio tests."""
    num_samples = int(duration_seconds * sample_rate)
    raw_frames = b"\x00\x00" * num_samples
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_frames)
    return buffer.getvalue()


@pytest.fixture
def dict_path(tmp_path: Path, part_a_schema: str) -> Path:
    """Create a test dictionary asset with valid candidate semantic refs."""
    db_path = tmp_path / "api_dict_test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(part_a_schema)

    lemma_rows = [
        (
            1,
            compute_lemma_semantic_ref("See", "NOUN", "der"),
            "See",
            "NOUN",
            "der",
            0,
            "Seen",
            0,
            "Sees",
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "zeː",
            "wiktionary",
            100,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            2,
            compute_lemma_semantic_ref("See", "NOUN", "die"),
            "See",
            "NOUN",
            "die",
            0,
            "Seen",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "zeː",
            "wiktionary",
            150,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            3,
            compute_lemma_semantic_ref("Bank", "NOUN", "die"),
            "Bank",
            "NOUN",
            "die",
            0,
            "Bänke",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "baŋk",
            "wiktionary",
            50,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            4,
            compute_lemma_semantic_ref("kranken", "NOUN", "die"),
            "kranken",
            "NOUN",
            "die",
            0,
            None,
            1,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "ˈkʁaŋkn̩",
            "wiktionary",
            500,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            5,
            compute_lemma_semantic_ref("Versicherung", "NOUN", "die"),
            "Versicherung",
            "NOUN",
            "die",
            0,
            "Versicherungen",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "fɛɐ̯ˈzɪçəʁʊŋ",
            "wiktionary",
            200,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            6,
            compute_lemma_semantic_ref("Karte", "NOUN", "die"),
            "Karte",
            "NOUN",
            "die",
            0,
            "Karten",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "ˈkaʁtə",
            "wiktionary",
            80,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            7,
            compute_lemma_semantic_ref("Haus", "NOUN", "das"),
            "Haus",
            "NOUN",
            "das",
            0,
            "Häuser",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "haʊ̯s",
            "wiktionary",
            20,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            8,
            compute_lemma_semantic_ref("Tür", "NOUN", "die"),
            "Tür",
            "NOUN",
            "die",
            0,
            "Türen",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "tyːɐ̯",
            "wiktionary",
            90,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            9,
            compute_lemma_semantic_ref("Tag", "NOUN", "der"),
            "Tag",
            "NOUN",
            "der",
            0,
            "Tage",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "taːk",
            "wiktionary",
            10,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            10,
            compute_lemma_semantic_ref("Licht", "NOUN", "das"),
            "Licht",
            "NOUN",
            "das",
            0,
            "Lichter",
            0,
            None,
            None,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            "lɪçt",
            "wiktionary",
            110,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            11,
            compute_lemma_semantic_ref("anrufen", "VERB", None),
            "anrufen",
            "VERB",
            None,
            0,
            None,
            0,
            None,
            "haben",
            1,
            "an",
            0,
            "ruft an",
            "rief an",
            "angerufen",
            "AKK",
            None,
            None,
            "ˈanˌʁuːfn̩",
            "wiktionary",
            60,
            "wiktionary",
            "CC BY-SA",
        ),
        (
            12,
            compute_lemma_semantic_ref("rufen", "VERB", None),
            "rufen",
            "VERB",
            None,
            0,
            None,
            0,
            None,
            "haben",
            0,
            None,
            0,
            "ruft",
            "rief",
            "gerufen",
            "AKK",
            None,
            None,
            "ˈʁuːfn̩",
            "wiktionary",
            70,
            "wiktionary",
            "CC BY-SA",
        ),
    ]

    lemma_insert_sql = (
        "INSERT INTO lemma ("
        "id, semantic_ref, lemma, pos, gender, plural_none, plural, genitive_sg, "
        "aux, separable, particle, reflexive, praesens_3sg, praeteritum_3sg, "
        "partizip_ii, governs, comparative, superlative, ipa, ipa_source, "
        "freq_rank, source, license) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.executemany(
        lemma_insert_sql,
        [
            (
                r[0],
                r[1],
                r[2],
                r[3],
                r[4],
                r[5],
                r[6],
                r[7],
                r[9],
                r[10],
                r[11],
                r[12],
                r[13],
                r[14],
                r[15],
                r[16],
                r[17],
                r[18],
                r[19],
                r[20],
                r[21],
                r[22],
                r[23],
            )
            for r in lemma_rows
        ],
    )

    surface_forms = [
        ("häuser", 7),
        ("Häuser", 7),
        ("rief an", 11),
        ("ruft an", 11),
        ("Kranken", 4),
    ]
    conn.executemany(
        "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)", surface_forms
    )

    raw_senses = [
        (
            1,
            1,
            "wiktextract:enwiktionary",
            "senseid:en-see-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            2,
            2,
            "wiktextract:enwiktionary",
            "senseid:en-see-2",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            3,
            3,
            "wiktextract:enwiktionary",
            "senseid:en-bank-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            4,
            4,
            "wiktextract:enwiktionary",
            "senseid:en-kranken-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            5,
            5,
            "wiktextract:enwiktionary",
            "senseid:en-versicherung-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            6,
            6,
            "wiktextract:enwiktionary",
            "senseid:en-karte-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            7,
            7,
            "wiktextract:enwiktionary",
            "senseid:en-house-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            8,
            8,
            "wiktextract:enwiktionary",
            "senseid:en-tuer-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            9,
            9,
            "wiktextract:enwiktionary",
            "senseid:en-tag-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            10,
            10,
            "wiktextract:enwiktionary",
            "senseid:en-licht-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            11,
            11,
            "wiktextract:enwiktionary",
            "senseid:en-call-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
        (
            12,
            12,
            "wiktextract:enwiktionary",
            "senseid:en-shout-1",
            0,
            None,
            "wiktionary",
            "CC BY-SA 4.0",
        ),
    ]
    lemma_ref_by_id = {row[0]: str(row[1]) for row in lemma_rows}
    sense_rows = [
        (
            s_id,
            lem_id,
            compute_sense_semantic_ref(lemma_ref_by_id[lem_id], ns, sref),
            ns,
            sref,
            ord_val,
            reg,
            src,
            lic,
        )
        for (s_id, lem_id, ns, sref, ord_val, reg, src, lic) in raw_senses
    ]
    sense_insert_sql = (
        "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, "
        "source_ref, ord, register, source, license) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.executemany(sense_insert_sql, sense_rows)

    meaning_insert_sql = (
        "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, "
        "source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.executemany(
        meaning_insert_sql,
        [
            (1, 1, "en", "translation", 0, "lake", "wiktionary", "CC BY-SA 4.0"),
            (2, 2, "en", "translation", 0, "sea, ocean", "wiktionary", "CC BY-SA 4.0"),
            (3, 3, "en", "translation", 0, "bank, bench", "wiktionary", "CC BY-SA 4.0"),
            (4, 4, "en", "translation", 0, "sick, patients", "wiktionary", "CC BY-SA 4.0"),
            (5, 5, "en", "translation", 0, "insurance", "wiktionary", "CC BY-SA 4.0"),
            (6, 6, "en", "translation", 0, "card, map", "wiktionary", "CC BY-SA 4.0"),
            (7, 7, "en", "translation", 0, "house, building", "wiktionary", "CC BY-SA 4.0"),
            (8, 8, "en", "translation", 0, "door", "wiktionary", "CC BY-SA 4.0"),
            (9, 9, "en", "translation", 0, "day", "wiktionary", "CC BY-SA 4.0"),
            (10, 10, "en", "translation", 0, "light", "wiktionary", "CC BY-SA 4.0"),
            (11, 11, "en", "translation", 0, "to call, phone", "wiktionary", "CC BY-SA 4.0"),
            (12, 12, "en", "translation", 0, "to shout, cry out", "wiktionary", "CC BY-SA 4.0"),
        ],
    )

    example_insert_sql = (
        "INSERT INTO example (id, de, en, source, license, token_count) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    conn.executemany(
        example_insert_sql,
        [
            (1, "Der See ist tief.", "The lake is deep.", "tatoeba", "CC BY 2.0 FR", 5),
            (2, "Die See ist stürmisch.", "The sea is stormy.", "tatoeba", "CC BY 2.0 FR", 5),
            (
                3,
                "Ich rufe dich morgen an.",
                "I will call you tomorrow.",
                "tatoeba",
                "CC BY 2.0 FR",
                5,
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)",
        [(1, 1), (2, 2), (11, 3)],
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def app_instance(dict_path: Path, user_db_path: Path) -> Any:
    """Create a standard test application instance with allowed origins."""
    return create_app(
        dict_path=dict_path,
        user_db_path=user_db_path,
        cors_origins=["http://localhost:3000", "http://127.0.0.1:5173"],
    )


@pytest.fixture
def client(app_instance: Any) -> Generator[TestClient, None, None]:
    """TestClient configured with loopback base URL."""
    with TestClient(app_instance, base_url="http://127.0.0.1:8000") as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Creation-time wildcard rejection (AGENTS R12)
# ---------------------------------------------------------------------------


def test_creation_time_wildcard_rejection(dict_path: Path, user_db_path: Path) -> None:
    """AGENTS R12: cors_origins must be exact; wildcard * is strictly forbidden."""
    with pytest.raises(ValueError, match="Wildcard origin is forbidden"):
        create_app(dict_path, user_db_path, cors_origins=["*"])

    with pytest.raises(ValueError, match="Wildcard origin is forbidden"):
        create_app(dict_path, user_db_path, cors_origins=["http://*.example.com"])

    with pytest.raises(ValueError, match="Wildcard origin is forbidden"):
        create_app(dict_path, user_db_path, cors_origins=["http://localhost:3000", "*"])


# ---------------------------------------------------------------------------
# 2. Host guard matrix (loopback accepted, external rejected)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host_header",
    [
        "127.0.0.1",
        "127.0.0.1:8000",
        "localhost",
        "localhost:3000",
        "[::1]",
        "[::1]:8080",
    ],
)
def test_host_guard_accepts_loopback(client: TestClient, host_header: str) -> None:
    """Loopback host in all standard forms is accepted."""
    response = client.get("/vocab/decks", headers={"Host": host_header})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "host_header",
    [
        "evil.com",
        "evil.com:8000",
        "192.168.1.100",
        "192.168.1.100:8000",
        "example.org",
        "attacker.local",
    ],
)
def test_host_guard_rejects_external_hosts(client: TestClient, host_header: str) -> None:
    """External/non-loopback host is rejected with HTTP 403."""
    response = client.get("/vocab/decks", headers={"Host": host_header})
    assert response.status_code == 403
    assert "Host header must be loopback" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Origin exact-match matrix
# ---------------------------------------------------------------------------


def test_origin_exact_match_matrix(client: TestClient) -> None:
    """Configured origins are accepted with CORS headers; unconfigured are rejected with 403."""
    # Configured origin 1
    r1 = client.get("/vocab/decks", headers={"Origin": "http://localhost:3000"})
    assert r1.status_code == 200
    assert r1.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"

    # Configured origin 2
    r2 = client.get("/vocab/decks", headers={"Origin": "http://127.0.0.1:5173"})
    assert r2.status_code == 200
    assert r2.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5173"

    # Forbidden / unconfigured origin
    r_evil = client.get("/vocab/decks", headers={"Origin": "http://evil.com"})
    assert r_evil.status_code == 403
    assert "Forbidden origin" in r_evil.json()["detail"]

    # Subdomain not in exact allowlist
    r_sub = client.get("/vocab/decks", headers={"Origin": "http://sub.localhost:3000"})
    assert r_sub.status_code == 403

    # Omitted Origin (e.g. CLI tool / curl) is permitted
    r_no_origin = client.get("/vocab/decks")
    assert r_no_origin.status_code == 200

    # OPTIONS preflight
    r_options = client.options(
        "/vocab/notes",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-Flashcards-Request",
        },
    )
    assert r_options.status_code == 200
    assert r_options.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


# ---------------------------------------------------------------------------
# 4. Missing / wrong X-Flashcards-Request on EVERY non-GET route returns 403
# ---------------------------------------------------------------------------


def test_custom_header_guard_on_all_non_get_routes(
    client: TestClient, user_db: sqlite3.Connection
) -> None:
    """Mutating routes require X-Flashcards-Request: 1; missing/wrong returns 403 with 0 writes."""
    dummy_audio = _make_dummy_wav(0.5)

    non_get_requests: list[tuple[str, str, dict[str, Any]]] = [
        (
            "POST",
            "/vocab/notes",
            {
                "json": {
                    "lemma_semantic_ref": "lemma:v1:test",
                    "meaning_languages": ["de"],
                }
            },
        ),
        ("POST", "/vocab/cards/1/review", {"json": {"confidence": 4}}),
        (
            "POST",
            "/vocab/notes/1/gloss",
            {"json": {"language": "de", "meaning_text": "test"}},
        ),
        ("DELETE", "/vocab/notes/1/gloss?language=de", {}),
        (
            "POST",
            "/vocab/notes/1/audio",
            {
                "content": dummy_audio,
                "headers": {"Content-Type": "audio/wav"},
            },
        ),
        ("DELETE", "/vocab/notes/1/audio", {}),
        (
            "POST",
            "/vocab/dictionary/activate",
            {"json": {"path": "candidate.sqlite"}},
        ),
        ("POST", "/vocab/decks", {"json": {"name": "NewDeck"}}),
        ("DELETE", "/vocab/decks/1", {}),
    ]

    for method, path, kwargs in non_get_requests:
        # Snapshot table counts
        notes_before = user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0]
        decks_before = user_db.execute("SELECT COUNT(*) FROM deck").fetchone()[0]
        reviews_before = user_db.execute("SELECT COUNT(*) FROM review_log").fetchone()[0]

        # Case A: Missing header
        res_missing = client.request(method, path, **kwargs)
        assert res_missing.status_code == 403, f"{method} {path} missing header expected 403"
        assert "X-Flashcards-Request" in res_missing.json()["detail"]

        # Case B: Wrong header value
        headers_wrong = dict(kwargs.get("headers", {}))
        headers_wrong["X-Flashcards-Request"] = "2"
        kwargs_wrong = dict(kwargs)
        kwargs_wrong["headers"] = headers_wrong
        res_wrong = client.request(method, path, **kwargs_wrong)
        assert res_wrong.status_code == 403, f"{method} {path} wrong header expected 403"

        # Assert ZERO writes occurred
        assert user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0] == notes_before
        assert user_db.execute("SELECT COUNT(*) FROM deck").fetchone()[0] == decks_before
        assert user_db.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == reviews_before


# ---------------------------------------------------------------------------
# 5. Wrong Content-Type on JSON routes returns 400
# ---------------------------------------------------------------------------


def test_wrong_content_type_on_json_routes(client: TestClient) -> None:
    """JSON routes require Content-Type: application/json; text/plain returns 400."""
    headers_auth = {"X-Flashcards-Request": "1", "Content-Type": "text/plain"}

    # POST /vocab/notes
    r1 = client.post(
        "/vocab/notes",
        content=b'{"lemma_semantic_ref": "test"}',
        headers=headers_auth,
    )
    assert r1.status_code == 400
    assert "Content-Type must be application/json" in r1.json()["detail"]

    # POST /vocab/decks
    r2 = client.post(
        "/vocab/decks",
        content=b'{"name": "Deck"}',
        headers=headers_auth,
    )
    assert r2.status_code == 400

    # POST /vocab/cards/1/review
    r3 = client.post(
        "/vocab/cards/1/review",
        content=b'{"confidence": 4}',
        headers=headers_auth,
    )
    assert r3.status_code == 400


# ---------------------------------------------------------------------------
# 6. Lookup endpoint returns candidate grammar + active asset token
# ---------------------------------------------------------------------------


def test_lookup_endpoint(client: TestClient, app_instance: Any) -> None:
    """GET /vocab/lookup resolves lemma and returns active asset token."""
    active_token = app_instance.state.runtime.asset_token

    response = client.get("/vocab/lookup?q=See")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "See"
    assert data["asset_token"] == active_token
    assert len(data["candidates"]) >= 2  # der See and die See

    candidate_masc = next((c for c in data["candidates"] if c["gender"] == "der"), None)
    assert candidate_masc is not None
    assert candidate_masc["lemma"] == "See"
    assert candidate_masc["pos"] == "NOUN"
    assert len(candidate_masc["senses"]) > 0
    assert len(candidate_masc["examples"]) > 0

    # Empty query returns 422
    r_empty = client.get("/vocab/lookup?q=  ")
    assert r_empty.status_code == 422


# ---------------------------------------------------------------------------
# 7. Note capture happy path, stale-token 409, and Persian fa 422 zero-writes
# ---------------------------------------------------------------------------


def test_capture_note_and_failure_matrix(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """Capture happy path, stale token 409, and Persian 422 with zero database writes."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # 1. Happy path
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    payload_valid = {
        "lemma_semantic_ref": lemma_ref,
        "sense_semantic_ref": sense_ref,
        "status": "resolved",
        "meaning_languages": ["de", "en"],
        "asset_token": active_token,
        "deck_name": "Lektion 1",
    }
    r_happy = client.post("/vocab/notes", json=payload_valid, headers=headers_valid)
    assert r_happy.status_code == 201
    created_data = r_happy.json()
    note_id = created_data["note_id"]
    assert note_id > 0
    assert created_data["meaning_languages"] == ["de", "en"]

    note_row = user_db.execute("SELECT id, status FROM note WHERE id = ?", (note_id,)).fetchone()
    assert note_row is not None and note_row["status"] == "resolved"

    # 2. Stale token rejection (HTTP 409) with zero writes
    notes_count_before = user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0]
    payload_stale = dict(payload_valid)
    payload_stale["asset_token"] = "0" * 64
    r_stale = client.post("/vocab/notes", json=payload_stale, headers=headers_valid)
    assert r_stale.status_code == 409
    assert "Asset token mismatch" in r_stale.json()["detail"]
    assert user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0] == notes_count_before

    # 3. Persian fa rejection (HTTP 422) with zero writes
    payload_fa = dict(payload_valid)
    payload_fa["meaning_languages"] = ["de", "fa"]
    r_fa = client.post("/vocab/notes", json=payload_fa, headers=headers_valid)
    assert r_fa.status_code == 422
    assert "Persian (fa) is deferred" in r_fa.json()["detail"]
    assert user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0] == notes_count_before

    # 4. Empty / unsupported language set (HTTP 422)
    payload_empty_lang = dict(payload_valid)
    payload_empty_lang["meaning_languages"] = []
    r_empty_lang = client.post("/vocab/notes", json=payload_empty_lang, headers=headers_valid)
    assert r_empty_lang.status_code == 422


# ---------------------------------------------------------------------------
# 8. Cards/next rendering display-time faces
# ---------------------------------------------------------------------------


def test_cards_next_rendering(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """GET /vocab/cards/next dynamically computes front and back faces (never stored)."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # 1. Initially no cards
    r_none = client.get("/vocab/cards/next")
    assert r_none.status_code == 200
    assert r_none.json()["card"] is None

    # 2. Capture a note
    lemma_ref = compute_lemma_semantic_ref("See", "NOUN", "der")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-see-1"
    )
    client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["de", "en"],
            "asset_token": active_token,
            "deck_name": "Nouns",
        },
        headers=headers_valid,
    )

    # 3. Request next due card
    r_card = client.get("/vocab/cards/next")
    assert r_card.status_code == 200
    card_data = r_card.json()["card"]
    assert card_data is not None

    # Verify front face
    front = card_data["front"]
    assert front["headword"] == "See"
    assert front["display_headword"] == "der See"
    assert front["pos"] == "NOUN"
    assert front["article"] == "der"
    assert front["audio_trigger"]["available"] is True

    # Verify back face
    back = card_data["back"]
    assert back["display_headword"] == "der See"
    assert "Grammatik:" in back["text"]
    assert len(back["meanings"]) > 0
    assert len(back["examples"]) > 0


def test_cards_next_skips_not_yet_due_cards(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """GET /vocab/cards/next returns only cards due at the request time."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )

    r_note = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["en"],
            "asset_token": active_token,
            "deck_name": "Due filter",
        },
        headers=headers_valid,
    )
    assert r_note.status_code == 201
    note_id = r_note.json()["note_id"]
    card_row = user_db.execute("SELECT id FROM card WHERE note_id = ?", (note_id,)).fetchone()
    assert card_row is not None
    card_id = int(card_row[0])

    r_due = client.get("/vocab/cards/next")
    assert r_due.status_code == 200
    assert r_due.json()["card"]["card_id"] == card_id

    r_review = client.post(
        f"/vocab/cards/{card_id}/review",
        json={"confidence": 5},
        headers=headers_valid,
    )
    assert r_review.status_code == 200
    assert client.get("/vocab/cards/next").json()["card"] is None

    future_due_at = "2099-01-01T00:00:00+00:00"
    with user_db:
        future_note = user_db.execute(
            """
            INSERT INTO note (lemma_semantic_ref, status, created_at, due_at)
            VALUES (?, 'needs_gloss', ?, ?)
            """,
            ("future-only", future_due_at, future_due_at),
        )
        assert future_note.lastrowid is not None
        future_note_id = future_note.lastrowid
        user_db.execute(
            "INSERT INTO card (note_id, state, step, due_at) VALUES (?, ?, ?, ?)",
            (future_note_id, 1, None, future_due_at),
        )

    assert client.get("/vocab/cards/next").json()["card"] is None


# ---------------------------------------------------------------------------
# 9. Review confidence-only contract (ADR-0003)
# ---------------------------------------------------------------------------


def test_review_confidence_only_contract(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """POST /vocab/cards/{id}/review accepts confidence 1..5 only; rejects rating."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # Create note & card
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    res_note = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["en"],
            "asset_token": active_token,
        },
        headers=headers_valid,
    )
    note_id = res_note.json()["note_id"]
    card_row = user_db.execute("SELECT id FROM card WHERE note_id = ?", (note_id,)).fetchone()
    card_id = int(card_row[0])

    # 1. Reject client-supplied rating field (HTTP 422)
    r_rating = client.post(
        f"/vocab/cards/{card_id}/review",
        json={"confidence": 4, "rating": 3},
        headers=headers_valid,
    )
    assert r_rating.status_code == 422
    assert "Client-supplied rating is forbidden" in r_rating.json()["detail"]

    # 2. Reject out-of-range confidence
    for invalid_conf in (0, 6, -1, 10):
        r_bad = client.post(
            f"/vocab/cards/{card_id}/review",
            json={"confidence": invalid_conf},
            headers=headers_valid,
        )
        assert r_bad.status_code == 422

    # 3. Valid confidence review (confidence=4 -> mapped FSRS rating=3)
    r_good = client.post(
        f"/vocab/cards/{card_id}/review",
        json={"confidence": 4},
        headers=headers_valid,
    )
    assert r_good.status_code == 200
    review_data = r_good.json()
    assert review_data["confidence"] == 4
    assert review_data["rating"] == 3

    # Verify review_log has append-only row with raw confidence 4 and rating 3
    log_row = user_db.execute(
        "SELECT confidence, rating FROM review_log WHERE card_id = ?", (card_id,)
    ).fetchone()
    assert log_row is not None
    assert log_row[0] == 4
    assert log_row[1] == 3


# ---------------------------------------------------------------------------
# 10. Gloss set/delete with Persian fa 422 rejection and zero writes
# ---------------------------------------------------------------------------


def test_gloss_endpoints_and_fa_rejection(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """POST/DELETE /vocab/notes/{id}/gloss manages user meanings and rejects fa with 422."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # Create note
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    res_note = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["de", "en"],
            "asset_token": active_token,
        },
        headers=headers_valid,
    )
    note_id = res_note.json()["note_id"]

    # 1. Persian fa rejection on POST gloss
    r_post_fa = client.post(
        f"/vocab/notes/{note_id}/gloss",
        json={"language": "fa", "meaning_text": "خانه"},
        headers=headers_valid,
    )
    assert r_post_fa.status_code == 422
    assert "Persian (fa) is deferred" in r_post_fa.json()["detail"]
    assert user_db.execute("SELECT COUNT(*) FROM note_user_meaning").fetchone()[0] == 0

    # 2. Persian fa rejection on DELETE gloss
    r_del_fa = client.delete(
        f"/vocab/notes/{note_id}/gloss?language=fa",
        headers={"X-Flashcards-Request": "1"},
    )
    assert r_del_fa.status_code == 422

    # 3. Valid user meaning upsert (English)
    r_post_en = client.post(
        f"/vocab/notes/{note_id}/gloss",
        json={"language": "en", "meaning_text": "my cozy home"},
        headers=headers_valid,
    )
    assert r_post_en.status_code == 200
    assert r_post_en.json()["meaning_text"] == "my cozy home"

    um_row = user_db.execute(
        "SELECT meaning_text FROM note_user_meaning WHERE note_id = ? AND lang = 'en'",
        (note_id,),
    ).fetchone()
    assert um_row is not None and um_row[0] == "my cozy home"

    # 4. Valid user meaning delete
    r_del_en = client.delete(
        f"/vocab/notes/{note_id}/gloss?language=en",
        headers={"X-Flashcards-Request": "1"},
    )
    assert r_del_en.status_code == 200
    assert user_db.execute("SELECT COUNT(*) FROM note_user_meaning").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# 11. Audio upload, validation failure preserving previous, streaming, and revert
# ---------------------------------------------------------------------------


def test_audio_endpoints_and_preservation(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """Custom audio persistence, crash-safe replacement, failure preserving previous, and revert."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # Create note
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    res_note = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["de"],
            "asset_token": active_token,
        },
        headers=headers_valid,
    )
    note_id = res_note.json()["note_id"]

    valid_wav = _make_dummy_wav(0.5)

    # 1. Upload valid audio
    r_upload_1 = client.post(
        f"/vocab/notes/{note_id}/audio",
        content=valid_wav,
        headers={"X-Flashcards-Request": "1", "Content-Type": "audio/wav"},
    )
    assert r_upload_1.status_code == 201
    media_fn_1 = r_upload_1.json()["media_filename"]
    sha_1 = r_upload_1.json()["sha256"]

    # 2. Upload invalid audio -> rejected (HTTP 422), previous audio MUST be preserved
    invalid_bytes = b"NOT_A_REAL_AUDIO_FILE_DATA_12345"
    r_upload_bad = client.post(
        f"/vocab/notes/{note_id}/audio",
        content=invalid_bytes,
        headers={"X-Flashcards-Request": "1", "Content-Type": "audio/wav"},
    )
    assert r_upload_bad.status_code == 422
    assert "Audio validation failed" in r_upload_bad.json()["detail"]

    # Assert previous valid audio is preserved intact
    cust_row = user_db.execute(
        "SELECT media_filename, sha256 FROM custom_pronunciation WHERE note_id = ?",
        (note_id,),
    ).fetchone()
    assert cust_row is not None
    assert cust_row[0] == media_fn_1
    assert cust_row[1] == sha_1

    # 3. Stream audio
    r_stream = client.get(f"/vocab/audio/{note_id}")
    assert r_stream.status_code == 200
    assert r_stream.content == valid_wav
    assert r_stream.headers["content-type"].startswith("audio/wav")

    # 4. Revert custom audio to automatic
    r_revert = client.delete(
        f"/vocab/notes/{note_id}/audio",
        headers={"X-Flashcards-Request": "1"},
    )
    assert r_revert.status_code == 200
    assert user_db.execute("SELECT COUNT(*) FROM custom_pronunciation").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# 12. Dictionary activation success, failure paths, and token update (ADR-0004 D47)
# ---------------------------------------------------------------------------


def test_dictionary_activate_endpoints(
    client: TestClient, app_instance: Any, dict_path: Path, part_a_schema: str
) -> None:
    """POST /vocab/dictionary/activate drives atomic activation and token update."""
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}
    managed_dir = dict_path.parent

    # Create candidate dictionary in managed directory
    cand_path = managed_dir / "dict_v2_candidate.sqlite"
    conn = sqlite3.connect(cand_path)
    conn.executescript(part_a_schema)
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktionary", "s1"
    )
    conn.execute(
        "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender) "
        "VALUES (1, ?, 'Haus', 'NOUN', 'das')",
        (lemma_ref,),
    )
    conn.execute(
        "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref) "
        "VALUES (1, 1, ?, 'wiktionary', 's1')",
        (sense_ref,),
    )
    conn.commit()
    conn.close()

    # 1. Activate valid candidate
    r_act = client.post(
        "/vocab/dictionary/activate",
        json={"path": "dict_v2_candidate.sqlite", "version": "v2"},
        headers=headers_valid,
    )
    assert r_act.status_code == 200
    data = r_act.json()
    assert data["status"] == "activated"
    assert data["version"] == "v2"
    assert data["asset_token"] == sha256(cand_path.read_bytes()).hexdigest()

    # 2. Activate non-existent candidate -> 422
    r_missing = client.post(
        "/vocab/dictionary/activate",
        json={"path": "missing_dict.sqlite", "version": "v3"},
        headers=headers_valid,
    )
    assert r_missing.status_code == 422

    # 3. Path traversal forbidden -> 422
    r_traversal = client.post(
        "/vocab/dictionary/activate",
        json={"path": "../outside.sqlite", "version": "v3"},
        headers=headers_valid,
    )
    assert r_traversal.status_code == 422


# ---------------------------------------------------------------------------
# 13. Decks CRUD and orphan preservation (AGENTS R5, ADR-0003 D30)
# ---------------------------------------------------------------------------


def test_decks_crud_and_orphan_preservation(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """Decks CRUD, mastery_percent formula (D30), and notes orphaned on deck deletion (R5)."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # 1. Create deck
    r_deck = client.post(
        "/vocab/decks",
        json={"name": "Lesson 1"},
        headers=headers_valid,
    )
    assert r_deck.status_code == 201
    deck_id = r_deck.json()["id"]

    # 2. Duplicate deck name -> 409
    r_dup = client.post(
        "/vocab/decks",
        json={"name": "Lesson 1"},
        headers=headers_valid,
    )
    assert r_dup.status_code == 409

    # 3. Capture note in this deck and review it
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    res_note = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["de"],
            "asset_token": active_token,
            "deck_name": "Lesson 1",
        },
        headers=headers_valid,
    )
    note_id = res_note.json()["note_id"]
    card_id = user_db.execute("SELECT id FROM card WHERE note_id = ?", (note_id,)).fetchone()[0]

    # Review with confidence 5 (100% mastery for this single card)
    client.post(f"/vocab/cards/{card_id}/review", json={"confidence": 5}, headers=headers_valid)

    # 4. Check decks list and mastery_percent
    r_decks = client.get("/vocab/decks")
    assert r_decks.status_code == 200
    decks = r_decks.json()
    lesson_deck = next((d for d in decks if d["id"] == deck_id), None)
    assert lesson_deck is not None
    assert lesson_deck["card_count"] == 1
    assert lesson_deck["mastery_percent"] == 100.0

    # 5. Delete deck -> note must move to Orphaned deck, never cascade-deleted (AGENTS R5)
    r_del_deck = client.delete(
        f"/vocab/decks/{deck_id}",
        headers={"X-Flashcards-Request": "1"},
    )
    assert r_del_deck.status_code == 200

    # Verify note status is orphaned and review history is intact
    note_row = user_db.execute("SELECT status FROM note WHERE id = ?", (note_id,)).fetchone()
    assert note_row is not None and note_row[0] == "orphaned"

    reviews_count = user_db.execute(
        "SELECT COUNT(*) FROM review_log WHERE card_id = ?", (card_id,)
    ).fetchone()[0]
    assert reviews_count == 1


# ---------------------------------------------------------------------------
# 14. Anki TSV export sanitization (AGENTS R10)
# ---------------------------------------------------------------------------


def test_anki_export_sanitization(
    client: TestClient, app_instance: Any, user_db: sqlite3.Connection
) -> None:
    """Anki TSV export is tab-separated, converts tabs to space, newlines to <br>."""
    active_token = app_instance.state.runtime.asset_token
    headers_valid = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # Create note with tabs and newlines in user meaning
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    res_note_1 = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["de", "en"],
            "asset_token": active_token,
            "deck_name": "Grammar A1",
        },
        headers=headers_valid,
    )
    note_id_1 = res_note_1.json()["note_id"]
    client.post(
        f"/vocab/notes/{note_id_1}/gloss",
        json={"language": "en", "meaning_text": "line1\nline2\twith\ttabs, and commas"},
        headers=headers_valid,
    )

    # Create a second note that needs_gloss
    lemma_ref_2 = compute_lemma_semantic_ref("Tür", "NOUN", "die")
    client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref_2,
            "status": "needs_gloss",
            "meaning_languages": ["de"],
            "asset_token": active_token,
            "deck_name": "Grammar A1",
        },
        headers=headers_valid,
    )

    # Export Anki
    r_export = client.get("/vocab/export/anki")
    assert r_export.status_code == 200
    assert "text/tab-separated-values" in r_export.headers["content-type"]

    content = r_export.text
    lines = content.strip().split("\n")

    # Header directives
    assert lines[0] == "#separator:tab"
    assert lines[1] == "#html:true"
    assert lines[2] == "#notetype:German Vocabulary"
    assert lines[3] == "#columns:Front\tBack\tGrammar\tExample\tIPA\tTags"

    # Data lines
    data_lines = lines[4:]
    assert len(data_lines) == 2

    for dline in data_lines:
        fields = dline.split("\t")
        assert len(fields) == 6, f"Expected 6 TSV fields per record, got {len(fields)}"

        # Assert no embedded literal tabs inside fields
        for field in fields:
            assert "\n" not in field, "Literal newline found in field!"
            assert "\r" not in field, "Literal carriage return found in field!"

    # Check note 1 with sanitized newlines/tabs
    record_1 = data_lines[0].split("\t")
    back_field = record_1[1]
    assert "<br>" in back_field
    assert "\t" not in back_field
    assert "line1<br>line2 with tabs, and commas" in back_field

    # Check needs_gloss note (empty back, tagged needs_gloss)
    record_2 = data_lines[1].split("\t")
    assert record_2[1] == ""  # Back face is empty
    tags_field = record_2[5]
    assert "needs_gloss" in tags_field


def test_post_activation_consistency_regression(
    tmp_path: Path, part_a_schema: str, user_db_path: Path
) -> None:
    """Post-activation consistency regression suite.

    Builds dictionary A and dictionary B in a managed directory.
    Creates the app with dictionary A.
    Activates managed dictionary B with distinct content.
    Asserts:
    - GET /vocab/lookup returns the B token WITH B-only content
      (a lemma present only in B appears; a lemma present only in A does not).
    - cards/next renders meanings sourced from B.
    - export emits B texts.
    - capture submitting an A-era ref under the B token is rejected 422 with zero writes.
    """
    managed_dir = tmp_path / "managed_dictionaries"
    managed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build Dictionary A
    dict_a_path = managed_dir / "dict_a.sqlite"
    conn_a = sqlite3.connect(dict_a_path)
    conn_a.executescript(part_a_schema)

    apfel_lem_ref = compute_lemma_semantic_ref("Apfel", "NOUN", "der")
    apfel_sense_ref = compute_sense_semantic_ref(apfel_lem_ref, "wiktionary", "s_apfel_1")
    haus_lem_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    haus_sense_ref = compute_sense_semantic_ref(haus_lem_ref, "wiktionary", "s_haus_1")

    # Insert Apfel (A-only) into Dict A
    conn_a.execute(
        """
        INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license)
        VALUES (1, ?, 'Apfel', 'NOUN', 'der', 'wiktionary', 'CC BY-SA')
        """,
        (apfel_lem_ref,),
    )
    conn_a.execute(
        """
        INSERT INTO sense (
            id, lemma_id, semantic_ref, source_namespace, source_ref, source, license
        )
        VALUES (1, 1, ?, 'wiktionary', 's_apfel_1', 'wiktionary', 'CC BY-SA')
        """,
        (apfel_sense_ref,),
    )
    conn_a.execute(
        """
        INSERT INTO sense_meaning (
            id, sense_id, language, kind, text, ord, source, license
        )
        VALUES (
            1, 1, 'de', 'definition', 'Frucht des Apfelbaums (Dict A)', 1, 'wiktionary', 'CC BY-SA'
        )
        """
    )
    # Insert Haus into Dict A
    conn_a.execute(
        """
        INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license)
        VALUES (2, ?, 'Haus', 'NOUN', 'das', 'wiktionary', 'CC BY-SA')
        """,
        (haus_lem_ref,),
    )
    conn_a.execute(
        """
        INSERT INTO sense (
            id, lemma_id, semantic_ref, source_namespace, source_ref, source, license
        )
        VALUES (2, 2, ?, 'wiktionary', 's_haus_1', 'wiktionary', 'CC BY-SA')
        """,
        (haus_sense_ref,),
    )
    conn_a.execute(
        """
        INSERT INTO sense_meaning (
            id, sense_id, language, kind, text, ord, source, license
        )
        VALUES (
            2, 2, 'de', 'definition', 'Gebäude zum Wohnen (Dict A)', 1, 'wiktionary', 'CC BY-SA'
        )
        """
    )
    conn_a.commit()
    conn_a.close()

    # 2. Build Dictionary B
    dict_b_path = managed_dir / "dict_b.sqlite"
    conn_b = sqlite3.connect(dict_b_path)
    conn_b.executescript(part_a_schema)

    birne_lem_ref = compute_lemma_semantic_ref("Birne", "NOUN", "die")
    birne_sense_ref = compute_sense_semantic_ref(birne_lem_ref, "wiktionary", "s_birne_1")

    # Insert Birne (B-only) into Dict B
    conn_b.execute(
        """
        INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license)
        VALUES (1, ?, 'Birne', 'NOUN', 'die', 'wiktionary', 'CC BY-SA')
        """,
        (birne_lem_ref,),
    )
    conn_b.execute(
        """
        INSERT INTO sense (
            id, lemma_id, semantic_ref, source_namespace, source_ref, source, license
        )
        VALUES (1, 1, ?, 'wiktionary', 's_birne_1', 'wiktionary', 'CC BY-SA')
        """,
        (birne_sense_ref,),
    )
    conn_b.execute(
        """
        INSERT INTO sense_meaning (
            id, sense_id, language, kind, text, ord, source, license
        )
        VALUES (1, 1, 'de', 'definition', 'Birnenfrucht (Dict B)', 1, 'wiktionary', 'CC BY-SA')
        """
    )
    # Insert Haus into Dict B with updated B-era meaning
    conn_b.execute(
        """
        INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license)
        VALUES (2, ?, 'Haus', 'NOUN', 'das', 'wiktionary', 'CC BY-SA')
        """,
        (haus_lem_ref,),
    )
    conn_b.execute(
        """
        INSERT INTO sense (
            id, lemma_id, semantic_ref, source_namespace, source_ref, source, license
        )
        VALUES (2, 2, ?, 'wiktionary', 's_haus_1', 'wiktionary', 'CC BY-SA')
        """,
        (haus_sense_ref,),
    )
    conn_b.execute(
        """
        INSERT INTO sense_meaning (
            id, sense_id, language, kind, text, ord, source, license
        )
        VALUES (2, 2, 'de', 'definition', 'Modernes Wohnhaus (Dict B)', 1, 'wiktionary', 'CC BY-SA')
        """
    )
    conn_b.commit()
    conn_b.close()

    # 3. Create app pointing to Dictionary A
    app = create_app(
        dict_path=dict_a_path,
        user_db_path=user_db_path,
        cors_origins=["http://localhost:3000"],
    )
    client = TestClient(app, base_url="http://localhost:3000")
    headers = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}

    # Capture Haus note under Dict A
    r_look_a = client.get("/vocab/lookup?q=Haus")
    assert r_look_a.status_code == 200
    token_a = r_look_a.json()["asset_token"]
    assert token_a == sha256(dict_a_path.read_bytes()).hexdigest()

    r_cap_haus = client.post(
        "/vocab/notes",
        json={
            "asset_token": token_a,
            "lemma_semantic_ref": haus_lem_ref,
            "sense_semantic_ref": haus_sense_ref,
            "meaning_languages": ["de"],
        },
        headers=headers,
    )
    assert r_cap_haus.status_code == 201
    assert r_cap_haus.json()["status"] == "resolved"

    # 4. Activate Dictionary B
    r_act = client.post(
        "/vocab/dictionary/activate",
        json={"path": "dict_b.sqlite", "version": "v2"},
        headers=headers,
    )
    assert r_act.status_code == 200
    act_data = r_act.json()
    assert act_data["status"] == "activated"
    token_b = act_data["asset_token"]
    assert token_b == sha256(dict_b_path.read_bytes()).hexdigest()
    assert token_b != token_a

    # 5. Assert GET /vocab/lookup returns B token WITH B-only content
    # (Birne appears, Apfel does not)
    r_look_birne = client.get("/vocab/lookup?q=Birne")
    assert r_look_birne.status_code == 200
    birne_data = r_look_birne.json()
    assert birne_data["asset_token"] == token_b
    assert len(birne_data["candidates"]) == 1
    assert birne_data["candidates"][0]["lemma"] == "Birne"
    assert (
        birne_data["candidates"][0]["senses"][0]["meanings"][0]["text"]
        == "Birnenfrucht (Dict B)"
    )

    r_look_apfel = client.get("/vocab/lookup?q=Apfel")
    assert r_look_apfel.status_code == 200
    apfel_data = r_look_apfel.json()
    assert apfel_data["asset_token"] == token_b
    assert len(apfel_data["candidates"]) == 0

    # 6. Assert cards/next renders meanings sourced from Dictionary B
    r_next = client.get("/vocab/cards/next")
    assert r_next.status_code == 200
    card_body = r_next.json()["card"]
    assert card_body is not None
    assert card_body["front"]["display_headword"] == "das Haus"
    rendered_meanings = [
        line
        for mb in card_body["back"]["meanings"]
        for line in mb["lines"]
    ]
    assert any("Modernes Wohnhaus (Dict B)" in m for m in rendered_meanings)
    assert not any("Gebäude zum Wohnen (Dict A)" in m for m in rendered_meanings)

    # 7. Assert export emits Dictionary B texts
    r_export = client.get("/vocab/export/anki")
    assert r_export.status_code == 200
    export_content = r_export.text
    assert "Modernes Wohnhaus (Dict B)" in export_content
    assert "Gebäude zum Wohnen (Dict A)" not in export_content

    # 8. Assert note capture submitting an A-era ref under token B is rejected 422 with zero writes
    user_conn = sqlite3.connect(user_db_path)
    notes_before = user_conn.execute("SELECT COUNT(*) FROM note").fetchone()[0]
    cards_before = user_conn.execute("SELECT COUNT(*) FROM card").fetchone()[0]
    user_conn.close()

    r_stale_ref = client.post(
        "/vocab/notes",
        json={
            "asset_token": token_b,
            "lemma_semantic_ref": apfel_lem_ref,
            "sense_semantic_ref": apfel_sense_ref,
            "meaning_languages": ["de"],
        },
        headers=headers,
    )
    assert r_stale_ref.status_code == 422
    assert "Unknown lemma semantic reference in active dictionary" in r_stale_ref.json()["detail"]

    user_conn = sqlite3.connect(user_db_path)
    notes_after = user_conn.execute("SELECT COUNT(*) FROM note").fetchone()[0]
    cards_after = user_conn.execute("SELECT COUNT(*) FROM card").fetchone()[0]
    user_conn.close()

    assert notes_after == notes_before
    assert cards_after == cards_before


def test_concurrency_complete_old_observation_during_activation(
    tmp_path: Path, part_a_schema: str, user_db_path: Path
) -> None:
    """Concurrency regression proving complete-old observation during activation.

    Spans cards/next and export observations pinned on Generation A while a real activation
    to Dictionary B commits and publishes, proving 100% Generation A consistency throughout.
    """
    managed_dir = tmp_path / "managed_dictionaries"
    managed_dir.mkdir(parents=True, exist_ok=True)
    dict_a_path = managed_dir / "dict_a.sqlite"
    dict_b_path = managed_dir / "dict_b.sqlite"

    haus_lem_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    haus_sense_ref = compute_sense_semantic_ref(haus_lem_ref, "wiktionary", "s_haus_1")

    # Build Dict A
    conn_a = sqlite3.connect(dict_a_path)
    conn_a.executescript(part_a_schema)
    conn_a.execute(
        """
        INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license)
        VALUES (1, ?, 'Haus', 'NOUN', 'das', 'wiktionary', 'CC BY-SA')
        """,
        (haus_lem_ref,),
    )
    conn_a.execute(
        """
        INSERT INTO sense (
            id, lemma_id, semantic_ref, source_namespace, source_ref, source, license
        )
        VALUES (1, 1, ?, 'wiktionary', 's_haus_1', 'wiktionary', 'CC BY-SA')
        """,
        (haus_sense_ref,),
    )
    conn_a.execute(
        """
        INSERT INTO sense_meaning (
            id, sense_id, language, kind, text, ord, source, license
        )
        VALUES (
            1, 1, 'de', 'definition', 'Gebäude zum Wohnen (Dict A)', 1, 'wiktionary', 'CC BY-SA'
        )
        """
    )
    conn_a.commit()
    conn_a.close()

    # Build Dict B with different meaning
    conn_b = sqlite3.connect(dict_b_path)
    conn_b.executescript(part_a_schema)
    conn_b.execute(
        """
        INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, source, license)
        VALUES (1, ?, 'Haus', 'NOUN', 'das', 'wiktionary', 'CC BY-SA')
        """,
        (haus_lem_ref,),
    )
    conn_b.execute(
        """
        INSERT INTO sense (
            id, lemma_id, semantic_ref, source_namespace, source_ref, source, license
        )
        VALUES (1, 1, ?, 'wiktionary', 's_haus_1', 'wiktionary', 'CC BY-SA')
        """,
        (haus_sense_ref,),
    )
    conn_b.execute(
        """
        INSERT INTO sense_meaning (
            id, sense_id, language, kind, text, ord, source, license
        )
        VALUES (
            1, 1, 'de', 'definition', 'Modernes Wohnhaus (Dict B)', 1, 'wiktionary', 'CC BY-SA'
        )
        """
    )
    conn_b.commit()
    conn_b.close()

    app = create_app(dict_a_path, user_db_path, ["http://127.0.0.1:3000"])
    client = TestClient(app, base_url="http://127.0.0.1:3000")
    headers = {
        "Host": "127.0.0.1:3000",
        "Origin": "http://127.0.0.1:3000",
        "X-Flashcards-Request": "1",
    }

    # 1. Lookup Haus to get active token A
    r_lookup = client.get("/vocab/lookup?q=Haus")
    assert r_lookup.status_code == 200
    token_a = r_lookup.json()["asset_token"]

    # 2. Capture Haus note under token A
    r_cap = client.post(
        "/vocab/notes",
        json={
            "asset_token": token_a,
            "lemma_semantic_ref": haus_lem_ref,
            "sense_semantic_ref": haus_sense_ref,
            "meaning_languages": ["de"],
        },
        headers=headers,
    )
    assert r_cap.status_code == 201

    runtime = app.state.runtime

    # --- PART 1: cards/next observation concurrency test ---
    obs_ready = threading.Event()
    activation_commit_done = threading.Event()
    obs_done = threading.Event()
    obs_errors: list[Exception] = []
    obs_card_holder: list[Any] = []

    def observation_worker() -> None:
        try:
            with runtime.reading():
                # Signal that we are pinned on Gen A
                obs_ready.set()
                # Wait until activation commit has occurred via seam probe
                if not activation_commit_done.wait(timeout=5.0):
                    raise TimeoutError("timed out waiting for activation commit")
                card_obs = runtime.observe_card_render()
                obs_card_holder.append(card_obs)
        except Exception as exc:
            obs_errors.append(exc)
        finally:
            obs_done.set()

    t_obs = threading.Thread(target=observation_worker)
    t_obs.start()
    assert obs_ready.wait(timeout=5.0)

    # Set up seam probe to signal when commit has happened in activation
    def seam_probe_fn() -> None:
        activation_commit_done.set()

    runtime._seam_probe = seam_probe_fn
    try:
        # Drive real activation to Dictionary B
        r_act = client.post(
            "/vocab/dictionary/activate",
            json={"path": "dict_b.sqlite", "version": "v2"},
            headers=headers,
        )
        assert r_act.status_code == 200
        token_b = r_act.json()["asset_token"]
        assert token_b != token_a
    finally:
        runtime._seam_probe = None

    t_obs.join(timeout=5.0)
    assert not t_obs.is_alive()
    assert not obs_errors
    assert len(obs_card_holder) == 1
    card_obs = obs_card_holder[0]
    assert card_obs is not None
    assert card_obs["asset_token"] == token_a
    assert card_obs["note_status"] == "resolved"

    render_input = _render_input_from_observation(card_obs)
    rendered = render_card(render_input)
    rendered_meanings = [
        line
        for mb in rendered.back.meanings
        for line in mb.lines
    ]
    # Assert observation completes 100% Gen A consistent (0 mixed values)
    assert any("Gebäude zum Wohnen (Dict A)" in m for m in rendered_meanings)
    assert not any("Modernes Wohnhaus (Dict B)" in m for m in rendered_meanings)

    # --- PART 2: export observation concurrency test ---
    # Reactivate Dict A to establish baseline for export observation
    r_act_a = client.post(
        "/vocab/dictionary/activate",
        json={"path": "dict_a.sqlite", "version": "v3"},
        headers=headers,
    )
    assert r_act_a.status_code == 200
    token_a3 = r_act_a.json()["asset_token"]
    assert token_a3 == token_a

    exp_ready = threading.Event()
    exp_activation_commit_done = threading.Event()
    exp_done = threading.Event()
    exp_errors: list[Exception] = []
    exp_holder: list[Any] = []

    def export_worker() -> None:
        try:
            with runtime.reading():
                exp_ready.set()
                if not exp_activation_commit_done.wait(timeout=5.0):
                    raise TimeoutError("timed out waiting for activation commit")
                export_obs = runtime.observe_export_payload()
                exp_holder.append(export_obs)
        except Exception as exc:
            exp_errors.append(exc)
        finally:
            exp_done.set()

    t_exp = threading.Thread(target=export_worker)
    t_exp.start()
    assert exp_ready.wait(timeout=5.0)

    def seam_probe_exp() -> None:
        exp_activation_commit_done.set()

    runtime._seam_probe = seam_probe_exp
    try:
        r_act_b2 = client.post(
            "/vocab/dictionary/activate",
            json={"path": "dict_b.sqlite", "version": "v4"},
            headers=headers,
        )
        assert r_act_b2.status_code == 200
    finally:
        runtime._seam_probe = None

    t_exp.join(timeout=5.0)
    assert not t_exp.is_alive()
    assert not exp_errors
    assert len(exp_holder) == 1
    export_obs = exp_holder[0]
    assert len(export_obs) >= 1
    card_exp = export_obs[0]
    assert card_exp["asset_token"] == token_a3

    render_exp_input = _render_input_from_observation(card_exp, with_audio=False)
    rendered_exp = render_card(render_exp_input)
    rendered_exp_meanings = [
        line
        for mb in rendered_exp.back.meanings
        for line in mb.lines
    ]
    assert any("Gebäude zum Wohnen (Dict A)" in m for m in rendered_exp_meanings)
    assert not any("Modernes Wohnhaus (Dict B)" in m for m in rendered_exp_meanings)

    # --- PART 3: Verify fresh observations yield complete-new (Dict B) ---
    r_fresh_next = client.get("/vocab/cards/next")
    assert r_fresh_next.status_code == 200
    fresh_card = r_fresh_next.json()["card"]
    fresh_meanings = [
        line
        for mb in fresh_card["back"]["meanings"]
        for line in mb["lines"]
    ]
    assert any("Modernes Wohnhaus (Dict B)" in m for m in fresh_meanings)
    assert not any("Gebäude zum Wohnen (Dict A)" in m for m in fresh_meanings)

    r_fresh_exp = client.get("/vocab/export/anki")
    assert r_fresh_exp.status_code == 200
    assert "Modernes Wohnhaus (Dict B)" in r_fresh_exp.text
    assert "Gebäude zum Wohnen (Dict A)" not in r_fresh_exp.text


def test_apkg_export_endpoint_is_deck_scoped_and_host_origin_guarded(
    client: TestClient, app_instance: Any
) -> None:
    """APKG export has the normal GET guard behavior and returns package bytes."""
    headers = {"X-Flashcards-Request": "1", "Content-Type": "application/json"}
    lemma_ref = compute_lemma_semantic_ref("Haus", "NOUN", "das")
    sense_ref = compute_sense_semantic_ref(
        lemma_ref, "wiktextract:enwiktionary", "senseid:en-house-1"
    )
    created = client.post(
        "/vocab/notes",
        json={
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "status": "resolved",
            "meaning_languages": ["de"],
            "asset_token": app_instance.state.runtime.asset_token,
            "deck_name": "APKG deck",
        },
        headers=headers,
    )
    assert created.status_code == 201
    deck_id = client.get("/vocab/decks").json()[0]["id"]

    valid = client.get(f"/vocab/export/apkg?deck_id={deck_id}")
    assert valid.status_code == 200
    assert valid.headers["content-type"].startswith("application/apkg")
    assert valid.content.startswith(b"PK")
    assert "attachment" in valid.headers["content-disposition"]

    missing_scope = client.get("/vocab/export/apkg")
    assert missing_scope.status_code == 422
    bad_host = client.get(f"/vocab/export/apkg?deck_id={deck_id}", headers={"Host": "evil.test"})
    assert bad_host.status_code == 403
    bad_origin = client.get(
        f"/vocab/export/apkg?deck_id={deck_id}", headers={"Origin": "https://evil.test"}
    )
    assert bad_origin.status_code == 403
