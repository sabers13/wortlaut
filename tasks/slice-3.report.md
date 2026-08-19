# Slice 3 report

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
