# Slice 8 report

## NARRATIVE

This stage implements S8A of Slice 8: repairing the executable smoke baseline, removing `reference` tool exclusions, implementing the pure deterministic example sentence ranking engine, and establishing the stateless two-stage capture endpoints (`POST /vocab/highlight`, `POST /vocab/cards`) and word-list import (`POST /vocab/import/csv`).

### Architecture & Implementation Details

1. **Repaired Reference Smoke Test (`reference/smoke_test.py`)**:
   - Updated database creation to read `reference/schema.sql` explicitly and execute PART A dictionary tables and PART B user tables under `isolation_level=None`.
   - Exercised exact noun lookup, separable verb lookup with Tatoeba example, compound splitting fallback, needs-gloss fallback, card face rendering, note and deck persistence, FSRS review with rating and confidence logging to append-only `review_log`, and user meaning updates.
   - Script passes full `mypy --strict` and `ruff check` verification with 0 errors.

2. **Tool Exclusions in `pyproject.toml`**:
   - Removed `reference` from `tool.mypy.exclude`, `tool.ruff.exclude`, and `tool.pytest.ini_options.norecursedirs`.

3. **Deterministic Example Ranking (`app/examples.py`)**:
   - Implemented a pure, deterministic example ranking algorithm conforming to ADR-0001 §11 and ADR-0002 §5.
   - Evaluates target length (near 9 tokens), penalizes untranslated examples, proper nouns (`has_proper`), unknown lemmas (with additional penalty for rare unknown lemmas > freq rank 5000), and awards a question sentence bonus.
   - Accurately builds known vocabulary: `known = deck lemmas ∪ known_lemmas` when `known_lemmas` is supplied by value, otherwise `deck lemmas`.
   - Free of I/O, network calls, or mutable module state.

4. **Endpoint Atomicity and Standalone Caller Preservation (`app/deck.py`)**:
   - Introduced explicit `_manage_transaction: bool = True` private option using `_transaction_context(conn, manage)`.
   - Standalone deck mutations (`create_deck`, `create_note`, `add_note_to_deck`, `set_meaning_languages`, `set_user_meaning`, `delete_user_meaning`) retain their existing `with conn:` auto-commit behavior for direct Slice-7 callers.
   - Multi-step endpoint transactions (`POST /vocab/cards`, `POST /vocab/import/csv`, `POST /vocab/notes`) open an outer `BEGIN IMMEDIATE` transaction and pass `_manage_transaction=False` to all helpers, achieving genuine atomicity without nested intermediate commits and guaranteeing clean zero-write rollback on failure.

5. **Capture Endpoints (`app/api.py`)**:
   - `POST /vocab/highlight`: Validates `sentence_text`, bounds-checks `selected_span` (integers, `0 <= start <= end <= len(sentence_text)`), non-blank `lesson_label`. Performs local candidate resolution via spaCy token resolution or surface/lemma dictionary lookup under `runtime.reading()`. Ranks examples with `known_lemmas`. Returns candidates and `capture_context` with ZERO writes to user DB.
   - `POST /vocab/cards`: Revalidates `asset_token` against active `snapshot.asset_token` (returns HTTP 409 `dictionary_changed` on mismatch with zero writes). Validates all selections against `snapshot.lemma_ids` and `snapshot.sense_ids`, strictly enforcing that every sense belongs to its submitted lemma (`snapshot.sense_ids[sense_ref][1] == snapshot.lemma_ids[lemma_ref]`) and every component sense belongs to its component lemma. Rejects duplicate same-identity selections (HTTP 422). Validates overrides (`front_override`, `back_override`, `meaning_langs`, `user_meanings` with Persian `fa` deferred/rejected). Executes atomic transaction (`BEGIN IMMEDIATE` ... `commit` / `rollback`).
   - `POST /vocab/import/csv`: Parses words line-by-line, resolves top candidate or `needs_gloss` stub, assigns to target deck, and executes atomic transaction per request under reading synchronization with rollback on failure.

6. **Test Suites (`tests/`)**:
   - `tests/test_examples.py`: Comprehensive unit tests for example length penalty, untranslated penalty, proper noun penalty, unknown/rare lemma penalties, question bonus, known lemma union, and deterministic ranking.
   - `tests/test_smoke_baseline.py`: Verifies subprocess execution of `reference/smoke_test.py` with exit code 0 and "OK" output.
   - `tests/test_capture.py`: Full ADR-0002 §5 matrix testing highlight validation, stale token 409, unrelated sense 422 rejection, multi-select, note reuse, override handling, atomic rollback, and direct standalone helper persistence.

---

## S8A Evidence

### 1. Verification Commands Output

#### A. Reference Smoke Test
Command: `/home/saber/projects/flashcard/.venv/bin/python reference/smoke_test.py`
Exit code: 0
Output:
```
=== 1. exact hit: noun ===
  ┌─ FRONT ─────────────────────┐
  │ Haus                       │
  │ [haʊ̯s]                    │
  │ das Haus
NOUN • haʊ̯s      │
  └────────────────────────────┘
  ┌─ BACK ──────────────────────┐
  │ [haʊ̯s]                    │
  │ das Haus
NOUN • haʊ̯s

Gra │
  │ • Gebäude zum Wohnen       │
  │ • house; building          │
  └────────────────────────────┘

=== 2. exact hit: separable verb ===
  ┌─ FRONT ─────────────────────┐
  │ anrufen                    │
  │ [ˈanˌʁuːfn̩]               │
  │ anrufen
VERB • ˈanˌʁuːfn̩  │
  └────────────────────────────┘
  ┌─ BACK ──────────────────────┐
  │ [ˈanˌʁuːfn̩]               │
  │ anrufen
VERB • ˈanˌʁuːfn̩
 │
  │ • to call, to phone        │
  │ Ruf mich morgen an!        │
  │ Call me tomorrow!          │
  └────────────────────────────┘

=== 3. compound fallback (no dict entry) ===
  split: ['kranken', 'versicherung', 'karte']
  ┌─ BACK ──────────────────────┐
  │ die Krankenversicherungska │
  │ • kranken: sick, patients  │
  │ • versicherung: insurance  │
  │ • karte: card; map; ticket │
  └────────────────────────────┘

=== 4. unresolved -> needs_gloss, card still created ===
  ┌─ BACK ──────────────────────┐
  │ der Feierabend
NOUN

Gramm │
  └────────────────────────────┘

=== 5. deck write + FSRS ===
  note 1 created
  due after Good: 2026-08-27T01:17:54
  due after Again: 2026-08-27T01:08:54
  reviews logged: 2
  note meanings now: {'en': ('end of the workday',)}

OK
```

#### B. Pytest Test Suites
Command: `/home/saber/projects/flashcard/.venv/bin/pytest -q tests/test_capture.py tests/test_examples.py tests/test_smoke_baseline.py`
Exit code: 0
Output:
```
.................                                                        [100%]
17 passed, 22 warnings in 9.89s
```

#### C. Git Diff Check
Command: `git diff --check`
Exit code: 0 (clean, no trailing whitespace or merge conflict markers)

### 2. Review-1 Blocker Remedies Verification
- **Blocker 1 (Genuinely atomic POST /vocab/cards and CSV import with rollback)**:
  `_manage_transaction=False` passed during endpoint transactions. Verified via `test_cards_atomic_rollback_on_failure` and `test_import_csv_happy_path_and_atomic_rollback` in `tests/test_capture.py` that simulated/invalid input in multi-select or CSV import leaves 0 notes and 0 decks created.
- **Blocker 2 (Revalidate candidate sense belongs to submitted lemma)**:
  `app/api.py` checks `snapshot.sense_ids[sense_ref][1] == snapshot.lemma_ids[lemma_ref]` and verifies each component pair in derived compounds. Verified via `test_cards_unrelated_sense_lemma_rejection` in `tests/test_capture.py`.
- **Blocker 3 (DictionaryRuntime reading/activation synchronization)**:
  Validation of `asset_token`, semantic references, sense ownership, and the database transaction execute inside a single `with runtime.reading():` block preventing generation retirement or mid-flight dictionary swaps. Verified via `test_cards_stale_asset_token_rejection` in `tests/test_capture.py`.
- **Blocker 4 (Stable-ref materialization and example preservation)**:
  `highlight_endpoint` and `cards_endpoint` use stable semantic refs (`lemma_semantic_ref`, `sense_semantic_ref`) and pure deterministic example ranking preserving primary examples.

---

## S8B-1a Evidence

### 1. Scope & Toolchain Configuration
- **Package Manifest & Toolchain (`frontend/package.json`, `frontend/package-lock.json`)**:
  - Locked Lit (`lit`), TypeScript (`typescript`, `@types/node`), Vite (`vite`), and Playwright (`@playwright/test`).
  - Scripts: `dev` (`vite`), `build` (`tsc && vite build`), `preview` (`vite preview`), `typecheck` (`tsc --noEmit`), `test:e2e` (`playwright test`).
- **Strict TypeScript Settings (`frontend/tsconfig.json`)**:
  - `target: ES2022`, `useDefineForClassFields: false`, `module: ESNext`, `moduleResolution: bundler`, `experimentalDecorators: true`.
  - Strict type checking enabled (`strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`, `noFallthroughCasesInSwitch: true`, `noUncheckedIndexedAccess: true`, `skipLibCheck: true`).
- **Vite Clean Output & Proxy (`frontend/vite.config.ts`)**:
  - Build output configured to `../app/frontend` with `emptyOutDir: true`.
  - Development server `/vocab` proxy target configured to `http://127.0.0.1:8000`.
- **Playwright Test Configuration (`frontend/playwright.config.ts`)**:
  - Test directory configured to `./tests/e2e`.
  - Base URL defaulting to `http://127.0.0.1:8000`.
- **Generated Output and Dependency Ignores (`.gitignore`)**:
  - Added rules for `node_modules/`, `app/frontend/`, `frontend/test-results/`, `frontend/playwright-report/`, `frontend/.playwright/`.
- **Sub-slice Invariants Enforced**:
  - No root app, CSS tokens, typed `/vocab` client, workflows, tests, or generated output created in this sub-slice.
  - No backend, runtime LLM, fa/Persian, lecture, React-family framework, ts-fsrs, IndexedDB, scheduler/FSRS, donor/schema/ADR, or unrelated paths modified.

### 2. Verification Commands Output

#### A. Frontend Typecheck
Command: `npm run --prefix frontend typecheck`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 typecheck
> tsc --noEmit
```

#### B. Git Diff Check
Command: `git diff --check`
Exit code: 0 (clean, no trailing whitespace or merge conflict markers)

#### C. Python Reference Smoke Test
Command: `/home/saber/projects/flashcard/.venv/bin/python reference/smoke_test.py`
Exit code: 0 (OK)

#### D. Pytest Test Suites
Command: `/home/saber/projects/flashcard/.venv/bin/pytest -q tests/test_capture.py tests/test_examples.py tests/test_smoke_baseline.py`
Exit code: 0 (17 passed)
