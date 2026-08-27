# Slice 8 — Standalone browser product completion

Task:        Complete the existing standalone FastAPI runtime as an independently
             usable browser product. Preserve and finish the order-9 backend/smoke
             work, then add the Lit browser client, real APKG export, one-service
             production serving, and deterministic browser E2E. The lecture app is
             explicitly out of scope; slice-9 remains its later composition work.

Depends:     slice-7

## Binding product contract

This brief implements ADR-0002 §6 order 9 on the accepted Slice-7 runtime. The
controlling requirements are ADR-0001 §7, §11 and D11/D13/D19; ADR-0002 §4,
§5, D24/D25/D27; ADR-0003 §5; ADR-0004 §6.6 D47 and §10; ADR-0005 §10;
ADR-0007 D72/D80; and AGENTS R1, R4–R6, R9–R13 and C1–C3.

The five stages are one slice on one `slice/8` branch. A later stage may begin
only after its predecessor has recorded its listed acceptance evidence. Do not
start the slice until slice-7 is accepted, merged, closed, and pushed from the
main HEAD verified by the fresh Slice-8 orchestrator.

### Frozen frontend and ownership rules

- Browser source is Lit + TypeScript + Web Components + Vite, using CSS design
  tokens. Playwright is the browser E2E runner. Web Awesome is optional and, if
  used, limited to generic primitives (`wa-button`, `wa-dialog`, `wa-spinner`,
  `wa-callout`/toast); native semantic controls remain preferred.
- `frontend/` is the only authoritative handwritten browser source. Its tests,
  package manifest, and lockfile are source too.
- `app/frontend/` is generated Vite output only. It is never hand-maintained,
  must be cleaned/rebuilt from `frontend/`, and must not be treated as authored
  source or a review substitute. Production images build it; local production
  E2E builds it before starting FastAPI.
- Do not adopt React, Next.js, Vue, Angular, Svelte, `ts-fsrs`, browser-owned
  scheduling, IndexedDB as authoritative flashcard storage, or a second
  scheduler. The client submits raw confidence `1..5`; Python maps it to FSRS
  and owns every durable mutation.
- All APIs remain under `/vocab`. Development may use a Vite `/vocab` proxy;
  production is one loopback FastAPI service that serves the compiled client at
  `/`. It requires neither a lecture app nor a separate frontend server, and it
  adds no runtime LLM path.

## S8A — Smoke baseline + capture/import/ranking

### Outcome

Repair the executable smoke baseline and remove its tool exclusions; implement
the stateless two-stage capture endpoints, CSV word-list import, and pure,
deterministic example ranking. Preserve all accepted Slice-7 behavior.

### Dependencies

Slice-7 closed on the expected main HEAD; its factory, R12 middleware,
`DictionaryRuntime`, rendering, FSRS review, and pronunciation runtime are the
starting contract.

### Exhaustive allowlist

- `reference/smoke_test.py`
- `pyproject.toml` (at this stage, remove only the `reference` tool exclusions)
- `app/api.py`
- `app/deck.py`
- `app/examples.py` (new)
- `tests/conftest.py`
- `tests/test_capture.py` (new)
- `tests/test_examples.py` (new)
- `tests/test_smoke_baseline.py` (new)
- `tasks/slice-8.report.md` (new; create the required scaffold before close)

### Acceptance evidence

1. `reference/smoke_test.py` imports the repository `app` package and opens
   `reference/schema.sql` explicitly; `reference` is no longer excluded from
   ruff, mypy, or pytest traversal. A subprocess smoke test runs it using the
   project venv and proves exit 0.
2. `POST /vocab/highlight` accepts `{sentence_text, selected_span,
   lesson_label, lesson_id?, known_lemmas?}`, bounds-validates the span, resolves
   locally, returns candidates with stable refs/grammar/current asset token plus
   normalized self-contained `capture_context`, and makes no user-db writes.
3. `POST /vocab/cards` accepts selected candidate refs, optional sense refs,
   allowed overrides, capture context, deck target, and asset token; revalidates
   all values and atomically creates/reuses notes and memberships. A stale token
   returns `409 dictionary_changed` with zero writes. Absent active-generation
   semantic refs, duplicate same-identity selections, unknown overrides, invalid
   spans, invalid deck data, and every validation failure return 422 with zero
   writes. It freezes the chosen primary dictionary sentence into `example_de`;
   ordinary rendering never reranks an existing note.
4. The only editable keys are `front_override`, `back_override`,
   `meaning_langs`, and `user_meanings`; `meaning_langs` is a non-empty subset
   of `{de,en}`. `user_meanings` follows D44 exactly (string upsert, null delete,
   omission no mutation, `{}`/blank invalid). `fa` is 422 zero-write. Reuse
   preserves omitted values and user meanings across deselect/reselect.
5. `POST /vocab/import/csv` accepts `{csv_text, deck_name, meaning_languages}`;
   processes one word per line through the same resolver/candidate pipeline,
   defaults to the top candidate, creates `needs_gloss` notes for misses, and
   commits atomically per request or performs zero writes on 422.
6. `app/examples.py` is pure and deterministic: target length near nine tokens;
   penalties for unknown/rare unknown lemmas, proper nouns, and untranslated
   examples; a small question bonus; and `known = deck lemmas ∪ known_lemmas`
   when supplied by value, otherwise deck lemmas.
7. Smoke and focused tests prove the complete ADR-0002 §5 capture matrix, the
   ADR-0003 raw-confidence/mapped-rating evidence, D47 renumber/relink,
   ambiguity/disappearance/mid-observation activation and stale-token cases, and
   ADR-0005 override/revert, media validation, cache-corruption, fallback,
   stable-identity, and no-deletion cases. Fakes provide zero network and zero
   subprocess dependencies.

### Risk

`public-api`, `data-loss` — new HTTP writes create/reuse durable notes and decks.

### Model

`antigravity/gemini-3.7-flash / T3 / high`

### Why

WORKFLOW §4 highest row: cross-cutting public API transactions, durable user
state, and several accepted ADR failure contracts require design judgment.

### Fallback

`codex/gpt-5.6-terra / T3 / high` (Gemini/GPT routes only; exact route names
come from the current routing file).

### STOP conditions

Stop for an unmet slice-7 closure/preflight, any needed path outside this
allowlist, any accepted-ADR conflict, a proposal to persist rendered faces or
cascade-delete reviewed notes, a non-DE/EN meaning request, a failed required
test/gate, or a need for a runtime LLM/dependency beyond this stage's scope.

## S8B — Frontend foundation

### Outcome

Establish the authoritative, reproducible Lit/Vite browser source tree and the
foundation for a server-authoritative standalone client. No product workflow is
claimed complete in this stage.

### Dependencies

S8A acceptance is recorded; its `/vocab` capture/import contracts are stable.

### Exhaustive allowlist

- `frontend/**` (new authoritative source, including lockfile and only the
  foundation application, typed client, token styles, and test configuration)
- `.gitignore` (only generated client output/dependency ignores)
- `tasks/slice-8.report.md`

### Acceptance evidence

1. `frontend/` has a locked TypeScript/Lit/Vite/Playwright toolchain, strict
   TypeScript configuration, CSS design tokens, a root app element, and a typed
   `/vocab` fetch client.
2. The client attaches `X-Flashcards-Request: 1` to every non-GET request and
   sends JSON content types where required by R12. Development configuration
   proxies `/vocab` to loopback FastAPI; it never invents another API prefix.
3. The only retained browser state is ephemeral UI state: active view/current
   card/reveal state/picker selections/form fields/unsaved recording Blob and
   loading-error-toast state. No scheduler, due date, FSRS state, authoritative
   card cache, or IndexedDB persistence exists.
4. `vite build` creates `app/frontend/` from `frontend/` with a clean output
   directory. The generated directory is ignored/not hand-maintained and the
   source/build ownership is documented in the stage report.

### Risk

`none` — isolated, reversible source/tooling foundation with no backend or user
data mutation.

### Model

`antigravity/gemini-3.7-flash / T2 / high`

### Why

WORKFLOW §4: a new but bounded frontend pattern needs judgment; the exhaustive
source boundary and build/type checks keep the blast radius contained.

### Fallback

`codex/gpt-5.6-luna / T2 / high`.

### STOP conditions

Stop if the foundation requires a framework or dependency outside the frozen
stack, needs a persistent browser store or client scheduler, changes a backend
contract, hand-edits generated `app/frontend/`, or changes a path outside the
allowlist.

## S8C — Standalone product workflows

### Outcome

Turn the foundation into the usable standalone product UI: navigation, decks,
manual/capture/import workflows, review, meanings, audio controls, and clear
failure states backed solely by the FastAPI service.

### Dependencies

S8A and S8B acceptance evidence, including the built typed client and stable
capture/import API contracts.

### Exhaustive allowlist

- `frontend/**`
- `app/api.py`
- `app/deck.py`
- `tests/test_api.py`
- `tests/test_capture.py`
- `tasks/slice-8.report.md`

### Acceptance evidence

1. The shell supplies navigable deck list/create/delete, deck opening, manual
   vocabulary creation, CSV import, import/export entry points, and explicit
   loading/empty/error/success states.
2. The capture view performs highlight → picker → `/vocab/cards`, supports D11
   multi-select and supported override/DE/EN meaning edits, surfaces stale asset
   `409` without pretending a write succeeded, and never relies on lecture data.
3. Review fetches server due cards, reveals the answer explicitly, and submits
   raw confidence buttons `1..5` (with documented keyboard behavior) to Python;
   it neither maps ratings nor calculates scheduling values in the browser.
4. Card presentation displays selected DE/EN meanings and supported user-meaning
   editing, preserves display-time render semantics, and leaves German grammar
   independent of meaning selection.
5. Pronunciation playback uses the server audio endpoint. Upload/record keeps an
   unsaved Blob browser-local until explicit Save; Revert to automatic is a
   deliberate server request. Conflict, validation, unavailable-audio, and save
   errors are clear and do not discard unsaved audio silently.
6. Backend changes, if genuinely required to expose an already accepted runtime
   capability to the client, retain R12, C1/C2, append-only review logging,
   zero-write validation, and existing endpoint compatibility; focused tests
   cover them.

### Risk

`public-api`, `data-loss` — this stage exercises durable deck/note/audio writes
through browser-facing API contracts.

### Model

`codex/gpt-5.6-terra / T3 / high`

### Why

WORKFLOW §4 highest row: cross-cutting product behavior touches public API,
durable data, R12 security guards, and user-media lifecycle.

### Fallback

`antigravity/gemini-3.7-flash / T3 / high`.

### STOP conditions

Stop for a required schema/ADR change, changed server authority for scheduling,
browser persistence of authoritative data, an R12 bypass, a lecture-app
dependency, non-DE/EN support, any path outside the allowlist, or any failing
required verification.

## S8D — APKG/audio export + production serving/package boundary

### Outcome

Add real, semantically verified `.apkg` export and package the browser product
as one FastAPI-served production service.

### Dependencies

S8A–S8C acceptance is recorded; export consumes server observations and the
accepted audio precedence without taking ownership of scheduling or reviews.

### Exhaustive allowlist

- `app/export.py` (new)
- `app/api.py`
- `pyproject.toml` (add only the exact export dependency and necessary tooling
  integration)
- `Dockerfile`
- `frontend/**`
- `app/frontend/**` (generated Vite output only; never hand-maintained)
- `.gitignore` (generated-output/dependency ignores only)
- `tests/test_export.py` (new)
- `tests/test_api.py`
- `tests/test_container.py` (new, if needed for deterministic packaging checks)
- `tasks/slice-8.report.md`

### Acceptance evidence

1. `pyproject.toml` pins `genanki==0.13.1`, unless implementation-time
   validation selects another exact version and records the evidence/reason in
   the report. `genanki` is imported only by the export boundary, never review,
   card creation, or scheduling code.
2. `app/export.py` produces `.apkg` bytes from server export observations and
   stable semantic refs. It preserves generated display values without persisting
   rendered card faces or creating a second due/scheduling model.
3. APKG audio precedence is custom learner audio > export-eligible human audio
   > Piper audio > absent. Fields use basename-only `[sound:filename.ext]`
   references; no paths leak into Anki fields.
4. Tests validate semantics, not package bytes: valid ZIP, `collection.anki2`,
   readable SQLite, expected deck/model/note records, stable GUIDs, media
   manifest, correct media basenames, and expected audio bytes.
5. The FastAPI factory serves generated `app/frontend/` at `/` after all `/vocab`
   routes are registered. Production needs no separate frontend server; Vite's
   proxy remains development-only. Static serving retains loopback host/origin
   protection. The Docker image builds the authoritative frontend, contains its
   generated output, starts the service rather than only a readiness script, and
   introduces no runtime LLM dependency or lecture-app requirement.

### Risk

`public-api`, `data-loss` — export can expose user content/media and production
serving changes a browser-facing deployment boundary.

### Model

`codex/gpt-5.6-terra / T3 / high`

### Why

WORKFLOW §4 highest row: a new archive/media format and production serving
boundary cross public API, user media, and deployment behavior.

### Fallback

`antigravity/gemini-3.7-flash / T3 / high`.

### STOP conditions

Stop if export owns review/scheduling/due state, media precedence violates
ADR-0005, Anki references are non-basename paths, generated output is edited by
hand, static serving weakens R12/loopback policy, a second server is required in
production, a path outside the allowlist is needed, or verification fails.

## S8E — Playwright product E2E + final acceptance

### Outcome

Prove the actual compiled, FastAPI-served standalone product works end to end,
then complete the mandated risk review and slice acceptance evidence.

### Dependencies

S8A–S8D acceptance is recorded; the production image/service boundary and
generated client build are available locally.

### Exhaustive allowlist

- `frontend/tests/e2e/**`
- `frontend/playwright.config.ts`
- `frontend/**` (only where a testability/accessibility correction is required
  by a failing specified E2E)
- `tests/test_api.py`
- `tests/test_export.py`
- `tasks/slice-8.report.md`

### Acceptance evidence

1. Playwright starts the actual FastAPI-served product, not Vite alone, and
   deterministically executes: launch → create/open deck → manually add or CSV
   import vocabulary → review → reveal → confidence submission → pronunciation
   → TSV/APKG export.
2. E2E also covers two-stage picker multi-select, stale asset-token conflict
   messaging and zero-write recovery, loading/empty/error states, audio custom
   override with browser-local preview/explicit Save/Revert, and deterministic
   unavailable/corrupt automatic-audio fallback behavior. It uses fakes/local
   assets only: no external-network dependency.
3. The full Python gate passes with `reference/` included; frontend lockfile
   install, type/build checks, and Playwright all pass. `git diff --check` is
   clean. The report maps every S8A–S8E requirement to tests/gate evidence and
   begins exactly `# Slice 8 report` then `## NARRATIVE`.
4. Because the slice contains `public-api` and `data-loss` paths, a fresh T3
   reviewer performs the mandatory full-diff review of `main...slice/8` before
   merge. Any finding follows WORKFLOW §5 / AGENTS G7; no closure occurs while
   review is pending or blocked.

### Risk

`public-api`, `data-loss` — final acceptance covers the full browser/API/export
surface and durable user state.

### Model

`codex/gpt-5.6-terra / T3 / high`

### Why

WORKFLOW §6 mandates a T3 full-diff review for these path-based risks; product
E2E also spans the cross-cutting serving, API, media, and durable-data boundary.

### Fallback

`antigravity/gemini-3.7-flash / T3 / high` for implementation evidence; the
mandatory independent final review remains a fresh T3 Gemini/GPT session.

### STOP conditions

Stop for any nondeterministic external dependency, a failing Python/frontend/
Playwright verification, an unreviewed risk diff, a scope expansion into lecture
integration or Compose, an accepted-ADR conflict, or any changed path outside
the stage allowlist.

## Required closure evidence

Before Worker CLOSE, the Slice-8 orchestrator supplies `EXPECTED_MAIN_HEAD` and
the worker verifies the branch/base, runs the project gate using the authoritative
venv paths supplied by the orchestrator, runs frontend build/type/Playwright
checks, and proves only the union of the five stage allowlists plus the report
changed. Then it records the exact commands, gate numbers, generated-output
policy, E2E evidence, APKG semantic evidence, and mandatory T3 review result in
`tasks/slice-8.report.md`. The closure worker alone performs the mechanical merge,
post-closure gate, handoff, and push under WORKFLOW §11.
