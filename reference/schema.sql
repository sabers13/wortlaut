-- ============================================================
-- PART A — shared, derived, ships as a read-only asset.
-- Built offline by tools/build_dict.py. No user data here.
-- Numeric IDs (lemma.id, sense.id, etc.) are local per-asset keys only.
-- Durable cross-version identity is defined by semantic_ref.
-- ============================================================

CREATE TABLE IF NOT EXISTS lemma (
  id            INTEGER PRIMARY KEY,
  semantic_ref  TEXT NOT NULL UNIQUE,
  lemma         TEXT NOT NULL,
  pos           TEXT NOT NULL,          -- NOUN | VERB | ADJ | ADV | PREP ...
  gender        TEXT,                   -- der | die | das
  plural        TEXT,
  plural_none   INTEGER NOT NULL DEFAULT 0 CHECK (plural_none IN (0,1)),
  genitive_sg   TEXT,
  aux           TEXT,                   -- haben | sein
  separable     INTEGER DEFAULT 0,
  particle      TEXT,
  reflexive     INTEGER DEFAULT 0,
  praesens_3sg  TEXT,
  praeteritum_3sg TEXT,
  partizip_ii   TEXT,
  governs       TEXT,                   -- JSON: ["Akkusativ"] or ["für+Akkusativ"]
  comparative   TEXT,
  superlative   TEXT,
  ipa           TEXT,
  ipa_source    TEXT,                   -- wiktionary | espeak
  freq_rank     INTEGER,
  source        TEXT,                   -- wiktionary | llm_generated_v1 | contributed
  license       TEXT,
  CHECK (plural_none = 0 OR plural IS NULL),
  UNIQUE(lemma, pos, gender)            -- der See / die See
);
CREATE INDEX IF NOT EXISTS ix_lemma_lookup ON lemma(lemma, pos);

CREATE TABLE IF NOT EXISTS surface_form (
  form      TEXT NOT NULL,              -- "Häuser", "rief an", "ruft"
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  PRIMARY KEY (form, lemma_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sense (
  id                INTEGER PRIMARY KEY,
  lemma_id          INTEGER NOT NULL REFERENCES lemma(id),
  semantic_ref      TEXT NOT NULL UNIQUE,
  source_namespace  TEXT NOT NULL,
  source_ref        TEXT NOT NULL,
  ord               INTEGER NOT NULL DEFAULT 0,
  register          TEXT,
  source            TEXT,
  license           TEXT
);
CREATE INDEX IF NOT EXISTS ix_sense_lemma ON sense(lemma_id, ord);

CREATE TABLE IF NOT EXISTS sense_meaning (
  id        INTEGER PRIMARY KEY,
  sense_id  INTEGER NOT NULL REFERENCES sense(id) ON DELETE CASCADE,
  language  TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK (kind IN ('definition', 'synonym', 'translation')),
  ord       INTEGER NOT NULL DEFAULT 0,
  text      TEXT NOT NULL,
  source    TEXT NOT NULL,
  license   TEXT NOT NULL,
  UNIQUE(sense_id, language, kind, ord)
);
CREATE INDEX IF NOT EXISTS ix_sense_meaning ON sense_meaning(sense_id, language, ord);

CREATE TABLE IF NOT EXISTS sense_meaning_derivation (
  generated_meaning_id INTEGER NOT NULL
      REFERENCES sense_meaning(id) ON DELETE CASCADE,
  source_meaning_id INTEGER NOT NULL
      REFERENCES sense_meaning(id) ON DELETE RESTRICT,
  PRIMARY KEY (generated_meaning_id, source_meaning_id),
  CHECK (generated_meaning_id <> source_meaning_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS example (
  id           INTEGER PRIMARY KEY,
  de           TEXT NOT NULL,
  en           TEXT,
  source       TEXT,                    -- tatoeba | wiktionary_de
  source_ref   TEXT,                    -- upstream id, for re-diffing dumps
  license      TEXT,
  token_count  INTEGER,
  has_proper   INTEGER DEFAULT 0
);

-- inverted index: lemma -> example. Built with the SAME resolver
-- used at highlight time, so "anrufen" matches "ruft ... an".
CREATE TABLE IF NOT EXISTS example_lemma (
  lemma_id   INTEGER NOT NULL REFERENCES lemma(id),
  example_id INTEGER NOT NULL REFERENCES example(id),
  PRIMARY KEY (lemma_id, example_id)
) WITHOUT ROWID;

-- ============================================================
-- PART B — per user, mutable. Separate DB file / schema.
-- ============================================================

CREATE TABLE IF NOT EXISTS note (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER NOT NULL,
  lemma_id       INTEGER,               -- NULL when unresolved
  lemma_text     TEXT NOT NULL,         -- denormalised: survives dict rebuilds
  pos            TEXT NOT NULL,
  sense_id       INTEGER,
  gloss_user     TEXT,                  -- user-filled when needs_gloss
  front_override TEXT,
  back_override  TEXT,
  status         TEXT NOT NULL,         -- resolved | derived_compound | needs_gloss
  -- ADR-0002 D21/D23: the primary example is stored by value and frozen at
  -- creation. Highlight stores the captured sentence; manual/CSV stores the
  -- chosen dictionary sentence when one exists. lesson_id/char_* are optional
  -- provenance only, never a live render dependency.
  example_de     TEXT,                  -- NULL only when no usable example exists
  lesson_label   TEXT,                  -- display name of source lecture
  lesson_id      TEXT,                  -- provenance, not a live pointer
  char_start     INTEGER,
  char_end       INTEGER,
  created_at     TEXT NOT NULL,
  UNIQUE(user_id, lemma_text, pos, sense_id)   -- Anki-style dupe detection
);

CREATE TABLE IF NOT EXISTS card (
  id          INTEGER PRIMARY KEY,
  note_id     INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  template    TEXT NOT NULL,            -- recognition | production | gender
  state       INTEGER NOT NULL,
  step        INTEGER,
  stability   REAL,
  difficulty  REAL,
  due         TEXT NOT NULL,
  last_review TEXT,
  UNIQUE(note_id, template)
);
CREATE INDEX IF NOT EXISTS ix_card_due ON card(due);

-- Append-only (AGENTS R6). rating = mapped FSRS grade 1-4;
-- confidence = raw user rating 1-5 (ADR-0003 D28/D29).
CREATE TABLE IF NOT EXISTS review_log (
  id             INTEGER PRIMARY KEY,
  card_id        INTEGER NOT NULL REFERENCES card(id) ON DELETE CASCADE,
  rating         INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4),
  confidence     INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
  reviewed_at    TEXT NOT NULL,
  review_duration_ms INTEGER
);

-- Decks are many-to-many with notes (ADR-0001 D12/§5). One note = one FSRS
-- state, appearing in any number of decks.
CREATE TABLE IF NOT EXISTS deck (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER NOT NULL,
  name        TEXT NOT NULL,
  lesson_id   TEXT,                     -- NULL for manual/custom decks
  kind        TEXT NOT NULL,            -- 'lecture' | 'manual' | 'custom'
  created_at  TEXT NOT NULL,
  UNIQUE(user_id, lesson_id),
  UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS note_deck (
  note_id  INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  deck_id  INTEGER NOT NULL REFERENCES deck(id) ON DELETE CASCADE,
  added_at TEXT NOT NULL,
  PRIMARY KEY (note_id, deck_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS gloss_contribution (
  lemma_text TEXT NOT NULL,
  pos        TEXT NOT NULL,
  gloss_en   TEXT NOT NULL,
  user_id    INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(lemma_text, pos, user_id)      -- one vote per user per lemma
);
