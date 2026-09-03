"""PART-B deck persistence, FSRS reviews, and learner-meaning selection.

This module owns only the mutable user database. Dictionary meaning data is an
already-validated value supplied by the caller; this module never opens the
dictionary database (AGENTS R9).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeAlias, cast

from fsrs import Card, Rating, Scheduler, State

from app.dictionary import DictionaryAsset, DictionaryAssetError, validate_candidate_dictionary
from app.provider import DictionaryProvider

DictionaryMeanings: TypeAlias = Mapping[str, object]
ComponentBinding: TypeAlias = tuple[str, str]


class DeckError(ValueError):
    """Raised when a deck-layer request violates its data contract."""


class DictionaryRuntimeError(DeckError):
    """Raised when dictionary runtime operations fail."""


class DictionaryClosedError(DictionaryRuntimeError):
    """Raised when an operation is attempted on a closed dictionary runtime."""


@dataclass(frozen=True, slots=True)
class ReadingSnapshot:
    """Inert immutable value snapshot holding only copied values from one generation."""

    asset_token: str
    lemma_ids: Mapping[str, int]
    sense_ids: Mapping[str, tuple[int, int]]
    lemma_identity_fingerprints: Mapping[str, str]
    sense_identity_fingerprints: Mapping[str, str]
    bindings: Mapping[tuple[int, str, int], tuple[int | None, int | None]]


@dataclass
class _Generation:
    """Generation descriptor tracking asset handle and lease pins."""

    generation_id: int
    asset: DictionaryAsset
    pins: int = 0
    retired: bool = False
    closed: bool = False


def _is_same_file(p1: Path, p2: Path) -> bool:
    try:
        return os.path.samefile(p1, p2)
    except OSError:
        return False


@dataclass(frozen=True)
class ReviewResult:
    """The persisted result of a confidence-based FSRS review."""

    card_id: int
    confidence: int
    rating: int
    due_at: datetime
    interval_days: float
    state: State
    stability: float | None
    difficulty: float | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return _utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat()


def _parse_timestamp(value: str) -> datetime:
    return _as_utc(datetime.fromisoformat(value))


def _last_insert_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite INSERT did not return a row id")
    return int(cursor.lastrowid)


def _validate_language(language: str) -> None:
    if language not in ("de", "en"):
        raise DeckError("meaning language must be 'de' or 'en'")


def _validate_languages(languages: Sequence[str]) -> tuple[str, ...]:
    selected = tuple(languages)
    if not selected:
        raise DeckError("at least one meaning language is required")
    if len(set(selected)) != len(selected):
        raise DeckError("meaning languages must not contain duplicates")
    for language in selected:
        _validate_language(language)
    return selected


def confidence_to_rating(confidence: int) -> Rating:
    """Apply the sole ADR-0003 D28 confidence-to-FSRS mapping."""
    match confidence:
        case 1 | 2:
            return Rating.Again
        case 3:
            return Rating.Hard
        case 4:
            return Rating.Good
        case 5:
            return Rating.Easy
        case _:
            raise DeckError("confidence must be an integer from 1 through 5")


def _scheduler() -> Scheduler:
    """Return the pinned v1 scheduler without module-level mutable state."""
    return Scheduler(
        learning_steps=(timedelta(minutes=1), timedelta(minutes=10)),
        enable_fuzzing=False,
    )


def _transaction_context(conn: sqlite3.Connection, manage: bool) -> Any:
    return conn if manage else nullcontext()


def create_deck(
    conn: sqlite3.Connection,
    name: str,
    *,
    created_at: datetime | None = None,
    _manage_transaction: bool = True,
) -> int:
    """Create a user deck and return its primary key."""
    if not name.strip():
        raise DeckError("deck name must not be blank")
    with _transaction_context(conn, _manage_transaction):
        cursor = conn.execute(
            "INSERT INTO deck (name, created_at) VALUES (?, ?)",
            (name.strip(), _timestamp(_as_utc(created_at))),
        )
    return _last_insert_id(cursor)


def create_note(
    conn: sqlite3.Connection,
    lemma_semantic_ref: str,
    *,
    sense_semantic_ref: str | None = None,
    status: str = "needs_gloss",
    component_bindings: Sequence[ComponentBinding] = (),
    meaning_languages: Sequence[str],
    created_at: datetime | None = None,
    _manage_transaction: bool = True,
) -> int:
    """Create a note, card, D47 bindings, and a non-empty language selection."""
    if not lemma_semantic_ref.strip():
        raise DeckError("lemma semantic reference must not be blank")
    if status not in ("resolved", "needs_gloss", "derived_compound", "orphaned"):
        raise DeckError("unknown note status")
    selected = _validate_languages(meaning_languages)
    components = tuple(component_bindings)
    if status == "derived_compound" and not components:
        raise DeckError("derived compounds require component bindings")
    if status == "resolved" and not sense_semantic_ref:
        raise DeckError("resolved notes require a sense semantic reference")
    for lemma_ref, sense_ref in components:
        if not lemma_ref.strip() or not sense_ref.strip():
            raise DeckError("component bindings require non-blank semantic references")

    now_text = _timestamp(_as_utc(created_at))
    with _transaction_context(conn, _manage_transaction):
        cursor = conn.execute(
            """
            INSERT INTO note (
                lemma_semantic_ref, sense_semantic_ref, status, created_at, due_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (lemma_semantic_ref, sense_semantic_ref, status, now_text, now_text),
        )
        note_id = _last_insert_id(cursor)
        conn.execute(
            "INSERT INTO card (note_id, state, step, due_at) VALUES (?, ?, ?, ?)",
            (note_id, int(State.Learning), None, now_text),
        )
        conn.executemany(
            "INSERT INTO note_meaning_lang (note_id, lang) VALUES (?, ?)",
            ((note_id, language) for language in selected),
        )
        if status == "resolved" and sense_semantic_ref is not None:
            conn.execute(
                """
                INSERT INTO note_dictionary_binding (
                    note_id, role, component_ord, lemma_semantic_ref, sense_semantic_ref,
                    binding_status, last_relinked_at
                ) VALUES (?, 'direct', 0, ?, ?, 'bound', ?)
                """,
                (note_id, lemma_semantic_ref, sense_semantic_ref, now_text),
            )
        elif status == "derived_compound":
            conn.executemany(
                """
                INSERT INTO note_dictionary_binding (
                    note_id, role, component_ord, lemma_semantic_ref, sense_semantic_ref,
                    binding_status, component_count, last_relinked_at
                ) VALUES (?, 'component', ?, ?, ?, 'bound', ?, ?)
                """,
                (
                    (note_id, ordinal, lemma_ref, sense_ref, len(components), now_text)
                    for ordinal, (lemma_ref, sense_ref) in enumerate(components)
                ),
            )
    return note_id


def add_note_to_deck(
    conn: sqlite3.Connection,
    note_id: int,
    deck_id: int,
    *,
    created_at: datetime | None = None,
    _manage_transaction: bool = True,
) -> None:
    """Add a note to a deck without duplicating an existing membership."""
    with _transaction_context(conn, _manage_transaction):
        conn.execute(
            """
            INSERT OR IGNORE INTO note_deck (note_id, deck_id, created_at)
            VALUES (?, ?, ?)
            """,
            (note_id, deck_id, _timestamp(_as_utc(created_at))),
        )


def _orphan_deck_id(conn: sqlite3.Connection, timestamp: str) -> int:
    row = conn.execute("SELECT id FROM deck WHERE name = 'Orphaned'").fetchone()
    if row is not None:
        return int(row[0])
    return _last_insert_id(
        conn.execute("INSERT INTO deck (name, created_at) VALUES ('Orphaned', ?)", (timestamp,))
    )


def delete_deck(conn: sqlite3.Connection, deck_id: int, *, now: datetime | None = None) -> None:
    """Remove a deck and place every newly membership-less note in Orphaned.

    A note is never deleted here. Review history therefore survives, and does
    not decide whether an otherwise orphaned note gets its required membership.
    """
    timestamp = _timestamp(_as_utc(now))
    try:
        conn.execute("BEGIN IMMEDIATE")
        note_rows = conn.execute(
            "SELECT note_id FROM note_deck WHERE deck_id = ?", (deck_id,)
        ).fetchall()
        conn.execute("DELETE FROM deck WHERE id = ?", (deck_id,))
        newly_orphaned = [
            int(row[0])
            for row in note_rows
            if conn.execute(
                "SELECT 1 FROM note_deck WHERE note_id = ? LIMIT 1", (int(row[0]),)
            ).fetchone()
            is None
        ]
        if newly_orphaned:
            orphan_id = _orphan_deck_id(conn, timestamp)
            for note_id in newly_orphaned:
                conn.execute("UPDATE note SET status = 'orphaned' WHERE id = ?", (note_id,))
                conn.execute(
                    """
                    INSERT OR IGNORE INTO note_deck (note_id, deck_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (note_id, orphan_id, timestamp),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def set_meaning_languages(
    conn: sqlite3.Connection,
    note_id: int,
    languages: Sequence[str],
    *,
    _manage_transaction: bool = True,
) -> None:
    """Replace a note's display language set after validating it in full."""
    selected = _validate_languages(languages)
    with _transaction_context(conn, _manage_transaction):
        conn.execute("DELETE FROM note_meaning_lang WHERE note_id = ?", (note_id,))
        conn.executemany(
            "INSERT INTO note_meaning_lang (note_id, lang) VALUES (?, ?)",
            ((note_id, language) for language in selected),
        )


def set_user_meaning(
    conn: sqlite3.Connection,
    note_id: int,
    language: str,
    meaning_text: str,
    *,
    now: datetime | None = None,
    _manage_transaction: bool = True,
) -> None:
    """Upsert a language-specific note-local user meaning."""
    _validate_language(language)
    if not meaning_text.strip():
        raise DeckError("user meaning must not be blank")
    timestamp = _timestamp(_as_utc(now))
    with _transaction_context(conn, _manage_transaction):
        conn.execute(
            """
            INSERT INTO note_user_meaning (
                note_id, lang, meaning_text, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(note_id, lang) DO UPDATE SET
                meaning_text = excluded.meaning_text,
                updated_at = excluded.updated_at
            """,
            (note_id, language, meaning_text, timestamp, timestamp),
        )


def delete_user_meaning(
    conn: sqlite3.Connection,
    note_id: int,
    language: str,
    *,
    _manage_transaction: bool = True,
) -> None:
    """Remove one note-local user meaning without changing selected languages."""
    _validate_language(language)
    with _transaction_context(conn, _manage_transaction):
        conn.execute(
            "DELETE FROM note_user_meaning WHERE note_id = ? AND lang = ?",
            (note_id, language),
        )


def selected_meaning_languages(conn: sqlite3.Connection, note_id: int) -> tuple[str, ...]:
    """Return a note's selected display languages in deterministic order."""
    rows = conn.execute(
        "SELECT lang FROM note_meaning_lang WHERE note_id = ? ORDER BY lang", (note_id,)
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _texts(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _dictionary_texts(
    dictionary_meanings: DictionaryMeanings | None, sense_ref: str, language: str
) -> tuple[str, ...]:
    """Read either a ref-keyed mapping or the small language-keyed test adapter."""
    if dictionary_meanings is None:
        return ()
    by_ref = dictionary_meanings.get(sense_ref)
    if isinstance(by_ref, Mapping):
        return _texts(by_ref.get(language))
    return _texts(dictionary_meanings.get(language))


def _valid_bindings(
    conn: sqlite3.Connection, note_id: int, role: str
) -> tuple[tuple[int, str], ...]:
    rows = conn.execute(
        """
        SELECT component_ord, sense_semantic_ref, binding_status, component_count
        FROM note_dictionary_binding
        WHERE note_id = ? AND role = ?
        ORDER BY component_ord
        """,
        (note_id, role),
    ).fetchall()
    bindings = tuple((int(row[0]), str(row[1]), str(row[2]), row[3]) for row in rows)
    if role == "direct":
        if len(bindings) != 1 or bindings[0][0] != 0 or bindings[0][2] != "bound":
            return ()
        return ((bindings[0][0], bindings[0][1]),)

    # Revalidate the complete persisted D46 component vector before inspecting
    # whether any entry is bound.  The resolver-declared count prevents a
    # deleted trailing row from becoming a plausible, contiguous prefix.
    if not bindings:
        return ()
    expected_count = bindings[0][3]
    if (
        not isinstance(expected_count, int)
        or isinstance(expected_count, bool)
        or expected_count <= 0
        or any(component_count != expected_count for _, _, _, component_count in bindings)
        or len(bindings) != expected_count
        or tuple(ordinal for ordinal, _, _, _ in bindings) != tuple(range(expected_count))
        or any(status != "bound" for _, _, status, _ in bindings)
    ):
        return ()
    return tuple((ordinal, sense_ref) for ordinal, sense_ref, _, _ in bindings)


def resolved_meanings(
    conn: sqlite3.Connection,
    note_id: int,
    dictionary_meanings: DictionaryMeanings | None = None,
) -> dict[str, tuple[str, ...]]:
    """Return selected meanings, with note-local text taking precedence.

    Availability uses validated D47 bindings matching note.status (M6).
    """
    row = conn.execute("SELECT status FROM note WHERE id = ?", (note_id,)).fetchone()
    if row is None:
        raise DeckError("unknown note")
    status = str(row[0])
    selected = selected_meaning_languages(conn, note_id)
    user_rows = conn.execute(
        "SELECT lang, meaning_text FROM note_user_meaning WHERE note_id = ?", (note_id,)
    ).fetchall()
    user_meanings = {str(row[0]): str(row[1]) for row in user_rows}

    if status == "derived_compound":
        direct: tuple[tuple[int, str], ...] = ()
        components = _valid_bindings(conn, note_id, "component")
    elif status == "resolved":
        direct = _valid_bindings(conn, note_id, "direct")
        components = ()
    elif status == "orphaned":
        direct = _valid_bindings(conn, note_id, "direct")
        components = () if direct else _valid_bindings(conn, note_id, "component")
    else:
        direct = ()
        components = ()

    result: dict[str, tuple[str, ...]] = {}
    for language in selected:
        if language in user_meanings:
            result[language] = (user_meanings[language],)
        elif direct:
            result[language] = _dictionary_texts(dictionary_meanings, direct[0][1], language)
        elif components:
            component_texts = [
                _dictionary_texts(dictionary_meanings, sense_ref, language)
                for _, sense_ref in components
            ]
            result[language] = (
                tuple(texts[0] for texts in component_texts) if all(component_texts) else ()
            )
        else:
            result[language] = ()
    return result


def meaning_state(
    conn: sqlite3.Connection,
    note_id: int,
    dictionary_meanings: DictionaryMeanings | None = None,
) -> str:
    """Compute ADR-0004 D43 availability for the selected language set."""
    meanings = resolved_meanings(conn, note_id, dictionary_meanings)
    available = sum(bool(texts) for texts in meanings.values())
    if available == 0:
        return "none"
    if available == len(meanings):
        return "complete"
    return "partial"


def _card_from_row(row: sqlite3.Row) -> Card:
    return Card(
        card_id=int(row["id"]),
        state=State(int(row["state"])),
        step=int(row["step"]) if row["step"] is not None else None,
        stability=float(row["stability"]) if row["stability"] is not None else None,
        difficulty=float(row["difficulty"]) if row["difficulty"] is not None else None,
        due=_parse_timestamp(str(row["due_at"])),
        last_review=(
            _parse_timestamp(str(row["last_review"])) if row["last_review"] is not None else None
        ),
    )


def review(
    conn: sqlite3.Connection,
    card_id: int,
    confidence: int,
    *,
    reviewed_at: datetime | None = None,
) -> ReviewResult:
    """Atomically schedule a card and append its raw confidence plus FSRS grade."""
    rating = confidence_to_rating(confidence)
    reviewed = _as_utc(reviewed_at)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT card.id, card.note_id, card.state, card.step, card.stability,
                   card.difficulty, card.due_at, card.last_review
            FROM card WHERE card.id = ?
            """,
            (card_id,),
        ).fetchone()
        if row is None:
            raise DeckError("unknown card")
        card = _card_from_row(cast(sqlite3.Row, row))
        previous_review = card.last_review
        scheduled_days = max(
            (card.due - (previous_review or reviewed)).total_seconds() / 86400, 0.0
        )
        elapsed_days = (
            max((reviewed - previous_review).total_seconds() / 86400, 0.0)
            if previous_review is not None
            else 0.0
        )
        updated, _ = _scheduler().review_card(card, rating, reviewed)
        interval_days = max((updated.due - reviewed).total_seconds() / 86400, 0.0)
        ease_factor = 2.5 if updated.difficulty is None else 11.0 - updated.difficulty
        conn.execute(
            """
            INSERT INTO review_log (
                card_id, confidence, rating, scheduled_days, elapsed_days, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (card_id, confidence, int(rating), scheduled_days, elapsed_days, _timestamp(reviewed)),
        )
        conn.execute(
            """
            UPDATE card
            SET state = ?, step = ?, stability = ?, difficulty = ?, due_at = ?, last_review = ?
            WHERE id = ?
            """,
            (
                int(updated.state),
                updated.step,
                updated.stability,
                updated.difficulty,
                _timestamp(updated.due),
                _timestamp(reviewed),
                card_id,
            ),
        )
        conn.execute(
            """
            UPDATE note
            SET due_at = ?, interval_days = ?, ease_factor = ?,
                review_count = review_count + 1, last_confidence = ?
            WHERE id = ?
            """,
            (_timestamp(updated.due), interval_days, ease_factor, confidence, int(row["note_id"])),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ReviewResult(
        card_id=card_id,
        confidence=confidence,
        rating=int(rating),
        due_at=updated.due,
        interval_days=interval_days,
        state=updated.state,
        stability=updated.stability,
        difficulty=updated.difficulty,
    )


class DictionaryRuntime:
    """Manages active dictionary asset lifecycle, atomic relinking, and read pins."""

    def __init__(
        self,
        dict_path: Path | str,
        user_db_path: Path | str,
        *,
        expected_sha256: str | None = None,
        expected_version: str = "v1",
    ) -> None:
        if not isinstance(dict_path, (str, Path)) or isinstance(dict_path, bool):
            raise TypeError("dict_path must be a str or Path")
        if not isinstance(user_db_path, (str, Path)) or isinstance(user_db_path, bool):
            raise TypeError("user_db_path must be a str or Path")
        if expected_sha256 is not None and (
            not isinstance(expected_sha256, str) or len(expected_sha256) != 64
        ):
            raise ValueError("expected_sha256 must be a 64-character SHA-256 string")
        if not isinstance(expected_version, str) or not expected_version.strip():
            raise ValueError("expected_version must be a non-blank string")

        self._user_db_path = Path(user_db_path).resolve()
        initial_dict_path = Path(dict_path)
        self._managed_dir = initial_dict_path.resolve().parent

        if not self._user_db_path.exists():
            raise DeckError(f"user database file not found: {self._user_db_path}")

        # Check underlying-file identity for initial dict_path
        if initial_dict_path.exists() and _is_same_file(initial_dict_path, self._user_db_path):
            raise DictionaryRuntimeError("dictionary path is the user database file")

        # WAL establishment on user database
        self._establish_wal()

        self._lock = threading.Lock()
        self._activation_lock = threading.Lock()
        self._thread_local = threading.local()
        self._closed = False
        self._generation_counter = 0
        self._seam_probe: Callable[[], None] | None = None
        self._pre_commit_probe: Callable[[], None] | None = None
        self._writer_close_hook: Callable[[], None] | None = None
        self._rollback_failure_hook: Callable[[], None] | None = None

        # Check active_dictionary_metadata
        self._init_active_generation(
            initial_dict_path,
            expected_sha256=expected_sha256.lower() if expected_sha256 is not None else None,
            expected_version=expected_version.strip(),
        )

    @property
    def managed_dir(self) -> Path:
        """Return the managed dictionary directory."""
        return self._managed_dir

    @property
    def asset_token(self) -> str:
        """Return the current active dictionary asset token (SHA-256)."""
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            return self._current_generation.asset.asset_token

    @property
    def lemma_ids(self) -> Mapping[str, int]:
        """Return the durable ``lemma_ref -> lemma_id`` map for the active asset."""
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            return self._current_generation.asset.lemma_ids

    @property
    def sense_ids(self) -> Mapping[str, tuple[int, int]]:
        """Return the durable ``sense_ref -> (sense_id, lemma_id)`` map for the active asset."""
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            return self._current_generation.asset.sense_ids

    def provider(self) -> DictionaryProvider:
        """Return a Slice-11 ``DictionaryProvider`` adapter for the current asset.

        Slice 12: ``app/api.py`` migrated served-product dictionary reads
        off raw ``asset.connection`` access onto the abstract provider
        contract. The adapter wraps the existing validated asset (and
        therefore reuses the runtime's read pin semantics) so the
        provider code path remains consistent with the activation /
        relink rules already enforced by ``DictionaryRuntime``.
        """
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            gen = self._current_generation
            cached = getattr(gen, "_provider_view", None)
            if cached is not None:
                return cached  # type: ignore[no-any-return]
            from app.provider_local import LocalDictionaryProvider

            view = LocalDictionaryProvider(gen.asset.path, asset=gen.asset)
            try:
                gen._provider_view = view  # type: ignore[attr-defined]
            except Exception:
                pass
            return view

    @property
    def current_generation_id(self) -> int:
        """Return the monotonic generation identifier of the current asset."""
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            return self._current_generation.generation_id

    @property
    def is_closed(self) -> bool:
        """Return whether the runtime is closed."""
        with self._lock:
            return self._closed

    def _establish_wal(self) -> None:
        try:
            conn = sqlite3.connect(self._user_db_path)
            try:
                cur = conn.execute("PRAGMA journal_mode=WAL")
                row = cur.fetchone()
                if row is None or str(row[0]).lower() != "wal":
                    raise DeckError("failed to establish WAL journal mode on user database")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise DeckError(f"failed to configure WAL on user database: {exc}") from exc

    def _init_active_generation(
        self,
        initial_dict_path: Path,
        *,
        expected_sha256: str | None,
        expected_version: str,
    ) -> None:
        conn = sqlite3.connect(self._user_db_path)
        try:
            row = conn.execute(
                "SELECT active_version, active_filename, active_sha256, activated_at "
                "FROM active_dictionary_metadata WHERE singleton = 1"
            ).fetchone()
        finally:
            conn.close()

        # Canonical launcher startup supplies the selected manifest identity.
        # Validate the configured pathname into one immutable snapshot before
        # consulting durable metadata; that snapshot is the only asset this
        # runtime can publish.  This closes both the pathname race after the
        # lightweight launcher precheck and the stale-metadata bypass.
        if expected_sha256 is not None:
            if not initial_dict_path.is_file():
                raise DictionaryRuntimeError(
                    f"initial dictionary file not found: {initial_dict_path}"
                )
            resolved = initial_dict_path.resolve()
            if resolved.parent != self._managed_dir:
                raise DictionaryRuntimeError("initial dictionary is outside managed directory")
            if _is_same_file(resolved, self._user_db_path):
                raise DictionaryRuntimeError("initial dictionary is the user database file")
            try:
                asset = validate_candidate_dictionary(resolved)
            except Exception as exc:
                raise DictionaryRuntimeError(
                    f"failed to validate initial dictionary: {exc}"
                ) from exc
            if asset.sha256 != expected_sha256:
                asset.close()
                raise DictionaryRuntimeError(
                    "initial dictionary SHA-256 does not match the selected manifest"
                )

            metadata_matches = (
                row is not None
                and str(row[1]) == resolved.name
                and str(row[2]) == asset.sha256
            )
            if not metadata_matches or str(row[0]) != expected_version:
                now_text = _timestamp(_utc_now())
                conn = sqlite3.connect(self._user_db_path)
                try:
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute("BEGIN IMMEDIATE")
                    if not metadata_matches:
                        self._relink_part_b(conn, asset, now_text)
                    conn.execute(
                        """
                        INSERT INTO active_dictionary_metadata (
                            singleton, active_version, active_filename, active_sha256, activated_at
                        ) VALUES (1, ?, ?, ?, ?)
                        ON CONFLICT(singleton) DO UPDATE SET
                            active_version = excluded.active_version,
                            active_filename = excluded.active_filename,
                            active_sha256 = excluded.active_sha256,
                            activated_at = excluded.activated_at
                        """,
                        (expected_version, resolved.name, asset.sha256, now_text),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    asset.close()
                    raise
                finally:
                    conn.close()

            self._generation_counter = 1
            self._current_generation = _Generation(
                generation_id=1,
                asset=asset,
                pins=0,
                retired=False,
                closed=False,
            )
            return

        if row is not None:
            active_filename, active_sha256 = str(row[1]), str(row[2])
            if "/" in active_filename or "\\" in active_filename or ".." in active_filename:
                raise DictionaryRuntimeError(
                    f"invalid active_filename in metadata: {active_filename}"
                )

            recovery_target = self._managed_dir / active_filename
            if not recovery_target.is_file():
                raise DictionaryRuntimeError(
                    f"recovery target dictionary file not found: {recovery_target}"
                )

            if _is_same_file(recovery_target, self._user_db_path):
                raise DictionaryRuntimeError("recovery target dictionary is the user database file")

            try:
                asset = validate_candidate_dictionary(recovery_target)
            except Exception as exc:
                raise DictionaryRuntimeError(f"failed to validate recovery target: {exc}") from exc

            if asset.sha256 != active_sha256:
                asset.close()
                raise DictionaryRuntimeError(
                    "recovery target SHA-256 does not match active_dictionary_metadata"
                )

            self._generation_counter = 1
            self._current_generation = _Generation(
                generation_id=1,
                asset=asset,
                pins=0,
                retired=False,
                closed=False,
            )
        else:
            if not initial_dict_path.is_file():
                raise DictionaryRuntimeError(
                    f"initial dictionary file not found: {initial_dict_path}"
                )

            resolved = initial_dict_path.resolve()
            if resolved.parent != self._managed_dir:
                raise DictionaryRuntimeError("initial dictionary is outside managed directory")

            if _is_same_file(resolved, self._user_db_path):
                raise DictionaryRuntimeError("initial dictionary is the user database file")

            try:
                asset = validate_candidate_dictionary(resolved)
            except Exception as exc:
                raise DictionaryRuntimeError(
                    f"failed to validate initial dictionary: {exc}"
                ) from exc

            now_text = _timestamp(_utc_now())
            conn = sqlite3.connect(self._user_db_path)
            try:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("BEGIN IMMEDIATE")
                self._relink_part_b(conn, asset, now_text)
                conn.execute(
                    """
                    INSERT INTO active_dictionary_metadata (
                        singleton, active_version, active_filename, active_sha256, activated_at
                    ) VALUES (1, 'v1', ?, ?, ?)
                    ON CONFLICT(singleton) DO UPDATE SET
                        active_version = excluded.active_version,
                        active_filename = excluded.active_filename,
                        active_sha256 = excluded.active_sha256,
                        activated_at = excluded.activated_at
                    """,
                    (resolved.name, asset.sha256, now_text),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                asset.close()
                raise
            finally:
                conn.close()

            self._generation_counter = 1
            self._current_generation = _Generation(
                generation_id=1,
                asset=asset,
                pins=0,
                retired=False,
                closed=False,
            )

    @contextmanager
    def reading(self) -> Generator[ReadingSnapshot, None, None]:
        """Yield an inert immutable value snapshot under an atomic read pin."""
        reader_conn: sqlite3.Connection | None = None
        gen: _Generation | None = None
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")

            try:
                reader_conn = sqlite3.connect(
                    f"{self._user_db_path.as_uri()}?mode=ro",
                    uri=True,
                    check_same_thread=False,
                )
                reader_conn.row_factory = sqlite3.Row
                reader_conn.execute("BEGIN DEFERRED")

                rows = reader_conn.execute(
                    """
                    SELECT note_id, role, component_ord, cached_lemma_id, cached_sense_id
                    FROM note_dictionary_binding
                    """
                ).fetchall()
                bindings_dict = {
                    (int(r[0]), str(r[1]), int(r[2])): (
                        int(r[3]) if r[3] is not None else None,
                        int(r[4]) if r[4] is not None else None,
                    )
                    for r in rows
                }

                gen = self._current_generation
                asset_token = str(gen.asset.asset_token)
                lemma_ids = MappingProxyType(dict(gen.asset.lemma_ids))
                sense_ids = MappingProxyType(dict(gen.asset.sense_ids))
                lemma_fps = MappingProxyType(dict(gen.asset.lemma_identity_fingerprints))
                sense_fps = MappingProxyType(dict(gen.asset.sense_identity_fingerprints))
                bindings = MappingProxyType(bindings_dict)

                snapshot = ReadingSnapshot(
                    asset_token=asset_token,
                    lemma_ids=lemma_ids,
                    sense_ids=sense_ids,
                    lemma_identity_fingerprints=lemma_fps,
                    sense_identity_fingerprints=sense_fps,
                    bindings=bindings,
                )

                gen.pins += 1
                depth = getattr(self._thread_local, "depth", 0)
                self._thread_local.depth = depth + 1
                prev_reader_conn = getattr(self._thread_local, "reader_conn", None)
                prev_gen = getattr(self._thread_local, "pinned_generation", None)
                self._thread_local.reader_conn = reader_conn
                self._thread_local.pinned_generation = gen
            except Exception:
                if reader_conn is not None:
                    try:
                        reader_conn.rollback()
                    except Exception:
                        pass
                    try:
                        reader_conn.close()
                    except Exception:
                        pass
                raise

        try:
            yield snapshot
        finally:
            if reader_conn is not None:
                try:
                    reader_conn.rollback()
                except Exception:
                    pass
                try:
                    reader_conn.close()
                except Exception:
                    pass

            self._thread_local.reader_conn = prev_reader_conn
            self._thread_local.pinned_generation = prev_gen

            if gen is not None:
                with self._lock:
                    depth = getattr(self._thread_local, "depth", 0)
                    self._thread_local.depth = max(0, depth - 1)
                    gen.pins = max(0, gen.pins - 1)
                    if gen.retired and gen.pins == 0 and not gen.closed:
                        gen.closed = True
                        try:
                            gen.asset.close()
                        except Exception:
                            pass

    def _materialize_lemma_under_gen(
        self,
        conn: sqlite3.Connection,
        lemma_semantic_ref: str,
    ) -> tuple[
        MappingProxyType[str, object] | None,
        tuple[MappingProxyType[str, object], ...],
        tuple[MappingProxyType[str, object], ...],
        tuple[MappingProxyType[str, object], ...],
    ]:
        lem_cur = conn.execute(
            """
            SELECT id, semantic_ref, lemma, pos, gender, plural, plural_none,
                   genitive_sg, aux, separable, particle, reflexive, praesens_3sg,
                   praeteritum_3sg, partizip_ii, governs, comparative, superlative,
                   ipa, ipa_source, freq_rank, source, license
            FROM lemma WHERE semantic_ref = ?
            """,
            (lemma_semantic_ref,),
        )
        lem = lem_cur.fetchone()
        if lem is None:
            return (None, (), (), ())

        lem_id = int(lem["id"])

        s_cur = conn.execute(
            """
            SELECT id, lemma_id, semantic_ref, source_namespace, source_ref, ord,
                   register, source, license
            FROM sense WHERE lemma_id = ?
            ORDER BY ord ASC, semantic_ref ASC, id ASC
            """,
            (lem_id,),
        )
        sense_rows = s_cur.fetchall()

        m_cur = conn.execute(
            """
            SELECT sm.id, sm.sense_id, sm.language, sm.kind, sm.ord, sm.text,
                   sm.source, sm.license
            FROM sense_meaning sm
            JOIN sense s ON sm.sense_id = s.id
            WHERE s.lemma_id = ?
            ORDER BY sm.language ASC, sm.kind ASC, sm.ord ASC, sm.id ASC
            """,
            (lem_id,),
        )
        meaning_rows = m_cur.fetchall()

        e_cur = conn.execute(
            """
            SELECT e.id, e.de, e.en, e.source, e.source_ref, e.license,
                   e.token_count, e.has_proper
            FROM example_lemma el
            JOIN example e ON el.example_id = e.id
            WHERE el.lemma_id = ?
            ORDER BY e.id ASC
            """,
            (lem_id,),
        )
        example_rows = e_cur.fetchall()

        lemma_map = MappingProxyType({
            "id": lem_id,
            "semantic_ref": str(lem["semantic_ref"]),
            "lemma": str(lem["lemma"]),
            "pos": str(lem["pos"]),
            "gender": str(lem["gender"]) if lem["gender"] is not None else None,
            "plural": str(lem["plural"]) if lem["plural"] is not None else None,
            "plural_none": int(lem["plural_none"]),
            "genitive_sg": (
                str(lem["genitive_sg"]) if lem["genitive_sg"] is not None else None
            ),
            "aux": str(lem["aux"]) if lem["aux"] is not None else None,
            "separable": int(lem["separable"]),
            "particle": str(lem["particle"]) if lem["particle"] is not None else None,
            "reflexive": int(lem["reflexive"]),
            "praesens_3sg": (
                str(lem["praesens_3sg"]) if lem["praesens_3sg"] is not None else None
            ),
            "praeteritum_3sg": (
                str(lem["praeteritum_3sg"]) if lem["praeteritum_3sg"] is not None else None
            ),
            "partizip_ii": (
                str(lem["partizip_ii"]) if lem["partizip_ii"] is not None else None
            ),
            "governs": str(lem["governs"]) if lem["governs"] is not None else None,
            "comparative": (
                str(lem["comparative"]) if lem["comparative"] is not None else None
            ),
            "superlative": (
                str(lem["superlative"]) if lem["superlative"] is not None else None
            ),
            "ipa": str(lem["ipa"]) if lem["ipa"] is not None else None,
        })
        senses_tuple = tuple(
            MappingProxyType({
                "id": int(s["id"]),
                "semantic_ref": str(s["semantic_ref"]),
                "source_namespace": str(s["source_namespace"]),
                "source_ref": str(s["source_ref"]),
                "ord": int(s["ord"]),
                "register": str(s["register"]) if s["register"] is not None else None,
            })
            for s in sense_rows
        )
        meanings_tuple = tuple(
            MappingProxyType({
                "id": int(m["id"]),
                "sense_id": int(m["sense_id"]),
                "language": str(m["language"]),
                "kind": str(m["kind"]),
                "ord": int(m["ord"]),
                "text": str(m["text"]),
            })
            for m in meaning_rows
        )
        examples_tuple = tuple(
            MappingProxyType({
                "id": int(ex["id"]),
                "de": str(ex["de"]),
                "en": str(ex["en"]) if ex["en"] is not None else None,
            })
            for ex in example_rows
        )
        return (lemma_map, senses_tuple, meanings_tuple, examples_tuple)

    def _materialize_components_under_gen(
        self,
        conn: sqlite3.Connection,
        comp_rows: Sequence[sqlite3.Row] | Sequence[Mapping[str, str]],
    ) -> tuple[MappingProxyType[str, object], ...]:
        components: list[MappingProxyType[str, object]] = []
        for cr in comp_rows:
            c_lem_ref = str(cr["lemma_semantic_ref"])
            c_sense_ref = str(cr["sense_semantic_ref"])
            lem_cur = conn.execute(
                "SELECT lemma FROM lemma WHERE semantic_ref = ?", (c_lem_ref,)
            ).fetchone()
            lemma_text = (
                str(lem_cur[0])
                if lem_cur is not None
                else c_lem_ref.split(":")[-1]
            )

            meanings_by_lang: dict[str, str] = {}
            for lang in ("de", "en"):
                m_cur = conn.execute(
                    """
                    SELECT sm.text FROM sense_meaning sm
                    JOIN sense s ON s.id = sm.sense_id
                    WHERE s.semantic_ref = ? AND sm.language = ?
                    ORDER BY sm.ord ASC LIMIT 1
                    """,
                    (c_sense_ref, lang),
                ).fetchone()
                if m_cur is not None:
                    meanings_by_lang[lang] = str(m_cur[0])

            components.append(
                MappingProxyType({
                    "lemma_ref": c_lem_ref,
                    "sense_ref": c_sense_ref,
                    "lemma": lemma_text,
                    "meanings": MappingProxyType(meanings_by_lang),
                })
            )
        return tuple(components)

    def _observe_card_render_internal(
        self,
        reader_conn: sqlite3.Connection,
        gen: _Generation,
        *,
        card_id: int | None = None,
        deck_id: int | None = None,
    ) -> MappingProxyType[str, object] | None:
        if card_id is not None:
            row = reader_conn.execute(
                """
                SELECT c.id AS card_id, c.note_id, c.due_at, c.state,
                       c.stability, c.difficulty,
                       n.lemma_semantic_ref, n.sense_semantic_ref,
                       n.status AS note_status
                FROM card c
                JOIN note n ON n.id = c.note_id
                WHERE c.id = ?
                """,
                (card_id,),
            ).fetchone()
        elif deck_id is not None:
            row = reader_conn.execute(
                """
                SELECT c.id AS card_id, c.note_id, c.due_at, c.state,
                       c.stability, c.difficulty,
                       n.lemma_semantic_ref, n.sense_semantic_ref,
                       n.status AS note_status
                FROM card c
                JOIN note n ON n.id = c.note_id
                JOIN note_deck nd ON nd.note_id = n.id
                WHERE nd.deck_id = ? AND c.due_at <= ?
                ORDER BY c.due_at ASC, c.id ASC
                LIMIT 1
                """,
                (deck_id, _timestamp(_utc_now())),
            ).fetchone()
        else:
            row = reader_conn.execute(
                """
                SELECT c.id AS card_id, c.note_id, c.due_at, c.state,
                       c.stability, c.difficulty,
                       n.lemma_semantic_ref, n.sense_semantic_ref,
                       n.status AS note_status
                FROM card c
                JOIN note n ON n.id = c.note_id
                WHERE c.due_at <= ?
                ORDER BY c.due_at ASC, c.id ASC
                LIMIT 1
                """,
                (_timestamp(_utc_now()),),
            ).fetchone()

        if row is None:
            return None

        c_id = int(row["card_id"])
        n_id = int(row["note_id"])
        due_at = str(row["due_at"])
        state = int(row["state"])
        stability = float(row["stability"]) if row["stability"] is not None else None
        difficulty = float(row["difficulty"]) if row["difficulty"] is not None else None
        lemma_ref = str(row["lemma_semantic_ref"])
        sense_ref = (
            str(row["sense_semantic_ref"])
            if row["sense_semantic_ref"]
            else None
        )
        note_status = str(row["note_status"])

        lang_rows = reader_conn.execute(
            "SELECT lang FROM note_meaning_lang WHERE note_id = ? ORDER BY lang",
            (n_id,),
        ).fetchall()
        selected_langs = (
            tuple(str(r[0]) for r in lang_rows)
            if lang_rows
            else ("de", "en")
        )

        user_meanings_rows = reader_conn.execute(
            "SELECT lang, meaning_text FROM note_user_meaning WHERE note_id = ?",
            (n_id,),
        ).fetchall()
        user_meanings_dict = MappingProxyType({
            str(r[0]): str(r[1]) for r in user_meanings_rows
        })

        custom_row = reader_conn.execute(
            "SELECT 1 FROM custom_pronunciation WHERE note_id = ?",
            (n_id,),
        ).fetchone()
        has_custom_audio = custom_row is not None

        comp_rows: list[sqlite3.Row] = []
        if note_status == "derived_compound":
            comp_rows = reader_conn.execute(
                """
                SELECT component_ord, lemma_semantic_ref, sense_semantic_ref
                FROM note_dictionary_binding
                WHERE note_id = ? AND role = 'component'
                ORDER BY component_ord ASC
                """,
                (n_id,),
            ).fetchall()

        dict_conn = gen.asset.connection
        components = (
            self._materialize_components_under_gen(dict_conn, comp_rows)
            if comp_rows
            else ()
        )

        lemma_map, senses_tuple, meanings_tuple, examples_tuple = (
            self._materialize_lemma_under_gen(dict_conn, lemma_ref)
        )

        payload_dict: dict[str, object] = {
            "card_id": c_id,
            "note_id": n_id,
            "due_at": due_at,
            "state": state,
            "stability": stability,
            "difficulty": difficulty,
            "note_status": note_status,
            "lemma_semantic_ref": lemma_ref,
            "sense_semantic_ref": sense_ref,
            "asset_token": str(gen.asset.asset_token),
            "selected_languages": selected_langs,
            "user_meanings": user_meanings_dict,
            "has_custom_audio": has_custom_audio,
            "components": components,
            "lemma": lemma_map,
            "senses": senses_tuple,
            "meanings": meanings_tuple,
            "examples": examples_tuple,
        }
        return MappingProxyType(payload_dict)

    def _observe_export_payload_internal(
        self,
        reader_conn: sqlite3.Connection,
        gen: _Generation,
        *,
        deck_id: int | None = None,
    ) -> tuple[MappingProxyType[str, object], ...]:
        if deck_id is not None:
            rows = reader_conn.execute(
                """
                SELECT c.id AS card_id, n.id AS note_id, n.status,
                       n.lemma_semantic_ref, n.sense_semantic_ref,
                       GROUP_CONCAT(DISTINCT d.name) AS deck_names
                FROM card c
                JOIN note n ON n.id = c.note_id
                JOIN note_deck nd ON nd.note_id = n.id
                JOIN deck d ON d.id = nd.deck_id
                WHERE d.id = ?
                GROUP BY c.id, n.id, n.status, n.lemma_semantic_ref,
                         n.sense_semantic_ref
                ORDER BY c.id ASC
                """,
                (deck_id,),
            ).fetchall()
        else:
            rows = reader_conn.execute(
                """
                SELECT c.id AS card_id, n.id AS note_id, n.status,
                       n.lemma_semantic_ref, n.sense_semantic_ref,
                       GROUP_CONCAT(DISTINCT d.name) AS deck_names
                FROM card c
                JOIN note n ON n.id = c.note_id
                LEFT JOIN note_deck nd ON nd.note_id = n.id
                LEFT JOIN deck d ON d.id = nd.deck_id
                GROUP BY c.id, n.id, n.status, n.lemma_semantic_ref,
                         n.sense_semantic_ref
                ORDER BY c.id ASC
                """
            ).fetchall()

        dict_conn = gen.asset.connection
        token = str(gen.asset.asset_token)
        export_items: list[MappingProxyType[str, object]] = []

        for row in rows:
            c_id = int(row["card_id"])
            n_id = int(row["note_id"])
            note_status = str(row["status"])
            lemma_ref = str(row["lemma_semantic_ref"])
            sense_ref = (
                str(row["sense_semantic_ref"])
                if row["sense_semantic_ref"]
                else None
            )
            deck_names_str = str(row["deck_names"]) if row["deck_names"] else ""

            lang_rows = reader_conn.execute(
                "SELECT lang FROM note_meaning_lang WHERE note_id = ? ORDER BY lang",
                (n_id,),
            ).fetchall()
            selected_langs = (
                tuple(str(r[0]) for r in lang_rows)
                if lang_rows
                else ("de", "en")
            )

            user_meanings_rows = reader_conn.execute(
                "SELECT lang, meaning_text FROM note_user_meaning WHERE note_id = ?",
                (n_id,),
            ).fetchall()
            user_meanings_dict = MappingProxyType({
                str(r[0]): str(r[1]) for r in user_meanings_rows
            })

            custom_row = reader_conn.execute(
                "SELECT 1 FROM custom_pronunciation WHERE note_id = ?",
                (n_id,),
            ).fetchone()
            has_custom_audio = custom_row is not None

            comp_rows: list[sqlite3.Row] = []
            if note_status == "derived_compound":
                comp_rows = reader_conn.execute(
                    """
                    SELECT component_ord, lemma_semantic_ref, sense_semantic_ref
                    FROM note_dictionary_binding
                    WHERE note_id = ? AND role = 'component'
                    ORDER BY component_ord ASC
                    """,
                    (n_id,),
                ).fetchall()

            components = (
                self._materialize_components_under_gen(dict_conn, comp_rows)
                if comp_rows
                else ()
            )

            lemma_map, senses_tuple, meanings_tuple, examples_tuple = (
                self._materialize_lemma_under_gen(dict_conn, lemma_ref)
            )

            card_dict: dict[str, object] = {
                "card_id": c_id,
                "note_id": n_id,
                "due_at": "",
                "state": 0,
                "stability": None,
                "difficulty": None,
                "note_status": note_status,
                "lemma_semantic_ref": lemma_ref,
                "sense_semantic_ref": sense_ref,
                "deck_names": deck_names_str,
                "asset_token": token,
                "selected_languages": selected_langs,
                "user_meanings": user_meanings_dict,
                "has_custom_audio": has_custom_audio,
                "components": components,
                "lemma": lemma_map,
                "senses": senses_tuple,
                "meanings": meanings_tuple,
                "examples": examples_tuple,
            }
            export_items.append(MappingProxyType(card_dict))

        return tuple(export_items)

    def observe_card_render(
        self,
        card_id: int | None = None,
        *,
        deck_id: int | None = None,
    ) -> MappingProxyType[str, object] | None:
        """Observe next or specified card render payload inside a single read pin."""
        active_reader_conn = getattr(self._thread_local, "reader_conn", None)
        active_gen = getattr(self._thread_local, "pinned_generation", None)

        if active_reader_conn is not None and active_gen is not None:
            return self._observe_card_render_internal(
                active_reader_conn, active_gen, card_id=card_id, deck_id=deck_id
            )

        with self.reading():
            reader_conn = getattr(self._thread_local, "reader_conn", None)
            gen = getattr(self._thread_local, "pinned_generation", None)
            if reader_conn is None or gen is None:
                raise DictionaryRuntimeError("reader connection not available")
            return self._observe_card_render_internal(
                reader_conn, gen, card_id=card_id, deck_id=deck_id
            )

    def observe_export_payload(
        self,
        deck_id: int | None = None,
    ) -> tuple[MappingProxyType[str, object], ...]:
        """Observe export card payloads inside a single read pin."""
        active_reader_conn = getattr(self._thread_local, "reader_conn", None)
        active_gen = getattr(self._thread_local, "pinned_generation", None)

        if active_reader_conn is not None and active_gen is not None:
            return self._observe_export_payload_internal(
                active_reader_conn, active_gen, deck_id=deck_id
            )

        with self.reading():
            reader_conn = getattr(self._thread_local, "reader_conn", None)
            gen = getattr(self._thread_local, "pinned_generation", None)
            if reader_conn is None or gen is None:
                raise DictionaryRuntimeError("reader connection not available")
            return self._observe_export_payload_internal(reader_conn, gen, deck_id=deck_id)

    def materialize_lookup(
        self, query: str
    ) -> tuple[str, tuple[MappingProxyType[str, object], ...]]:
        """Look up exact and surface lemmas, returning (asset_token, candidate_entries)."""
        clean_q = query.strip()
        if not clean_q:
            return ("", ())

        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            gen = self._current_generation
            token = gen.asset.asset_token
            conn = gen.asset.connection

            # 1. Exact lemmas
            cur = conn.execute(
                """
                SELECT id, semantic_ref, lemma, pos, gender, plural, plural_none,
                       genitive_sg, aux, separable, particle, reflexive, praesens_3sg,
                       praeteritum_3sg, partizip_ii, governs, comparative, superlative,
                       ipa, ipa_source, freq_rank, source, license
                FROM lemma
                WHERE (lemma = ? OR lower(lemma) = ?)
                ORDER BY freq_rank ASC NULLS LAST, pos ASC, gender ASC NULLS LAST, semantic_ref ASC
                """,
                (clean_q, clean_q.lower()),
            )
            exact_rows = cur.fetchall()

            # 2. Surface lemmas (if no exact lemmas)
            surface_rows: list[sqlite3.Row] = []
            if not exact_rows:
                cur = conn.execute(
                    """
                    SELECT l.id, l.semantic_ref, l.lemma, l.pos, l.gender, l.plural,
                           l.plural_none, l.genitive_sg, l.aux, l.separable, l.particle,
                           l.reflexive, l.praesens_3sg, l.praeteritum_3sg, l.partizip_ii,
                           l.governs, l.comparative, l.superlative, l.ipa, l.ipa_source,
                           l.freq_rank, l.source, l.license
                    FROM surface_form sf
                    JOIN lemma l ON sf.lemma_id = l.id
                    WHERE (sf.form = ? OR lower(sf.form) = ?)
                    ORDER BY l.freq_rank ASC NULLS LAST, l.pos ASC, l.gender ASC NULLS LAST,
                             l.semantic_ref ASC
                    """,
                    (clean_q, clean_q.lower()),
                )
                seen_ids: set[int] = set()
                for r in cur.fetchall():
                    lid = int(r["id"])
                    if lid not in seen_ids:
                        seen_ids.add(lid)
                        surface_rows.append(r)

            all_lemma_rows = exact_rows if exact_rows else surface_rows
            if not all_lemma_rows:
                return (token, ())

            candidates: list[MappingProxyType[str, object]] = []
            for lem in all_lemma_rows:
                lem_id = int(lem["id"])

                # Senses
                s_cur = conn.execute(
                    """
                    SELECT id, lemma_id, semantic_ref, source_namespace, source_ref, ord,
                           register, source, license
                    FROM sense WHERE lemma_id = ?
                    ORDER BY ord ASC, semantic_ref ASC, id ASC
                    """,
                    (lem_id,),
                )
                sense_rows = s_cur.fetchall()

                # Meanings
                m_cur = conn.execute(
                    """
                    SELECT sm.id, sm.sense_id, sm.language, sm.kind, sm.ord, sm.text,
                           sm.source, sm.license
                    FROM sense_meaning sm
                    JOIN sense s ON sm.sense_id = s.id
                    WHERE s.lemma_id = ?
                    ORDER BY sm.language ASC, sm.kind ASC, sm.ord ASC, sm.id ASC
                    """,
                    (lem_id,),
                )
                meaning_rows = m_cur.fetchall()

                # Examples
                e_cur = conn.execute(
                    """
                    SELECT e.id, e.de, e.en, e.source, e.source_ref, e.license,
                           e.token_count, e.has_proper
                    FROM example_lemma el
                    JOIN example e ON el.example_id = e.id
                    WHERE el.lemma_id = ?
                    ORDER BY e.id ASC
                    """,
                    (lem_id,),
                )
                example_rows = e_cur.fetchall()

                senses_data: list[MappingProxyType[str, object]] = []
                for s in sense_rows:
                    sid = int(s["id"])
                    meanings_data = tuple(
                        MappingProxyType({
                            "language": str(m["language"]),
                            "kind": str(m["kind"]),
                            "text": str(m["text"]),
                            "ord": int(m["ord"]),
                        })
                        for m in meaning_rows
                        if int(m["sense_id"]) == sid
                    )
                    senses_data.append(
                        MappingProxyType({
                            "sense_id": sid,
                            "sense_semantic_ref": str(s["semantic_ref"]),
                            "source_namespace": str(s["source_namespace"]),
                            "source_ref": str(s["source_ref"]),
                            "ord": int(s["ord"]),
                            "register": str(s["register"]) if s["register"] is not None else None,
                            "meanings": meanings_data,
                        })
                    )

                candidates.append(
                    MappingProxyType({
                        "lemma_id": lem_id,
                        "lemma_semantic_ref": str(lem["semantic_ref"]),
                        "lemma": str(lem["lemma"]),
                        "pos": str(lem["pos"]),
                        "gender": str(lem["gender"]) if lem["gender"] is not None else None,
                        "plural": str(lem["plural"]) if lem["plural"] is not None else None,
                        "plural_none": int(lem["plural_none"]),
                        "genitive_sg": (
                            str(lem["genitive_sg"]) if lem["genitive_sg"] is not None else None
                        ),
                        "aux": str(lem["aux"]) if lem["aux"] is not None else None,
                        "separable": int(lem["separable"]),
                        "particle": str(lem["particle"]) if lem["particle"] is not None else None,
                        "reflexive": int(lem["reflexive"]),
                        "praesens_3sg": (
                            str(lem["praesens_3sg"]) if lem["praesens_3sg"] is not None else None
                        ),
                        "praeteritum_3sg": (
                            str(lem["praeteritum_3sg"])
                            if lem["praeteritum_3sg"] is not None
                            else None
                        ),
                        "partizip_ii": (
                            str(lem["partizip_ii"]) if lem["partizip_ii"] is not None else None
                        ),
                        "governs": str(lem["governs"]) if lem["governs"] is not None else None,
                        "comparative": (
                            str(lem["comparative"]) if lem["comparative"] is not None else None
                        ),
                        "superlative": (
                            str(lem["superlative"]) if lem["superlative"] is not None else None
                        ),
                        "ipa": str(lem["ipa"]) if lem["ipa"] is not None else None,
                        "senses": tuple(senses_data),
                        "examples": tuple(
                            MappingProxyType({
                                "de": str(ex["de"]),
                                "en": str(ex["en"]) if ex["en"] is not None else None,
                            })
                            for ex in example_rows
                        ),
                    })
                )

            return (token, tuple(candidates))

    def materialize_card_render_payload(
        self, lemma_semantic_ref: str
    ) -> MappingProxyType[str, object] | None:
        """Materialize immutable lemma data, senses, meanings, and examples for card rendering."""
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            gen = self._current_generation
            conn = gen.asset.connection
            lemma_map, senses_tuple, meanings_tuple, examples_tuple = (
                self._materialize_lemma_under_gen(conn, lemma_semantic_ref)
            )
            if lemma_map is None:
                return None
            return MappingProxyType({
                "lemma": lemma_map,
                "senses": senses_tuple,
                "meanings": meanings_tuple,
                "examples": examples_tuple,
            })

    def materialize_compound_components(
        self, component_refs: Sequence[tuple[str, str]]
    ) -> tuple[MappingProxyType[str, object], ...]:
        """Materialize immutable compound component lemma texts and meanings for languages."""
        with self._lock:
            if self._closed:
                raise DictionaryClosedError("runtime is closed")
            gen = self._current_generation
            conn = gen.asset.connection
            comp_rows = [
                {"lemma_semantic_ref": cr[0], "sense_semantic_ref": cr[1]}
                for cr in component_refs
            ]
            return self._materialize_components_under_gen(conn, comp_rows)

    def activate_dictionary(
        self,
        path: Path | str,
        *,
        version: str = "v1",
        activated_at: datetime | None = None,
    ) -> None:
        """Atomically validate candidate dictionary, relink PART-B, and swap generations."""
        # Phase (1): same-thread reentrancy refusal
        if getattr(self._thread_local, "depth", 0) > 0:
            raise DictionaryRuntimeError("same-thread reentrancy is forbidden")

        # Phase (2): acquire _activation_lock
        with self._activation_lock:
            # Phase (3): closed check under runtime lock
            with self._lock:
                if self._closed:
                    raise DictionaryClosedError("runtime is closed")

            # Phase (4): argument / type validation
            if not isinstance(path, (str, Path)) or isinstance(path, bool):
                raise TypeError(f"path must be a str or Path, got {type(path).__name__}")
            if isinstance(path, str) and not path.strip():
                raise ValueError("candidate dictionary path must not be blank")
            if not isinstance(version, str) or not version.strip():
                raise ValueError("version must be a non-blank string")

            raw_str = str(path)
            normalized_parts = raw_str.replace("\\", "/").split("/")
            if ".." in normalized_parts:
                raise DictionaryAssetError(
                    "path traversal is forbidden in candidate dictionary path"
                )

            candidate_path = Path(path)
            if candidate_path.is_absolute():
                resolved_cand = candidate_path.resolve()
            else:
                resolved_cand = (self._managed_dir / candidate_path).resolve()

            # Phase (5): managed-path validation
            if resolved_cand.parent != self._managed_dir:
                raise DictionaryAssetError(
                    f"candidate dictionary must reside in managed directory: {resolved_cand}"
                )

            if "/" in resolved_cand.name or "\\" in resolved_cand.name:
                raise DictionaryAssetError("candidate dictionary filename contains separators")

            if not resolved_cand.is_file():
                raise DictionaryAssetError(f"candidate dictionary file not found: {resolved_cand}")

            if _is_same_file(resolved_cand, self._user_db_path):
                raise DictionaryAssetError("candidate dictionary is the user database file")

            # Phase (6): candidate validation
            candidate_asset: DictionaryAsset | None = None
            write_conn: sqlite3.Connection | None = None
            committed = False

            try:
                candidate_asset = validate_candidate_dictionary(resolved_cand)

                # Phase (7): BEGIN IMMEDIATE on dedicated write connection, relink, upsert metadata
                now_text = _timestamp(_as_utc(activated_at))
                write_conn = sqlite3.connect(self._user_db_path, check_same_thread=False)
                write_conn.execute("PRAGMA foreign_keys = ON")
                write_conn.execute("BEGIN IMMEDIATE")

                self._relink_part_b(write_conn, candidate_asset, now_text)

                write_conn.execute(
                    """
                    INSERT INTO active_dictionary_metadata (
                        singleton, active_version, active_filename, active_sha256, activated_at
                    ) VALUES (1, ?, ?, ?, ?)
                    ON CONFLICT(singleton) DO UPDATE SET
                        active_version = excluded.active_version,
                        active_filename = excluded.active_filename,
                        active_sha256 = excluded.active_sha256,
                        activated_at = excluded.activated_at
                    """,
                    (version.strip(), resolved_cand.name, candidate_asset.sha256, now_text),
                )

                if self._pre_commit_probe is not None:
                    self._pre_commit_probe()

                # Phase (8): [runtime lock: defensive closed recheck, commit, seam probe, publish]
                seam_exc: BaseException | None = None
                with self._lock:
                    if self._closed:
                        raise DictionaryClosedError("runtime is closed")

                    write_conn.commit()
                    committed = True

                    if self._seam_probe is not None:
                        try:
                            self._seam_probe()
                        except BaseException as exc:
                            seam_exc = exc

                    old_generation = self._current_generation
                    old_generation.retired = True
                    if old_generation.pins == 0 and not old_generation.closed:
                        old_generation.closed = True
                        try:
                            old_generation.asset.close()
                        except Exception:
                            pass

                    self._generation_counter += 1
                    self._current_generation = _Generation(
                        generation_id=self._generation_counter,
                        asset=candidate_asset,
                        pins=0,
                        retired=False,
                        closed=False,
                    )

                if seam_exc is not None:
                    raise seam_exc

            finally:
                if not committed:
                    if write_conn is not None:
                        try:
                            if self._rollback_failure_hook is not None:
                                self._rollback_failure_hook()
                            write_conn.rollback()
                        except Exception:
                            pass
                        try:
                            write_conn.close()
                        except Exception:
                            pass
                    if candidate_asset is not None:
                        try:
                            candidate_asset.close()
                        except Exception:
                            pass
                else:
                    if write_conn is not None:
                        try:
                            if self._writer_close_hook is not None:
                                self._writer_close_hook()
                            write_conn.close()
                        except Exception:
                            pass

    def _relink_part_b(
        self, conn: sqlite3.Connection, asset: DictionaryAsset, now_text: str
    ) -> None:
        notes = conn.execute("SELECT id, status FROM note").fetchall()
        note_status_map = {int(r[0]): str(r[1]) for r in notes}

        binding_rows = conn.execute(
            """
            SELECT note_id, role, component_ord, lemma_semantic_ref, sense_semantic_ref,
                   cached_lemma_id, cached_sense_id, binding_status, component_count
            FROM note_dictionary_binding
            ORDER BY note_id, role, component_ord
            """
        ).fetchall()

        direct_bindings: dict[int, list[sqlite3.Row]] = {}
        component_bindings: dict[int, list[sqlite3.Row]] = {}
        for r in binding_rows:
            nid = int(r[0])
            role = str(r[1])
            if role == "direct":
                direct_bindings.setdefault(nid, []).append(r)
            elif role == "component":
                component_bindings.setdefault(nid, []).append(r)

        for note_id, current_status in note_status_map.items():
            direct_rows = direct_bindings.get(note_id, [])
            comp_rows = component_bindings.get(note_id, [])

            if direct_rows:
                for r in direct_rows:
                    ord_val = int(r[2])
                    sense_ref = str(r[4])
                    target_sense = asset.sense_ids.get(sense_ref)
                    if target_sense is not None:
                        sense_id, lemma_id = target_sense
                        conn.execute(
                            """
                            UPDATE note_dictionary_binding
                            SET cached_lemma_id = ?, cached_sense_id = ?, binding_status = 'bound',
                                last_relinked_at = ?
                            WHERE note_id = ? AND role = 'direct' AND component_ord = ?
                            """,
                            (lemma_id, sense_id, now_text, note_id, ord_val),
                        )
                        if current_status in ("resolved", "derived_compound", "needs_gloss"):
                            conn.execute(
                                "UPDATE note SET status = 'resolved' WHERE id = ?", (note_id,)
                            )
                    else:
                        conn.execute(
                            """
                            UPDATE note_dictionary_binding
                            SET cached_lemma_id = NULL, cached_sense_id = NULL,
                                binding_status = 'unbound', last_relinked_at = ?
                            WHERE note_id = ? AND role = 'direct' AND component_ord = ?
                            """,
                            (now_text, note_id, ord_val),
                        )
                        if current_status in ("resolved", "derived_compound", "needs_gloss"):
                            conn.execute(
                                "UPDATE note SET status = 'needs_gloss' WHERE id = ?", (note_id,)
                            )

            if comp_rows:
                expected_count = comp_rows[0][8]
                is_valid_vector = (
                    isinstance(expected_count, int)
                    and not isinstance(expected_count, bool)
                    and expected_count > 0
                    and len(comp_rows) == expected_count
                    and [r[2] for r in comp_rows] == list(range(expected_count))
                    and all(r[8] == expected_count for r in comp_rows)
                )

                if not is_valid_vector:
                    for r in comp_rows:
                        ord_val = int(r[2])
                        conn.execute(
                            """
                            UPDATE note_dictionary_binding
                            SET cached_lemma_id = NULL, cached_sense_id = NULL,
                                binding_status = 'ambiguous', last_relinked_at = ?
                            WHERE note_id = ? AND role = 'component' AND component_ord = ?
                            """,
                            (now_text, note_id, ord_val),
                        )
                    if current_status in ("resolved", "derived_compound", "needs_gloss"):
                        conn.execute(
                            "UPDATE note SET status = 'needs_gloss' WHERE id = ?", (note_id,)
                        )
                else:
                    all_found = True
                    matched_components: list[tuple[int, int, int]] = []
                    for r in comp_rows:
                        ord_val = int(r[2])
                        sense_ref = str(r[4])
                        target_sense = asset.sense_ids.get(sense_ref)
                        if target_sense is None:
                            all_found = False
                            break
                        matched_components.append((ord_val, target_sense[1], target_sense[0]))

                    if all_found:
                        for ord_val, lemma_id, sense_id in matched_components:
                            conn.execute(
                                """
                                UPDATE note_dictionary_binding
                                SET cached_lemma_id = ?, cached_sense_id = ?,
                                    binding_status = 'bound', last_relinked_at = ?
                                WHERE note_id = ? AND role = 'component' AND component_ord = ?
                                """,
                                (lemma_id, sense_id, now_text, note_id, ord_val),
                            )
                        if current_status in ("resolved", "derived_compound", "needs_gloss"):
                            conn.execute(
                                "UPDATE note SET status = 'derived_compound' WHERE id = ?",
                                (note_id,),
                            )
                    else:
                        for r in comp_rows:
                            ord_val = int(r[2])
                            conn.execute(
                                """
                                UPDATE note_dictionary_binding
                                SET cached_lemma_id = NULL, cached_sense_id = NULL,
                                    binding_status = 'unbound', last_relinked_at = ?
                                WHERE note_id = ? AND role = 'component' AND component_ord = ?
                                """,
                                (now_text, note_id, ord_val),
                            )
                        if current_status in ("resolved", "derived_compound", "needs_gloss"):
                            conn.execute(
                                "UPDATE note SET status = 'needs_gloss' WHERE id = ?", (note_id,)
                            )

    def close(self) -> None:
        """Idempotently close the runtime, retiring and releasing unpinned assets."""
        # Phase (1): same-thread reentrancy refusal
        if getattr(self._thread_local, "depth", 0) > 0:
            raise DictionaryRuntimeError("same-thread reentrancy is forbidden")

        with self._activation_lock:
            with self._lock:
                if self._closed:
                    return
                self._closed = True
                old_generation = self._current_generation
                old_generation.retired = True
                if old_generation.pins == 0 and not old_generation.closed:
                    old_generation.closed = True
                    try:
                        old_generation.asset.close()
                    except Exception:
                        pass

    def __enter__(self) -> DictionaryRuntime:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        self.close()
