"""PART-B deck persistence, FSRS reviews, and learner-meaning selection.

This module owns only the mutable user database. Dictionary meaning data is an
already-validated value supplied by the caller; this module never opens the
dictionary database (AGENTS R9).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TypeAlias, cast

from fsrs import Card, Rating, Scheduler, State

DictionaryMeanings: TypeAlias = Mapping[str, object]
ComponentBinding: TypeAlias = tuple[str, str]


class DeckError(ValueError):
    """Raised when a deck-layer request violates its data contract."""


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


def create_deck(conn: sqlite3.Connection, name: str, *, created_at: datetime | None = None) -> int:
    """Create a user deck and return its primary key."""
    if not name.strip():
        raise DeckError("deck name must not be blank")
    with conn:
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
    with conn:
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
) -> None:
    """Add a note to a deck without duplicating an existing membership."""
    with conn:
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
        conn.execute(
            "INSERT INTO deck (name, created_at) VALUES ('Orphaned', ?)", (timestamp,)
        )
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
    conn: sqlite3.Connection, note_id: int, languages: Sequence[str]
) -> None:
    """Replace a note's display language set after validating it in full."""
    selected = _validate_languages(languages)
    with conn:
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
) -> None:
    """Upsert a language-specific note-local user meaning."""
    _validate_language(language)
    if not meaning_text.strip():
        raise DeckError("user meaning must not be blank")
    timestamp = _timestamp(_as_utc(now))
    with conn:
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


def delete_user_meaning(conn: sqlite3.Connection, note_id: int, language: str) -> None:
    """Remove one note-local user meaning without changing selected languages."""
    _validate_language(language)
    with conn:
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

    Availability uses validated D47 bindings, not ``note.status``. Thus a
    relink owner changing a resolver status cannot accidentally change D43
    meaning availability; unbound bindings are the fail-closed condition.
    """
    if conn.execute("SELECT 1 FROM note WHERE id = ?", (note_id,)).fetchone() is None:
        raise DeckError("unknown note")
    selected = selected_meaning_languages(conn, note_id)
    user_rows = conn.execute(
        "SELECT lang, meaning_text FROM note_user_meaning WHERE note_id = ?", (note_id,)
    ).fetchall()
    user_meanings = {str(row[0]): str(row[1]) for row in user_rows}
    direct = _valid_bindings(conn, note_id, "direct")
    components = _valid_bindings(conn, note_id, "component")
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
            _parse_timestamp(str(row["last_review"]))
            if row["last_review"] is not None
            else None
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
