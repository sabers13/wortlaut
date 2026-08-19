"""Pytest fixtures and configuration for flashcard tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.resolve import LemmaRecord, LookupProtocol

PART_A_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lemma (
  id            INTEGER PRIMARY KEY,
  lemma         TEXT NOT NULL,
  pos           TEXT NOT NULL,
  gender        TEXT,
  plural        TEXT,
  genitive_sg   TEXT,
  aux           TEXT,
  separable     INTEGER DEFAULT 0,
  particle      TEXT,
  reflexive     INTEGER DEFAULT 0,
  praesens_3sg  TEXT,
  praeteritum_3sg TEXT,
  partizip_ii   TEXT,
  governs       TEXT,
  comparative   TEXT,
  superlative   TEXT,
  ipa           TEXT,
  ipa_source    TEXT,
  freq_rank     INTEGER,
  source        TEXT,
  license       TEXT,
  UNIQUE(lemma, pos, gender)
);
CREATE INDEX IF NOT EXISTS ix_lemma_lookup ON lemma(lemma, pos);

CREATE TABLE IF NOT EXISTS surface_form (
  form      TEXT NOT NULL,
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  PRIMARY KEY (form, lemma_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sense (
  id        INTEGER PRIMARY KEY,
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  ord       INTEGER NOT NULL DEFAULT 0,
  gloss_en  TEXT NOT NULL,
  register  TEXT,
  source    TEXT,
  license   TEXT
);
CREATE INDEX IF NOT EXISTS ix_sense_lemma ON sense(lemma_id, ord);

CREATE TABLE IF NOT EXISTS example (
  id           INTEGER PRIMARY KEY,
  de           TEXT NOT NULL,
  en           TEXT,
  source       TEXT,
  source_ref   TEXT,
  license      TEXT,
  token_count  INTEGER,
  has_proper   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS example_lemma (
  lemma_id   INTEGER NOT NULL REFERENCES lemma(id),
  example_id INTEGER NOT NULL REFERENCES example(id),
  PRIMARY KEY (lemma_id, example_id)
) WITHOUT ROWID;
"""


@dataclass
class InMemoryLookupOracle(LookupProtocol):
    """In-memory pure test double implementing LookupProtocol."""

    lemmas: list[LemmaRecord] = field(default_factory=list)
    surface_forms: dict[str, list[LemmaRecord]] = field(default_factory=dict)

    def add_lemma(
        self,
        lemma: str,
        pos: str,
        gender: str | None = None,
        lemma_id: int | None = None,
    ) -> LemmaRecord:
        record = LemmaRecord(
            id=lemma_id if lemma_id is not None else len(self.lemmas) + 1,
            lemma=lemma,
            pos=pos,
            gender=gender,
        )
        self.lemmas.append(record)
        return record

    def add_surface_form(self, form: str, record: LemmaRecord) -> None:
        entries = self.surface_forms.setdefault(form.lower(), [])
        if record not in entries:
            entries.append(record)

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[LemmaRecord]:
        matches: list[LemmaRecord] = []
        target = lemma.strip().lower()
        for rec in self.lemmas:
            if rec.lemma.lower() == target:
                if pos is not None and rec.pos != pos:
                    continue
                if gender is not None and rec.gender != gender:
                    continue
                matches.append(rec)
        return matches

    def lookup_surface_form(self, form: str) -> Sequence[LemmaRecord]:
        target = form.strip().lower()
        return self.surface_forms.get(target, [])


@pytest.fixture
def part_a_schema() -> str:
    """Return PART A schema SQL string."""
    return PART_A_SCHEMA_SQL


@pytest.fixture
def empty_oracle() -> InMemoryLookupOracle:
    """Return an empty pure in-memory lookup oracle."""
    return InMemoryLookupOracle()


@pytest.fixture
def populated_oracle() -> InMemoryLookupOracle:
    """Return an in-memory lookup oracle populated with standard test vocabulary."""
    oracle = InMemoryLookupOracle()
    # Nouns with gender disambiguation
    oracle.add_lemma("See", "NOUN", "der", lemma_id=1)  # der See (lake)
    oracle.add_lemma("See", "NOUN", "die", lemma_id=2)  # die See (sea)
    oracle.add_lemma("Bank", "NOUN", "die", lemma_id=3)  # die Bank

    # Compound test vocabulary (ADR-0001 §10 verified case)
    l_kranken = oracle.add_lemma("kranken", "NOUN", "die", lemma_id=4)
    oracle.add_lemma("Versicherung", "NOUN", "die", lemma_id=5)
    oracle.add_lemma("Karte", "NOUN", "die", lemma_id=6)
    oracle.add_lemma("Haus", "NOUN", "das", lemma_id=7)
    oracle.add_lemma("Tür", "NOUN", "die", lemma_id=8)
    oracle.add_lemma("Tag", "NOUN", "der", lemma_id=9)
    oracle.add_lemma("Licht", "NOUN", "das", lemma_id=10)

    # Verbs and separable verbs
    l_anrufen = oracle.add_lemma("anrufen", "VERB", None, lemma_id=11)
    oracle.add_lemma("rufen", "VERB", None, lemma_id=12)

    # Surface forms
    oracle.add_surface_form("häuser", oracle.lemmas[6])  # Haus
    oracle.add_surface_form("Häuser", oracle.lemmas[6])
    oracle.add_surface_form("rief an", l_anrufen)
    oracle.add_surface_form("ruft an", l_anrufen)
    oracle.add_surface_form("Kranken", l_kranken)

    return oracle


@pytest.fixture
def create_test_db(tmp_path: Path) -> Callable[..., Path]:
    """Factory fixture to create and populate a temporary PART A SQLite database."""

    def _factory(populate: bool = True) -> Path:
        db_path = tmp_path / "dict_test.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(PART_A_SCHEMA_SQL)

        if populate:
            # Insert test lemmas
            lemma_rows = [
                (1, "See", "NOUN", "der", 0, None, "zeː", "wiktionary", 100, "wiktionary", "CC"),
                (2, "See", "NOUN", "die", 0, None, "zeː", "wiktionary", 150, "wiktionary", "CC"),
                (3, "Bank", "NOUN", "die", 0, None, "baŋk", "wiktionary", 50, "wiktionary", "CC"),
                (4, "kranken", "NOUN", "die", 0, None, None, None, 500, "wiktionary", "CC"),
                (
                    5,
                    "Versicherung",
                    "NOUN",
                    "die",
                    0,
                    None,
                    "fɛɐ̯ˈzɪçəʁʊŋ",
                    "wiktionary",
                    200,
                    "wiktionary",
                    "CC",
                ),
                (
                    6,
                    "Karte",
                    "NOUN",
                    "die",
                    0,
                    None,
                    "ˈkaʁtə",
                    "wiktionary",
                    80,
                    "wiktionary",
                    "CC",
                ),
                (7, "Haus", "NOUN", "das", 0, None, "haʊ̯s", "wiktionary", 20, "wiktionary", "CC"),
                (8, "Tür", "NOUN", "die", 0, None, "tyːɐ̯", "wiktionary", 90, "wiktionary", "CC"),
                (9, "Tag", "NOUN", "der", 0, None, "taːk", "wiktionary", 10, "wiktionary", "CC"),
                (
                    10,
                    "Licht",
                    "NOUN",
                    "das",
                    0,
                    None,
                    "lɪçt",
                    "wiktionary",
                    110,
                    "wiktionary",
                    "CC",
                ),
                (
                    11,
                    "anrufen",
                    "VERB",
                    None,
                    1,
                    "an",
                    "ˈanˌʁuːfn̩",
                    "wiktionary",
                    60,
                    "wiktionary",
                    "CC",
                ),
                (
                    12,
                    "rufen",
                    "VERB",
                    None,
                    0,
                    None,
                    "ˈʁuːfn̩",
                    "wiktionary",
                    70,
                    "wiktionary",
                    "CC",
                ),
            ]
            conn.executemany(
                """
                INSERT INTO lemma (
                    id, lemma, pos, gender, separable, particle,
                    ipa, ipa_source, freq_rank, source, license
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                lemma_rows,
            )

            # Insert surface forms
            conn.executemany(
                "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
                [
                    ("Häuser", 7),
                    ("häuser", 7),
                    ("rief an", 11),
                    ("ruft an", 11),
                    ("ruft", 12),
                ],
            )

            # Insert senses
            sense_insert_sql = (
                "INSERT INTO sense (id, lemma_id, ord, gloss_en, source, license) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            conn.executemany(
                sense_insert_sql,
                [
                    (1, 1, 0, "lake", "wiktionary", "CC BY-SA 4.0"),
                    (2, 2, 0, "sea, ocean", "wiktionary", "CC BY-SA 4.0"),
                    (3, 7, 0, "house, building", "wiktionary", "CC BY-SA 4.0"),
                    (4, 11, 0, "to call, phone", "wiktionary", "CC BY-SA 4.0"),
                    (5, 12, 0, "to shout, cry out", "wiktionary", "CC BY-SA 4.0"),
                ],
            )

            # Insert examples
            example_insert_sql = (
                "INSERT INTO example (id, de, en, source, license, token_count) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            conn.executemany(
                example_insert_sql,
                [
                    (1, "Der See ist tief.", "The lake is deep.", "tatoeba", "CC BY 2.0 FR", 5),
                    (
                        2,
                        "Die See ist stürmisch.",
                        "The sea is stormy.",
                        "tatoeba",
                        "CC BY 2.0 FR",
                        5,
                    ),
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

            # Insert example_lemma mappings
            conn.executemany(
                "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)",
                [
                    (1, 1),
                    (2, 2),
                    (11, 3),
                ],
            )

            conn.commit()

        conn.close()
        return db_path

    return _factory
