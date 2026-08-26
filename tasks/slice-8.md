# Slice 8 — Smoke baseline repair, two-stage capture/import flows, and pronunciation end-to-end smoke

Task:        Repair the `reference/smoke_test.py` baseline (path defect and
             stale contracts) and remove the `reference/` tool exclusions from
             `pyproject.toml` in the same change; implement the remaining
             ADR-0002 §6 order-9 capture flows — D27 two-stage highlight
             (`POST /vocab/highlight`, `POST /vocab/cards`) and D19 CSV
             word-list import — on top of the accepted Slice-7 runtime;
             add deterministic example ranking (`app/examples.py`, ADR-0001
             §11 as amended by ADR-0002 §5); amend the smoke baseline's
             assertions to exactly ADR-0002 §4/§5, ADR-0003 §5, ADR-0004 D47,
             and ADR-0005 §10 including the end-to-end pronunciation smoke;
             keep every accepted Slice-7 behavior intact.

Depends:     slice-7

## Entry condition

slice-7 must be ACCEPTED, merged, closed, and pushed before implementation
dispatch. The authoritative starting point is the closed `main` HEAD recorded
in `STATE.md` and the handoff manifest.

## Authority

The binding architecture is:

- `docs/plan.md` slice-8 row (§6 order 9);
- ADR-0002 §4 (two-stage capture and commit contract, normative) and §5
  (smoke-baseline amendment list), D24/D25/D27;
- ADR-0001 §11 (example ranking; `known = deck lemmas ∪ known_lemmas` when
  supplied by value, else deck lemmas), D11 (picker defaults/multi-select),
  D13/D19 (manual entry and CSV import share the pipeline), §7 (export);
- ADR-0003 §5 (`deck.review(db, card_id, confidence)` baseline signature;
  both raw confidence and mapped rating asserted);
- ADR-0004 §6.6 D47 replacement/stale-picker smoke scenarios and §10 card
  behaviour; ADR-0007 D80 ({de,en} only, fa → 422 zero writes);
- ADR-0005 §10 required implementation verification (pronunciation E2E items);
- AGENTS R1, R4, R5, R6, R9, R10, R12, R13; C1/C2/C3;
- The FINAL accepted Slice-7 contract as shipped on `main`: `create_app`
  factory with R12 ASGI guards; `DictionaryRuntime` (path-only activation,
  value-snapshot reads, observe_card_render/observe_export_payload
  single-scope observations); `deck.create_note/review/delete_deck`;
  `app/render.py`; `app/audio.py`; PART-B schema in `reference/schema.sql`.

## Allowlist

Implementation may modify/create only:

- `reference/smoke_test.py`
- `pyproject.toml` (ONLY: remove `reference` from the mypy/ruff/pytest
  exclusion lists; no other pyproject change)
- `app/api.py`
- `app/deck.py`
- `app/examples.py`
- `tests/conftest.py`
- `tests/test_capture.py` (new)
- `tests/test_smoke_baseline.py` (new)
- `tasks/slice-8.report.md`

No other tracked path is allowed. In particular do NOT modify: ADRs,
AGENTS.md, WORKFLOW.md, PROMPTS.md, STATE.md, docs/, tools/,
`reference/schema.sql`, `app/render.py`, `app/audio.py`, `app/dictionary.py`,
`app/resolve.py`, Dockerfile.

## Acceptance

### A1 — Smoke baseline repair (paths + tooling inclusion)

1. `reference/smoke_test.py` imports the repo-root `app` package correctly
   (no `sys.path.insert(dirname(__file__))` defect) and opens
   `reference/schema.sql` explicitly;
2. `pyproject.toml` removes `reference` from `[tool.mypy] exclude`,
   `[tool.ruff] exclude`, and `[tool.pytest.ini_options] norecursedirs` in the
   SAME change; `reference/smoke_test.py` passes ruff and `mypy --strict`;
3. `tests/test_smoke_baseline.py::test_smoke_baseline_runs_green` executes the
   repaired baseline as a subprocess (`<venv python> reference/smoke_test.py`)
   and asserts exit 0 with empty stderr tail tolerance only for warnings.

### A2 — Two-stage capture (D27) on the accepted factory

1. `POST /vocab/highlight` receives `{sentence_text, selected_span,
   lesson_label, lesson_id?, known_lemmas?}`, validates the span in bounds,
   resolves locally through the accepted dictionary ladder, returns picker
   candidates (stable refs + grammar data + current asset token) plus the
   normalized self-contained `capture_context`, and performs ZERO writes;
2. `POST /vocab/cards` receives `{selections:[{ref, sense_ref?, overrides}],
   capture_context, deck:{kind,name,lesson_id?}, asset_token}`; revalidates
   everything; returns HTTP 409 `dictionary_changed` with zero writes on any
   stale asset token; validates `meaning_langs` non-empty subset of {de,en}
   and `user_meanings` per ADR-0004 D44 (string upsert / null delete /
   omission = no mutation / {} invalid / blank invalid); permits exactly
   `front_override`, `back_override`, `meaning_langs`, `user_meanings`
   (scalar `gloss_user` stays superseded); atomically creates/reuses notes and
   memberships in ONE transaction; any validation failure → HTTP 422 with
   zero writes; duplicate selections revalidating to the same note identity →
   422; submitted semantic refs absent from the active generation → 422 zero
   writes (Slice-7 rule carries over);
3. Manual entry and CSV import freeze the chosen primary dictionary sentence
   into the note by value at creation (`example_de`), never re-ranked on
   ordinary render; existing notes keep their first frozen example;
4. `POST /vocab/import/csv` accepts `{csv_text, deck_name,
   meaning_languages}`; one word per line through the same ladder; top
   candidate default-selected (D11); misses become `needs_gloss` notes;
   atomic per-request commit with 422 zero-write validation failures.

### A3 — Deterministic example ranking (ADR-0001 §11)

`app/examples.py`: pure ranking over dictionary examples — length toward 9
tokens, penalise unknown lemmas (i+1; rare unknowns harder), proper nouns,
untranslated; small bonus for questions; `known = deck lemmas ∪ known_lemmas`
when supplied by value, else deck lemmas; fully deterministic; unit-tested.

### A4 — Smoke assertions amended to the final contracts

The repaired baseline asserts, at minimum:

1. ADR-0002 §5: explicit `meaning_langs` required at creation; omission =
   no mutation on reuse; add/update/delete one language without touching
   others; user meaning survives deselection/reselection; no implicit English;
   unsupported language → 422 zero writes; blank user meaning → 422 zero
   writes; malformed `user_meanings` → 422 zero writes; atomic rollback of the
   entire `/vocab/cards` request; multi-select with distinct valid overrides;
   unknown/invalid override → 422 zero writes; `/vocab/highlight` performs no
   note/membership write;
2. ADR-0003 §5: `deck.review(db, card_id, confidence)` persists BOTH raw
   confidence and mapped rating; client `rating` rejected at the API;
3. ADR-0004 D47: dictionary replacement with numeric-ID renumbering where
   stable refs bind correctly; unrelated recycled numeric ID does not bind;
   disappeared sense fails closed to `needs_gloss` preserving user meanings
   and history; duplicate/ambiguous stable refs abort activation; derived
   compound component disappearance renders the whole derived block
   unavailable; `meaning_state` consults only validated current bindings;
   stale picker asset token → 409 zero writes; no mixed old-binding/new-asset
   state observable (use the runtime seam probe for a mid-observation
   activation);
4. ADR-0005 §10 pronunciation E2E: custom override wins; Revert restores
   automatic; failed validation preserves the previous override; unsafe media
   rejected; human-cache corruption falls through to Piper; offline/remote
   `/speak` failure falls back silently to Piper (injectable fakes, zero
   network, zero subprocesses); custom audio survives cache deletion and
   numeric-ID renumbering; disappeared stable target fails closed without
   deleting learner media.

### A5 — Gate and report

1. `make gate` passes (ruff incl. `reference/`, `mypy --strict .` incl.
   `reference/smoke_test.py`, full pytest, check_agents R1/R3/R6/R7/R12/R13);
2. `git diff --check` passes;
3. New non-GET routes are covered by the structural R12 middleware (verified
   by the existing R12 checker and by guard tests);
4. `tasks/slice-8.report.md` created with the exact scaffold (line 1
   `# Slice 8 report`, line 3 `## NARRATIVE`) documenting: baseline repair,
   capture/import flows, ranking, assertion coverage map, pronunciation E2E
   evidence, and full gate numbers.

## Stop-and-ask

STOP and return to the slice-8 orchestrator if: `Depends: slice-7` is not
merged/closed; any requirement needs a file outside the Allowlist; any
requirement conflicts with an accepted ADR or the accepted Slice-7 contract;
implementing capture would require storing rendered faces (R4) or cascade-
deleting reviewed notes (R5); Persian activation is proposed (ADR-0007); any
mandatory test or gate check fails.

## Risk

Risk: public-api, data-loss

## Why-risk

WORKFLOW §6 lookup: new externally callable HTTP routes (`app/api.py`) →
public-api; capture commits, note reuse, and import write durable user state →
data-loss. Pre-committed T3 full-diff review of `main...slice/8` before merge.

## Model

Model: gemini-3.7-flash / T3 / high

## Why

WORKFLOW §4: blast radius crosses the public API and durable user data;
novelty in the two-stage commit transaction; judgment across five ADR
assertion suites. Highest triggered row → T3 high.

## Fallback

Fallback: ox-alpha-free / T3 / high. Independent review: gpt-5.6-terra as the
LAST reviewer of each review cycle (owner directive, 2026-08-26); prompts to
gemini/ox travel as argv and must stay under 32 KiB — batch larger briefs.

## Worker implementation constraints

1. Start only after the slice-8 orchestrator supplies the exact verified
   expected `main` HEAD; create `slice/8` from that HEAD; mismatch is STOP.
2. Read `AGENTS.md`, `docs/adr/0001..0005`, `docs/adr/0007`,
   `tasks/slice-8.md`, the accepted `app/*` modules, and
   `reference/smoke_test.py` before editing.
3. Zero module-level state; no env reads at import time; dependency direction
   `api -> deck -> render -> dictionary -> resolve` unchanged; `examples.py`
   sits beside `render.py` (pure, below deck).
4. All new non-GET routes inherit the R12 middleware structurally; do not add
   per-route guard bypasses.
5. No runtime LLM; no new third-party dependencies.
6. Create `tasks/slice-8.report.md` before Worker CLOSE.

## Exact report scaffold

```markdown
# Slice 8 report

## NARRATIVE
```

Populate only `## NARRATIVE`.

## Required terminal verification before Worker CLOSE

The slice-8 orchestrator supplies `EXPECTED_MAIN_HEAD`.

```sh
: "${EXPECTED_MAIN_HEAD:?STOP: EXPECTED_MAIN_HEAD was not supplied}"
test "$(git branch --show-current)" = "slice/8" || { echo "STOP: not on slice/8"; exit 1; }
test "$(git rev-parse main)" = "$EXPECTED_MAIN_HEAD" || { echo "STOP: main differs"; exit 1; }
test "$(git merge-base slice/8 main)" = "$EXPECTED_MAIN_HEAD" || { echo "STOP: base differs"; exit 1; }
make gate
git diff --check "$EXPECTED_MAIN_HEAD"...HEAD
outside="$({
  git diff --name-only "$EXPECTED_MAIN_HEAD"...HEAD
  git ls-files --others --exclude-standard
} | grep -vxF \
  -e reference/smoke_test.py \
  -e pyproject.toml \
  -e app/api.py \
  -e app/deck.py \
  -e app/examples.py \
  -e tests/conftest.py \
  -e tests/test_capture.py \
  -e tests/test_smoke_baseline.py \
  -e tasks/slice-8.report.md || true)"
test -z "$outside" || { echo "STOP: scope violation:"; printf '%s\n' "$outside"; exit 1; }
test "$(sed -n '1p' tasks/slice-8.report.md)" = "# Slice 8 report" || { echo "STOP: report header"; exit 1; }
test "$(sed -n '3p' tasks/slice-8.report.md)" = "## NARRATIVE" || { echo "STOP: report NARRATIVE heading"; exit 1; }
```
