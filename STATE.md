# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0 accepted and merged 2026-08-19** (ADR-0002 §6 order 1). Branch
  `slice/0` at `584e05f3762e1dd16de9e99a1d048b42e7da31b5`, accepted on Attempt 1;
  `Risk: none`. It established the repository skeleton and the authoritative
  `make gate` covering ruff, `mypy --strict`, pytest, and executable AGENTS
  checks.
* **slice-1 accepted and merged 2026-08-19** (ADR-0002 §6 order 2). Branch
  `slice/1` at `8d0507b349110b002e381ecd93729a012c5946f5`, accepted on Attempt 1;
  `Risk: none`, so WORKFLOW §6 required no full-diff review. It landed the pure
  resolver ladder and compound splitter in `app/resolve.py`, the read-only PART A
  SQLite dictionary reader in `app/dictionary.py`, the canonical resolver
  SHA-256 helper, and executable AGENTS R3 enforcement. Worker CLOSE evidence:
  ruff clean; `mypy --strict .` clean over 9 source files; pytest 75 passed;
  executable AGENTS R1, R3 and R7 passed.
* **`tasks/slice-2.md` authored** — ADR-0002 §6 order 3 / Gate 1. It verifies the
  real `de_core_news_md` separable-particle dependency label before any edit,
  locks exactly the five ADR-0001 §13 CASES against the real model, and has
  `Depends: slice-1`; `Risk: none`; `gemini-flash / T1 / low`, fallback
  `codex-low / T1 / low`.
* **Two Authorities / GitHub-first transport is active.** Local Git/terminal is
  authoritative for machine state, working-tree state, installed runtime
  dependencies and fresh gates. Private `origin` (`sabers13/flashcard`) is the
  persistent authoritative mirror for committed/pushed project context.
  Routine handoff ZIP, report and diff uploads are no longer required when the
  relevant pushed GitHub state is accessible; the validated ZIP remains the
  immutable offline fallback. Push synchronization is fail-closed.
* **ADR-0001/0002/0003 remain accepted and unmodified.** No active
  `NEEDS COLD REVIEW` marker exists.

## Gate

* `make gate` — PASS on the accepted slice-1 HEAD: ruff all checks passed;
  `mypy --strict .` success over 9 source files; `pytest -q` 75 passed;
  `tools/check_agents.py` passes R1 (runtime LLM), R3 (resolver cache key), and
  R7 (lecture coupling). R6 and R12 remain deliberately unscaffolded until
  their owning later slices. The closure worker refreshes the authoritative
  post-closure stdout+stderr evidence at `handoff/main-gate.txt` after the
  STATE commit; handoff exists only if that final main gate passes.

## Escalation status

* none — slice-1 accepted on Attempt 1 at its brief-selected T3/high route.
  Startup verification, next-brief materialization, GitHub transport governance,
  and remote bootstrap were governance/mechanical operations, not §5 attempts.

## Sessions since last audit

* 2    <!-- incremented exactly once by slice-1 closure. Audit at >= 10 or a phase boundary. -->

## Blocked

* **`reference/smoke_test.py`** — the filed smoke baseline remains path-broken
  and excluded from normal discovery. `docs/plan.md` assigns its repair to
  slice-8; that repair must remove the exclusion in the same change.
* **Compose integration** — independently BLOCKED by the lecture app's Phase 4
  decomposition and missing donor evidence; slice-9 performs the read-only donor
  verification immediately before compose work.
* **Build stage 04 (batch gloss)** — time-bound: API credit expires
  **mid-September 2026**; `docs/plan.md` governs the sequence.

## Next three actions

1. **slice-2 startup:** open a fresh orchestrator via PROMPTS.md §NEW SLICE OPEN,
   GitHub-first against private `sabers13/flashcard`; formally verify the
   closure `main` HEAD, clean local tree, fresh `make gate`, `Depends: slice-1`
   ancestry, audit triggers, and the slice-2 precondition that
   `spacy.load("de_core_news_md")` succeeds locally without download.
2. **slice-2 Gate 1 implementation:** dispatch `tasks/slice-2.md` on
   `gemini-flash / T1 / low` (fallback `codex-low / T1 / low`). Empirically
   identify the separable-particle dependency label and lock exactly the five
   ADR-0001 §13 CASES; any model absence or inconsistent evidence STOPs before
   implementation rather than inventing a dependency/model policy.
3. **Before slice-2 closure, author `tasks/slice-3.md`** for ADR-0002 §6 order 4:
   Stage 01 output carrying the schema/attribution contract consumed by Gate 2,
   with its allowlist, risk lookup, and model routing decided from WORKFLOW at
   that time.
