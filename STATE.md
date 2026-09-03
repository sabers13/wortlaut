# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE from repository/gate evidence.

## What landed

* **ADR-0008 is terminally BLOCKED and permanently closed on `main`.** Its
  three cold reviews are exhausted; F1 found that persisted Online preference
  semantics conflict with explicit Offline Developer/Recovery custom-manifest
  startup. `main` was fast-forwarded and pushed at
  `0a6c0c22f18bc8f761e21a75f6a8616df48699dd`. ADR-0008 and blocked
  `tasks/slice-10.md` remain immutable historical evidence; no review #4 or
  implementation dispatch is permitted.

* **ADR-0009 successor lineage is ACCEPTED / FROZEN.** Cold review #2 —
  FOCUSED REMEDY VERIFICATION (2026-09-03) at review-start/state HEAD
  `f8a85f0be818450961f291cf5f47854233ea87a6` verified the bounded O1–O5
  revision at `4f563c8b64f0bfcb9b93ec3be4a3ff79ad28ff50` against example
  routing, exact lookup-bucket closure/normalization parity, Offline-removal
  metadata semantics, the Slice-12 E2E harness scope, and complete
  provider-read migration sequencing, and found no qualifying material
  blocker. ADR-0009 is approved and frozen; `NEEDS COLD REVIEW` is removed.
  No ADR-0009 cold review #3 is required. No production Online-dictionary
  code, shards, or release has been created. Slice 11 is ready for
  mechanical ADR branch closure into `main` and then implementation; Slice
  12 remains blocked on accepted Slice 11; Slice 13 remains blocked on
  accepted Slices 11 and 12.

* **slice-0 through slice-6 are accepted, merged and closed.**
  slice-0 governance/gate; slice-1 resolver/dictionary boundary; slice-2 Gate 1;
  slice-3 Stage-01 + ADR-0004 PART-A alignment; slice-4 Gate 2 (99.00% CONTINUE);
  slice-5 Stage-02 Tatoeba index; slice-6 Stage-03/04/05 infrastructure +
  Piper build prerequisite.

* **slice-7 is ACCEPTED, MERGED AND CLOSED.**
  Standalone runtime application on `main`: complete PART-B user schema;
  FSRS review loop with append-only raw-confidence logging (fsrs==6.3.2,
  learning steps 1/10 min); DE/EN meaning sets, user meanings, D43
  availability; display-time rendering with tri-state noun plural and D46
  all-components-or-none decomposition (`app/render.py`); `DictionaryRuntime`
  atomic activation/relink with value-snapshot reads, all-or-nothing pins,
  cleanup containment, underlying-file identity, role/status consistency, and
  generation-consistent API observations (`app/deck.py`); pronunciation audio
  precedence, sacred custom media, crash-safe replacement, disposable caches,
  exact-id human discovery, Piper boundary (`app/audio.py`); FastAPI app
  factory with R12 browser guards and the full `/vocab` API including
  sanitized Anki TSV export (`app/api.py`; fastapi==0.141.1,
  uvicorn==0.52.4); executable AGENTS checks R1/R3/R6/R7/R12/R13
  (`tools/check_agents.py`). Accepted stage SHAs: S1 `a678f1b`, S2a
  `8cf6367`, S2b `bbf858e`, S3 `3e3e9d8`, S4 `35c70c9`, S5 `b5b7e93`,
  S6 `c6cdb8f`; full-diff repair lineage `d6fbcda` then `3e6898b`.

* **Mandatory WORKFLOW section 6 T3 full-diff review over main...slice/7: PASS**
  within the bounded convergence budget. Review #1 (gpt-5.6-terra): BLOCK, 5
  findings, of which 2 confirmed (API stale-path dictionary reads, critical;
  git diff --check EOF blanks) and 3 rejected with recorded evidence
  (dictionary.py byte-identity to accepted S2a; orchestrator-owned governance
  paths; ADR-0004 section 6.2 commit/API-layer language invariant). Bounded
  repair, then Review #2 (terra): BLOCK on one residual RB1 (PART-B reads
  outside reading() scope). Final mechanical repair, then Review #3 FINAL
  CONVERGENCE (terra): PASS with residual fixed-verified, rejections
  affirmed, regressions clean. Routing notes: GPT quota exhaustion confined
  implementation to gemini-3.7-flash; ox-alpha-free suffered repeated opencode
  server errors (transport, not content); owner directive made terra the last
  reviewer of each cycle.

* **slice-8 is ACCEPTED, MERGED AND CLOSED.**
  Standalone browser product on `main`: ADR-0002 §6 order 9 closure on the
  accepted Slice-7 runtime. S8A repaired the executable smoke baseline,
  removed `reference` tool exclusions, and implemented the stateless
  two-stage capture endpoints (`POST /vocab/highlight`,
  `POST /vocab/cards`), CSV word-list import, and the pure deterministic
  example ranking engine (`app/examples.py`); S8B established the locked
  Lit/Vite/TypeScript/Playwright frontend source tree with CSS design tokens,
  the root `<flashcard-app>` Lit custom element, the typed `/vocab` fetch
  client (R12 header enforcement + ADR-0004 D47 typed picker/active token
  extraction), and the Vite build that emits the generated `app/frontend/`
  bundle; S8C turned the foundation into the usable standalone product UI
  (navigable deck shell, manual/capture/CSV import, server-authoritative
  refresh-confirm-create/delete, review surface with five confidence
  buttons 1–5 + keyboard contract, DE/EN meaning persistence,
  pronunciation lifecycle + browser-local preview + explicit Save/Revert),
  and added the late E2E-discovered S8C corrective repairs (cards/next
  filters to actually-due cards via `c.due_at <= ?`; the highlight
  materializer preserves multi-gender candidates by selecting the lemma row
  matching the ref's `pos`+`gender`; associated regression coverage in
  `tests/test_api.py` and `tests/test_capture.py`); S8D added the isolated
  APKG export boundary (`app/export.py`, genanki==0.13.1, stable semantic
  GUIDs, basename-only `[sound:...]` references, audio precedence custom →
  eligible human → Piper → absent, no second scheduler, no persisted
  rendered faces), deck-scoped `GET /vocab/export/apkg`, static Vite
  serving at `/` after every `/vocab` route with explicit path-traversal
  protection, multi-stage Docker image with frontend build stage, and
  `uvicorn … --factory --host 127.0.0.1 --port 8000`; S8E added the
  authoritative Playwright E2E coverage against the actual FastAPI-served
  compiled product (`frontend/tests/e2e/product.spec.ts` with deterministic
  Promise-barrier loading/error/empty state, manual creation + local audio
  + review + unavailable fallback + TSV and APKG export, two-stage capture
  with stale asset-token zero-write recovery, and responsive viewport
  behaviour for 360/768/1366/1920 widths). Recovery branch
  `recovery/s8e-rp20-final-candidate` recorded the closure lineage:
  `ef087ff` (final implementation candidate), `af1af7b` (pre-final
  acceptance evidence reclassification of S8C late repairs, separate S8E
  Playwright scope, pending final-validation section), `8f94875` (Promise-
  barrier repair replacing the fixed-150 ms sleep in the deterministic
  loading-state E2E scenario, no product-code change), `a01ab3c`
  (final-authoritative-validation evidence + T3 full-diff review PASS,
  recorded under section `## Final Authoritative Validation` in the report).
  Slice-8 closure lineage on canonical branches: `fb5031b` (slice/8 merge
  of recovery with `-X theirs` to favor the accepted recovery content on
  the two `frontend/src/app.ts` / `tasks/slice-8.report.md` conflicts whose
  slice/8 side was the abandoned intermediate work), `ac2b4d6` (main merge
  of slice/8 with `--no-ff`). Acceptance gate at the validation starting
  candidate `8f94875`: 691 pytest pass, ruff clean, mypy --strict clean on
  35 source files, AGENTS R1/R3/R6/R7/R12/R13 PASS, npm ci 26 packages
  clean, `tsc --noEmit` clean, 25 frontend unit tests pass, vite build
  clean (~88 kB JS bundle), 4/4 Playwright scenarios pass against the real
  FastAPI-served compiled product (12.8 s wall clock).

* **Agent-efficiency foundation is ACCEPTED, REVIEWED AND MERGED.**
  The repository now has the canonical `MODULES.toml` machine-readable
  16-module map; `tools/check_modules.py` is fail-closed and part of
  `make gate`; `tools/affected_tests.py` provides iteration-time
  dependency-scoped validation using source reverse-dependency closure plus
  direct-only known-test handling; `WORKFLOW.md` / `PROMPTS.md` add explicit
  `Required reading:` context boundaries without weakening global governance
  or exact-final-candidate validation. Accepted implementation candidate:
  `c136a2e`; exact-candidate full gate: ruff clean, mypy --strict clean on
  39 source files, 731 pytest passed, AGENTS R1/R3/R6/R7/R12/R13 PASS,
  MODULES validation 16 modules. Independent full-diff review:
  `0a42fbc`, PASS WITH NON-BLOCKING NOTES, 0 blockers,
  HISTORY_ACCEPTABLE, PROPORTIONATE. Review follow-ups N1
  (`build_dict -> check_agents` over-selection) and N2
  (audit Option-C/direct-owner documentation drift) are explicitly
  non-blocking and remain recorded in
  `reviews/agent-efficiency-foundation-c136.md`.

## Gate

* ADR-0009 O1-O5 revision candidate
  `4f563c8b64f0bfcb9b93ec3be4a3ff79ad28ff50`: PASS — ruff clean;
  mypy --strict clean on 45 source files; 821 pytest passed;
  executable AGENTS R1/R3/R6/R7/R12/R13 PASS; MODULES validation
  PASS for 18 modules.
* ADR-0008 terminal branch gate at `0a6c0c22`: PASS — ruff clean, mypy strict
  clean, pytest passed, and the executable AGENTS checks passed before the
  authorized fast-forward to `main`.

* Agent-efficiency exact candidate `c136a2e`: PASS — ruff clean;
  mypy --strict clean on 39 source files; 731 pytest passed;
  AGENTS R1/R3/R6/R7/R12/R13 PASS; MODULES validation passed
  for 16 modules. Final merged-main gate is performed by this closure
  worker after the STATE commit.
* Fresh gate on slice/7 @ `3e6898b`: PASS — ruff clean, mypy strict,
  667 tests, AGENTS R1/R3/R6/R7/R12/R13.
* Fresh gate on slice/8 @ `8f94875` (validation starting candidate):
  PASS — ruff clean, mypy --strict clean on 35 source files,
  691 pytest pass (216.92 s), AGENTS R1/R3/R6/R7/R12/R13.
* Final main gate after closure commits: see `handoff/main-gate.txt`.

## Escalation status

* none active. Slice-7 consumed its authorized budgets exactly: the S2b
  clarified-contract lineage (two gate-fail retries, one tightened
  re-dispatch, one final convergence fix) and the full-diff review lineage
  (one bounded repair plus one final mechanical repair inside the
  three-review cap).
* Slice-8 consumed its recovery lineage as follows: one orchestrator
  recovery attempt (the `recovery/s8e-rp20-final-candidate` branch from
  `8f94875`), the deterministic-loading E2E repair commit `8f94875` on top
  of the pre-existing evidence-reorganisation commit `af1af7b`, and a
  single T3 full-diff risk review of `main...recovery/s8e-rp20-final-candidate`
  that found no blocker. No §5 escalation tier was triggered; the recovery
  branch's two follow-on commits (`8f94875` repair, `a01ab3c` final
  evidence) live within the same closure lineage, not a fresh
  implementation dispatch.

## Sessions since last audit

* 2 (slice-7 closure session; slice-8 closure session. Counter incremented
  exactly once at each session close.)

## Blocked

* ADR-0009 is accepted and frozen at cold review #2 (2026-09-03); no
  review #3 is required. The implementation sequence is mechanical ADR
  branch closure into `main` first, then Slice 11 dispatch. Slice 12
  remains blocked on accepted Slice 11; Slice 13 remains blocked on
  accepted Slices 11 and 12. ADR-0008/Slice-10 remain terminal historical
  evidence.

* Compose integration blocked by lecture-app Phase-4 decomposition (slice-9)
  and the missing donor-evidence file `tasks/adr-0002-donor-notes.md`.
* ADR-0002 D27 / ADR-0003 D27 identifier collision remains naming debt only.
* Full paid Stage-04 production remains deferred by owner decision.

## Next three actions

1. Mechanically close the accepted ADR-0009 branch into `main` per
   WORKFLOW §11 (final authoritative gate on `main` after the closure
   commit, `handoff/` packaging, and `git push origin main` and slice
   branch), then dispatch Slice 11 against the merged `main`. Slice 12
   remains blocked on accepted Slice 11; Slice 13 remains blocked on
   accepted Slices 11 and 12.
2. After Slice 11 closure, dispatch Slice 12; after Slice 12 closure,
   dispatch Slice 13 — Slice 13 is publication-only and must STOP rather
   than repair product code if it finds a provider bypass.
3. Independently, before any Slice-9 implementation/review dispatch, amend
   `tasks/slice-9.md` with `Required reading:`, complete its donor/lecture-app
   blockers, then use normal fresh-startup and required risk-review workflow.
