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

---

## S8B-1b Evidence

### 1. Root Shell, Design Tokens & Build Proof
- **CSS Design Tokens (`frontend/src/styles/tokens.css`)**:
  - Color system: base background, surfaces, borders, text hierarchy (primary, secondary, muted, inverse), brand/primary accents, and status feedback (success, warning, danger).
  - Typography: system font stack, monospace font stack, modular scale font sizes (`xs` to `3xl`), font weights, and line heights.
  - Geometry & Motion: spacing scale (`0.5` to `12`), border radii (`sm` to `full`), elevation shadows (`sm`, `md`, `lg`), and transition curves.
  - Global CSS reset and baseline body setup.
- **Minimal Lit Root Component (`frontend/src/app.ts`)**:
  - Registered custom element `<flashcard-app>` extending `LitElement`.
  - Scoped component styles referencing CSS custom properties with fallbacks.
  - Ephemeral component state (`@state() private appTitle`), with zero local persistence, scheduler, or IndexedDB storage.
  - Global type augmentation in `HTMLElementTagNameMap`.
- **Application Entrypoint & HTML (`frontend/src/main.ts`, `frontend/index.html`)**:
  - Entrypoint importing CSS tokens and root component.
  - `index.html` referencing entrypoint module `<script type="module" src="/src/main.ts"></script>`.
- **Sub-slice Boundaries Maintained**:
  - No typed `/vocab` client, product workflows, scheduler/FSRS, IndexedDB, generated files, or tests beyond toolchain added.
  - No React-family framework, ts-fsrs, runtime LLM, fa/Persian, lecture, donor/schema/ADR, backend, or .gitignore touched.

### 2. Verification Commands Output

#### A. Frontend Typecheck
Command: `npm run --prefix frontend typecheck`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 typecheck
> tsc --noEmit
```

#### B. Frontend Build & Output Proof
Command: `npm run --prefix frontend build`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 build
> tsc && vite build

vite v6.4.3 building for production...
transforming (1) src/main.ts✓ 22 modules transformed.
rendering chunks (1)...computing gzip size (0)...computing gzip size (1)...computing gzip size (2)...computing gzip size (3)...../app/frontend/index.html                  0.41 kB │ gzip: 0.27 kB
../app/frontend/assets/index-B7pGa7di.css   2.00 kB │ gzip: 0.83 kB
../app/frontend/assets/index-DGAbqAPX.js   20.74 kB │ gzip: 7.64 kB
✓ built in 261ms
```

#### C. Git Diff Check
Command: `git diff --check`
Exit code: 0 (clean, no trailing whitespace or merge conflict markers)

---

## S8B-2 Evidence

### 1. Typed `/vocab` Client Implementation Details
- **Type Definitions (`frontend/src/api/types.ts`)**:
  - Full TypeScript types for all `/vocab` endpoints matching `app/api.py`: `LookupResponse`, `HighlightRequest`, `HighlightResponse`, `CaptureCardsRequest`, `CaptureCardsResponse`, `ImportCsvRequest`, `ImportCsvResponse`, `CreateNoteRequest`, `CreateNoteResponse`, `NextCardResponse`, `ReviewCardRequest`, `ReviewCardResponse`, `SetGlossRequest`, `SetGlossResponse`, `DeleteGlossResponse`, `UploadAudioResponse`, `RevertAudioResponse`, `ActivateDictionaryRequest`, `ActivateDictionaryResponse`, `DeckSummary`, `CreateDeckRequest`, `CreateDeckResponse`, `DeleteDeckResponse`.
  - Strictly typed language unions (`'de' | 'en'`), note statuses (`'resolved' | 'derived_compound' | 'needs_gloss' | 'orphaned'`), and audio/grammar structures.
- **Typed Error Handling (`frontend/src/api/errors.ts`)**:
  - Custom `ApiError` class exposing HTTP `status`, `statusText`, `detail`, `body`, and ADR-0004 D47 token mismatches (`pickerToken`, `activeToken`).
  - Helper predicates: `isConflict` (409), `isNotFound` (404), `isUnprocessable` (422), `isForbidden` (403), `isBadRequest` (400).
  - Robust `parseApiError` response parser extracting FastAPI validation detail strings/arrays and dictionary asset tokens.
- **Stateless Fetch Client (`frontend/src/api/client.ts`)**:
  - `VocabClient` with configurable `baseUrl` and optional custom `fetch` injection.
  - Automatically enforces AGENTS R12 / ADR-0002 §4.1: every non-GET request sends `X-Flashcards-Request: 1`; JSON requests send `Content-Type: application/json`.
  - Uses only the `/vocab` prefix across all methods.
  - Ephemeral and stateless: zero scheduler, FSRS/rating mapping, due state, authoritative card cache, IndexedDB, or persistence.
- **Client Unit Test Suite (`frontend/src/api/client.test.ts`)**:
  - 24 unit tests covering header enforcement (`X-Flashcards-Request: 1` on non-GET, omitted on GET, `Content-Type: application/json`), all 19 API methods, query string encoding, audio binary transfer, and typed error parsing (400, 403, 404, 409 with picker/active tokens, 422, 500).
- **Sub-slice Boundaries Maintained**:
  - No alteration of backend/API, `.gitignore`, report history, generated `app/frontend/`, or unrelated paths.
  - No runtime LLM, fa/Persian, lecture, React-family framework, ts-fsrs, or donor/schema/ADR changes.

### 2. Verification Commands Output

#### A. Frontend Typecheck
Command: `npm run --prefix frontend typecheck`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 typecheck
> tsc --noEmit
```

#### B. Frontend Unit Tests
Command: `npm test --prefix frontend`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 test
> node --experimental-strip-types --test src/api/client.test.ts

▶ VocabClient
  ✔ instantiates cleanly via factory and constructor with default or custom options (1.892846ms)
  ▶ Security guards & headers (AGENTS R12 / ADR-0002)
    ✔ does NOT send X-Flashcards-Request on GET requests (47.664122ms)
    ✔ sends X-Flashcards-Request: 1 and Content-Type: application/json on non-GET JSON requests (2.42331ms)
    ✔ sends X-Flashcards-Request: 1 on DELETE requests (0.89447ms)
  ✔ Security guards & headers (AGENTS R12 / ADR-0002) (51.565491ms)
  ▶ Lookup & Dictionary endpoints
    ✔ executes GET /vocab/lookup with query param encoding (1.367106ms)
    ✔ executes POST /vocab/lookup with query body (1.014983ms)
    ✔ executes POST /vocab/dictionary/activate (0.944875ms)
  ✔ Lookup & Dictionary endpoints (3.847131ms)
  ▶ Capture workflows
    ✔ executes POST /vocab/highlight (Stage 1 candidate resolution) (0.931715ms)
    ✔ executes POST /vocab/cards (Stage 2 atomic card creation) (0.801301ms)
    ✔ executes POST /vocab/import/csv for batch imports (0.931112ms)
    ✔ executes POST /vocab/notes for single note creation (1.031495ms)
  ✔ Capture workflows (4.106656ms)
  ▶ Review & Study endpoints
    ✔ executes GET /vocab/cards/next with optional deck_id (0.881428ms)
    ✔ executes POST /vocab/cards/{card_id}/review with raw confidence (0.555349ms)
  ✔ Review & Study endpoints (1.618668ms)
  ▶ Gloss & User meaning endpoints
    ✔ executes POST /vocab/notes/{note_id}/gloss (0.80062ms)
    ✔ executes DELETE /vocab/notes/{note_id}/gloss?language=... (0.631714ms)
  ✔ Gloss & User meaning endpoints (1.635223ms)
  ▶ Audio endpoints
    ✔ generates audio URL via getAudioUrl (0.314658ms)
    ✔ fetches audio binary blob via fetchAudio (22.321639ms)
    ✔ uploads custom pronunciation audio via uploadAudio (0.824767ms)
    ✔ reverts custom pronunciation audio via revertAudio (0.527297ms)
  ✔ Audio endpoints (24.371468ms)
  ▶ Export Anki endpoint
    ✔ executes GET /vocab/export/anki with text response (0.615273ms)
  ✔ Export Anki endpoint (0.743076ms)
  ▶ Error handling & typed ApiError
    ✔ throws ApiError on 404 with parsed detail (1.525004ms)
    ✔ throws ApiError on 409 Conflict with picker_token and active_token (0.787188ms)
    ✔ throws ApiError on 422 Unprocessable Entity with error list or string detail (0.680291ms)
    ✔ throws ApiError on non-JSON error response (0.633775ms)
  ✔ Error handling & typed ApiError (3.958839ms)
✔ VocabClient (96.235782ms)
ℹ tests 24
ℹ suites 9
ℹ pass 24
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 301.726492
```

#### C. Git Diff Check
Command: `git diff --check`
Exit code: 0 (clean, no trailing whitespace or merge conflict markers)

#### D. Python Reference Smoke Test
Command: `/home/saber/projects/flashcard/.venv/bin/python reference/smoke_test.py`
Exit code: 0 (OK)

#### E. Pytest Test Suites
Command: `/home/saber/projects/flashcard/.venv/bin/pytest -q tests/test_capture.py tests/test_examples.py tests/test_smoke_baseline.py`
Exit code: 0 (17 passed)

---

## S8B Final Verification Evidence

### 1. Cumulative Frontend Foundation & Verification
- **Strict TypeScript & Toolchain Configuration**:
  - `frontend/tsconfig.json` enforces strict TypeScript compilation (`strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`, `noFallthroughCasesInSwitch: true`, `noUncheckedIndexedAccess: true`, `skipLibCheck: true`, `target: ES2022`, `module: ESNext`, `moduleResolution: bundler`).
  - Vite (`frontend/vite.config.ts`) targets `../app/frontend` with `emptyOutDir: true` and proxies `/vocab` to `http://127.0.0.1:8000`.
  - Playwright (`frontend/playwright.config.ts`) configured with `baseURL: http://127.0.0.1:8000`, parallel execution, and test directory `./tests/e2e`.
- **Lit Root Custom Element & Design Tokens**:
  - Registered `<flashcard-app>` Lit custom element (`frontend/src/app.ts`) and CSS custom property token hierarchy (`frontend/src/styles/tokens.css`).
  - Strict ephemeral state (`@state() private appTitle`); zero local storage, IndexedDB, or client-side caching.
- **Typed `/vocab` Client (AGENTS R12, ADR-0002 §4.1 / §5, ADR-0004 D47)**:
  - `VocabClient` strictly prefixes all endpoints with `/vocab`.
  - Enforces `X-Flashcards-Request: 1` on all non-GET requests and `Content-Type: application/json` on JSON requests.
  - Complete TypeScript interface coverage (`HighlightRequest`/`HighlightResponse`, `CaptureCardsRequest`/`CaptureCardsResponse`, `ImportCsvRequest`/`ImportCsvResponse`, `LookupResponse`, `NextCardResponse`, `ReviewCardResponse`, `SetGlossResponse`, `UploadAudioResponse`, `ActivateDictionaryResponse`, etc.).
  - Typed `ApiError` with 400/403/404/409/422 status helpers and ADR-0004 D47 `pickerToken`/`activeToken` extraction.
- **Prohibitions & Architecture Invariants Verified**:
  - Zero client-side scheduler or FSRS rating algorithm (FSRS is strictly backend-managed; review endpoint accepts only raw confidence 1..5).
  - Zero client-side database / IndexedDB / persistence.
  - Zero React / non-Lit UI frameworks or external UI dependencies.
  - Zero runtime LLM dependencies or imports (AGENTS R1).
  - No Persian (`fa`) language option in client type unions.
  - Clean repository boundary (`.gitignore` covers `node_modules/`, `app/frontend/`, `frontend/test-results/`, `frontend/playwright-report/`, `frontend/.playwright/`).

### 2. Process & Transport Argv Safety Record
- **Implementation Packages**: 3 primary implementation packages (S8B-1a toolchain/metadata, S8B-1b Lit shell/CSS tokens, S8B-2 typed `/vocab` client) plus 1 bounded repair package.
- **Task Prompt Compactness**: Post-policy task prompts were compact and well below 28,672 UTF-8 bytes.
- **Transport Warnings**: One earlier generated model prompt was reported at 63,534 bytes as a transport warning; no routing substitution was made because of prompt size.

### 3. Verification Commands Output

#### A. Frontend Dependencies Installation (`npm ci`)
Command: `npm ci --prefix frontend`
Exit code: 0
Output:
```
added 26 packages, and audited 27 packages in 2s
found 0 vulnerabilities
```

#### B. Frontend Typecheck (`tsc --noEmit`)
Command: `npm run --prefix frontend typecheck`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 typecheck
> tsc --noEmit
```

#### C. Frontend Build (`tsc && vite build`)
Command: `npm run --prefix frontend build`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 build
> tsc && vite build

vite v6.4.3 building for production...
transforming (1) src/main.tstransforming (21) node_modules/@lit/reactive-element/css-tag.js✓ 22 modules transformed.
rendering chunks (1)...computing gzip size (0)...computing gzip size (1)...computing gzip size (2)...computing gzip size (3)...../app/frontend/index.html                  0.41 kB │ gzip: 0.27 kB
../app/frontend/assets/index-B7pGa7di.css   2.00 kB │ gzip: 0.83 kB
../app/frontend/assets/index-DGAbqAPX.js   20.74 kB │ gzip: 7.64 kB
✓ built in 353ms
```

#### D. Frontend Unit Tests (`node --test`)
Command: `npm test --prefix frontend`
Exit code: 0
Output:
```
> flashcard-frontend@0.1.0 test
> node --experimental-strip-types --test src/api/client.test.ts

▶ VocabClient
  ✔ instantiates cleanly via factory and constructor with default or custom options (1.538413ms)
  ▶ Security guards & headers (AGENTS R12 / ADR-0002)
    ✔ does NOT send X-Flashcards-Request on GET requests (50.962137ms)
    ✔ sends X-Flashcards-Request: 1 and Content-Type: application/json on non-GET JSON requests (1.693005ms)
    ✔ sends X-Flashcards-Request: 1 on DELETE requests (0.925557ms)
  ✔ Security guards & headers (AGENTS R12 / ADR-0002) (54.127086ms)
  ▶ Lookup & Dictionary endpoints
    ✔ executes GET /vocab/lookup with query param encoding (1.302859ms)
    ✔ executes POST /vocab/lookup with query body (0.897471ms)
    ✔ executes POST /vocab/dictionary/activate (0.933598ms)
  ✔ Lookup & Dictionary endpoints (4.440569ms)
  ▶ Capture workflows
    ✔ executes POST /vocab/highlight (Stage 1 candidate resolution) (0.883784ms)
    ✔ executes POST /vocab/cards (Stage 2 atomic card creation) (0.913139ms)
    ✔ executes POST /vocab/import/csv for batch imports (0.977642ms)
    ✔ executes POST /vocab/notes for single note creation (1.205229ms)
  ✔ Capture workflows (4.492449ms)
  ▶ Review & Study endpoints
    ✔ executes GET /vocab/cards/next with optional deck_id (1.047584ms)
    ✔ executes POST /vocab/cards/{card_id}/review with raw confidence (0.742661ms)
  ✔ Review & Study endpoints (2.041473ms)
  ▶ Gloss & User meaning endpoints
    ✔ executes POST /vocab/notes/{note_id}/gloss (0.68676ms)
    ✔ executes DELETE /vocab/notes/{note_id}/gloss?language=... (0.586578ms)
  ✔ Gloss & User meaning endpoints (1.529881ms)
  ▶ Audio endpoints
    ✔ generates audio URL via getAudioUrl (0.352913ms)
    ✔ fetches audio binary blob via fetchAudio (31.868527ms)
    ✔ uploads custom pronunciation audio via uploadAudio (0.811291ms)
    ✔ reverts custom pronunciation audio via revertAudio (0.687178ms)
  ✔ Audio endpoints (34.456301ms)
  ▶ Export Anki endpoint
    ✔ executes GET /vocab/export/anki with text response (1.083704ms)
  ✔ Export Anki endpoint (1.192768ms)
  ▶ Error handling & typed ApiError
    ✔ throws ApiError on 404 with parsed detail (1.258709ms)
    ✔ throws ApiError on 409 Conflict with picker_token and active_token (0.62623ms)
    ✔ throws ApiError on 422 Unprocessable Entity with error list or string detail (0.594867ms)
    ✔ throws ApiError on non-JSON error response (0.488437ms)
  ✔ Error handling & typed ApiError (3.218912ms)
✔ VocabClient (109.361236ms)
ℹ tests 24
ℹ suites 9
ℹ pass 24
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 317.990242
```

#### E. Python Reference Smoke Test
Command: `/home/saber/projects/flashcard/.venv/bin/python reference/smoke_test.py`
Exit code: 0
Output: OK (5/5 sections passed)

#### F. Python Ruff Linter
Command: `/home/saber/projects/flashcard/.venv/bin/ruff check .`
Exit code: 0
Output: `All checks passed!`

#### G. Python Mypy Strict Typecheck
Command: `/home/saber/projects/flashcard/.venv/bin/mypy --strict .`
Exit code: 0
Output: `Success: no issues found in 31 source files`

#### H. AGENTS Rule Validator
Command: `/home/saber/projects/flashcard/.venv/bin/python tools/check_agents.py`
Exit code: 0
Output: `AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R6 (review log append-only), R7 (lecture coupling), R12 (browser origin/host guards), R13 (durable semantic identity)`

#### I. Pytest Full Test Suite
Command: `/home/saber/projects/flashcard/.venv/bin/pytest -q`
Exit code: 0
Output: `684 passed, 82 warnings in 257.32s`

#### J. Git Diff Check
Command: `git diff --check`
Exit code: 0 (clean, no trailing whitespace or merge conflict markers)

## S8C-1a Evidence — navigation and deck shell

Implemented the frontend-only deck navigation shell with the existing typed `/vocab` client: server-authoritative list, create, open, refresh, and explicit delete confirmation. Loading, empty, error/retry, and success states remain distinct; no browser persistence or scheduling was added.

### Repair evidence

The refresh outcome is now explicit: a failed `GET /vocab/decks` returns failure to create/delete flows, clears any success notice, and produces an error rather than a false success. Creation opens a deck only after the refreshed server list contains its returned ID; deletion likewise requires a refreshed list that no longer contains the deleted ID. The historical S8B full-gate output above is not evidence for this repair.

Verification for this repair: `npm run typecheck`, `npm test`, and `npm run build` passed in `frontend/`. `make gate` reached mypy after ruff passed, then stopped on the pre-existing unavailable `fsrs`/`spacy` imports (7 missing-import errors in six non-frontend files), so it did not reach pytest. `git diff --check` passed.
