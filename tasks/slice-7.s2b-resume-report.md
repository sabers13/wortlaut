# Slice-7 S2b RESUME — orchestration report (fresh implementation attempt)

Session of 2026-08-24/25 (OpenCode orchestration, ox-alpha-free primary).
Resumed Stage S2b only, per owner instruction, from the amended contract
committed at `0a839c408dc7fde86995416d90b7badc2d5cb2e2`
("slice-7: clarify S2b D47 runtime choreography", verdict
IMPLEMENTABLE_WITH_BRIEF_CLARIFICATION). Audit artifact — not the
implementation report (`tasks/slice-7.report.md` remains owned by stage S6).

## 1. Startup verification — PASSED

- Repo `/home/saber/projects/flashcard`; branch `slice/7`;
  HEAD == `origin/slice/7` == `0a839c408dc7fde86995416d90b7badc2d5cb2e2`;
  `origin/main` == `eb42ccf5144b70e1baeef1e7623a5ba17475a8e1` (untouched);
  working tree completely clean.
- S1 `a678f1b2…` and S2a `8cf63675…` verified ancestors of `slice/7`.
- No rejected S2b candidate integrated into `main` (verified directly).
- Required corpus read in full: WORKFLOW.md, AGENTS.md, PROMPTS.md, STATE.md,
  tasks/slice-7.md (amended A5), tasks/slice-7.escalation.md,
  tasks/slice-7.orchestration-report.md, ADR-0004 (incl. §6.6 D47),
  app/deck.py, app/dictionary.py, tests/test_deck.py,
  tests/test_dictionary.py, reference/schema.sql, tests/conftest.py.
- Fresh startup gate PASS: ruff clean; mypy --strict 20 files; 552 tests;
  AGENTS R1/R3/R7 (venv-linked toolchain).

## 2. Dispatch protocol used

- Engine: `/home/saber/projects/orchestrator-v2/.venv/bin/orch`, persistent
  default database, isolated candidate worktrees off base `0a839c4`,
  workers forbidden git mutations (engine stages/commits candidates).
- Gate: `make gate PYTHON=…/.venv/bin/python RUFF=…/.venv/bin/ruff
  MYPY=…/.venv/bin/mypy PYTEST=…/.venv/bin/pytest` (authoritative venv).
- Worker task distilled amended A5 into 16 binding mechanics (M1–M16) and 13
  mandatory evidence items (E1–E13); four-path allowlist
  {app/deck.py, app/dictionary.py, tests/test_deck.py,
  tests/test_dictionary.py}; prior rejected candidates declared read-forbidden.

## 3. Environment incidents (not implementation failures)

Two dispatch attempts were killed before any candidate existed:

- `run_da0f4c23fc` (created 2026-08-24T22:43:16Z) — killed by the
  orchestrator's own foreground shell timeout; worker had produced zero
  tracked changes (worktree verified clean at base).
- `run_9a6297c250` (created 2026-08-24T23:07:04Z) — killed when the owner
  aborted the foreground shell call; zero tracked changes.

Both rows remain stuck status RUNNING in the orch database (zombie rows);
their empty worktrees/branches exist. Cleanup deferred pending owner approval.
Remedy adopted: all subsequent runs launched detached (nohup + log file) and
monitored via `orch status`/`events` polling under an explicit owner
monitoring override (WORKFLOW §15.3).

Note: concurrent `SLICE 3A` runs in the shared orch database belong to a
different session targeting `/home/saber/projects/orchestrator-v2`; they do
not touch this repository.

## 4. Implementation run — COMPLETED, gate PASS

- Run: `run_bd077bd3e3`, T3, provider `opencode`,
  model `opencode-go/deepseek-v4-pro` (owner-specified; Muse excluded),
  training allowed, attempt 1 of 2.
- Created 2026-08-24T23:35:23Z; completed 2026-08-25T00:24:13Z.
- Candidate: commit `4fefdda173d0f5657de5e6ea4de4ce625229440e` on branch
  `orch/run_bd077bd3e3/a1`; base `0a839c4…` verified.
- Deterministic gate: PASS (exit 0), full suite, venv-linked toolchain.
- Scope verified by orchestrator: ONLY `app/deck.py` (+501/−1) and
  `tests/test_dictionary.py` (+852) differ; `app/dictionary.py` and
  `tests/test_deck.py` untouched; nothing outside the four-path allowlist.
- Shape: `DictionaryRuntime` implemented in `app/deck.py`; new S2b evidence
  suite added to `tests/test_dictionary.py`.

## 5. Independent adversarial review — VERDICT: BLOCK (9 findings)

- Run: `run_84f2cbc2ac`, T3, provider `codex`, model `gpt-5.6-sol`
  (owner-specified independent reviewer; did not implement the candidate),
  read-only VERDICT.md contract, attempt 1.
- Reviewer candidate commit `b274e9ba3831edbbcbb9bd725be1991e015b2925` on
  branch `orch/run_84f2cbc2ac/a1`; full diff of
  `0a839c4..4fefdda` inspected plus both modules in full.
- Verdict first line: `VERDICT: BLOCK`. Findings as returned (abridged
  wording preserved):

1. `_ReadingView.query()` (app/deck.py:594-604) exposes unrestricted
   caller-supplied SQL; the user connection (app/deck.py:744-751) opens
   without `PRAGMA query_only=ON` or statement restriction — PART-B writes
   and even COMMIT can bypass the activation transaction, defeating the
   read-only-view clause and complete-old/complete-new atomicity.
2. Relink treats independent lemma-ref/sense-ref membership as an exact
   binding (app/deck.py:910-913, 997-1003) without verifying
   `sense_ids[sense_ref][1] == lemma_ids[lemma_ref]`; a mismatched
   lemma/sense pair is marked `bound` (R13 fail-closed violation).
3. Reentrancy refusal is not first/terminal: path/type/version/closed checks
   (app/deck.py:790-796) precede the pin-depth check (797-800), so a pinned
   caller may receive a different error than the distinct reentrancy error,
   contradicting the fixed ordering clause.
4. Lifecycle races: `reading()` checks `_closed` before taking the runtime
   lock (739-740) so `close()` can complete mid-check and yield a post-close
   view; activation checks `_closed` before path resolution and before the
   activation lock (796-804) and never rechecks, so `close()` can overtake
   an activation which then publishes into a closed runtime.
5. Total-failure semantics incomplete: dedicated user-DB connection opened
   (811) before the try begins (815); if `sqlite3.connect` fails, no
   rollback/cleanup runs and the candidate handle leaks.
6. Managed-name rejection happens after normalization: `_recover()` combines
   untrusted persisted text directly (678-680); `_resolve_managed()` resolves
   traversal away (696-703) and checks separators only in `resolved.name`
   (707-713); `sub/../a.sqlite` resolving inside the managed directory is
   accepted despite embedded traversal/separator; E12 test does not cover the
   accepted in-directory case.
7. A completely missing derived-component vector is not failed closed:
   `_relink()` builds `by_note` only from existing rows (881-895); a
   `derived_compound` note with zero surviving component rows stays
   `derived_compound` instead of `needs_gloss`.
8. E5 uses unbounded waits: `Barrier.wait()` without timeout at
   tests/test_dictionary.py:992 and :1012 violates the bounded-wait rule.
9. E6 non-vacuity broken: baseline and success companion share
   `activated_at=NOW` (:1050, :1086) so `last_relinked_at` provably cannot
   change; assertions compare whole tables only and never assert each named
   field actually differs.

Assessment recorded by the orchestrator: findings 1–7 are implementation
defects, 8–9 evidence defects; none indicates the amended no-drain /
path-only-activation design itself is defective.

## 6. Disposition — STOP per owner protocol

Owner protocol for this session: on BLOCK, STOP and present findings; no
automatic repair loop; no acceptance without explicit owner approval after an
independent PASS. Accordingly:

- Nothing accepted; nothing merged; `main` untouched at `eb42ccf…`;
  `slice/7` untouched at `0a839c4…`.
- Candidate retained as diagnostic evidence: `orch/run_bd077bd3e3/a1`
  (`4fefdda`); review record: `orch/run_84f2cbc2ac/a1` (VERDICT.md).
- Options presented to the owner:
  - **A.** Authorize ONE same-tier (T3) repair dispatch reproducing
    candidate `4fefdda` plus exactly findings 1–9, followed by a fresh
    independent gpt-5.6-sol review (mirrors the accepted S1 bounded-repair
    pattern).
  - **B.** Halt S2b again for a fresh governance consult, if any finding is
    judged structural rather than mechanical.

## 7. Repository state at report time

- `main` = `origin/main` = `eb42ccf5144b70e1baeef1e7623a5ba17475a8e1`.
- `slice/7` = `origin/slice/7` = `0a839c408dc7fde86995416d90b7badc2d5cb2e2`.
- Working tree: clean except this uncommitted report file
  (`tasks/slice-7.s2b-resume-report.md`, untracked).
- Accepted stage commits on `slice/7` unchanged: S1 `a678f1b`, S2a `8cf6367`.
- Audit counter: unchanged (8); no closure occurred.
