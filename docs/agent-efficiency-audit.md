# Agent and Repository Efficiency Audit

**Repository:** `/home/saber/projects/flashcard`
**Audit base main HEAD:** `17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5`
**Audit branch:** `audit/agent-efficiency` (extends prior audit `3553d9c`)
**Audit date:** 2026-09-01 (correction pass)
**Scope:** evidence-only audit. No code, tests, governance, or ADRs were modified.

This is the convergence pass. The prior audit at `3553d9c` contained
contradictory rollout recommendations and inconsistent token-estimate
methodology. The corrections are:

- One reproducible token heuristic (`UTF-8 char count // 4`) replaces
  the mix of line-count and char-count estimates.
- One canonical machine-readable module map (`MODULES.toml`) replaces
  the `docs/repo-map.md`-as-database idea; `tools/affected_tests.py`
  consumes `MODULES.toml` only.
- Nested `app/AGENTS.md` / `frontend/AGENTS.md` / `tools/AGENTS.md` are
  downgraded from "BEFORE SLICE 9" to "SHOULD FOLLOW / EXPERIMENTAL".
- One consistent three-bucket rollout (BEFORE SLICE 9, SHOULD FOLLOW,
  DEFER / REJECT) — no item appears in two buckets.
- The Python import graph is described accurately, not as a strict
  linear chain (it has sibling edges from `api` to `audio`, `examples`,
  `export`).
- Generated reviewer context is an index, not authoritative evidence.

---

## Executive Decision

The repository is structurally efficient at current scale. The audit's
top recommendation is therefore **not a refactor or a build-system
adoption**; it is a **module-metadata + affected-test infrastructure**
that turns the current "read the whole repo" worker model into a "read
the brief, the explicitly required files, the relevant `MODULES.toml`
rows, and the focused tests" model. Final candidate validation (`make
` make gate` plus slice-specific frontend checks plus Playwright) is
**unchanged**.

**Architecture decision (single, consistent):**

- **Stay monorepo.** No Pants / Bazel / Nx / Turborepo at this size;
  no multi-repo split; no Python package explosion; no frontend
  component split for LLM context; no microservice decomposition.
  The repo's growth is governance-bound (~117k tokens of docs vs ~73k
  tokens of app source); splitting the repo does not shrink the docs.
- **One canonical machine-readable module map:** `MODULES.toml` (TOML
  is parsed by Python 3.12 stdlib `tomllib`; no dependency added).
  `docs/repo-map.md` is **only** a generated view of `MODULES.toml` or
  a strictly non-authoritative human view. Tools never parse Markdown
  as metadata.
- **One focused-test resolver:** `tools/affected_tests.py` reads
  `MODULES.toml` plus `git diff --name-only main...HEAD` and emits a
  focused pytest command. Conservative — unmapped paths force a broad
  fallback rather than silent omission. Final acceptance remains
  `make gate` plus frontend plus Playwright (unchanged).
- **Root `AGENTS.md` is not reduced as a prerequisite.** It contains
  the cross-cutting binding prohibitions (R1/R3/R6/R7/R12/R13) and
  the G-rules the workflow depends on. Any "shrink root AGENTS.md"
  move is a separate governance amendment and is **not** on the
  slice-9 critical path.
- **Nested `app/AGENTS.md` / `frontend/AGENTS.md` / `tools/AGENTS.md`
  are SHOULD FOLLOW / EXPERIMENTAL**, not BEFORE SLICE 9. Their value
  is plausible but correctness depends on every worker being explicitly
  instructed to read them and on rules not being duplicated or silently
  overridden.

**BEFORE SLICE 9 (small, zero product code):** land `MODULES.toml`;
amend `WORKFLOW.md §2` brief schema with a `Required reading:` field;
amend `PROMPTS.md` so workers and risk-label reviewers use it; land
`tools/affected_tests.py` consuming `MODULES.toml`; add an executable
check that `MODULES.toml` is internally valid and every mapped test
path exists; add focused tests for the resolver itself.

**SHOULD FOLLOW:** `tools/context_pack.py`; conversion of straightforward
reviewed rules to executable checks (already backlog); nested
per-domain `AGENTS.md` only after explicit inheritance / duplication
rules are defined; optionally generated `docs/repo-map.md` from
`MODULES.toml`.

**DEFER / REJECT:** Pants, Bazel, Nx, Turborepo, multi-repo split,
Python package explosion, frontend component split for LLM context,
auto-refactoring `app/api.py` purely on file length, any microservice
decomposition.

---

## Repository Evidence

All token estimates in this document use **one method**:

```
approximate_tokens = UTF-8 decoded character count // 4
```

This is a coarse heuristic, explicitly labelled as such. No measured
LLM token counts are claimed. Where the heuristic is meaningless
(binary / ZIP / lockfile content), no estimate is given. The exact
script is recorded in "Evidence Commands".

### Tracked file totals (observed, base `17a899e`)

- **Tracked files: 101** (`git ls-files | wc -l`).
- Layout: 27 in `tasks/`, 22 in `tests/`, 18 in `frontend/`, 9 in
  `app/`, 9 in `docs/`, 4 in `tools/`, 2 in `reference/`. Single
  copies of `WORKFLOW.md`, `PROMPTS.md`, `STATE.md`, `AGENTS.md`,
  `pyproject.toml`, `Makefile`, `Dockerfile`, `README.md`, `.gitignore`,
  `.dockerignore`, `STATE.template.md`.
- Total tracked chars (UTF-8 text): **2,625,625**, lines: **58,519**.
  Approx tokens (chars/4): **656,406** — this is the *entire*
  repository's text budget, **not** what any single worker loads.

### Per-area token budgets (observed; chars//4)

| Area | Files | Lines | ~Tokens |
|---|---:|---:|---:|
| `app/` (Python runtime) | 9 | 7,565 | **72,719** |
| `tests/` (Python tests + fixtures) | 21 + 2 fixtures | 16,748 | **163,689** |
| `tools/` (Python build/gate) | 4 | 7,040 | **73,856** |
| `reference/` (schema + smoke) | 2 | 625 | **5,263** |
| `frontend/src/` (TS + CSS) | 8 | 3,052 | **30,889** |
| `frontend/tests/e2e/` | 3 | 452 | **4,539** |
| `frontend/` config (no lockfile) | 5 | 122 | **787** |
| `frontend/package-lock.json` | 1 | 1,316 | n/a (lockfile, skipped) |
| Governance (WORKFLOW + AGENTS + PROMPTS + STATE + plan + backlog) | 6 | 2,357 | **32,382** |
| 7 ADRs (`docs/adr/0001..0007.md`) | 7 | 5,184 | **81,722** |
| Canonical slice briefs (`tasks/slice-N.md` only) | 11 | 6,033 | **61,855** |
| Canonical slice reports (`tasks/slice-N.report.md`) | 9 | 4,684 | **71,830** |
| Auxiliary task files (escalation, consult, reference-notes, etc.) | 6 | 1,803 | **28,516** |

Largest individual files:

| File | Lines | ~Tokens |
|---|---:|---:|
| `tools/build_dict.py` | 5,981 | 64,327 |
| `tests/test_build_dict_stage04.py` | 4,155 | 51,753 |
| `tasks/slice-6.report.md` (historical, frozen) | 2,823 | 44,098 |
| `app/api.py` | 2,455 | 25,357 |
| `frontend/src/app.ts` | 1,573 | 20,146 |
| `docs/adr/0004-multilingual-learner-meanings.md` | 1,238 | 18,652 |
| `app/deck.py` | 1,880 | 18,613 |
| `tests/test_api.py` | 2,045 | 16,854 |
| `docs/adr/0002-standalone-and-integration.md` | 939 | 15,304 |

### Frontend breakdown (observed)

- `frontend/src/app.ts` — 20,146 tokens (single root Lit element, 1,573
  lines, 137 methods).
- `frontend/src/api/*` — 5,318 tokens total
  (`client.ts` 2,885, `types.ts` 1,721, `errors.ts` 691, `index.ts` 21).
- `frontend/tests/e2e/` — 4,539 tokens (4 Playwright scenarios in
  `product.spec.ts`).
- `frontend/src/api/client.test.ts` — 5,132 tokens (25 unit tests).

### Test inventory (observed, AST)

Total `test_*` functions across `tests/`: **476**.

| Group | Tests | Files |
|---|---:|---|
| `build_dict` (stages 01–05) | 231 | 5 |
| `governance` (`check_agents`, `gate2_coverage`, `container`) | 78 | 3 |
| `dictionary` | 42 | 1 |
| `runtime-api` (`api`, `capture`, `smoke`) | 31 | 3 |
| `render` | 27 | 1 |
| `resolve` (+ spaCy) | 26 | 2 |
| `audio` | 21 | 1 |
| `deck` | 10 | 1 |
| `examples` | 7 | 1 |
| `export` | 3 | 1 |

The `build_dict` group (231 tests, 48% of total) is **orthogonal** to
runtime work and would never be affected by a slice that does not
touch `tools/build_dict.py` or `tests/fixtures/wiktextract_*`.

### Intra-`app/` import graph (observed; `ast.ImportFrom`)

```
app/__init__.py      ->  app.api
app/api.py           ->  app.audio, app.deck, app.dictionary,
                        app.examples, app.export, app.render, app.resolve
app/deck.py          ->  app.dictionary
app/dictionary.py    ->  app.resolve
app/export.py        ->  app.render
app/render.py        ->  app.dictionary
app/audio.py         ->  (none)
app/examples.py      ->  (none)
app/resolve.py       ->  (none)
```

**This is not a strict chain.** AGENTS C2's wording
("`api → deck → render → dictionary → resolve`") describes the
*deepest* path; the actual graph also has sibling edges from `api`
to `audio`, `examples`, `export`. `export` itself depends on `render`.
`audio`, `examples`, and `resolve` are leaves (no `app.*` imports).
No module imports upward. No reverse coupling is observed.

### Frontend module graph (observed)

`frontend/src/main.ts` imports the compiled `app.js` and tokens.css.
`frontend/src/app.ts` imports only `lit`, `./api/client.ts`,
`./api/errors.ts`, and `./api/types.ts` (no cycles).

### Gate composition (observed; from `Makefile`)

```
gate: ruff mypy pytest check-agents
ruff:        ruff check .
mypy:        mypy --strict .
pytest:      pytest -q
check-agents:python tools/check_agents.py
```

`tools/check_agents.py` enforces R1 / R3 / R6 / R7 / R12 / R13 (6 of
the 7 `[executable]` rules; R2 is structurally enforced because
`tools/check_agents.py` scans `app/`). AGENTS R8, R9, R10, R11 are
`[reviewed]`.

### Committed gate timing (observed from `handoff/main-gate.stdout`)

- `ruff check .` — "All checks passed!"
- `mypy --strict .` — "Success: no issues found in 35 source files"
- `pytest -q` — "691 passed, 88 warnings in **210.28s** (0:03:30)"
  (slice-8 base)
- `python tools/check_agents.py` — AGENTS R-rules PASS

Frontend authoritative checks (slice-8): `npm ci` 26 packages in 3s;
`npm test --prefix frontend` 25 pass in ~9.89s; `npm run build`
431–557 ms; Playwright 4/4 scenarios in **12.8s wall clock** against
the FastAPI-served compiled product.

### Handoff / closure cost (observed)

`handoff/` directory at base: `MANIFEST.md`, `main-gate.stdout` /
`main-gate.stderr`, `git-log.txt`, and 9 historical
`orchestrator-handoff-slice-N.zip` files (72 KB slice-1 → 475 KB
slice-8). The seven ADRs together account for ~330 KB uncompressed
text inside the slice-8 zip. **No nested `AGENTS.md` / `README` /
`CONTEXT` files exist under `app/`, `frontend/`, `tools/`, or
`tests/`** (verified via `find`).

---

## Current Cost Model

Each category identifies the specific repository evidence that causes
or prevents cost. Labels: **[observed]** = directly counted;
**[inference]** = derived; **[recommendation]** = proposed change.

### 1. Repository discovery (cold-start)

**[observed]** Minimum startup material for a fresh orchestrator
(governance = WORKFLOW + AGENTS + PROMPTS + STATE + plan + backlog)
is **~32,382 tokens** before any slice brief.

**[observed]** A fresh slice-9 worker that reads the minimum
governance + slice brief + slice-8 closure report + every ADR named in
`tasks/slice-8.md`'s "Binding product contract" recital (all 7 ADRs) +
every relevant `app/` source would absorb approximately
`(governance 32k) + (slice-8 brief 4,415) + (slice-8 report 11,715) +
(ADR total 82k) + (app source 72k) ≈ 202,000 tokens`. Today the brief
lists the binding ADR IDs but does not say which subset is normative
for this slice.

**[inference]** The structural reason discovery is expensive: no
module index exists. They compensate by reading more than needed.

### 2. Global governance / context reading

**[observed]** WORKFLOW / AGENTS / PROMPTS / STATE are a fixed corpus
that does not change per slice. Per-session rediscovery is
unavoidable for cold workers per WORKFLOW §1.

**[recommendation]** Amend WORKFLOW §2 brief schema with a
`Required reading:` field that explicitly enumerates the file list
the worker must load. Zero code; one schema-line change.

### 3. Implementation context

**[observed]** The "Binding product contract" recital in slice briefs
(e.g. `tasks/slice-8.md` lines 12–16) lists every relevant ADR ID.
It does *not* say which subset is normative for this slice or which
ADR sections to load first.

**[recommendation]** The `Required reading:` field (item 2 above) is
the load-on-cold minimum; the binding recital remains the normative
authority. The two are complementary, not duplicates.

### 4. Test discovery

**[observed]** The path mapping `app/<module>.py` →
`tests/test_<module>.py` is already 1:1 by naming convention for 7
of 8 `app/` modules (`api` shares three test files: `test_api.py`,
`test_capture.py`, `test_smoke_baseline.py`):

| `app/` file | Owning test file(s) | Tests |
|---|---|---:|
| `app/api.py` | `test_api.py`, `test_capture.py`, `test_smoke_baseline.py` | 31 |
| `app/audio.py` | `test_audio.py` | 21 |
| `app/deck.py` | `test_deck.py` | 10 |
| `app/dictionary.py` | `test_dictionary.py` | 42 |
| `app/examples.py` | `test_examples.py` | 7 |
| `app/export.py` | `test_export.py` | 3 |
| `app/render.py` | `test_render.py` | 27 |
| `app/resolve.py` | `test_resolve.py`, `test_resolve_spacy.py` | 26 |
| `tools/build_dict.py` | `test_build_dict_stage01.py`…`stage05.py` | 231 |
| `tools/check_agents.py` | `test_check_agents.py` | 40 |
| `tools/gate2_coverage.py` | `test_gate2_coverage.py` | 37 |
| `tools/resolver_hash.py` | (transitively via `test_check_agents.py`) | — |
| `frontend/src/api/client.ts` | `frontend/src/api/client.test.ts` | 25 |
| `frontend/src/app.ts` | `frontend/tests/e2e/product.spec.ts` | 4 scenarios |
| `Dockerfile` | `test_container.py` | 1 |
| `reference/schema.sql` | `test_smoke_baseline.py` | 1 |

**[inference]** Test discovery is not the cost — the naming
convention is obvious. The cost is workers *not trusting* the
mapping and re-running the whole tree anyway (what WORKFLOW §16
prohibits).

**[recommendation]** Codify the mapping in `MODULES.toml` (TOML, not
Markdown) and a small `tools/affected_tests.py` that reads it plus
`git diff --name-only main...HEAD`.

### 5. Test execution

**[observed]** Full `make gate` on slice-8 base: **~3:30 wall clock**
(`pytest -q` alone **210.28s** on 691 tests). Focused checks like
`pytest -q tests/test_audio.py` are sub-10-seconds per slice-8
report.

**[recommendation]** No tooling change to gate composition. The
staged-validation rule (WORKFLOW §16) already prescribes focused
tests. `tools/affected_tests.py` removes the "what-is-the-focused-
command" friction.

### 7. Closure / handoff

**[observed]** Closure worker packages
`handoff/orchestrator-handoff-slice-<NEXT>.zip` containing 6
governance files + 7 ADRs + `tasks/<NEXT>.md` +
`tasks/<PREV>.report.md` + MANIFEST + git-log + main-gate. Slice-8
zip: 475 KB; ADRs account for ~330 KB uncompressed.

**[recommendation]** No change. The duplication is intentional for
the offline-fallback case (WORKFLOW §10). Sub-1 MB at current ADR
count is acceptable. **DEFER** a smaller ZIP using `MODULES.toml` in
place of ADRs — only revisit if ADR count or single-ADR size grows.

---

## Natural Module Boundaries

The 8 `app/*.py` files are natural Python ownership boundaries and
already satisfy AGENTS C2 in spirit. The dependency graph in
"Repository Evidence" shows the edges.

### Domain 1 — Resolution / dictionary / render / examples (read-only core)

- **Owned paths:** `app/resolve.py` (3,579 tokens), `app/dictionary.py`
  (7,283), `app/render.py` (4,961), `app/examples.py` (1,741).
- **Public interfaces:** `app.resolve.resolve_word`, `resolve_token`,
  `LookupProtocol`, `LemmaRecord`, `SenseRecord`;
  `app.dictionary.Dictionary`, `DictionaryAsset`, `DictionaryRuntime`,
  `validate_candidate_dictionary`; `app.render.render_card`,
  `CardRenderInput`, `RenderLemmaData`; `app.examples.rank_examples`,
  `ExampleScore`.
- **Direct dependencies:** `app.dictionary` imports `app.resolve`;
  `app.render` imports `app.dictionary` (types only per its
  docstring). `app.resolve`, `app/examples` import nothing from `app/`.
- **Owning tests:** `test_resolve.py` (25), `test_resolve_spacy.py`
  (1), `test_dictionary.py` (42), `test_render.py` (27),
  `test_examples.py` (7).
- **Why useful to an LLM worker:** pure / no-DB core; reading only
  this domain yields all deterministic transformations without I/O.

### Domain 2 — HTTP / API surface (single factory, 19 `/vocab` routes)

- **Owned paths:** `app/api.py` (25,357 tokens).
- **Public interface:** `create_app` factory (per AGENTS C1).
- **Direct dependencies:** imports every other `app/` module
  (`audio`, `deck`, `dictionary`, `examples`, `export`, `render`,
  `resolve`).
- **Owning tests:** `test_api.py` (19), `test_capture.py` (11),
  `test_smoke_baseline.py` (1).
- **Why useful to an LLM worker:** every domain above this layer
  touches HTTP concerns. The largest single source file. Reading it
  is unavoidable for HTTP work; isolating it lets other workers
  ignore it.

### Domain 3 — Deck / review (user-state; FSRS authority)

- **Owned paths:** `app/deck.py` (18,613 tokens).
- **Public interfaces:** `create_deck`, `create_note`,
  `add_note_to_deck`, `delete_deck`, `set_meaning_languages`,
  `set_user_meaning`, `delete_user_meaning`,
  `selected_meaning_languages`, `resolved_meanings`, `meaning_state`,
  `review`, `DictionaryRuntime`, `confidence_to_rating`.
- **Direct dependencies:** `app.dictionary` (for `DictionaryAsset`,
  `DictionaryAssetError`, `validate_candidate_dictionary`), plus
  `fsrs`.
- **Owning tests:** `test_deck.py` (10); indirect coverage from
  `test_api.py`.
- **Why useful to an LLM worker:** FSRS scheduling authority lives
  here; R6 (`review_log` append-only) enforced by `check_agents.py`
  plus `test_check_agents.py`. A worker changing confidence → rating
  mapping reads `app/deck.py` + `tests/test_deck.py`; nothing else.
- **Coupling note:** tightly coupled to
  `app.dictionary.DictionaryRuntime` (ADR-0004 D47).

### Domain 4 — Audio (format validation / cache / custom records)

- **Owned paths:** `app/audio.py` (9,089 tokens).
- **Public interfaces:** `validate_audio_bytes`,
  `evaluate_human_audio_policy`, `save_custom_pronunciation`,
  `revert_custom_pronunciation`, `get_custom_pronunciation`,
  `cleanup_orphaned_custom_media`, `AudioCacheManager`,
  `select_pronunciation_audio`, exception hierarchy.
- **Direct dependencies:** none from `app/`.
- **Owning tests:** `test_audio.py` (21).

### Domain 5 — Export (Anki APKG boundary)

- **Owned paths:** `app/export.py` (2,070 tokens).
- **Public interfaces:** `ExportAudio`, `build_apkg`, `stable_guid`.
- **Direct dependencies:** `app.render` (types only), plus `genanki`.
- **Owning tests:** `test_export.py` (3).

### Domain 6 — Build-time tooling

- **Owned paths:** `tools/build_dict.py` (64,327 tokens),
  `tools/gate2_coverage.py` (2,435), `tools/check_agents.py` (6,667),
  `tools/resolver_hash.py` (426).
- **Owning tests:** `test_build_dict_stage01.py`–`stage05.py` (231),
  `test_check_agents.py` (40), `test_gate2_coverage.py` (37),
  `test_container.py` (1).
- **Why useful to an LLM worker:** these tools run only during
  offline dictionary builds, never at runtime. A runtime-app slice
  never reads `tools/build_dict.py`.

### Domain 7 — Frontend shell (single root Lit element)

- **Owned paths:** `frontend/src/app.ts` (20,146 tokens),
  `frontend/src/main.ts`.
- **Owning tests:** `frontend/tests/e2e/product.spec.ts` (4
  scenarios).
- **Coupling note:** slice-8 froze this in `tasks/slice-8.md`
  "Frozen frontend and ownership rules". Splitting it is **DEFER /
  REJECT**.

### Domain 8 — Frontend API client (typed /vocab fetch)

- **Owned paths:** `frontend/src/api/client.ts` (2,885),
  `frontend/src/api/types.ts` (1,721), `frontend/src/api/errors.ts`
  (691), `frontend/src/api/index.ts` (21).
- **Public interfaces:** `VocabClient`, `createVocabClient`,
  `ApiError`, `parseApiError`, plus every typed request/response in
  `types.ts`.
- **Owning tests:** `frontend/src/api/client.test.ts` (25 unit tests).

### High-context files (large ≠ bad boundary)

| File | ~Tokens | Boundary assessment |
|---|---:|---|
| `tools/build_dict.py` | 64,327 | single offline CLI; bad boundary only if a runtime worker reads it |
| `tests/test_build_dict_stage04.py` | 51,753 | test density; only relevant to build-dict changes |
| `tasks/slice-6.report.md` | 44,098 | historical artifact, frozen; not a current worker read |
| `app/api.py` | 25,357 | single factory body; slice-8 S8A `_manage_transaction=False` choreography depends on it being one file |
| `frontend/src/app.ts` | 20,146 | single root Lit element; slice-8 froze the design |
| `app/deck.py` | 18,613 | only FSRS authority; coupled to D47 runtime |

**Large file ≠ bad module boundary.** None of these files require
splitting on architectural grounds; their token cost is addressed by
the path → focused-test resolver (Domain / Affected Validation
Strategy).

### Areas that should NOT be split

- **`app/resolve.py`** (AGENTS R2 single resolver).
- **`tools/check_agents.py`** (R1/R3/R6/R7/R12/R13 gate enforcement).
- **`app/render.py`** (pure-function display renderer; 4,961 tokens).
- **Root `AGENTS.md`** (cross-cutting prohibitions + governance).
- **`frontend/src/app.ts`** (per slice-8 frozen design).
- **`app/api.py`** (refactoring purely on file length is rejected —
  see "Rejected or Deferred Options").

---

## Proposed Context Architecture

Workers should read:

```
global invariants (root AGENTS.md unchanged)
+
task brief (tasks/<ID>.md with the new Required reading: field)
+
relevant app module(s) per MODULES.toml row(s) for the touched paths
+
relevant tests (per MODULES.toml)
+
explicit ADR subset per the Required reading: list
```

instead of the current "read the whole repo" model.

### Option A — `MODULES.toml` (canonical machine-readable module map)

- **File:** `MODULES.toml` at repo root.
- **Format:** TOML, parsed by Python 3.12 stdlib `tomllib`. No new
  dependency. Human-readable. Deterministic. Easy to validate.
- **Encoding (minimum):** per module — `id`, `owned_paths` (globs),
  `dependencies` (module ids), `focused_tests`, `agents_rules`,
  optional `adrs`.
- **Example shape (illustrative, not a spec):**

```toml
[modules.api]
owned_paths = ["app/api.py"]
dependencies = ["audio", "deck", "dictionary", "examples", "export",
                "render", "resolve"]
focused_tests = ["tests/test_api.py", "tests/test_capture.py",
                 "tests/test_smoke_baseline.py"]
agents_rules = ["R12"]

[modules.audio]
owned_paths = ["app/audio.py"]
dependencies = []
focused_tests = ["tests/test_audio.py"]
agents_rules = []
```

- **Benefit:** single authoritative source consumed by tooling. No
  Markdown parsing.
- **Maintenance cost:** refresh only when boundaries move (every
  several slices).
- **Failure mode / staleness risk:** `MODULES.toml` goes stale if a
  module is added without a row. Mitigation: an executable check
  (BEFORE-SLICE-9 item 7) verifies every `git ls-files` Python module
  has a row, every `focused_tests` path exists, every
  `dependencies` id resolves.
- **Recommendation:** **BEFORE SLICE 9**. The canonical
  machine-readable source.

### Option B — Nested per-domain `AGENTS.md` (SHOULD FOLLOW / EXPERIMENTAL)

- **Files (hypothetical):** `app/AGENTS.md`, `frontend/AGENTS.md`,
  `tools/AGENTS.md`.
- **Benefit:** module-scoped onboarding reduces per-worker
  re-discovery.
- **Failure mode / staleness risk:** nested files can duplicate or
  silently override root rules. Until explicit inheritance /
  duplication rules are defined in root AGENTS.md, these are
  **EXPERIMENTAL**.
- **Recommendation:** **SHOULD FOLLOW**. NOT required BEFORE SLICE 9.

### Option C — `tools/affected_tests.py` (focused-test resolver)

- **File:** `tools/affected_tests.py` (~50 LOC).
- **Consumes:** `MODULES.toml` (NOT `docs/repo-map.md`);
  `git diff --name-only main...HEAD` or a path argument.
- **Algorithm:**

```text
changed_paths = parse(argv or git diff --name-only main...HEAD)
directly_owning_modules = unique([m.id for p in changed_paths
                                   for m in MODULES.modules
                                   if p matches m.owned_paths])
if no module matched a changed path:
    emit("BROAD: pytest -q (no MODULES.toml row for some changed paths)")
    exit 2
# No automatic dependency closure by default. Conservative.
focused = sorted(set(m.focused_tests for m in directly_owning_modules))
emit("pytest -q " + " ".join(focused))
```

- **Conservative fallback:** any unmapped changed path → emit a
  *broad* recommendation (`pytest -q`) and exit non-zero. Never
  silently omit verification.
- **Benefit:** codifies WORKFLOW §16.1 mechanically.
- **Recommendation:** **BEFORE SLICE 9**.

### Option D — `tools/context_pack.py` (task reading-list generator)

- **File:** `tools/context_pack.py` (~80 LOC).
- **Consumes:** `MODULES.toml`; `tasks/<ID>.md` (allowlist + binding
  recital).
- **Emits:** a compact reading list (e.g.
  `handoff/context-<ID>.md`). The committed brief + governance +
  `MODULES.toml` remain authoritative; the pack is an *index*, not
  evidence.
- **Recommendation:** **SHOULD FOLLOW** (not on slice-9 critical
  path).

### Options rejected

- **Auto-AST-generated `MODULES.toml`** — AST cannot guess
  *intended* module ownership (it sees imports, not policy). DEFER
  until the hand-curated file shows sign of churn.
- **`docs/repo-map.md` as the metadata source** — Markdown is not
  parseable as a stable database; tools would need a fragile parser
  that drifts with reformatting. Rejected in favor of TOML.
- **More documentation** — every extra doc is a staleness surface.
  The right move is fewer, more pointed ones (`MODULES.toml` is
  structural, not narrative).

---

## Affected Validation Strategy

WORKFLOW §16 already prescribes focused tests during iteration and one
full `make gate` at candidate-final time. The audit's contribution is
a **mechanical path → focused-test command resolver** that codifies
§16.1 without changing the gate composition.

### Iteration-time focused commands

The naming convention already gives a deterministic mapping (table in
"Current Cost Model" §4). The `MODULES.toml` `focused_tests` column is
the canonical storage. Examples (no new infrastructure needed today):

| Changed paths | Focused pytest | Focused frontend |
|---|---|---|
| `app/audio.py` | `pytest -q tests/test_audio.py` | — |
| `app/deck.py` | `pytest -q tests/test_deck.py` | — |
| `app/dictionary.py` | `pytest -q tests/test_dictionary.py` | — |
| `app/export.py` | `pytest -q tests/test_export.py` | — |
| `app/render.py` | `pytest -q tests/test_render.py` | — |
| `app/resolve.py` | `pytest -q tests/test_resolve.py tests/test_resolve_spacy.py` | — |
| `app/examples.py` | `pytest -q tests/test_examples.py` | — |
| `app/api.py` | `pytest -q tests/test_api.py tests/test_capture.py tests/test_smoke_baseline.py` | — |
| `tools/build_dict.py` | `pytest -q tests/test_build_dict_stage01.py tests/test_build_dict_stage02.py tests/test_build_dict_stage03.py tests/test_build_dict_stage04.py tests/test_build_dict_stage05.py` | — |
| `tools/check_agents.py` | `pytest -q tests/test_check_agents.py` + run `tools/check_agents.py` | — |
| `frontend/src/api/client.ts` | — | `npm test --prefix frontend` |
| `frontend/src/app.ts` | — | `npm run --prefix frontend typecheck` + Playwright |
| `Dockerfile` | `pytest -q tests/test_container.py` | — |
| `reference/schema.sql` | `pytest -q tests/test_smoke_baseline.py` + manual smoke | — |

### Final-candidate validation (unchanged)

**Unchanged.** Per WORKFLOW §16.2 / §16.4: one full `make gate`
Python: ruff + mypy --strict on 35 source files + 691 pytest +
check_agents) plus slice-specific frontend (`npm ci`, `npm run
--prefix frontend typecheck`, `npm test`, `npm run build`) plus
Playwright (4 scenarios against the FastAPI-served compiled
product). **No reduction permitted.**

### Tooling summary

| Tool | Verdict |
|---|---|
| `Make + pytest/npm` (current) | **keep** |
| `tools/affected_tests.py` (~50 LOC) consuming `MODULES.toml` | **BEFORE SLICE 9** |
| `pytest -xdist` | DEFER (reduces wall-clock, not LLM context) |
| pytest markers / `-k` filters | DEFER (naming convention already groups by domain) |
| Pants / Bazel / Nx / Turborepo | **REJECT** |
| Auto-AST `MODULES.toml` generation | DEFER |
| `docs/repo-map.md` as machine-readable metadata | **REJECT** |
| Multi-repo split | **REJECT** |

---

## Reviewer Context Strategy

### What a reviewer MUST independently inspect

- **The full diff.** Per WORKFLOW §6 + PROMPTS §Risk-label review —
  the one exception to "reviewer-never-reads-the-diff". The reviewer
  verifies idempotency, partial-failure states, rollback safety, and
  divergence between what the report claims and what the diff does.
- **AGENTS R-rules** that the diff touches (path-lookup per WORKFLOW
  §6). Short, executable checklist per `tools/check_agents.py`, not a
  re-read of AGENTS.md.
- **ADR IDs cited in the slice brief.** The brief's "Binding product
  contract" recital lists them; the reviewer reads only those ADRs,
  not all 7.

### What generated context may provide (an INDEX, not evidence)

- A reviewer-context pack emitted by `tools/context_pack.py` listing
  the touched modules per `MODULES.toml`, their owning tests, and the
  ADR subset. **The pack is an index; it is not authoritative
  evidence.**
- The MANIFEST.md pattern (already exists at handoff time) records
  what passed at gate time; the reviewer trusts the prior gate per
  §16.4.

### Authority split (binding; from WORKFLOW §0 / G8)

- **Local checkout remains authoritative for fresh gate/runtime facts.**
- **Private GitHub mirror remains authoritative for pushed committed state.**
- **Generated context is an index** — it points to evidence but does
  not substitute for it. The reviewer re-runs the gate (or trusts the
  prior gate per §16.4) and reads the diff directly from GitHub.

### What a reviewer should NOT re-read

- The entire `WORKFLOW.md` (they have it from session-open).
- The full ADR corpus (the slice brief recites the binding IDs).
- Other slices's briefs/reports unless the diff cross-references them.
- `tools/build_dict.py` (64,327 tokens) unless the diff touches it.
- `tasks/slice-6.report.md` (44,098 tokens; historical artifact).

---

## Monorepo Decision

**Stay monorepo.** One repository, three sub-trees (`app/`,
`frontend/`, `tools/`) co-located in one working tree. Reasons
(observed):

- The repo's growth is governance-bound (~117k tokens of governance +
  ADRs vs ~73k tokens of app source). Splitting the repo does not
  shrink the docs.
- The ADR corpus is cross-cutting by design (ADR-0002 governs the
  standalone↔lecture split; ADR-0004 governs the meanings
  contract). Splitting ADRs across repos would re-create the
  integration boundary ADR-0002 §7 prevents.
- Single gate, single handoff ZIP, single governance corpus, single
  dependency graph. AGENTS R7 (zero lecture coupling) is enforced at
  the Python-import level; nothing about a multi-repo split would
  help.
- `tools/check_agents.py` reads `app/` imports; a repo split would
  require duplicating it.

The current monorepo threshold is not crossed: 100 tracked files,
~73k tokens of app source, ~3.5 min full-gate wall-clock. The audit
also recommends **no package explosion** within the monorepo — the
`app/*.py` files are already natural boundaries and the dependency
graph is already one-way per C2 (with sibling-edge caveats noted in
"Repository Evidence").

---

## Tooling Evaluation

Already covered in "Affected Validation Strategy" and "Monorepo
Decision". Summary:

| Tool | Verdict |
|---|---|
| `Make + pytest/npm` | keep |
| `MODULES.toml` + `tools/affected_tests.py` (~50 LOC) | **BEFORE SLICE 9** |
| `tools/context_pack.py` (~80 LOC) | **SHOULD FOLLOW** |
| `pytest -xdist` | DEFER |
| pytest markers | DEFER |
| Auto-AST `MODULES.toml` generation | DEFER |
| Generated `docs/repo-map.md` from `MODULES.toml` | SHOULD FOLLOW (or never) |
| Nested per-domain `AGENTS.md` | SHOULD FOLLOW (after inheritance rules) |
| Pants / Bazel / Nx / Turborepo | REJECT |
| Multi-repo split | REJECT |
| Auto-refactor `app/api.py` for length | REJECT |
| Frontend component split for LLM context | REJECT |
| Python package explosion | REJECT |
| Microservice decomposition | REJECT |

---

## Target Agent Workflow

The current per-slice lifecycle (WORKFLOW §10 / PROMPTS §NEW SLICE OPEN):

```
fresh orchestrator → startup preflight → implementation worker →
review/retries → mechanical closure worker → final main gate →
STATE update → handoff packaging + remote push → next NEW SLICE OPEN
```

The audit's *target* flow adds three context-efficiency steps without
changing the lifecycle's failure-closed guarantees:

```
1. fresh orchestrator (reads GitHub committed state)
2. startup preflight (WORKFLOW §10; unchanged)
3. CONTEXT COMPOSITION: orchestrator drafts tasks/<ID>.md with the new
   `Required reading:` field listing exact governance + ADR + source +
   test files; orchestrator may run tools/context_pack.py (SHOULD
   FOLLOW) to emit a compact reading list — the committed brief +
   governance + MODULES.toml remain authoritative.
4. implementation worker
   a. read AGENTS.md (root, ~5k tokens) — unchanged
   b. read tasks/<ID>.md (including the Required reading: field)
      and tasks/<PREV-ID>.report.md
   c. read the app/<module>.py and tests/test_<module>.py listed by
      MODULES.toml row(s) for the touched paths
   d. read ONLY the ADRs listed in the brief's Required reading: —
      not all 7
   e. SKIP everything else
5. focused validation (WORKFLOW §16.1; tools/affected_tests.py outputs
   the command)
6. orchestrator review/retries (unchanged)
7. closure worker (unchanged; per WORKFLOW §11)
8. final main gate (unchanged; per WORKFLOW §16.2 / §16.4)
9. STATE update + handoff + remote push (unchanged)
10. next NEW SLICE OPEN (unchanged)
```

Static metadata: `MODULES.toml`, root `AGENTS.md`. Generated
metadata: `handoff/context-<ID>.md` (SHOULD FOLLOW). LLM-authored:
orchestrator startup reasoning, worker implementation,
orchestrator-authored STATE.md at closure, brief + binding recital.
T1-mechanical: closure worker.

---

## Recommended Implementation Sequence

Three buckets. **No item appears in two buckets.**

### BEFORE SLICE 9 (small, zero product code)

A dedicated efficiency/governance implementation session before
slice-9 dispatch lands:

1. **`MODULES.toml`** at repo root — canonical machine-readable
   module map (Option A). TOML; consumed by Python 3.12 stdlib
   `tomllib`. Encoding: `id`, `owned_paths`, `dependencies`,
   `focused_tests`, `agents_rules`, optional `adrs`.
2. **`docs/repo-map.md`** — either generated from `MODULES.toml`
   (SHOULD FOLLOW path) or omitted. If shipped now, it MUST be
   non-authoritative and MUST NOT be parsed by tooling. Tools only
   consume `MODULES.toml`.
3. **`WORKFLOW.md §2` brief schema** — add `Required reading:` field
   that explicitly enumerates the file list a worker loads on cold
   start. (~5 LOC amendment.)
4. **`PROMPTS.md`** worker / risk-label-review prompts — use the
   explicit `Required reading:` list. The risk-label-review prompt
   may add an optional reviewer-context-pack reference. (~5 LOC
   amendment total.)
5. **`tools/affected_tests.py`** (~50 LOC) — consumes `MODULES.toml`
   plus `git diff --name-only main...HEAD`; conservative fallback to
   broad-recommendation on unmapped paths. (Algorithm in Option C.)
6. **Executable validation that `MODULES.toml` is internally valid**
   — `tools/check_modules.py` (or extend `tools/check_agents.py`)
   verifies every Python module under `app/`, `tools/` has a
   `MODULES.toml` row; every `focused_tests` path exists on disk;
   every referenced `dependencies` id exists.
8. **Focused tests for the resolver itself** —
   `tests/test_affected_tests.py` exercising the conservative
   fallback, the unmapped-path behavior, and a happy-path diff.

This BEFORE-SLICE-9 package is a small infrastructure/governance
change, not a product slice. It MUST NOT alter the final-full-gate
requirement.

---

## Rejected or Deferred Options

Recorded separately from "Recommended Implementation Sequence" so a
reader can audit what was *not* chosen.

| Option | Reason | Evidence |
|---|---|---|
| Pants | current scale not justified | 100 tracked files; ~3.5 min full-gate wall-clock; staged-validation (WORKFLOW §16) already formalizes focused-vs-final |
| Bazel | current scale not justified | same as Pants; BUILD files add more LLM context per slice than the savings |
| Nx | no JS monorepo | single frontend (`frontend/`); no pipeline |
| Turborepo | no JS monorepo | same as Nx |
| Multi-repo split | cross-cutting governance / ADRs | ADR corpus is binding across sub-trees; triples per-session discovery cost |
| Python package explosion | already natural boundaries | 1:1 test ownership already works; `app/*.py` are not coupled in either direction |
| Frontend component split for LLM context | slice-8 froze the design | `tasks/slice-8.md` "Frozen frontend and ownership rules" |
| Auto-refactor `app/api.py` for length | cohesive single factory | slice-8 S8A `_manage_transaction=False` choreography depends on it being one file |
| Microservice decomposition | zero lecture-app coupling | AGENTS R7 forbids; ADR-0002 §7 governs compose |
| Auto-AST `MODULES.toml` | cannot guess intended ownership | AST sees edges, not semantic roles |
| Smaller handoff ZIP using `MODULES.toml` | sub-1 MB acceptable | current ZIP 72–475 KB; intentional offline fallback (WORKFLOW §10) |
| Root `AGENTS.md` reduction as prerequisite | cross-cutting binding rules | root rules (R1/R3/R6/R7/R12/R13) bind every worker; shrink is separate governance |
| Nested `app/AGENTS.md` etc. BEFORE SLICE 9 | duplication risk | until inheritance / override rules are defined in root, nested files can silently override |
| `pytest -xdist` | irrelevant for LLM context | only reduces wall-clock; not a token lever |

---

## Risks and Staleness Controls

### Risks of the audit's recommendations

1. **`MODULES.toml` staleness.** Mitigation: BEFORE-SLICE-9 item 6
   (`tools/check_modules.py` / extended `tools/check_agents.py`)
   verifies every Python module has a row, every `focused_tests`
   path exists, every `dependencies` id resolves.
2. **`tools/affected_tests.py` misclassification.** Conservative
   fallback (BROAD on unmapped paths) ensures verification is never
   silently omitted; it is loud rather than quiet.
3. **WORKFLOW / PROMPTS amendment requires care.** Per WORKFLOW §0 /
   §10 the brief schema and prompts are binding. Adding a
   `Required reading:` field is non-breaking (additive); no existing
   slice brief is invalidated.
4. **Per-slice "Reviewer notes" overhead** (SHOULD FOLLOW).
   Mitigation: keep short; gate on risk-labeled slices only.
5. **Generated `docs/repo-map.md` drift.** Mitigation: regenerate on
   every slice closure; tools MUST NOT parse it.

### Staleness controls

- **`MODULES.toml`** is committed and reviewed per slice closure;
  any new module requires a row before its owning slice is accepted.
- **Root `AGENTS.md`** remains binding per WORKFLOW §0; the audit
  does not propose reducing it.
- **`PROMPTS.md`** amendment is per PROMPTS §CLOSE (non-slice)
  workflow; no ADR-level change.

### Risks NOT taken by this audit (per the brief)

- No modularization of source code.
- No modification of source code, tests, or governance (the WORKFLOW
  / PROMPTS amendments recommended here are explicitly OUT of audit
  scope; they are governance work owned by a separate non-slice
  session, not implemented by this audit).
- No new or edited ADRs.
- No slice-9 dispatch.
- No inspection of the lecture-app repository.

---

## Evidence Commands

All evidence above is reproducible from the audit base
`17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5` using the commands below.
None modify the working tree.

### Single token-estimate method (the only method used)

```sh
python3 -c "
import os
total = 0
for root, _, files in os.walk('.'):
    if any(p in root for p in ('.git','.venv','node_modules',
                              '.pytest_cache','.mypy_cache',
                              '.ruff_cache','frontend/test-results')):
        continue
    for f in files:
        p = os.path.join(root, f)
        if not os.path.isfile(p):
            continue
        try:
            total += len(open(p, 'rb').read().decode('utf-8', errors='replace'))
        except Exception:
            pass
print(f'{total} chars; approx_tokens = {total // 4}')
"
```

Per-area variants substitute the starting directory. Lockfiles
(`frontend/package-lock.json`) and binary content are excluded by
hand when the method is meaningless for them.

### File / line counts

```sh
git ls-files | wc -l                                      # 101
git ls-files | xargs wc -l                                # 58,519 lines
```

### Per-area budgets

```sh
python3 -c "
import os
for d in ['app','tests','tools','reference','frontend/src','frontend/tests']:
    chars = 0
    files = 0
    for root, _, fs in os.walk(d):
        for f in fs:
            chars += len(open(os.path.join(root,f),'rb').read()
                         .decode('utf-8', errors='replace'))
            files += 1
    print(f'{d:15s}  files={files:>3d}  chars={chars:>9,d}  ~tokens={chars//4:>6,d}')
"
```

### Test inventory

```sh
python3 -c "
import ast, os
n = 0
for root, _, files in os.walk('tests'):
    for f in files:
        if f.startswith('test_') and f.endswith('.py'):
            with open(os.path.join(root, f)) as fh:
                for node in ast.walk(ast.parse(fh.read())):
                    if (isinstance(node, ast.FunctionDef)
                        and node.name.startswith('test_')):
                        n += 1
print(n)                                                   # 476
"
```

### Intra-app import graph (AST)

```sh
python3 -c "
import ast, os
for f in sorted(os.listdir('app')):
    if not f.endswith('.py'): continue
    deps = sorted({n.module for n in ast.walk(ast.parse(open(f'app/{f}').read()))
                   if isinstance(n, ast.ImportFrom) and n.module
                   and n.module.startswith('app')})
    print(f'{f:25s} -> {deps}')
"
```

### Governance / ADR sizes

```sh
python3 -c "
import os, glob
for p in (['WORKFLOW.md','AGENTS.md','PROMPTS.md','STATE.md',
           'docs/plan.md','docs/backlog.md']
          + sorted(glob.glob('docs/adr/*.md'))):
    c = len(open(p,'rb').read().decode('utf-8', errors='replace'))
    print(f'{p:50s} {c:>7,d} chars  ~{c//4:>5,d} tokens')
"
```

### AGENTS executable vs reviewed rules

```sh
grep -c '\[executable\]' AGENTS.md                          # 7
grep -c '\[reviewed\]' AGENTS.md                            # 14
```

### Endpoint inventory

```sh
grep -nE '@app\.(get|post|put|delete|patch)\(\"/vocab' app/api.py | wc -l   # 19
```

### Handoff / closure evidence

```sh
cat handoff/MANIFEST.md
grep -E "passed|Success|checks" handoff/main-gate.stdout
python3 -c "
import zipfile
with zipfile.ZipFile('handoff/orchestrator-handoff-slice-8.zip') as z:
    for n in sorted(z.namelist()): print(n)
"
```

### Path → focused-test mapping (the proposed `MODULES.toml` data source)

```sh
python3 -c "
import ast, os
groups = {
    'runtime-api':  ['tests/test_api.py','tests/test_capture.py','tests/test_smoke_baseline.py'],
    'audio':        ['tests/test_audio.py'],
    'deck':         ['tests/test_deck.py'],
    'dictionary':   ['tests/test_dictionary.py'],
    'render':       ['tests/test_render.py'],
    'resolve':      ['tests/test_resolve.py','tests/test_resolve_spacy.py'],
    'export':       ['tests/test_export.py'],
    'examples':     ['tests/test_examples.py'],
    'build_dict':   ['tests/test_build_dict_stage01.py',
                     'tests/test_build_dict_stage02.py',
                     'tests/test_build_dict_stage03.py',
                     'tests/test_build_dict_stage04.py',
                     'tests/test_build_dict_stage05.py'],
    'governance':   ['tests/test_check_agents.py','tests/test_gate2_coverage.py',
                     'tests/test_container.py'],
}
data = {}
for root, _, files in os.walk('tests'):
    for f in files:
        if f.startswith('test_') and f.endswith('.py'):
            p = os.path.join(root, f)
            data[p] = sum(1 for n in ast.walk(ast.parse(open(p).read()))
                          if isinstance(n, ast.FunctionDef)
                          and n.name.startswith('test_'))
for g, names in groups.items():
    print(g, sum(data.get(f, 0) for f in names))
"
```

(All commands run against audit base
`17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5`; no working tree mutation.)