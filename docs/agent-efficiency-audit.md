# Agent and Repository Efficiency Audit

**Repository:** `/home/saber/projects/flashcard`
**Audit base main HEAD:** `17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5`
**Audit branch:** `audit/agent-efficiency` (created from base main, no commits yet at write time)
**Audit date:** 2026-09-01
**Scope:** evidence-only audit. No code, tests, governance, or ADRs were modified.
**Brief:** identify the smallest architecture/tooling changes that would materially
reduce LLM context/token consumption, repeated repository rediscovery, broad worker
context, unnecessary test/gate execution, reviewer re-reading, and pre–lecture-app
scaling cost.

---

## Executive Decision

The repository is already structurally efficient — the `app/` module graph is
cleanly one-way per AGENTS C2 (`api → deck → render → dictionary → resolve`),
every app module has a same-name test file, and the staged-validation rule
(WORKFLOW §16) already formalizes focused-vs-final validation. The audit's
**top recommendation** is therefore not a refactor of code or a heavy build
system; it is a **context-pack layer** that turns the current "read the whole
repo" worker model into a "read the brief, the relevant module's
`AGENTS.md`, the relevant tests, and the owning slice's evidence" model:

1. **Add a `docs/repo-map.md` (committed, hand-curated, ~80 lines)** that lists
   every module's owned paths, public surface, owning tests, and coupling
   contract — produced once, refreshed only when boundaries move.
2. **Add nested per-domain `AGENTS.md` files** at `app/AGENTS.md`,
   `frontend/AGENTS.md`, `tools/AGENTS.md` carrying only module-scoped rules,
   constraints, and reading order. Root `AGENTS.md` is reduced to a thin
   pointer plus the cross-cutting prohibitions and governance that apply
   everywhere.
3. **Add a tiny `tools/affected_tests.py`** (~50 LOC) that maps a `git diff
   --name-only main...HEAD` glob against the module→test table in
   `docs/repo-map.md` and emits the focused-test command. Workers continue
   to run `make gate` exactly once at candidate-final time (WORKFLOW §16.2,
   §16.4).
4. **Slice-9-specific gating in `PROMPTS.md` `NEW SLICE OPEN`** that pre-declares
   which ADRs and slice briefs the slice-9 worker MUST read (it does not need
   to re-read ADR-0006 / ADR-0007 / `tasks/slice-6.report.md`); the slice
   brief itself names the file list.

Heavy build systems (Pants, Bazel, Nx, Turborepo) and repository split are
**REJECTED** at the current 100-file, 7,565-LOC scale — they would add more
context than they remove.

Before slice-9: ship only items 1 + 4 (the docs and PROMPTS amendments, both
zero code cost, both additively cheap). Items 2 and 3 are small follow-ons
that can be bundled into the slice-9 implementation allowlist if desired, but
**must not delay dispatch**.

---

## Repository Evidence

All counts come from `git ls-files` on the audit base. All file sizes are
`wc -l` from the same base. Token estimates are `len(chars) // 4` — a coarse
upper bound for English markdown / code; not measured.

### File counts (observed)

- Tracked files: **100**.
- Top-level layout: 26 in `tasks/`, 22 in `tests/`, 17 in `frontend/`, 9 in
  `app/`, 9 in `docs/`, 4 in `tools/`, 2 in `reference/`. One each of
  `WORKFLOW.md`, `PROMPTS.md`, `STATE.md`, `AGENTS.md`, `pyproject.toml`,
  `Makefile`, `Dockerfile`, `README.md`, `.gitignore`, `.dockerignore`.
- `app/` contains 9 Python modules. `frontend/src/` contains 8 TypeScript
  files plus 1 CSS file. `tests/` contains 21 `test_*.py` files plus 1
  `conftest.py` and 2 small fixture JSONLs.

### Lines of code (observed)

| Area | Lines | ~Tokens |
|---|---:|---:|
| `app/` (Python) | 7,565 | ~19,000 |
| `tests/` (Python) | 16,710 | ~42,000 |
| `tools/` (Python) | 7,040 | ~18,000 |
| `reference/` (schema + smoke) | 625 | ~1,600 |
| `frontend/src/` (TS + CSS) | 3,052 | ~7,600 |
| `frontend/tests/e2e/` | 452 | ~1,100 |
| `frontend/` other (lockfile etc.) | 1,438 | ~3,600 |
| Governance: WORKFLOW + AGENTS + PROMPTS + STATE + plan + backlog | 2,357 | ~32,000 |
| 7 ADRs (`docs/adr/0001..0007.md`) | 5,184 | ~82,000 |
| Slice briefs (`tasks/slice-*.md`) | 12,478 | ~31,000 |
| Slice reports (`tasks/*.report.md`) | 4,643 | ~12,000 |
| Handoff dirs (committed evidence + 9 zips) | ~5,300 lines (mostly zip binary) | n/a |
| **Tracked total** | **57,237** | n/a |

The largest single source file is `tools/build_dict.py` at **5,981 lines** —
the offline Stage-01–05 builder that already lives in its own `tools/` namespace
and is never imported by `app/` (R1 enforcement). The largest `app/` file is
`app/api.py` at 2,455 lines. The largest frontend file is
`frontend/src/app.ts` at 1,573 lines (single root Lit element, 137 methods).

### Test ownership (observed, AST)

Total `test_*` functions across `tests/`: **476** (AST count via
`ast.walk(FunctionDef).name.startswith("test_")`). Per-domain counts:

| Domain group | Tests | Files |
|---|---:|---|
| `build_dict` (5 stage files) | 231 | 5 |
| `dictionary` | 42 | 1 |
| `governance` (`check_agents`, `gate2_coverage`, `container`) | 78 | 3 |
| `render` | 27 | 1 |
| `resolve` (+ spacy) | 26 | 2 |
| `runtime-api` (`api` + `capture` + `smoke_baseline`) | 31 | 3 |
| `audio` | 21 | 1 |
| `deck` | 10 | 1 |
| `examples` | 7 | 1 |
| `export` | 3 | 1 |

Inference: the build-dict test suite (231 tests, 48% of the total) is
**orthogonal** to runtime work and would never be affected by a slice that
does not touch `tools/build_dict.py` or `tests/fixtures/wiktextract_*`. A
worker that touched only `app/audio.py` would only need to run
`tests/test_audio.py` (21 tests, sub-10-second) plus R12/R13-affected tests
in `tests/test_api.py`. A worker that touched only `tools/check_agents.py`
would only need `tests/test_check_agents.py` (40 tests).

### Module dependency graph (observed)

Intra-`app/` imports (`grep -E '^from app' app/*.py`):

| Source | Imports from |
|---|---|
| `app/api.py` | `app.audio`, `app.deck`, `app.dictionary`, `app.examples`, `app.export`, `app.render`, `app.resolve` |
| `app/deck.py` | `app.dictionary` |
| `app/dictionary.py` | `app.resolve` |
| `app/export.py` | `app.render` |
| `app/render.py` | `app.dictionary` |
| `app/resolve.py` | (none) |
| `app/audio.py` | (none) |
| `app/examples.py` | (none) |

This is **identical to AGENTS C2's documented direction** (`api → deck →
render → dictionary → resolve`), with `app.audio` and `app.examples`
plugging in at `api` only. No reverse imports observed. No cross-cutting
imports of `app.audio` from `app/deck.py` or `app/render.py` — audio is a
sibling to deck at the API surface only.

### Frontend module layout (observed)

```
frontend/src/
  app.ts          (1573 lines, 1 root Lit element, 137 methods, 50 @state)
  main.ts         (entry: imports app.js + tokens.css)
  api/
    client.ts     (378 lines: typed /vocab fetch client)
    client.test.ts (620 lines: node:test unit)
    errors.ts     (101 lines)
    types.ts      (332 lines)
    index.ts      (3 lines, barrel)
  styles/tokens.css (43 lines, design tokens)
```

Frontend tests:
```
frontend/tests/e2e/
  product.spec.ts (186 lines, 4 Playwright scenarios)
  serve.py        (255 lines, deterministic test server)
  run-server.sh   (11 lines)
```

Inference: the frontend is **two distinct modules**: a thin typed API
client (`frontend/src/api/`, ~830 lines of source + 620 lines of test) and a
single root UI element (`frontend/src/app.ts`, 1,573 lines). The API
client is owned and testable independently; the UI element is monolithic
because Lit web components are leaf-rendered and the product UI is one
shell. There is no implicit "frontend module structure" beyond this; the
current shape is justified by S8B's "frozen frontend and ownership rules"
in `tasks/slice-8.md`.

### Gate composition (observed)

`Makefile` (whole file, 20 lines):

```
gate: ruff mypy pytest check-agents
mypy:        $(MYPY) --strict .
pytest:      $(PYTEST) -q
ruff:        $(RUFF) check .
check-agents:$(PYTHON) tools/check_agents.py
```

`pyproject.toml`:
- Python runtime deps: `fastapi==0.141.1`, `fsrs==6.3.2`, `genanki==0.13.1`,
  `spacy>=3.8.0,<3.9.0`, `uvicorn==0.52.4`, plus the `de_core-news-md`
  spaCy model wheel.
- Python dev deps: `mypy`, `pytest`, `ruff`.
- `[tool.pytest.ini_options].testpaths = ["tests"]`, `pythonpath = ["."]`.

`frontend/package.json`:
- 1 runtime dep (`lit ^3.2.1`).
- 4 dev deps (`@playwright/test`, `@types/node`, `typescript`, `vite`).
- Scripts: `dev`, `build` (`tsc && vite build`), `typecheck`, `test`
  (`node --experimental-strip-types --test src/api/client.test.ts`),
  `test:e2e` (`playwright test`).

`tools/check_agents.py` enforces R1/R3/R6/R7/R12/R13 (6 of the 13
`[executable]`-eligible rules; 7 are `[executable]` per AGENTS — actually 7
executable rules, with 6 currently checked; AGENTS R13 is checked but the
current rules in check_agents cover exactly R1, R3, R6, R7, R12, R13 — the
7th executable rule is implicit via AGENTS conventions).

### Gate timing (observed from committed evidence)

- `handoff/main-gate.stdout` (slice-8 closure): `ruff check .` "All checks
  passed!"; `mypy --strict .` "Success: no issues found in 35 source files";
  `pytest -q` "691 passed, 88 warnings in 210.28s"; `check_agents.py` PASS.
- `tasks/slice-8.report.md`: Playwright 4/4 scenarios pass in 12.8s wall
  clock against the FastAPI-served compiled product.
- Frontend authoritative checks (slice-8): `npm ci` 26 packages in 3s;
  `npm run --prefix frontend typecheck` 0; `npm test --prefix frontend`
  25 pass in ~9.89s; `npm run --prefix frontend build` 431–557 ms.

### Handoff and closure cost (observed)

`handoff/` directory contents at audit base:
- `MANIFEST.md` (33 lines, committed)
- `main-gate.stdout` (54 lines, committed)
- `main-gate.stderr` (committed)
- `git-log.txt` (committed)
- 9 `orchestrator-handoff-slice-N.zip` files ranging 72 KB (slice-1) to
  475 KB (slice-8); slice-9 stub is 190 KB.
- One legacy `slice 3 new.zip` (233 KB).

Contents of one zip (`orchestrator-handoff-slice-8.zip`, 475 KB):
- 6 governance files (WORKFLOW, AGENTS, PROMPTS, STATE, plan, backlog)
- 7 ADRs (totalling ~330 KB uncompressed; ~5,184 lines)
- `tasks/slice-7.report.md` (19 KB) + `tasks/slice-8.md` (11 KB)
- `handoff/MANIFEST.md` + `git-log.txt` + `main-gate.txt`

Inference: the handoff ZIP duplicates **the entire governance + ADR
corpus on every slice closure** (per WORKFLOW §11). This is intentional
for offline fallback (PROMPTS.md §Fall-back startup transport) but
guarantees a growing ZIP per slice as the ADR count grows. ADR-0004 alone
is 75 KB of the slice-8 zip; the seven ADRs together are ~330 KB of the
slice-8 zip's 475 KB.

### Global instruction locations (observed)

Root-level governance (always-loaded):
- `WORKFLOW.md` (837 lines, ~11k tokens)
- `AGENTS.md` (306 lines, ~5k tokens)
- `PROMPTS.md` (762 lines, ~9k tokens)
- `STATE.md` (148 lines, ~2k tokens)
- `docs/plan.md` (176 lines, ~3k tokens)
- `docs/backlog.md` (128 lines, ~2k tokens)

Per-slice instructions:
- `tasks/<ID>.md` — the brief (executable allowlist + acceptance contract)
- `tasks/<ID>.report.md` — the closure-evidence narrative
- `tasks/<ID>.escalation.md` / `<ID>.reference-notes.md` / `<ID>.s2b-*.md` —
  slice-specific auxiliary files (slice-7 alone has 5 such files;
  slice-6's report is 2,823 lines).

There are **no nested AGENTS.md / README / CONTEXT files inside `app/`,
`frontend/`, `tools/`, or `tests/`**. Workers currently have no
module-scoped onboarding material and rely on reading the whole source tree
or the top-level brief alone.

---

## Current Cost Model

Each category below identifies the specific repository evidence that causes
or prevents cost. Categorical labels: **[observed]** = directly counted;
**[inference]** = derived from observed numbers; **[recommendation]** =
proposed change.

### 1. Repository discovery (cold-start cost)

**[observed]** A fresh orchestrator reading the minimum startup material
(`WORKFLOW.md` + `AGENTS.md` + `PROMPTS.md` + `STATE.md` + `docs/plan.md` +
`docs/backlog.md`) consumes **~32k tokens** before reading the slice brief
or any source.

**[observed]** A fresh slice-9 worker that reads the minimum required +
optional supporting material (governance + slice brief + slice-8 report +
all 7 ADRs + all `app/` source + the root Lit element) would absorb
**~277k tokens** if it read everything. This is an upper bound; the
realistic worker budget is the union of slice-brief allowlist + the ADR
IDs cited by that brief.

**[observed]** Per-slice brief length: `tasks/slice-9.md` is 111 lines;
`tasks/slice-8.md` is 415 lines; `tasks/slice-7.md` 722; `tasks/slice-6.md`
958; `tasks/slice-5.md` 1,242; `tasks/slice-4.md` 1,546. The brief itself
contains an architecture narrative and a binding-contract recital of ADR
IDs. The brief is not redundant with the ADRs it cites, but it does
duplicate the cross-references.

**[inference]** The structural reason discovery is expensive: the only
"module index" in the repo is the list of file paths in
`app/`, `tests/`, `frontend/`, `tools/`. There is no per-module
"owned-by, tested-by, depends-on, public-surface" map. A worker
that needs to know "what depends on `app/resolve.py`" must grep.

### 2. Global governance / context reading

**[observed]** WORKFLOW.md is 837 lines (~11k tokens), AGENTS.md is 306
lines, PROMPTS.md is 762 lines. WORKFLOW has 17 top-level sections (§0 –
§16). PROMPTS.md is structurally a sequence of "reusable orchestrator
prompts" each followed by an owner-facing `## Next step` per the §10
chain rule.

**[observed]** No slice or session changes the *governance* layer. The
governance is a fixed corpus, not a per-slice cost. The per-session
rediscovery of governance is wasteful but unavoidable for cold workers
per WORKFLOW §1 ("Workers start cold from a brief").

**[recommendation]** This is a structural ceiling, not a per-session cost.
The efficiency lever here is to ensure the *minimum* governance corpus is
loaded into every worker (it is) and that the *slice-specific* material is
pre-pointed by the brief (mostly already true, but the slice briefs
duplicate the ADR-IDs recital). See "Proposed Context Architecture"
below.

### 3. Implementation context

**[observed]** A slice that touches only `app/audio.py` (992 LOC, 9089
tokens) currently requires reading (per WORKFLOW §14 brief contents):
`AGENTS.md` + `WORKFLOW.md` + `PROMPTS.md` + `STATE.md` + `docs/plan.md`
+ `docs/backlog.md` + the slice brief + every ADR cited by the slice
brief. The audio-relevant ADRs are ADR-0005 (pronunciation) and ADR-0004
(multilingual learner meanings). A focused worker that *only* reads
those two ADRs would read ~30k tokens of ADR text instead of ~82k.

**[inference]** Slice briefs currently embed the ADR ID list ("The
controlling requirements are ADR-0001 §7, §11 and D11/D13/D19; ADR-0002
§4, §5, D24/D25/D27; ...") but do not embed the *resolution* (i.e. "for
this slice, only ADR-0002 and ADR-0005 are normative"). A worker who
treats the recital as exhaustive must read all 7 ADRs to be safe.

**[recommendation]** Slice briefs should gain a `Required reading:`
section that lists the minimum set of files (governance + ADRs + slice
reports + source modules) the worker must load, distinct from the
"Binding product contract" section that lists the *normative* IDs. This
is a 5-line amendment per slice brief and a 2-line amendment to the
brief schema in WORKFLOW §2.

### 4. Test discovery

**[observed]** 476 test functions across 21 test files. The mapping from
`app/<module>.py` → `tests/test_<module>.py` is **already 1:1 for 7 of
the 8 app modules**:

| `app/` file | Owning test file(s) | Tests |
|---|---|---:|
| `app/api.py` | `tests/test_api.py`, `tests/test_capture.py`, `tests/test_smoke_baseline.py` | 31 |
| `app/audio.py` | `tests/test_audio.py` | 21 |
| `app/deck.py` | `tests/test_deck.py` | 10 |
| `app/dictionary.py` | `tests/test_dictionary.py` | 42 |
| `app/examples.py` | `tests/test_examples.py` | 7 |
| `app/export.py` | `tests/test_export.py` | 3 |
| `app/render.py` | `tests/test_render.py` | 27 |
| `app/resolve.py` | `tests/test_resolve.py`, `tests/test_resolve_spacy.py` | 26 |

Plus `tests/test_check_agents.py` (40), `tests/test_gate2_coverage.py`
(37), `tests/test_container.py` (1), and 5 `tests/test_build_dict_stage*.py`
files (231) that cover `tools/build_dict.py` and only run during
build-time testing.

**[inference]** The path→test mapping is **already convention-following
enough that a simple `glob → file` resolver is sufficient**. A worker
that touched only `app/audio.py` knows the focused test is
`tests/test_audio.py` by naming convention. The cost here is *not* test
discovery (the mapping is obvious) but the worker not trusting the
mapping and re-running `pytest -q` on the whole tree anyway. This is
exactly what WORKFLOW §16.1 says not to do; the rule exists precisely
because workers over-validate.

**[recommendation]** Codify the mapping as machine-checkable metadata in
`docs/repo-map.md` (a YAML or markdown table; see Section "Proposed
Context Architecture"). A small `tools/affected_tests.py` reads that
table and the worker's `git diff --name-only` to emit the exact focused
invocation. Total LOC: ~50.

### 5. Test execution

**[observed]** Full gate on slice-8 base: `make gate` ≈ **3:30 wall clock**
(`pytest -q` alone is **210.28s** on 691 tests; ruff + mypy + check_agents
add a few seconds). Playwright against the FastAPI-served compiled
product is **12.8s** for 4 scenarios.

**[observed]** Focused checks (per slice-8 report) like
`pytest -q tests/test_audio.py` take sub-10-seconds. Frontend `npm test`
takes ~9.89s.

**[inference]** Workers that run the full gate after every small edit
(this is what WORKFLOW §16 prohibits) waste **3+ minutes per iteration**.
The slice-8 closure lineage shows the S8C-reclassification, Promise-barrier
repair, and final validation each ran focused checks (1–10s) and only
ran the full gate once at candidate-final. Slice-6 (the largest report
at 2,823 lines) explicitly enumerated several "Subtotal: 64 passed in
7.90s" focused runs.

**[recommendation]** No tooling change. The existing staged-validation
policy is enforced by worker discipline, not by tooling. The
`tools/affected_tests.py` addition (Section 4) reduces the *cost of
finding* the focused invocation but does not change gate composition.

### 6. Review

**[observed]** Slice-8 was risk-labeled `public-api, data-loss`; per
WORKFLOW §6 the T3 reviewer performed a full-diff review of
`main...recovery/s8e-rp20-final-candidate` (18 files, +3009/-148 lines,
recorded in `handoff/MANIFEST.md`). The reviewer is a fresh cold T3
session per PROMPTS §Risk-label review; that session must read the diff,
the slice brief, the slice report, the relevant ADRs, and AGENTS.

**[inference]** The reviewer currently re-discovers the repo from the
slice brief and the risk-label rationale. The MANIFEST already lists the
AGENTS rules and ADR contracts that were checked. A reviewer-context
summary that ships in `tasks/<ID>.report.md` "Reviewer Notes" section
could let the reviewer skip the repo re-discovery and jump to the diff.

**[recommendation]** Slice reports gain an optional "Reviewer notes"
section (the orchestrator authors it at acceptance, like STATE.md). The
section lists: which AGENTS R-rules the diff must satisfy, which ADR
IDs are in scope, the exact changed files, and which tests cover them.
This is a workflow-level change, not a code change, and lives in
PROMPTS.md §Risk-label review.

### 7. Closure

**[observed]** Closure worker per WORKFLOW §11 performs: merge `--no-ff`,
write STATE.md verbatim, run full gate (`make gate` 3:30), package ZIP
(governance + ADRs + slice briefs + slice report + MANIFEST + git-log +
main-gate.txt), validate ZIP, push to origin, push slice branch.

**[inference]** The handoff ZIP duplicates the entire governance + ADR
corpus. As ADRs grow, the ZIP grows monotonically (72 KB at slice-1, 475
KB at slice-8). The cost is local disk + git history, not LLM tokens. The
only LLM-side impact is when a *future* orchestrator falls back to the
ZIP because GitHub is unavailable; in that case they re-read ~330 KB of
ADR text. This is a deliberate offline fallback per WORKFLOW §10.

**[recommendation]** No change. The ZIP cost is bounded (sub-1 MB even at
the current ADR count), is committed only locally (per `.gitignore` the
`handoff/` zips are tracked but the artifact is git-local), and the
fallback case is rare. A future "smaller ZIP" optimization (e.g.
generating a `repo-map.md` once and including that in the ZIP instead of
all 7 ADRs) is **DEFER** — the current size is acceptable.

---

## Natural Module Boundaries

The audit deliberately does not invent boundaries. Each row below is
evidence-supported by the dependency graph in Section "Repository
Evidence" and the test ownership table above.

### Domain 1 — Resolution & Dictionary (read-only core)

- **Owned paths:** `app/resolve.py` (465 LOC), `app/dictionary.py` (726
  LOC), `app/render.py` (599 LOC), `app/examples.py` (212 LOC).
- **Public interfaces (stable):** `app.resolve.resolve_word`,
  `app.resolve.resolve_token`, `LookupProtocol`, `LemmaRecord`,
  `SenseRecord`; `app.dictionary.Dictionary`, `DictionaryAsset`,
  `DictionaryRuntime`; `app.render.render_card`, `CardRenderInput`,
  `RenderLemmaData`; `app.examples.rank_examples`.
- **Direct dependencies:** none of `app/resolve.py`, `app/audio.py`,
  `app/examples.py` import from `app/deck` (zero user-state coupling per
  AGENTS C2). `app/dictionary.py` imports `app.resolve`. `app/render.py`
  imports `app.dictionary` (only types, per its own module docstring).
- **Likely owning tests:** `tests/test_resolve.py` (25),
  `tests/test_resolve_spacy.py` (1, locked Gate 1), `tests/test_dictionary.py`
  (42), `tests/test_render.py` (27), `tests/test_examples.py` (7).
- **Why useful to an LLM worker:** this is the *pure / no-DB* core.
  A worker that reads only this domain's files gets all the deterministic
  transformations, the rendering contract, and the example ranking
  without any I/O.
- **Coupling that prevents isolation:** none at the application layer;
  `app.dictionary` opens `sqlite3.Connection` to a read-only asset, but
  this is via the dependency-injected `LookupProtocol` for tests.

### Domain 2 — Capture / Import / API surface (HTTP)

- **Owned paths:** `app/api.py` (2,455 LOC).
- **Public interfaces:** `create_app`, `BrowserSecurityMiddleware`, and
  the 19 `@app.<verb>` endpoints under `/vocab` (`grep -nE
  "@app\.(get|post|put|delete|patch)\(\"/vocab"` shows 19 routes).
- **Direct dependencies:** `app.audio`, `app.deck`, `app.dictionary`,
  `app.examples`, `app.export`, `app.render`, `app.resolve`, plus
  `fastapi`/`starlette`/stdlib.
- **Likely owning tests:** `tests/test_api.py` (19), `tests/test_capture.py`
  (11), `tests/test_smoke_baseline.py` (1).
- **Why useful to an LLM worker:** every domain above this layer touches
  HTTP concerns. It is the single largest file in the repo. Reading
  `app/api.py` is unavoidable for HTTP work; isolating it lets other
  workers ignore it.
- **Coupling that prevents isolation:** `app/api.py` is the only public
  HTTP surface. A "no-HTTP" worker (e.g. one working on `app/audio.py`
  internal) must still load the routing dispatch to know which path
  endpoints they expose.

### Domain 3 — Deck / Review (user-state mutations)

- **Owned paths:** `app/deck.py` (1,880 LOC).
- **Public interfaces:** `create_deck`, `create_note`, `add_note_to_deck`,
  `delete_deck`, `set_meaning_languages`, `set_user_meaning`,
  `delete_user_meaning`, `selected_meaning_languages`, `resolved_meanings`,
  `meaning_state`, `review`, `DictionaryRuntime`, `confidence_to_rating`.
- **Direct dependencies:** `app.dictionary` (for `DictionaryAsset`,
  `DictionaryAssetError`, `validate_candidate_dictionary`), plus `fsrs`.
- **Likely owning tests:** `tests/test_deck.py` (10). Plus indirect
  coverage from `tests/test_api.py` and `tests/test_capture.py`.
- **Why useful to an LLM worker:** FSRS scheduling authority lives here.
  This is the only place `review_log` mutations happen; R6 executable
  enforces append-only. A worker changing FSRS confidence mapping must
  read `app/deck.py` and `tests/test_deck.py`; nothing else.
- **Coupling that prevents isolation:** `app/deck.py` is tightly coupled
  to `app/dictionary.DictionaryRuntime` (co-owned slice-7 boundary work
  per ADR-0004 D47). A worker touching either must read both.

### Domain 4 — Audio (format validation, cache, custom records)

- **Owned paths:** `app/audio.py` (992 LOC).
- **Public interfaces:** `validate_audio_bytes`, `evaluate_human_audio_policy`,
  `save_custom_pronunciation`, `revert_custom_pronunciation`,
  `get_custom_pronunciation`, `cleanup_orphaned_custom_media`,
  `AudioCacheManager`, `select_pronunciation_audio`, plus exception
  hierarchy `AudioError`/`MediaValidationError`/`CustomAudioError`/
  `ProvenancePolicyError`.
- **Direct dependencies:** none from `app/`. Only stdlib
  (`hashlib`, `sqlite3`, `struct`, `wave`, etc.).
- **Likely owning tests:** `tests/test_audio.py` (21). Plus
  `tests/test_api.py` for the upload/revert HTTP surface.
- **Why useful to an LLM worker:** audio is a sibling domain with zero
  coupling to the deck/render/dictionary core. A worker touching audio
  can ignore the deck module entirely.
- **Coupling that prevents isolation:** none at the application layer.
  Audio's only caller is `app/api.py` (and the test files).

### Domain 5 — Export (Anki APKG boundary)

- **Owned paths:** `app/export.py` (231 LOC).
- **Public interfaces:** `ExportAudio`, `build_apkg`, `stable_guid`.
- **Direct dependencies:** `app.render` (only types), plus `genanki`.
- **Likely owning tests:** `tests/test_export.py` (3).
- **Why useful to an LLM worker:** export is a leaf output format. R10
  enforcement (tab vs comma) and ADR-0005 audio precedence for APKG live
  here. A worker touching APKG must read this domain plus ADR-0010 /
  ADR-0005; nothing else.
- **Coupling that prevents isolation:** none.

### Domain 6 — Build-time tooling (`tools/`)

- **Owned paths:** `tools/build_dict.py` (5,981 LOC),
  `tools/gate2_coverage.py` (312 LOC), `tools/check_agents.py` (694
  LOC), `tools/resolver_hash.py` (53 LOC).
- **Public interfaces:** `tools.build_dict` stage functions (CLI-driven),
  `tools.check_agents.check_all`, `tools.gate2_coverage` CLI,
  `tools.resolver_hash.canonical_resolver_hash`.
- **Direct dependencies:** none from `app/` (R1 enforcement forbids LLM
  imports in `app/`, but `tools/build_dict.py` is permitted to import
  LLM SDKs at stage 04 per AGENTS R1 exception).
- **Likely owning tests:** `tests/test_build_dict_stage01.py` through
  `tests/test_build_dict_stage05.py` (231 tests),
  `tests/test_check_agents.py` (40), `tests/test_gate2_coverage.py` (37),
  `tests/test_container.py` (1).
- **Why useful to an LLM worker:** these tools run only during offline
  dictionary builds, never at runtime. A runtime-app slice (any of
  slice-0 through slice-8) should never need to read `build_dict.py`.
- **Coupling that prevents isolation:** `tools/check_agents.py` reads
  `app/` imports to enforce R1/R7/R13 — a coupling that is intentional
  (it is the gate) but means a worker changing `app/api.py` should also
  re-run `tools/check_agents.py`.

### Domain 7 — Frontend shell (single root Lit element)

- **Owned paths:** `frontend/src/app.ts` (1,573 LOC),
  `frontend/src/main.ts` (entry).
- **Direct dependencies:** `lit`, `frontend/src/api/*`.
- **Likely owning tests:** `frontend/tests/e2e/product.spec.ts` (4
  scenarios), `frontend/src/api/client.test.ts` (25 unit tests on the
  API client, not the UI).
- **Why useful to an LLM worker:** the root Lit element is the only
  stateful UI surface. UI iteration can be isolated to this file plus
  CSS tokens.
- **Coupling that prevents isolation:** `frontend/src/app.ts` is one
  1,573-line element with 137 methods and 50 `@state` properties. There
  is no internal decomposition (no shell / capture / review components).
  Slice-8 froze this design per `tasks/slice-8.md` "Frozen frontend and
  ownership rules". A worker touching the UI must read the whole file
  regardless.

### Domain 8 — Frontend API client (typed /vocab fetch)

- **Owned paths:** `frontend/src/api/client.ts` (378 LOC),
  `frontend/src/api/types.ts` (332 LOC), `frontend/src/api/errors.ts`
  (101 LOC), `frontend/src/api/index.ts` (3 LOC barrel).
- **Public interfaces:** `VocabClient`, `createVocabClient`, `ApiError`,
  `parseApiError`, plus every typed request/response type from
  `frontend/src/api/types.ts`.
- **Direct dependencies:** none from `frontend/src/app.ts` cycle
  (verified by `grep -E "^import" frontend/src/app.ts` — only imports
  `client.ts`, `errors.ts`, `types.ts`).
- **Likely owning tests:** `frontend/src/api/client.test.ts` (25 tests).
- **Why useful to an LLM worker:** this domain is independently testable
  (25 unit tests, ~10s). R12 enforcement (X-Flashcards-Request: 1 header
  + Content-Type: application/json) lives in `client.ts` and can be
  iterated without the UI.
- **Coupling that prevents isolation:** the types in `types.ts` mirror
  the FastAPI `/vocab` response shapes — when `app/api.py` changes a
  response shape, `types.ts` must change too. That coupling is
  intentional and enforced by `tests/test_api.py` ↔ `client.test.ts`
  coverage.

### Areas that should NOT be split

- **`app/resolve.py`** (AGENTS R2): single resolver, exactly one
  implementation. Any split would re-introduce the divergent-resolution
  defect R2 names.
- **`tools/check_agents.py`** (AGENTS R1/R3/R6/R7/R12/R13): the gate
  enforcement code itself is the only authority. Splitting it across
  files would obscure the executable contract.
- **`app/render.py`** (AGENTS C2): pure-function display renderer; its
  monadic split (input dataclass → output dataclass) is already small
  enough (599 LOC) that splitting it would add files without value.
- **Governance `WORKFLOW.md` / `AGENTS.md` / `PROMPTS.md`**: per
  WORKFLOW §0 / §10 these are deliberately one document each; slicing
  them would break the chain rule.

---

## Proposed Context Architecture

Goal: a worker reads

```
global invariants (root AGENTS.md thin pointer + WORKFLOW.md §0/§1/§10/§16)
+
task brief (tasks/<ID>.md)
+
owning module's nested AGENTS.md (app/AGENTS.md or frontend/AGENTS.md)
+
direct dependency interfaces (looked up in docs/repo-map.md)
+
relevant tests (looked up in docs/repo-map.md)
```

instead of reading the entire repo. Each option below has a benefit,
maintenance cost, failure mode, and recommendation.

### Option A — Root `AGENTS.md` + nested per-domain `AGENTS.md`

- **Files added:** `app/AGENTS.md` (~30 lines), `frontend/AGENTS.md`
  (~30 lines), `tools/AGENTS.md` (~20 lines).
- **Benefit:** workers reading for `app/audio.py` work only need to
  load `AGENTS.md` (root, 5k tokens) + `app/AGENTS.md` (~1k tokens)
  instead of the full repo. The root AGENTS.md is reduced to
  cross-cutting prohibitions (R1, R3, R6, R7, R12, R13) + G-rules +
  pointers; the module-scoped AGENTS.md carries module conventions
  (e.g. "audio is zero-coupling", "deck is the only FSRS authority",
  "frontend is single root element with typed API client").
- **Maintenance cost:** ~30 LOC per domain × 3 domains, refreshed only
  when a module boundary or convention changes (every several slices). The
  root AGENTS.md is reduced by the delocalization, not added.
- **Failure mode / staleness risk:** a nested AGENTS.md can become
  contradictory to the root. Mitigation = the root explicitly says "if a
  nested AGENTS.md conflicts with this file, the root wins" (mirroring
  the "AGENTS.md wins over module README" pattern used elsewhere).
- **Recommendation:** **NOW** (small; high token savings; zero code
  change). Bundle into the audit-driven governance amendment (allowed by
  the brief: "Do not modify governance" applies to *unauthorized*
  changes; this audit recommends a governance amendment in the
  "Recommended Implementation Sequence" section below).

### Option B — `docs/repo-map.md` (committed, hand-curated module map)

- **Files added:** `docs/repo-map.md` (~80 lines).
- **Content:** a single markdown table per module with columns
  `Owned paths | Public interfaces | Direct dependencies | Owning tests |
  Coupling note`. Plus a `tests/conftest.py` pointer. Plus the
  build/runtime split.
- **Benefit:** any worker or reviewer that needs to know "what owns
  this, what depends on it, what tests it" reads one ~80-line file
  instead of grepping. Reduces reviewer re-reading.
- **Maintenance cost:** refresh only when boundaries move (boundaries
  move roughly every slice; the file would change 5–15 lines per slice).
  Could be partially generated by `tools/affected_tests.py`.
- **Failure mode / staleness risk:** the map goes stale when paths are
  added without updating the table. Mitigation = add a `make check-repo-map`
  step that greps the path-glob against `git ls-files` and fails if a
  tracked file is not owned by any module.
- **Recommendation:** **NOW** (small; high benefit; zero code change).
  Optionally auto-checked by a `make repo-map` target.

### Option C — Generated repo-map (script emits the table)

- **Files added:** `tools/repo_map.py` (~50 LOC, AST inspection only).
- **Benefit:** the table never goes stale. Adding a new module
  automatically gets a row.
- **Maintenance cost:** the script must be kept compatible with Python
  AST and the project's file conventions; one more tool to maintain.
- **Failure mode / staleness risk:** AST inspection cannot guess
  *intended* module ownership (it sees imports, not policy). It would
  populate the table from observed imports, which is already correct for
  this repo (per the C2 dependency graph), but would not distinguish
  e.g. `app/render.py` from `app/dictionary.py` in terms of which one owns
  the *concept* of "the dictionary asset".
- **Recommendation:** **DEFER**. The repo-map is small and
  hand-curated; automation is not yet justified.

### Option D — Symbol/import map (machine-readable YAML index)

- **Files added:** `docs/repo-map.yaml` (~80 lines) + small loader.
- **Benefit:** programmatically queryable; the affected-test resolver
  (Option F) reads it directly.
- **Maintenance cost:** same as Option B, plus the YAML schema must be
  kept stable.
- **Recommendation:** **NOW** if Option B + F both ship together
  (single file: `docs/repo-map.md` with embedded YAML table is
  sufficient — markdown frontmatter style).

### Option E — Task context-pack generator

- **Files added:** `tools/context_pack.py` (~80 LOC).
- **Function:** reads `tasks/<ID>.md`'s allowlist, the ADR IDs cited,
  the module paths affected, and emits a "context pack" file (either
  pasted into the worker prompt or written to a path the worker
  reads). Reduces the orchestrator's manual composition of "what to
  attach" per slice.
- **Benefit:** removes a per-slice composition step from the
  orchestrator; reduces the orchestrator's per-slice token spend on
  drafting the brief's "Required reading:" list.
- **Maintenance cost:** the script must understand the brief schema
  (WORKFLOW §2) and the path→module table from Option B/D. Two coupled
  tools.
- **Recommendation:** **SHOULD FOLLOW**. Useful but not load-bearing for
  slice-9.

### Option F — Affected-test resolver

- **Files added:** `tools/affected_tests.py` (~50 LOC, AST-light).
- **Function:** reads `git diff --name-only main...HEAD`, classifies each
  path into one or more modules per `docs/repo-map.md`, and emits the
  focused pytest command. Pure mechanical; no AST.
- **Benefit:** reduces the worker's "what tests do I run" discovery
  cost to a single command. Codifies WORKFLOW §16.1.
- **Maintenance cost:** same as Option B/D (it reads the same table).
- **Recommendation:** **NOW** (small; high benefit; complements Option B).

### Option G — More documentation

- **Benefit:** none beyond what Options A + B + F already give.
- **Maintenance cost:** every doc added is a doc that can go stale and
  must be refreshed per slice.
- **Recommendation:** **REJECT**. "More docs" is not a structural fix;
  it is a tax on every reader. The right move is fewer, more pointed
  docs.

---

## Affected Validation Strategy

WORKFLOW §16 already requires focused tests during iteration and a single
full gate at candidate-final. The audit's contribution here is a **path
→ focused-test command resolver** that codifies §16.1 mechanically.

### Iteration-time focused commands

For each `app/<module>.py` change the focused commands are:

| Changed paths | Focused pytest | Focused frontend |
|---|---|---|
| `app/audio.py` | `pytest -q tests/test_audio.py` | — |
| `app/deck.py` | `pytest -q tests/test_deck.py` | — |
| `app/dictionary.py` | `pytest -q tests/test_dictionary.py` | — |
| `app/examples.py` | `pytest -q tests/test_examples.py` | — |
| `app/export.py` | `pytest -q tests/test_export.py` | — |
| `app/render.py` | `pytest -q tests/test_render.py` | — |
| `app/resolve.py` | `pytest -q tests/test_resolve.py tests/test_resolve_spacy.py` | — |
| `app/api.py` | `pytest -q tests/test_api.py tests/test_capture.py tests/test_smoke_baseline.py` | — |
| `tools/build_dict.py` | `pytest -q tests/test_build_dict_stage01.py tests/test_build_dict_stage02.py tests/test_build_dict_stage03.py tests/test_build_dict_stage04.py tests/test_build_dict_stage05.py` | — |
| `tools/check_agents.py` | `pytest -q tests/test_check_agents.py` + run `tools/check_agents.py` | — |
| `frontend/src/api/client.ts` | — | `npm test --prefix frontend` |
| `frontend/src/app.ts` | — | `npm run --prefix frontend typecheck` + Playwright |
| `Dockerfile` | `pytest -q tests/test_container.py` | — |
| `pyproject.toml` (deps only) | `pytest -q` (full Python, no skipping) | `npm ci --prefix frontend` (lockfile refresh) |
| `reference/schema.sql` | `pytest -q tests/test_smoke_baseline.py` + manual smoke | — |

**Implementation: a tiny `tools/affected_tests.py`** reads
`docs/repo-map.md`, accepts a path-glob argument or defaults to
`git diff --name-only main...HEAD`, and emits a shell snippet. No AST. Total
 LOC: ~50. Estimated time saved per iteration: 3+ minutes (from
running the full 210s pytest to running 7–42 tests in 1–10s).

### Final-candidate validation

**Unchanged.** WORKFLOW §16.2 / §16.4 already require one full
`make gate` (Python: ruff + mypy --strict + 691 pytest + check_agents) plus
slice-specific frontend (`npm ci`, `npm test`, `npm run build`,
`tsc --noEmit`) and Playwright (`npm run --prefix frontend test:e2e`).
The audit **does not propose** any reduction of this final validation
— see "Non-negotiables" in WORKFLOW §16.5.

### What an affected-test resolver does NOT replace

- **`make gate`** at candidate-final time. WORKFLOW §16.2 / §16.4 are
  binding.
- **T3 full-diff review** for risk-labeled slices per WORKFLOW §6.
- **Mandatory Playwright** for any slice that touches
  `frontend/src/app.ts` (UI behavior).
- **The `recovery/`-branch lineage** workflow per slice-8.

### Build systems evaluated

| System | Benefit at this size | Setup cost | LLM impact | Recommendation |
|---|---|---|---|---|
| Make + pytest/npm (current) | sufficient; staged-validation already formalizes focused-vs-final | none (zero) | none (zero) | keep |
| Custom `tools/affected_tests.py` (~50 LOC) | codifies §16.1 mechanically | small (~50 LOC) | reduces per-edit full-test runs | **NOW** |
| pytest markers | could group tests by domain | small (~30 LOC config) | minor (markers add words) | DEFER |
| pytest-xdist | parallel pytest runs | small (~10 LOC config) | reduces full-gate wall-clock | DEFER (irrelevant for LLM context) |
| Pants | fine-grained target graph, dep-aware tests | high (full toolchain) | neutral (target refs are names, not paths) | REJECT (overkill) |
| Bazel | same as Pants + hermeretic | high | high (BUILD files in every change) | REJECT (overkill) |
| Nx | JS monorepo aware | high for a single frontend | n/a | REJECT (no JS monorepo) |
| Turborepo | JS pipeline caching | high | n/a | REJECT (single frontend, no pipeline) |

**Inferred principle:** a build system is justified when the cost of
*not* having it exceeds the cost of maintaining it. At 100 tracked files
and ~3.5 minutes full-gate wall-clock, that threshold is not crossed.

---

## Reviewer Context Strategy

A T3 reviewer (per PROMPTS §Risk-label review) is a fresh cold session
that reads `AGENTS.md`, the slice brief, the slice report, and the full
diff. The audit's recommendation distinguishes what a reviewer MUST
independently inspect from what can be provided.

### What the reviewer must independently inspect (mandatory)

- **The full diff.** Per WORKFLOW §6 + PROMPTS §Risk-label review, this
  is the one exception to "reviewer-never-reads-the-diff". The reviewer
  verifies idempotency, partial-failure states, rollback safety, and
  divergence between what the report claims and what the diff does.
- **AGENTS R-rules** that the diff touches (path-lookup per WORKFLOW
  §6). This is a **short, executable** checklist per `tools/check_agents.py`
  — not a re-read of AGENTS.md.
- **ADR IDs cited in the slice brief.** The brief's "Binding product
  contract" recital already lists them. The reviewer verifies the diff
  honors each cited ID.

### What can be provided as generated context (audit-recommended)

- **`docs/repo-map.md` snippet** for the modules touched by the diff.
  Reduces the reviewer's "what does this module do" re-discovery.
- **The slice report's "Reviewer notes" section** (a new optional
  section that the orchestrator authors at acceptance). The section
  lists: changed files, owning tests, AGENTS R-rules to check, ADR IDs
  to verify, expected test evidence.
- **The MANIFEST.md pattern** (already exists at handoff time). The
  MANIFEST records what passed at gate time; the reviewer re-runs the
  gate (or trusts the prior gate per WORKFLOW §16.4) and reads the
  MANIFEST to know what was already checked.
- **`tools/affected_tests.py` output** for the diff — a one-line
  command the reviewer can re-run to confirm test coverage of the diff.

### What the reviewer should NOT re-read

- The entire `WORKFLOW.md` (they already have it from their own
  session-open).
- The full ADR corpus. The slice brief recites the binding IDs; the
  reviewer reads only those ADRs, not all 7 (~82k tokens saved per
  review).
- Other slices' briefs/reports unless the diff cross-references them.
- `tools/build_dict.py` (5,981 LOC) unless the diff touches it.

### Specific reviewer-context text change

PROMPTS.md §Risk-label review currently says the reviewer reads
"AGENTS.md, tasks/<ID>.md, tasks/<ID>.report.md, then the FULL diff".
The audit recommends amending that prompt to add:

```
Also read `docs/repo-map.md` and the orchestrator-authored "Reviewer
notes" section of `tasks/<ID>.report.md`. Do not re-read the entire
ADR corpus; only read the ADRs cited by the slice brief's "Binding
product contract" recital.
```

This is a 3-line amendment to PROMPTS.md, zero code cost.

---

## Monorepo Decision

### Current state

- One private GitHub repository: `/home/saber/projects/flashcard`.
- 100 tracked files, ~57k lines.
- Three conceptually distinct sub-trees (`app/`, `frontend/`,
  `tools/`) co-located in one working tree.
- `Dockerfile` builds the FastAPI service including the Vite-built
  `app/frontend/` bundle.
- All `app/`, `tests/`, `tools/`, `reference/` share the same
  `pyproject.toml`, `Makefile`, `.gitignore`, and `tools/check_agents.py`
  gate.

### Options

| Option | Description | Pros | Cons |
|---|---|---|---|
| **Current monorepo** | one repo, three sub-trees | single gate, single handoff ZIP, single governance corpus, single dependency graph; AGENTS R7 already enforced at the Python-import level | the ADR corpus is re-read in every slice brief's binding-contract recital |
| **Package/module boundaries within the monorepo** | add `app/api/`, `app/deck/`, etc. packages; keep one repo, add per-package `pyproject.toml` | isolates module-level interfaces | adds setup overhead; forces `app/__init__.py` re-exports; the dependency graph is already clean (no real win) |
| **Multiple repositories** | one repo per sub-tree (e.g. `flashcard-app`, `flashcard-frontend`, `flashcard-build`) | smaller per-repo context | forces every worker to load governance + state from N repos; triples the gate; breaks the single-source-of-truth for AGENTS and the ADRs |
| **Future lecture-app integration** | post-slice-9 the lecture-app and flashcard compose over HTTP per ADR-0002 §7 | zero coupling (R7) | already covered by ADR-0002 §7; no repo split required |

### Recommendation: **stay monorepo**.

The repo is at the threshold where a *package* split inside the monorepo
(`app/api/`, `app/deck/`, etc.) would add setup overhead without
isolation benefit. The dependency graph is already one-way per C2; the
*file* boundaries are already the natural module boundaries.

A future repo split would force every orchestrator session to load N
governance + state copies, increasing per-session discovery cost. The
ADRs are cross-cutting by design (ADR-0002 governs the entire
standalone↔lecture split; ADR-0004 governs the entire meanings
contract); splitting them across repos would re-create the integration
boundary ADR-0002 §7 exists to prevent.

**Reject "split because growing"** — the repo's growth (100 files,
~57k lines) is *governance-bound* (the ADR corpus is ~82k tokens,
larger than the app source), not code-bound. The cost is in the docs,
not the code; splitting the repo does not shrink the docs.

---

## Tooling Evaluation

Already covered above in "Affected Validation Strategy" and "Monorepo
Decision". This section summarizes.

| Tool | Status | One-line reason |
|---|---|---|
| `Make + pytest/npm` (current) | **keep** | sufficient; staged-validation already formalizes focused-vs-final |
| Custom `tools/affected_tests.py` (~50 LOC) | **NOW** | codifies §16.1 mechanically; reduces per-iteration full-gate runs |
| Custom `tools/repo_map.py` (auto-generated repo-map) | **DEFER** | hand-curated map sufficient at current size; AST cannot guess *intended* ownership |
| Task context-pack generator (~80 LOC) | **SHOULD FOLLOW** | removes per-slice orchestrator composition overhead |
| pytest markers | **DEFER** | domain-grouping already obvious from naming |
| pytest-xdist | **DEFER** | irrelevant for LLM context; only reduces wall-clock |
| Pants / Bazel / Nx / Turborepo | **REJECT** | overkill at 100 files; each adds more context than it removes |

---

## Target Agent Workflow

The current per-slice lifecycle (per WORKFLOW §10 / PROMPTS §NEW SLICE
OPEN) is:

```
fresh orchestrator → startup preflight → implementation worker →
review/retries → mechanical closure worker → final main gate →
STATE update → handoff packaging + remote push → next NEW SLICE OPEN
```

The audit's *target* flow adds three context-efficiency steps without
changing the lifecycle's failure-closed guarantees:

```
1. fresh orchestrator (reads GitHub committed state)
2. startup preflight (existing; WORKFLOW §10)
3. CONTEXT PACK: orchestrator drafts `tasks/<ID>.md` with new
   `Required reading:` section listing exact governance + ADR + source +
   test files; orchestrator generates `handoff/context-<ID>.md` listing
   touched modules, owning tests, AGENTS R-rules to check, and ADR IDs
   to verify. [AUDIT RECOMMENDATION: small per-slice overhead, large
   per-worker savings.]
4. implementation worker
   a. read AGENTS.md (root, ~5k tokens) → root prohibitions only
   b. read tasks/<ID>.md + tasks/<ID>.report.md of immediate predecessor
   c. read app/AGENTS.md OR frontend/AGENTS.md OR tools/AGENTS.md
      (whichever owns the touched paths)
   d. read docs/repo-map.md (only the touched modules' rows)
   e. read the touched app/<module>.py + the touched tests/test_<module>.py
   f. read the ADRs listed in the brief's "Required reading:" (not all 7)
   g. SKIP everything else
5. focused validation (WORKFLOW §16.1; `tools/affected_tests.py` outputs
   the command)
6. orchestrator review/retries
7. mechanical closure worker (unchanged; per WORKFLOW §11)
8. final main gate (unchanged; per WORKFLOW §11)
9. STATE update + handoff + remote push (unchanged)
10. next NEW SLICE OPEN (unchanged)
```

Steps that are **static metadata** (always committed, refreshed on
boundary change): root AGENTS.md, app/AGENTS.md, frontend/AGENTS.md,
tools/AGENTS.md, docs/repo-map.md.

Steps that are **generated automatically**: `handoff/context-<ID>.md`
(emitted by `tools/context_pack.py`, committed in slice closure).

Steps that are **performed by an LLM**: orchestrator startup reasoning,
worker implementation, orchestrator review (per WORKFLOW §6 risk
review), orchestrator-authored STATE.md at closure.

Steps that are **performed by T1 mechanics** (unchanged from today):
the closure worker's merge + final gate + ZIP packaging + push.

---

## Recommended Implementation Sequence

Three buckets, with effort estimates. Per the brief, **no
recommendation is implemented in this audit**.

### NOW — small, zero-code, can ship before slice-9

| # | Change | Effort | Effect |
|---|---|---|---|
| 1 | `docs/repo-map.md` (committed, hand-curated) | tiny (~80 LOC) | single source of "what owns what, what tests it" |
| 2 | Root `AGENTS.md` reduced to thin pointer + cross-cutting R/G rules | small (~50 LOC edit) | reduces mandatory context for every worker |
| 3 | Add nested `app/AGENTS.md`, `frontend/AGENTS.md`, `tools/AGENTS.md` | small (~80 LOC total) | module-scoped onboarding |
| 4 | Amend `PROMPTS.md §NEW SLICE OPEN` and `PROMPTS.md §Risk-label review` to require `docs/repo-map.md` and the per-slice "Reviewer notes" | small (~10 LOC edit) | reduces orchestrator + reviewer per-slice composition |
| 5 | Amend `WORKFLOW.md §2` brief schema to add `Required reading:` field | tiny (~5 LOC) | brief carries the file list |

### SHOULD FOLLOW — small, may bundle with slice-9 implementation

| # | Change | Effort | Effect |
|---|---|---|---|
| 6 | `tools/affected_tests.py` (~50 LOC) | small | codifies WORKFLOW §16.1 mechanically |
| 7 | `tools/context_pack.py` (~80 LOC) | small | removes per-slice orchestrator composition |
| 8 | Convert `[reviewed]` AGENTS R-rules R8/R9/R10 to `[executable]` checks in `tools/check_agents.py` | small | already backlog (docs/backlog.md "Standing") |
| 9 | Author `tasks/adr-0002-donor-notes.md` (per WORKFLOW §12, the slice-9 pre-dispatch prerequisite already named in STATE.md) | tiny | unblocks slice-9 dispatch |

### DEFER / REJECT

| # | Change | Effort | Effect / Reason |
|---|---|---|---|
| 10 | Pants / Bazel / Nx / Turborepo | large | REJECT — overkill at 100 files; each adds more context than it removes |
| 11 | Split into multiple repositories | large | REJECT — ADRs and governance are cross-cutting; triples the per-session discovery cost |
| 12 | Auto-generated `docs/repo-map.md` via `tools/repo_map.py` | small | DEFER — hand-curated sufficient; AST cannot guess *intended* module ownership |
| 13 | `pytest -xdist` parallelization | small | DEFER — irrelevant for LLM context; only reduces wall-clock |
| 14 | pytest markers | small | DEFER — domain-grouping already obvious from naming |
| 15 | Split `app/api.py` (2,455 LOC) into per-endpoint files | medium | REJECT — would re-introduce cross-endpoint atomicity risk (slice-8 S8A depends on `_manage_transaction=False` choreography); the file is large but cohesive |
| 16 | Split `frontend/src/app.ts` (1,573 LOC) into sub-components | medium | REJECT — slice-8 froze the single-root-element design; the cost of splitting now exceeds the benefit |
| 17 | Auto-checked `make repo-map` target | small | DEFER — possible to add later; not load-bearing |
| 18 | Smaller handoff ZIP (skip ADRs in favor of repo-map) | small | DEFER — sub-1 MB at current size; deliberate offline-fallback |

### What must happen BEFORE slice-9 dispatch

Per the slice-9 brief (`tasks/slice-9.md`) and STATE.md, slice-9 has two
named pre-dispatch prerequisites:

1. **`tasks/adr-0002-donor-notes.md`** — read-only donor inspection
   finding per WORKFLOW §12. Not in this audit's recommendations
   (this audit recommends it for slice-9, but it is owned by the slice-9
   orchestrator, not by this audit).
2. **Lecture-app Phase-4 decomposition closed on the lecture side** —
   owned by the lecture-app repository.

This audit's *additional* recommendations that should land before
slice-9 dispatch:

- **Item 1** (`docs/repo-map.md` committed). Tiny; unblocks reviewer
  context savings during slice-9's mandatory risk-label T3 review.
- **Item 4** (PROMPTS.md amendment) and **Item 5** (WORKFLOW.md brief
  schema amendment). Both zero code cost; both reduce orchestrator
  per-slice composition.

Items 2 and 3 (root AGENTS.md reduction + nested AGENTS.md) are small
but may defer to a post-slice-9 governance amendment to avoid
distracting from the compose-level work.

### What can safely wait until later

- Items 6 + 7 (`tools/affected_tests.py`, `tools/context_pack.py`).
  Both are mechanical additions that are useful but not load-bearing for
  slice-9.
- Items 8, 9 (executable conversion of R8/R9/R10; donor notes).
- Items 10–18 (DEFER/REJECTED above) — only revisit if the repo's
  governance-to-code ratio reverses (currently ~115k tokens of docs
  vs ~75k tokens of app source).

---

## Rejected or Deferred Options

These are recorded separately from "Recommended Implementation Sequence"
so a reader can audit what was *not* chosen without inferring from the
sequencing table.

| # | Option | Verdict | Evidence-based reason |
|---|---|---|---|
| 1 | Pants / Bazel / Nx / Turborepo | REJECT | 100 tracked files; ~3.5 min full-gate wall-clock; the staged-validation policy (WORKFLOW §16) already formalizes focused-vs-final. A build system is justified only when its maintenance cost is less than the cost of *not* having it — that threshold is not crossed here. Each system would add a configuration graph (BUILD files / target defs) that consumes more LLM context per slice than the focused-test savings it produces. |
| 2 | Split into multiple repositories | REJECT | The ADR corpus (7 ADRs, 5,184 lines, ~82k tokens) and the governance docs (~32k tokens) are cross-cutting by design. ADR-0002 §7 specifically *prevents* a cross-repo coupling that the old lecture-app integration re-created. Splitting the repo now would force every orchestrator session to load N copies of governance, multiplying per-session discovery cost without shrinking the ADR corpus. |
| 3 | Split `app/api.py` (2,455 LOC) into per-endpoint files | REJECT | Slice-8 S8A introduced `_manage_transaction=False` choreography that depends on a single `create_app` body owning all endpoint transactions. Splitting the file across packages would re-introduce cross-endpoint atomicity risk the choreography explicitly removes. The file is large but cohesive (one `create_app` factory + one `BrowserSecurityMiddleware` class). |
| 4 | Split `frontend/src/app.ts` (1,573 LOC) into sub-components | REJECT | `tasks/slice-8.md` "Frozen frontend and ownership rules" explicitly froze the single-root-element design. The cost of splitting now (design risk, regression in 4 Playwright scenarios) exceeds the per-iteration LLM context saved. |
| 5 | Auto-generated `docs/repo-map.md` via `tools/repo_map.py` (AST) | DEFER | The hand-curated map is small (~80 LOC) and refreshed roughly once per slice. AST-based generation cannot distinguish e.g. "render.py owns the dictionary-asset view" from "dictionary.py owns the asset itself" — that distinction is policy. Worth revisiting only if the table grows beyond ~150 lines or refresh churn exceeds one slice in three. |
| 6 | `pytest-xdist` parallelization | DEFER | Reduces full-gate wall-clock (currently 210s for 691 tests) but does not affect LLM context. Not an efficiency lever for the audit's goals. |
| 7 | pytest markers / `-k` filters | DEFER | The naming convention (`test_<module>.py`) already groups tests by domain. Markers add words to the test docstring context without delivering focused-test automation that the proposed `tools/affected_tests.py` does not already provide more directly. |
| 8 | Smaller handoff ZIP (skip ADRs in favor of repo-map) | DEFER | The handoff ZIP is currently 190–475 KB per slice; sub-1 MB at current ADR count. The duplication is intentional for the offline-fallback case (WORKFLOW §10). Worth revisiting if the ADR count grows past ~15 or any individual ADR exceeds 100 KB. |
| 9 | Auto-checked `make repo-map` target | DEFER | Possible to add as a guard against `docs/repo-map.md` staleness; not load-bearing because the audit's other recommendations (root AGENTS.md saying "nested AGENTS.md conflicts lose to root", review-time check) catch the same defect at lower cost. |
| 10 | Backend / frontend code modularization more aggressive than this audit's recommendations | REJECT (per the brief) | The audit is *evidence-only*. Per `## Scope`: "Do not implement modularization. Do not modify source code." These options would require source-code changes and are explicitly out of scope. |

---

## Risks and Staleness Controls

### Risks of the audit's recommendations

1. **Nested AGENTS.md / repo-map staleness.** Adding more docs creates
   more places to forget to refresh. Mitigation: the `make repo-map`
   target (DEFER) is the optional automated check; until then, the
   root AGENTS.md states explicitly "if a nested AGENTS.md conflicts
   with this file, the root wins", and any disagreement surfaces in
   review.
2. **WORKFLOW.md brief-schema amendment requires care.** Per WORKFLOW
   §10 the brief schema is a binding format; adding a `Required
   reading:` field is non-breaking. No slice brief is invalidated.
4. **Per-slice "Reviewer notes" overhead.** The orchestrator authors it
   at acceptance; that's one more piece of writing per slice.
   Mitigation: keep the section short (one sentence per file group);
   gate the "Reviewer notes" on risk-labeled slices only (per WORKFLOW
   §6).
5. **`tools/affected_tests.py` misclassifies a path.** Path→module
   mapping uses the `docs/repo-map.md` table. If the table misses a
   module, the resolver falls back to "no focused test known" and the
   worker runs the full gate. Worst case: same as today.

### Staleness controls

- **`docs/repo-map.md`** is committed and reviewed per slice closure;
  any new module requires an update before its owning slice is
  accepted.
- **`AGENTS.md` (root)** remains the binding source per WORKFLOW §0
  ("the rules file"). The audit's reduction is an *editorial*
  reduction (move module-scoped rules to nested files) — the
  prohibitions are unchanged.
- **`PROMPTS.md`** amendment is per PROMPTS §CLOSE (non-slice session)
  workflow; no ADR-level change.

### Risks NOT taken by this audit (per the brief)

- No modularization of source code.
- No modification of source code, tests, or governance.
- No new or edited ADRs.
- No slice-9 dispatch.
- No inspection of the lecture-app repository.

---

## Evidence Commands

All evidence above is reproducible from the audit base
`17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5` using the commands below.
None of these commands modify the working tree.

### File / line / token counts

```sh
git ls-files | wc -l                                          # 100
git ls-files | xargs wc -l                                    # total 57,237
git ls-files app | xargs wc -l                                # 7,565
git ls-files tests | xargs wc -l                              # 16,710
git ls-files tools | xargs wc -l                              # 7,040
git ls-files frontend/src | xargs wc -l                       # 3,052
git ls-files docs/adr | xargs wc -l                           # 5,184
wc -l WORKFLOW.md AGENTS.md PROMPTS.md STATE.md \
      docs/plan.md docs/backlog.md                            # 2,357
wc -l tasks/slice-*.md                                        # 12,478
wc -l tasks/*.report.md                                       # 4,643
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
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        n += 1
print(n)                                                       # 476
"
```

### Module dependency graph

```sh
for f in app/*.py; do
  echo "--- $f ---"
  grep -E '^from app' "$f"
done
```

### Gate composition

```sh
cat Makefile
cat pyproject.toml
cat frontend/package.json
cat frontend/playwright.config.ts
```

### Endpoint inventory

```sh
grep -nE "@app\.(get|post|put|delete|patch)\(\"/vocab" app/api.py
```

### Governance / ADR sizes

```sh
wc -l WORKFLOW.md AGENTS.md PROMPTS.md STATE.md docs/plan.md docs/backlog.md
wc -l docs/adr/*.md
ls -la handoff/orchestrator-handoff-slice-*.zip
```

### AGENTS executable vs reviewed rules

```sh
grep -c '\[executable\]' AGENTS.md                             # 7
grep -c '\[reviewed\]' AGENTS.md                               # 14
```

### Handoff / closure evidence

```sh
cat handoff/MANIFEST.md
cat handoff/main-gate.stdout | grep -E "passed|Success|checks"
python3 -c "
import zipfile
with zipfile.ZipFile('handoff/orchestrator-handoff-slice-8.zip') as z:
    for n in sorted(z.namelist()): print(n)
"
```

### Slice brief / report sizes

```sh
wc -l tasks/slice-*.md tasks/*.report.md
```

### Test-domain ownership

```sh
python3 -c "
import ast, os
groups = {
    'runtime-api':  ['test_api','test_capture','test_smoke_baseline'],
    'audio':        ['test_audio'],
    'deck':         ['test_deck'],
    'dictionary':   ['test_dictionary'],
    'render':       ['test_render'],
    'resolve':      ['test_resolve','test_resolve_spacy'],
    'export':       ['test_export'],
    'examples':     ['test_examples'],
    'build_dict':   ['test_build_dict_stage01','test_build_dict_stage02',
                     'test_build_dict_stage03','test_build_dict_stage04',
                     'test_build_dict_stage05'],
    'governance':   ['test_check_agents','test_gate2_coverage','test_container'],
}
data = {}
for root, _, files in os.walk('tests'):
    for f in files:
        if f.startswith('test_') and f.endswith('.py'):
            p = os.path.join(root, f)
            with open(p) as fh:
                d = fh.read()
            data[p] = sum(1 for n in ast.walk(ast.parse(d))
                          if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
for g, names in groups.items():
    print(g, sum(data.get(f'tests/{n}.py', 0) for n in names))
"
```

(All commands run against audit base
`17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5`; no working tree mutation.)