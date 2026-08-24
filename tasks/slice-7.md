# Slice 7 — Core runtime application: deck, review scheduling, multilingual rendering, security guards, and pronunciation

Task:        Implement the standalone runtime application required by ADR-0001,
             ADR-0002 §6 order 8, ADR-0003, ADR-0004 (D43, D46, D47), ADR-0005
             (D48–D56), accepted ADR-0007 (D72–D81), and AGENTS R4, R5, R6, R9,
             R10, R12, R13: complete `reference/schema.sql` PART-B user database
             DDL; FSRS review scheduling and append-only raw confidence logging;
             note-local DE/EN selected meaning sets, user-authored meanings, and
             D43 availability; display-time card rendering and tri-state noun plural;
             D47 atomic dictionary activation, relink, and stale-picker HTTP 409
             rejection; note-local custom audio persistence, crash-safe replacement,
             approved human discovery, and on-demand Piper synthesis; app factory
             `create_app` and browser-facing loopback origin/host security guards;
             and executable AGENTS checks for R6, R12, and R13.

Depends:     slice-6

## Entry condition

slice-6 must be ACCEPTED, merged, closed, and pushed before implementation
dispatch.

**Full paid Stage-04 LLM production generation is NOT an entry condition.**

The runtime application operates on the accepted source-backed dictionary baseline
(e.g. Stage-02 output or Stage-05 packaged dictionary from source-backed data)
and handles partial/absent German learner-meaning coverage under ADR-0004 D43
(`meaning_state = none | partial | complete`). Missing German learner meanings
are represented according to D43, never generated at runtime.

Persian (`fa`) remains deferred from active v1 scope under accepted/frozen
ADR-0007.

Runtime LLM usage remains strictly forbidden (AGENTS R1).

## Authority

The binding architecture is:

- `docs/plan.md` slice-7 row and governance amendments;
- ADR-0001 §§5, 6, 7, 10, 11 and D8, D12, D14, D18;
- ADR-0002 §6 order 8 and D24, D25, D26;
- ADR-0003 §3, §4, §5 and D27 (confidence UI / FSRS mapping), review_log schema;
- ADR-0004 D36, D43, D46, D47 and §§6, 7, 8, 10;
- ADR-0005 D48–D56 (pronunciation audio precedence, note-local custom media,
  sacred user data, crash-safe replacement, human discovery, on-demand Piper);
- ADR-0007 D72–D81 (accepted/frozen: active meaning languages strictly `{de, en}`,
  Persian deferred, HTTP 422 on `fa` with zero writes, RTL removed);
- AGENTS C1 (app factory), C2 (dependency direction), C3 (German-only target);
- AGENTS R1 (no runtime LLM), R4 (rendered faces never stored), R5 (no cascade delete
  of notes with history), R6 (review_log append-only + raw confidence), R7 (zero
  lecture-app coupling), R8 (127.0.0.1 bind only), R9 (separate dictionary/user DBs),
  R10 (sanitized TSV Anki export), R12 (origin/host guards), R13 (numeric IDs never
  durable semantic identity).

## Allowlist

Implementation may modify/create only:

- `reference/schema.sql`
- `app/__init__.py`
- `app/api.py`
- `app/deck.py`
- `app/render.py`
- `app/dictionary.py`
- `app/examples.py`
- `app/audio.py`
- `tools/check_agents.py`
- `tests/conftest.py`
- `tests/test_api.py`
- `tests/test_deck.py`
- `tests/test_render.py`
- `tests/test_audio.py`
- `tests/test_dictionary.py`
- `tests/test_check_agents.py`
- `pyproject.toml`
- `tasks/slice-7.report.md`

No other tracked path is allowed.

In particular do NOT modify:

- `app/resolve.py` (canonical resolver is frozen and hash-keyed)
- `tools/build_dict.py`
- `tools/resolver_hash.py`
- `tools/gate2_coverage.py`
- `reference/smoke_test.py` (owned by slice-8)
- `Dockerfile`
- `.dockerignore`
- ADRs
- `AGENTS.md`
- `WORKFLOW.md`
- `PROMPTS.md`
- `STATE.md`
- `docs/plan.md`
- `docs/backlog.md`

## Acceptance

### A1 — PART-B user database schema and data separation

Complete `reference/schema.sql` PART-B user tables:

1. `deck`: `id`, `name`, `created_at`;
2. `note`: `id`, `lemma_semantic_ref`, `sense_semantic_ref` (nullable), `status`
   (`resolved`, `needs_gloss`, `derived_compound`, `orphaned`), `created_at`, `due_at`,
   `interval_days`, `ease_factor`, `review_count`, `last_confidence`;
3. `card`: front/back rendered at runtime, never stored (AGENTS R4);
4. `note_deck`: `note_id`, `deck_id`, `created_at`;
5. `review_log`: append-only review history (AGENTS R6) with `NOT NULL` and `CHECK`
   constraints: `confidence` integer 1..5, `rating` integer 1..4, `scheduled_days`,
   `elapsed_days`, `reviewed_at`;
6. `note_meaning_lang`: `note_id`, `lang` (`de` or `en`), with composite primary key
   and at least one language required per note;
7. `note_user_meaning`: `note_id`, `lang` (`de` or `en`), `meaning_text`,
   `created_at`, `updated_at`, superseding scalar `note.gloss_user`;
8. `note_dictionary_binding`: `note_id`, `lemma_semantic_ref`, `sense_semantic_ref`,
   `cached_lemma_id` (nullable), `cached_sense_id` (nullable), `binding_status`
   (`bound`, `unbound`, `ambiguous`), `last_relinked_at`; derived-compound notes
   additionally persist an expected ordered `component_count` (captured at note
   creation from the resolver's decomposition and revalidated at D47 relink)
   so the D46 all-components-or-none rule is checkable against an independent
   declared length, never against the surviving rows themselves;
9. `active_dictionary_metadata`: singleton table tracking `active_version`,
   `active_filename`, `active_sha256`, `activated_at`;
10. `custom_pronunciation`: `note_id` (primary key), `media_filename`, `sha256`,
    `byte_size`, `format`, `source_type` (`recorded`, `uploaded`), `created_at`.

Rules:
- Foreign keys enabled;
- Deck deletion removes `note_deck` rows; orphaned notes move to an "Orphaned"
  deck and are NEVER cascade-deleted if they have review history (AGENTS R5);
- Dictionary and user database never share a database file or SQLite connection
  (AGENTS R9);
- Numeric dictionary IDs (`lemma_id`, `sense_id`) are active-asset caches only,
  never durable semantic identity (AGENTS R13, ADR-0004 D47).

### A2 — FSRS review loop and append-only confidence logging

Implement FSRS scheduling in `app/deck.py`:

1. Card review accepts raw 1–5 learner confidence (ADR-0003 D27);
2. Maps raw confidence 1–5 to FSRS 4-grade rating through the single ADR-0003
   D28 function `{1: Again, 2: Again, 3: Hard, 4: Good, 5: Easy}`:
   - 1 -> Again (rating 1)
   - 2 -> Again (rating 1; identical scheduling to 1 on new cards)
   - 3 -> Hard (rating 2)
   - 4 -> Good (rating 3)
   - 5 -> Easy (rating 4; graduates new cards to Review per FSRS)
3. Computes updated interval, due date, ease factor, and stability;
4. Appends a new row to `review_log` recording BOTH raw confidence (1–5) and
   mapped FSRS rating (1–4) (AGENTS R6);
5. Application code contains ZERO `UPDATE review_log` or `DELETE FROM review_log`
   queries (AGENTS R6);
6. Pins `fsrs==6.3.2` in `pyproject.toml` runtime dependencies with learning
   steps `(1 min, 10 min)` (ADR-0003 §6); a five-case scheduler test asserts
   the mapped grades, the 1/2 equality on new cards, the 3/4 learning-step
   intervals, and confidence 5 graduation to Review.

### A3 — Multilingual meaning set, user meanings, and D43 availability

In `app/deck.py` and `app/render.py`:

1. Per-note selected meaning languages: non-empty subset of `{de, en}` (`{de}`,
   `{en}`, `{de, en}`);
2. User-authored meanings (`note_user_meaning`) take precedence over dictionary
   meanings for each selected language;
3. Language-bearing user-meaning endpoints:
   - `POST /vocab/notes/{id}/gloss`: sets/updates note-local user meaning for `de` or `en`;
   - `DELETE /vocab/notes/{id}/gloss`: removes note-local user meaning;
4. Meaning availability state computed per ADR-0004 D43:
   - `complete`: all selected languages have at least one meaning text (user or dictionary);
   - `partial`: at least one selected language has meaning text, but not all;
   - `none`: none of the selected languages have meaning text;
5. Persian `fa` is rejected with HTTP 422 Unprocessable Entity and zero database writes (ADR-0007).

### A4 — Display-time card rendering and tri-state noun plural

In `app/render.py`:

1. Render front and back faces dynamically at display time (AGENTS R4);
2. Front face contains:
   - Headword, article/gender (for nouns), POS, IPA (if present), pronunciation audio trigger;
3. Back face contains:
   - Front content;
   - Rendered learner meanings grouped by selected language;
   - User-authored meanings marked / rendered with precedence;
   - Tri-state noun plural rendering (ADR-0004 §10):
     - `lemma.plural` present -> rendered plural form;
     - `lemma.plural_none = 1` -> explicit "kein Plural" / singular-only indicator;
     - both null / non-noun -> plural line omitted;
   - Grammatical metadata (separable prefix, auxiliary, inflection/governs);
   - Tatoeba example sentences (German text + English translation if available);
   - Render handles `examples=[]` cleanly without error;
4. Derived compound rendering per ADR-0004 D46: renders all components or none.

### A5 — Durable semantic bindings, atomic dictionary activation/relink, and stale picker

In `app/dictionary.py`, `app/deck.py`, `app/api.py`:

1. Stale picker prevention:
   - Dictionary lookup returns current active dictionary asset token (SHA-256);
   - Note creation/capture validates the submitted asset token;
   - Mismatched / stale asset token is rejected with HTTP 409 Conflict;
2. Atomic dictionary activation and relink:
   - `activate_dictionary(new_dict_path)` validates the new asset against PART-A schema;
   - Validates all PART-B `lemma_semantic_ref` and `sense_semantic_ref` values against
     the new dictionary;
   - Validates each derived_compound note's component vector against its persisted
     expected `component_count` BEFORE any binding-status filtering: any missing,
     unbound, or ambiguous component, or an undeterminable count, fails closed
     with no dictionary meaning block (ADR-0004 D46 all-components-or-none);
   - Activation mechanics are structural, not advisory: all dictionary reads and
     activation run through ONE runtime instance (created later by the app
     factory) whose lock serializes reads against activation —
     `activate_dictionary` is a method on that runtime and NO runtime-less
     activation path exists; the candidate asset is opened ONCE and its SHA-256,
     integrity_check, PART-A schema validation, stable-ref verification, and the
     handle installed by the swap all bind to that same opened content (no
     validate-close-reopen gap); stable semantic refs are verified against their
     exact persisted source fields with NO normalization or whitespace
     stripping — mismatch, unverifiable ref, or cross-version ref reuse aborts
     activation; `asset_token` is a required argument on note creation with no
     sentinel default, and creation fails closed when no active dictionary
     exists;
   - Incumbency is tracked by LEASE IDENTITY, never by asset equality or SHA:
     the frozen asset is non-aliasable (its lease/connection is not a
     replaceable public dataclass field), activation releases only assets the
     runtime itself produced, and no caller-reachable construction (including
     dataclass replace/copy paths) can cause the incumbent's connection to be
     closed; rollback restoration covers EVERY PART-B column activation mutates
     (cached ids, binding_status, last_relinked_at, note.status) and the
     visibility invariant is evidenced by reads that genuinely OVERLAP an
     activation, each observation being complete-old or complete-new;
   - Activation is capability-gated and reads are generation-pinned: only
     assets produced by the validator carry an opaque provenance capability
     (registry-checked, not reproducible by copying or replace), so forged or
     stolen-lease wrappers cannot be activated; open read observations are
     pinned to one live generation (refcounted leases) and always complete
     successfully even if activation swaps the runtime's current generation
     while they are open; concurrency evidence uses an injected synchronization
     point between the PART-B commit and runtime publication with readers
     sampling across it, and the rollback fixture exercises a non-no-op
     binding_status transition;
   - Atomically updates `active_dictionary_metadata` and relinks `cached_lemma_id` and
     `cached_sense_id` in `note_dictionary_binding`;
   - Exact matching stable refs are relinked (`binding_status='bound'`);
   - Missing or disappeared stable refs fail closed safely (`binding_status='unbound'`);
   - User notes, custom user meanings, and review history survive intact (AGENTS R9, R13);
   - Duplicate or ambiguous stable refs in the new dictionary fail closed;
   - Atomic rollback to the prior dictionary version is supported.

### A6 — Runtime pronunciation audio precedence, custom media, and on-demand Piper

In `app/audio.py`, `app/render.py`, `app/api.py`:

1. Audio-source precedence (ADR-0005 D48):
   - 1. Note-local saved custom audio;
   - 2. Validated human pronunciation recording from approved Commons metadata;
   - 3. Automatic local Piper TTS generation / cache;
   - 4. Optional remote `/speak` (ADR-0002 D26, <= 1s timeout, silent fallback to Piper);
   - 5. Silent fallback (card display and review remain functional without audio);
2. Note-local custom audio persistence:
   - Supports audio upload (`POST /vocab/notes/{id}/audio`) from browser recording or file;
   - Validates untrusted media: supported container/codec (WAV, MP3, OGG, WebM/Opus),
     bounded file size (<= 2MB), bounded duration (<= 15s), actual media content verification;
   - Custom audio is sacred user data: stored in user media directory, separate from disposable cache (ADR-0005 D50);
   - Crash-safe replacement: candidate validated and written under non-active identity -> atomic activation commit -> old object reclaimed;
   - Revert to automatic (`DELETE /vocab/notes/{id}/audio`): removes custom override without deleting automatic capabilities;
   - Note-local ownership: custom audio is note-specific and not silently shared;
   - Survives dictionary replacement when stable semantic refs match; fails closed (unbound, not deleted) if target disappears;
3. Disposable automatic audio cache:
   - Human recordings and Piper synthesis cached in disposable cache directory;
   - On-demand Piper generation uses pinned engine and voice (`de_DE-thorsten-high`);
   - Approved Commons discovery policy: exact-id metadata only (no generic live free-text search);
   - Corrupt or missing automatic cache entries fall back cleanly to Piper.

### A7 — App factory, HTTP routes, and browser loopback security guards

In `app/api.py`, `app/__init__.py`:

1. App factory `create_app(dict_path, user_db_path, cors_origins, *, tts_remote_url=None, media_dir=None, cache_dir=None)`:
   - Zero module-level state; no env reads at import time (AGENTS C1);
   - Strict one-way dependency direction: `api -> deck -> render -> dictionary -> resolve` (AGENTS C2);
2. AGENTS R12 Origin/Host security guards:
   - `cors_origins` is an exact-origin allowlist; wildcard `*` is strictly forbidden and raises an error at app creation;
   - Every request validates `Host` is loopback (`127.0.0.1`, `localhost`, `[::1]`, with configured port);
   - Any present `Origin` header must exactly match `cors_origins`;
   - Every non-GET browser-callable route requires `X-Flashcards-Request: 1`; missing/invalid header returns HTTP 403 Forbidden or HTTP 400 before any action;
   - JSON routes require `Content-Type: application/json`;
3. API endpoints under `/vocab` prefix:
   - `GET /vocab/lookup?q=...`: resolution ladder + dictionary entry + active asset token;
   - `POST /vocab/notes`: capture new note with selected meaning languages, context sentence, source lecture label, asset token;
   - `GET /vocab/cards/next`: next due card;
   - `POST /vocab/cards/{id}/review`: submit 1–5 confidence rating;
   - `POST /vocab/notes/{id}/gloss`: set/update note-local user meaning for `de` or `en`;
   - `DELETE /vocab/notes/{id}/gloss`: remove user meaning;
   - `POST /vocab/notes/{id}/audio`: upload custom pronunciation audio;
   - `DELETE /vocab/notes/{id}/audio`: revert custom audio to automatic;
   - `GET /vocab/audio/{audio_id}`: stream pronunciation audio;
   - `POST /vocab/dictionary/activate`: atomic dictionary activation/relink;
   - `GET /vocab/decks`, `POST /vocab/decks`, `DELETE /vocab/decks/{id}`;
   - `GET /vocab/export/anki`: sanitized tab-separated Anki export (AGENTS R10);
4. Reject Persian `fa` with HTTP 422 with zero writes (ADR-0007);
5. No LLM SDK or runtime provider dependency (AGENTS R1).

### A8 — Executable AGENTS checks for R6, R12, and R13

Extend `tools/check_agents.py` and `tests/test_check_agents.py`:

1. **R6 check:** verifies `reference/schema.sql` enforces `confidence` 1..5 and `rating`
   1..4 with `NOT NULL` + `CHECK`; scans `app/` and verifies zero `UPDATE review_log`
   or `DELETE FROM review_log` SQL statements;
2. **R12 check:** verifies wildcard `*` in CORS origins is rejected; verifies host/origin
   middleware presence; verifies `X-Flashcards-Request: 1` guard coverage on non-GET
   `/vocab` routes;
3. **R13 check:** verifies stable semantic ref validation on dictionary activation and
   stale-token HTTP 409 rejection logic.

### A9 — Tests and gate verification

1. Comprehensive unit and integration test suites:
   - `tests/test_deck.py`: FSRS review loop, raw confidence logging, note-deck lifecycle, orphaned notes, user meanings, meaning availability (complete/partial/none);
   - `tests/test_render.py`: front/back card rendering, selected meaning sets, user-meaning precedence, tri-state noun plural, derived compound rendering, empty examples handling;
   - `tests/test_audio.py`: audio precedence, untrusted media validation, sacred custom audio persistence, crash-safe replacement, revert to automatic, human cache fallback, Piper on-demand invocation;
   - `tests/test_dictionary.py`: D47 atomic activation, stable semantic ref relink, missing ref fail-closed, stale token 409, asset token verification;
   - `tests/test_api.py`: all `/vocab` endpoints, R12 host/origin guards, custom header enforcement, JSON content-type check, Anki TSV export sanitization, Persian 422 rejection;
   - `tests/test_check_agents.py`: executable R6, R12, R13 checker tests;
2. `make gate` passes (ruff, `mypy --strict .`, pytest, `check_agents.py` R1/R3/R6/R7/R12/R13);
3. `git diff --check` passes;
4. Zero runtime LLM dependencies in `pyproject.toml` runtime deps or `app/`.

### A10 — Report

Create `tasks/slice-7.report.md` documenting:
- Schema changes and PART-B tables;
- Review scheduling and confidence logging evidence;
- Multilingual meaning and D43 availability evidence;
- Card rendering and tri-state plural evidence;
- Dictionary activation/relink and stale picker evidence;
- Pronunciation audio precedence, custom media, and Piper cache evidence;
- API endpoint coverage and R12 security guard evidence;
- Executable AGENTS R6/R12/R13 check results;
- Full `make gate` and test numbers.

## Stop-and-ask

STOP and return to the slice-7 orchestrator if:

- `Depends: slice-6` is not merged/closed;
- Satisfying any requirement requires a runtime LLM SDK, API call, or provider dependency (violates AGENTS R1);
- Satisfying any requirement requires activating Persian (`fa`) at runtime instead of deferring it (violates ADR-0007);
- Any requirement would need modifying a file outside the Allowlist;
- `review_log` UPDATE or DELETE path is proposed (violates AGENTS R6);
- Rendered card faces are stored in the database (violates AGENTS R4);
- Notes with review history would be cascade-deleted on deck deletion (violates AGENTS R5);
- Dictionary and user database share a file or connection (violates AGENTS R9);
- Direct coupling to the lecture app is introduced (violates AGENTS R7);
- Browser localhost guards cannot reject wildcard origins or missing custom request headers (violates AGENTS R12);
- Durable dictionary identity relies on numeric SQLite IDs rather than stable semantic refs (violates AGENTS R13);
- Custom audio save is autosaved before explicit user confirmation or lacks crash-safe replacement (violates ADR-0005);
- Anki export uses comma-separated format or unescaped newlines/tabs (violates AGENTS R10);
- Any mandatory test or `make gate` check fails.

## Risk

Risk: migration, auth-security, public-api, data-loss

## Why-risk

WORKFLOW.md §6 is a path/consumer lookup. Slice-7 touches:
- `reference/schema.sql` (schema/data migration file for PART-B user database) -> `migration`;
- `app/api.py` (loopback CORS exact allowlist, host/origin validation, custom request header security checks) -> `auth-security`;
- `app/api.py`, `app/__init__.py`, `app/render.py`, `app/deck.py`, `app/dictionary.py`, `app/audio.py` (publicly importable and externally callable HTTP routes) -> `public-api`;
- `app/deck.py`, `app/audio.py` (irreversible review log, note/deck deletion and orphan handling, crash-safe custom audio replacement, atomic dictionary relink) -> `data-loss`.

Because all four risk categories apply, a pre-committed T3 full-diff review is required before merge.

## Model

Model: gpt-5.6-terra / T3 / high

## Why

WORKFLOW.md §4:
- **Blast radius:** Cross-cutting slice establishing the entire runtime application (`app/deck.py`, `app/render.py`, `app/api.py`, `app/audio.py`), user database schema, security middleware, and audio engine;
- **Novelty:** First implementation of the runtime application factory, FSRS review loop, multilingual availability, D47 atomic relink, and ADR-0005 audio precedence;
- **Verification & Judgment:** Implements multiple concurrent state machines and binding architectural invariants (AGENTS R4, R5, R6, R9, R10, R12, R13; ADR-0003, ADR-0004, ADR-0005, ADR-0007).

Novelty, blast radius, and judgment route to T3 with high reasoning effort.

## Fallback

Fallback: opus-5 / T3 / high

No lower-tier fallback is authorized.

## Worker implementation constraints

1. Start only after the slice-7 orchestrator supplies the exact verified `EXPECTED_MAIN_HEAD`.
   Create `slice/7` from that HEAD; a mismatch is STOP.
2. Read `reference/schema.sql`, `AGENTS.md`, `WORKFLOW.md`, ADR-0001, ADR-0002, ADR-0003,
   ADR-0004, ADR-0005, ADR-0007, and this brief before editing.
3. Keep dependency direction strictly one-way: `api -> deck -> render -> dictionary -> resolve`.
4. App factory `create_app` must not perform environment reads or instantiate module-level state at import time.
5. All non-GET `/vocab` browser routes require `X-Flashcards-Request: 1`. Wildcard `*` in CORS origins is rejected.
6. `review_log` is append-only.
7. Card faces are rendered dynamically at display time, never stored in SQLite.
8. Custom pronunciation audio is sacred user data; automatic Piper/human cache is disposable.
9. Missing German learner meanings are represented as `meaning_state = partial | none` under D43, never synthesized at runtime.
10. Persian `fa` returns HTTP 422 with zero database writes.
11. Create `tasks/slice-7.report.md` before Worker CLOSE.

## Exact report scaffold

Create before Worker CLOSE:

```markdown
# Slice 7 report

## NARRATIVE
```

Populate only `## NARRATIVE`.

## Required terminal verification before Worker CLOSE

The slice-7 orchestrator will supply `EXPECTED_MAIN_HEAD`.

Run all of:

```sh
: "${EXPECTED_MAIN_HEAD:?STOP: EXPECTED_MAIN_HEAD was not supplied}"

test "$(git branch --show-current)" = "slice/7" || {
  echo "STOP: not on slice/7"; exit 1; }

test "$(git rev-parse main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: main differs from expected main HEAD"; exit 1; }

test "$(git merge-base slice/7 main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: slice/7 base differs from expected main HEAD"; exit 1; }

make gate

git diff --check "$EXPECTED_MAIN_HEAD"...HEAD

outside="$({
  git diff --name-only "$EXPECTED_MAIN_HEAD"...HEAD
  git ls-files --others --exclude-standard
} |
grep -vxF \
  -e reference/schema.sql \
  -e app/__init__.py \
  -e app/api.py \
  -e app/deck.py \
  -e app/render.py \
  -e app/dictionary.py \
  -e app/examples.py \
  -e app/audio.py \
  -e tools/check_agents.py \
  -e tests/conftest.py \
  -e tests/test_api.py \
  -e tests/test_deck.py \
  -e tests/test_render.py \
  -e tests/test_audio.py \
  -e tests/test_dictionary.py \
  -e tests/test_check_agents.py \
  -e pyproject.toml \
  -e tasks/slice-7.report.md || true)"

test -z "$outside" || {
  echo "STOP: scope violation:"
  printf '%s\n' "$outside"
  exit 1
}

test -f tasks/slice-7.report.md || {
  echo "STOP: tasks/slice-7.report.md missing"
  exit 1
}

test "$(sed -n '1p' tasks/slice-7.report.md)" = "# Slice 7 report" || {
  echo "STOP: report header incorrect"
  exit 1
}

test "$(sed -n '3p' tasks/slice-7.report.md)" = "## NARRATIVE" || {
  echo "STOP: report NARRATIVE heading incorrect"
  exit 1
}
```
