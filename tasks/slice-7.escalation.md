# Slice-7 escalation record

- Original brief: tasks/slice-7.md
- Attempt 1 (gpt-5.6-terra / T3 / high): monolithic whole-slice dispatch,
  run `run_e002589566` attempt a1 — deterministic gate FAIL (exit 2). Root
  cause: isolated orch worktree has no `.venv`, so the Makefile falls back to
  system tools and strict mypy cannot resolve `spacy`
  (`import-not-found` x4). Not an implementation defect.
- Attempt 2 (gpt-5.6-terra / T3 / high): same dispatch, attempt a2 —
  implementation substantially complete (~1,120 inserted lines across schema,
  deck, dictionary, render, audio, api, check_agents; targeted ruff/mypy PASS,
  56 targeted tests PASS). Worker STOPped when its provider sandbox blocked
  `git commit` (read-only `.git/worktrees/<id>/index.lock` outside the
  workspace-write scope). The engine captured the candidate (`4724c38`) and the
  gate failed on the same worktree-environment defect as attempt 1.
- The failures agree on: the isolated-worktree gate environment cannot satisfy
  `make gate` (missing project venv ⇒ spaCy unresolvable), independent of
  implementation quality; secondarily, worker-side git commits are impossible
  under the provider sandbox and are unnecessary because the orchestration
  engine captures candidates itself.
- Orchestrator's respecification (WORKFLOW §5.3 ceiling → design split):
  slice-7 implementation is re-dispatched as six gated sub-dispatches accepted
  sequentially onto `slice/7` —
  S1 schema + deck core (A1–A3 deck-side),
  S2 dictionary identity/activation (A5),
  S3 rendering (A4),
  S4 audio (A6),
  S5 app factory/API/security guards (A7),
  S6 executable AGENTS checks + slice report (A8, A10).
  Run gates symlink the authoritative main `.venv` into the worktree before
  `make gate`; workers are forbidden from any git mutation (the engine stages
  and commits candidates). Owner approved the split, chained auto-acceptance
  of gate+review-passing sub-candidates, and the environment measures on
  2026-08-24. The mandatory WORKFLOW §6 T3 full-diff review over the entire
  `main...slice/7` diff remains required before merge and is not replaced by
  per-sub-run reviews.

## Stage S1 review-repair addendum (2026-08-24)

- S1 implementation attempt 1 (`run_a9892eedd7`, candidate `cac2e74`): gate
  PASS; independent gpt-5.6-sol stage review BLOCKED with five findings
  (tracked `.venv` symlink — orchestrator gate-mechanism defect; orphan move
  gated on review history; D43 status-coupled availability; FSRS transition
  outside the review transaction; unenforced non-empty `note_meaning_lang`).
- S1 same-tier retry (attempt 2, `run_2f2f17fcd3`, candidate `f454ca5`): gate
  PASS; all five findings fixed; follow-up gpt-5.6-sol review BLOCKED with
  three narrower residual findings: implicit `meaning_languages=("en",)`
  creation default (contradicts ADR-0004 §6.4/D44); derived-compound component
  vector validated after `bound` filtering, letting a truncated contiguous
  prefix pass (D46 all-components-or-none); deck-deletion membership read
  outside the deletion transaction, allowing a concurrent membership insert to
  lose its Orphaned placement (AGENTS R5).
- Owner disposition (2026-08-24, this chat): one narrow T3 repair dispatch
  reproducing the attempt-2 content plus exactly those three corrections,
  followed by a fresh independent review. If that review BLOCKs again, Stage
  S1 returns to design (split/redesign) with no further repair attempts. This
  addendum documents why the third pass is a bounded repair under the §5.3
  respecification umbrella rather than an uncounted brute-force retry.
- S1 bounded repair (attempt 3, `run_e9735fd409`, candidate `bfe10ef`): gate
  PASS; final stop-or-go gpt-5.6-sol review confirmed F1 and F3 fixed with no
  regressions, but BLOCKED on one structural residual: the D46 vector check
  compared surviving ordinals against the surviving row count (circular), and
  no independently persisted expected component count existed, so trailing-row
  loss still passed as a valid vector.
- Design return per the authorized stop-or-go: owner approved amending
  `tasks/slice-7.md` (A1 item 8 and A5) so derived_compound notes persist an
  expected ordered `component_count` captured at creation and revalidated at
  D47 relink; full-vector validation precedes any binding-status filtering and
  an undeterminable count fails closed. This completes frozen ADR-0004 D46's
  ordered component vector without amending the ADR. Stage S1 is re-dispatched
  fresh from attempt 1 of the amended stage contract per WORKFLOW §5.3.
  Outcome: fresh S1 dispatch (`run_ac40b393db`, candidate `a678f1b`) passed
  gate and the gpt-5.6-sol review (VERDICT: PASS, defeat-check included) and
  was accepted onto `slice/7`.

## Stage S2 ceiling and split (2026-08-24)

- S2 attempt 1 (`run_e9a8cb7f0b`, `ff9fadf`): gate PASS; sol review BLOCKED
  (5): token check outside the write transaction; lookup tokens derived from
  the constructed path instead of active metadata (mixed-state exposure);
  arbitrary `lemma:v*`/`sense:v*` strings accepted as stable identity;
  `asset_token=None` permitted without active metadata; mandated
  corrupted-candidate and single-transaction assertions missing.
- S2 same-tier retry (`run_2c11e3f861`, `efc4d2f`): gate PASS; sol re-review
  BLOCKED (5 second-order findings): runtime-less activation path with a
  call-local lock breaks exclusion; whitespace-stripping bypasses canonical
  ref verification; a private-sentinel default bypasses token validation;
  validate-close-reopen race can bind one asset's relink maps to another's
  SHA/handle; ordering/rollback test evidence too weak.
- T3 ceiling reached per WORKFLOW §5. Owner chose the §5.3 split response:
  Stage S2 divides into **S2a** (candidate asset validation and stable-ref
  verification bound to a single opened content; no PART-B writes) and **S2b**
  (atomic activation/relink and runtime visibility through one runtime
  instance; required `asset_token`; complete-old-or-complete-new reads).
  `tasks/slice-7.md` A5 amended with the structural mechanics. Each sub-stage
  is dispatched fresh from attempt 1 with independent gpt-5.6-sol review.
