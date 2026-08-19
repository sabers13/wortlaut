# Slice 3 report

Review: PENDING (T3, full diff)

## NARRATIVE

### 1. Implemented CLI and Output Contract
- Implemented `tools/build_dict.py` exposing the exact subcommand CLI:
  `python tools/build_dict.py stage01 --en-jsonl <path> --de-jsonl <path> --output <path>`.
- The transform processes input JSON Lines dumps line-by-line without loading entire datasets into memory, using standard library modules only.
- Output database contains exactly the stage-01-owned PART A tables (`lemma`, `surface_form`, and `sense`), with schema and column definitions compatible with `reference/schema.sql` and readable by `app.dictionary.Dictionary`. Foreign key checks are enabled (`PRAGMA foreign_keys = ON;`).
- Builds to a temporary sibling file and atomically publishes upon complete success. Fails closed on existing output paths, malformed JSON, invalid field types on participating records, and conflicting gender tags, leaving no target file on error.

### 2. Exact Fixture and Gate Numbers
- `tests/test_build_dict_stage01.py` executes 11 targeted unit and contract tests verifying schema compatibility, deterministic IDs and ordering, POS mappings, form derivation, sense limits, failure modes, and CLI execution:
  - `.venv/bin/pytest -q tests/test_build_dict_stage01.py`: 11 passed in 1.20s.
- Project gate execution (`make gate`):
  - `.venv/bin/ruff check .`: All checks passed.
  - `.venv/bin/mypy --strict .`: Success: no issues found in 12 source files.
  - `.venv/bin/pytest -q`: 91 passed in 6.59s (80 existing + 11 new tests).
  - `.venv/bin/python tools/check_agents.py`: AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling).

### 3. Source and License Attribution Policy
- In compliance with AGENTS R11, every persisted `lemma` and `sense` row carries `source='wiktionary'` and `license='CC BY-SA'`.
- English-edition records own English gloss senses (`sense` table). Senses are de-duplicated and capped at the first 3 glosses per lemma with sequential `ord=0, 1, 2...`. German-edition glosses are not written to `gloss_en`.

### 4. Multi-word Surface Form Evidence (`rief an` / `ruft an`)
- Multi-word separable forms `rief an` (past 3sg) and `ruft an` (present 3sg) are extracted verbatim from Wiktextract `forms` and persisted in `surface_form` associated with lemma `anrufen`.
- Verified via `Dictionary.lookup_surface_form("rief an")` and `Dictionary.lookup_surface_form("ruft an")` returning `anrufen`, confirming inflected manual entry support.

### 5. Stop-and-Ask Conditions
- No Stop-and-ask conditions were encountered.

### 6. Deliberately Deferred Fields and Problems
- Lemma grammatical fields `aux`, `governs`, `reflexive`, `separable`, `particle`, and `freq_rank` are left at NULL or schema defaults (0) in stage 01 per C7.
- Stage 02 Tatoeba indexing (`example`, `example_lemma`), frequency computation, gap finding, and LLM glossing are deferred to stages 02–04.
- User-state PART B tables (`note`, `card`, `review_log`) remain absent from dictionary assets per R9 / C3.

### 7. Work Left Undone
- None for slice-3 scope.

## ADR-0004 Stage-01 alignment amendment

### 1. Amended Commit and Attempt Invariant
- Amended commit SHA: `7ceea14e39a7c831edfc803632d3c868ea0f3091` (accepted Attempt-1 tip).
- Attempt ladder status: The attempt ladder was NOT incremented (remains Attempt 1, aligned with accepted/frozen ADR-0004 D36/D45/D46/D47 governance alignment amendment). The audit counter is NOT incremented.

### 2. Aligned Schema Tables and Columns
The following PART A schema changes from ADR-0004 were aligned in `reference/schema.sql`, `tools/build_dict.py`, and test fixtures:
- `lemma.semantic_ref TEXT NOT NULL UNIQUE`: Canonical versioned stable reference format `lemma:v1:<sha256>`.
- `lemma.plural_none INTEGER NOT NULL DEFAULT 0 CHECK (plural_none IN (0, 1))`: Tri-state noun plural tracking with schema check `CHECK (plural_none = 0 OR plural IS NULL)`.
- `sense.semantic_ref TEXT NOT NULL UNIQUE`: Canonical versioned stable reference format `sense:v1:<sha256>`.
- `sense.source_namespace TEXT NOT NULL`: Explicit upstream provenance namespace (`wiktextract:enwiktionary` in stage 01).
- `sense.source_ref TEXT NOT NULL`: Stable upstream reference (`senseid:<id>`, `senseids:v1:<hash>`, `wikidata:<qid>`, `wikidata-set:v1:<hash>`, or canonical fingerprint `fingerprint:v1:<hash>`).
- `sense_meaning`: Normalized language-neutral meaning table storing DE/EN/FA learner meanings with explicit provenance (`source`, `license`, `language`, `kind`, `ord`, `text`).
- `sense_meaning_derivation`: Normalized table recording consumption edges from source-backed meanings to generated meanings (`generated_meaning_id`, `source_meaning_id`).
- Removed `sense.gloss_en`: Language-neutral `sense` table decoupled from English gloss text (D36).
- Documented in schema comments that all PART A numeric IDs (`lemma.id`, `sense.id`, `sense_meaning.id`, etc.) are local SQLite database keys only and must never be treated as durable semantic identity (R13).

### 3. Attribution and Derivation Policy (R11 / D45 / D46)
- Every persisted `lemma`, `sense`, and `sense_meaning` row carries non-empty `source` and `license` fields.
- Upstream Wiktionary rows carry `source='wiktionary'` and `license='CC BY-SA'` (or explicit variant).
- Derived/generated meaning rows require versioned markers matching `^llm_generated_v[0-9]+$` and must have valid, non-self, same-sense derivation edges to source-backed meanings. Generated-to-generated derivation edges and cross-sense edges fail closed.
- Build-time validation `validate_sense_meaning_derivations()` enforces all D45 derivation rules on build completion.

### 4. Tri-State Noun Plural Handling (D36 / A9)
- Known plural: `plural = <form>` and `plural_none = 0`.
- Explicit no-plural (e.g. `tags: ["no-plural"]`, "no plural"): `plural = NULL` and `plural_none = 1`.
- Unknown/unattested plural: `plural = NULL` and `plural_none = 0`.
- Contradictory plural state (both explicit form and `no-plural` tag present) fails closed during dictionary build.

### 5. Verified Golden Test Vectors (A15 #5-#6)
- Lemma semantic ref: `["de","Haus","NOUN","das"]` -> `lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436`
- Lemma semantic ref (verb with null gender): `["de","anrufen","VERB","<null>"]` -> `lemma:v1:0694906fb1cb9a54d2a100d341607d922446d187b0bb250546f06c755a229c8b`
- Sense semantic ref: `["lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436","wiktextract:enwiktionary","senseid:en-house-1"]` -> `sense:v1:2fdd041adad74df1dfcd67a3ed5245c54bb03c20e373f989829e30dc755a70e6`

### 6. Targeted Test and Gate Numbers
- Targeted tests:
  - `tests/test_build_dict_stage01.py`: 23 passed in 2.92s
  - `tests/test_dictionary.py`: 14 passed in 3.36s
  - `tests/test_resolve.py`: 22 passed in 0.02s
  - `tests/test_resolve_spacy.py`: 5 passed in 1.60s
  - Subtotal: 64 passed in 7.90s
- Full project gate (`make gate`):
  - `.venv/bin/ruff check .`: All checks passed!
  - `.venv/bin/mypy --strict .`: Success: no issues found in 12 source files
  - `.venv/bin/pytest -q`: 106 passed in 9.03s
  - `.venv/bin/python tools/check_agents.py`: AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling)

### 7. PART-B Scope Declaration
- No PART-B code was modified. Stage-01 is strictly PART-A dictionary build, dictionary reader, and resolver alignment.
