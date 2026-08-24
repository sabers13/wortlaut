"""Tests for PART-B deck scheduling and selected learner meanings."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fsrs import State

from app import deck

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def _new_note_and_card(conn: sqlite3.Connection) -> tuple[int, int]:
    note_id = deck.create_note(
        conn,
        "lemma:v1:haus",
        sense_semantic_ref="sense:v1:haus:0",
        status="resolved",
        meaning_languages=("de", "en"),
        created_at=NOW,
    )
    row = conn.execute("SELECT id FROM card WHERE note_id = ?", (note_id,)).fetchone()
    assert row is not None
    return note_id, int(row[0])


def test_confidence_mapping_and_new_card_scheduler_cases(user_db: sqlite3.Connection) -> None:
    expected = {
        1: (1, State.Learning, timedelta(minutes=1)),
        2: (1, State.Learning, timedelta(minutes=1)),
        3: (2, State.Learning, timedelta(minutes=5, seconds=30)),
        4: (3, State.Learning, timedelta(minutes=10)),
        5: (4, State.Review, timedelta(days=8)),
    }
    results: dict[int, deck.ReviewResult] = {}
    for confidence, (rating, state, interval) in expected.items():
        _, card_id = _new_note_and_card(user_db)
        result = deck.review(user_db, card_id, confidence, reviewed_at=NOW)
        results[confidence] = result
        assert result.rating == rating
        assert result.state is state
        assert result.due_at - NOW == interval

    assert results[1].due_at == results[2].due_at
    assert results[1].interval_days == results[2].interval_days
    assert results[3].due_at - NOW == timedelta(minutes=5, seconds=30)
    assert results[4].due_at - NOW == timedelta(minutes=10)
    assert results[5].state is State.Review


def test_review_log_persists_raw_confidence_and_mapped_rating(
    user_db: sqlite3.Connection,
) -> None:
    note_id, card_id = _new_note_and_card(user_db)
    first = deck.review(user_db, card_id, 2, reviewed_at=NOW)
    second = deck.review(user_db, card_id, 4, reviewed_at=first.due_at)

    logs = user_db.execute(
        "SELECT confidence, rating FROM review_log WHERE card_id = ? ORDER BY id", (card_id,)
    ).fetchall()
    assert [(row[0], row[1]) for row in logs] == [(2, 1), (4, 3)]
    note = user_db.execute(
        "SELECT review_count, last_confidence, due_at FROM note WHERE id = ?", (note_id,)
    ).fetchone()
    assert note is not None
    assert tuple(note) == (2, 4, second.due_at.isoformat())


def test_deck_deletion_orphans_unreviewed_and_reviewed_notes(user_db: sqlite3.Connection) -> None:
    reviewed_note, card_id = _new_note_and_card(user_db)
    unreviewed_note, _ = _new_note_and_card(user_db)
    deck_id = deck.create_deck(user_db, "Lesson 1", created_at=NOW)
    deck.add_note_to_deck(user_db, reviewed_note, deck_id, created_at=NOW)
    deck.add_note_to_deck(user_db, unreviewed_note, deck_id, created_at=NOW)
    deck.review(user_db, card_id, 4, reviewed_at=NOW)

    deck.delete_deck(user_db, deck_id, now=NOW)

    for note_id in (reviewed_note, unreviewed_note):
        note = user_db.execute("SELECT status FROM note WHERE id = ?", (note_id,)).fetchone()
        assert note is not None and note[0] == "orphaned"
        membership = user_db.execute(
            """
            SELECT 1 FROM note_deck JOIN deck ON deck.id = note_deck.deck_id
            WHERE note_deck.note_id = ? AND deck.name = 'Orphaned'
            """,
            (note_id,),
        ).fetchone()
        assert membership is not None
    review_count = user_db.execute(
        "SELECT COUNT(*) FROM review_log WHERE card_id = ?", (card_id,)
    ).fetchone()[0]
    assert review_count == 1


def test_user_meanings_precede_dictionary_and_availability_uses_binding(
    user_db: sqlite3.Connection,
) -> None:
    note_id, _ = _new_note_and_card(user_db)
    dictionary = {"sense:v1:haus:0": {"de": ("Haus",), "en": ("house",)}}
    assert deck.meaning_state(user_db, note_id, dictionary) == "complete"

    deck.set_user_meaning(user_db, note_id, "en", "my home", now=NOW)
    assert deck.resolved_meanings(user_db, note_id, dictionary) == {
        "de": ("Haus",),
        "en": ("my home",),
    }
    user_db.execute("UPDATE note SET status = 'orphaned' WHERE id = ?", (note_id,))
    user_db.commit()
    assert deck.meaning_state(user_db, note_id, dictionary) == "complete"


def test_derived_compound_requires_all_component_languages(user_db: sqlite3.Connection) -> None:
    note_id = deck.create_note(
        user_db,
        "lemma:v1:compound",
        status="derived_compound",
        component_bindings=(
            ("lemma:v1:haus", "sense:v1:haus:0"),
            ("lemma:v1:tuer", "sense:v1:tuer:0"),
        ),
        meaning_languages=("de", "en"),
        created_at=NOW,
    )
    dictionary = {
        "sense:v1:haus:0": {"de": ("Haus",), "en": ("house",)},
        "sense:v1:tuer:0": {"de": ("Tür",)},
    }
    assert deck.meaning_state(user_db, note_id, dictionary) == "partial"
    deck.set_user_meaning(user_db, note_id, "en", "door house", now=NOW)
    assert deck.meaning_state(user_db, note_id, dictionary) == "complete"


def test_derived_compound_requires_a_full_bound_contiguous_component_vector(
    user_db: sqlite3.Connection,
) -> None:
    note_id = deck.create_note(
        user_db,
        "lemma:v1:compound",
        status="derived_compound",
        component_bindings=(
            ("lemma:v1:haus", "sense:v1:haus:0"),
            ("lemma:v1:tuer", "sense:v1:tuer:0"),
        ),
        meaning_languages=("en",),
        created_at=NOW,
    )
    dictionary = {
        "sense:v1:haus:0": {"en": ("house",)},
        "sense:v1:tuer:0": {"en": ("door",)},
    }
    assert deck.resolved_meanings(user_db, note_id, dictionary) == {"en": ("house", "door")}
    component_counts = user_db.execute(
        """
        SELECT component_count FROM note_dictionary_binding
        WHERE note_id = ? AND role = 'component' ORDER BY component_ord
        """,
        (note_id,),
    ).fetchall()
    assert [row[0] for row in component_counts] == [2, 2]

    user_db.execute(
        """
        UPDATE note_dictionary_binding SET binding_status = 'unbound'
        WHERE note_id = ? AND role = 'component' AND component_ord = 1
        """,
        (note_id,),
    )
    user_db.commit()
    assert deck.resolved_meanings(user_db, note_id, dictionary) == {"en": ()}

    user_db.execute(
        """
        UPDATE note_dictionary_binding SET binding_status = 'bound'
        WHERE note_id = ? AND role = 'component' AND component_ord = 1
        """,
        (note_id,),
    )
    user_db.execute(
        """
        DELETE FROM note_dictionary_binding
        WHERE note_id = ? AND role = 'component' AND component_ord = 1
        """,
        (note_id,),
    )
    user_db.commit()
    # The remaining ordinal-zero row still says the resolver supplied two
    # components, so this must not render a one-component dictionary prefix.
    assert deck.resolved_meanings(user_db, note_id, dictionary) == {"en": ()}


def test_create_note_requires_an_explicit_non_empty_language_selection(
    user_db: sqlite3.Connection,
) -> None:
    before = user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0]
    with pytest.raises(TypeError, match="meaning_languages"):
        getattr(deck, "create_note")(user_db, "lemma:v1:haus")
    with pytest.raises(deck.DeckError, match="at least one"):
        deck.create_note(user_db, "lemma:v1:haus", meaning_languages=())
    assert user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0] == before


def test_deck_deletion_reads_memberships_inside_its_immediate_transaction(
    user_db: sqlite3.Connection,
) -> None:
    note_id, _ = _new_note_and_card(user_db)
    deck_id = deck.create_deck(user_db, "Lesson transaction", created_at=NOW)
    deck.add_note_to_deck(user_db, note_id, deck_id, created_at=NOW)
    statements: list[str] = []
    user_db.set_trace_callback(statements.append)
    try:
        deck.delete_deck(user_db, deck_id, now=NOW)
    finally:
        user_db.set_trace_callback(None)

    normalized = [statement.upper() for statement in statements]
    begin_at = normalized.index("BEGIN IMMEDIATE")
    membership_read_at = next(
        index
        for index, statement in enumerate(normalized)
        if statement.startswith("SELECT NOTE_ID FROM NOTE_DECK WHERE DECK_ID")
    )
    assert begin_at < membership_read_at
    orphaned = user_db.execute(
        """
        SELECT 1 FROM note_deck JOIN deck ON deck.id = note_deck.deck_id
        WHERE note_deck.note_id = ? AND deck.name = 'Orphaned'
        """,
        (note_id,),
    ).fetchone()
    assert orphaned is not None


def test_fa_is_rejected_before_any_write(user_db: sqlite3.Connection) -> None:
    before = user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0]
    with pytest.raises(deck.DeckError, match="'de' or 'en'"):
        deck.create_note(user_db, "lemma:v1:haus", meaning_languages=("fa",))
    assert user_db.execute("SELECT COUNT(*) FROM note").fetchone()[0] == before

    note_id, _ = _new_note_and_card(user_db)
    meanings_before = user_db.execute("SELECT COUNT(*) FROM note_user_meaning").fetchone()[0]
    with pytest.raises(deck.DeckError, match="'de' or 'en'"):
        deck.set_user_meaning(user_db, note_id, "fa", "خانه")
    meaning_count = user_db.execute("SELECT COUNT(*) FROM note_user_meaning").fetchone()[0]
    assert meaning_count == meanings_before


def test_meaning_language_selection_must_remain_non_empty(user_db: sqlite3.Connection) -> None:
    note_id, _ = _new_note_and_card(user_db)
    before = deck.selected_meaning_languages(user_db, note_id)
    with pytest.raises(deck.DeckError, match="at least one"):
        deck.set_meaning_languages(user_db, note_id, ())
    assert deck.selected_meaning_languages(user_db, note_id) == before
