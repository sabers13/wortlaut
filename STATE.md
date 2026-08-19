# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

- **slice-0 accepted and merged 2026-08-19** (ADR-0002 §6 order 1). Branch
  `slice/0` at `584e05f3762e1dd16de9e99a1d048b42e7da31b5`, accepted on Attempt 1;
  `Risk: none`, so WORKFLOW §6 required no full-diff review. `make gate` now
  exists and is the single authoritative local verification command, from
  `.gitignore`, `pyproject.toml`, `Makefile`, `tools/check_agents.py` and
  `tests/test_check_agents.py`. The Makefile resolves `.venv/bin/*` when present
  and the system interpreter otherwise, so bare `make gate` works identically for
  the closure gate and at fresh-orchestrator startup.
- **`tasks/slice-1.md` authored** — ADR-0002 §6 order 2: `app/resolve.py` ladder
  and compound splitter, `app/dictionary.py` read-only PART A reader, and the
  executable R3 stage-02 cache-key scaffold. `Depends: slice-0`; `Risk: none` by
  the §6 path lookup; `gpt-5.6-terra / T3 / high` on the §4 Verification and
  Novelty rows.
- **Bootstrap and pre-dispatch repair.** `f379e2df` created `main`; `817c23cc`
  de-staled this file and `docs/backlog.md` against disk and amended slice-0 A6
  to ignore `handoff/`, which PROMPTS.md §Closure worker writes into the repo
  and never commits. Neither is a §5 attempt.
- **Two Authorities & GitHub transport governance revision.** Encoded the strict
  authority split: local Git/terminal is authoritative for machine state,
  uncommitted files, and fresh gate execution; private GitHub repository mirror
  is authoritative for committed context, briefs, reports, and allowed diff
  ranges. Encoded GitHub-first startup, push synchronization (G9), no routine
  ZIP/diff uploads (G10), remote sanity checks, and privacy protections, retaining
  handoff ZIPs as immutable offline snapshots and fallbacks.
- **ADR-0001/0002/0003 remain accepted and unmodified.** No active
  `NEEDS COLD REVIEW` marker exists.

## Gate

- `make gate` — PASS. ruff: all checks passed. `mypy --strict .`: success, no
  issues in 2 source files. `pytest -q`: 33 passed. `tools/check_agents.py`: R1
  (runtime LLM) and R7 (lecture coupling) pass. R3, R6 and R12 are deliberately
  not scaffolded yet — R3 lands in slice-1, R6 with the application schema, R12
  with the `/vocab` API. Authoritative post-closure evidence, stdout and stderr:
  `handoff/main-gate.txt`.

## Escalation status

- none — slice-0 accepted on Attempt 1 at T3; the ladder was never entered.
  Bootstrap, startup verification, and the pre-closure governance commits are
  not §5 attempts.

## Sessions since last audit

- 1    <!-- incremented once by slice-0 closure. Audit at >= 10 or a phase boundary. -->

## Blocked

- **`app/` code / `reference/smoke_test.py`** — application modules remain absent
  and the filed smoke baseline is path-broken. slice-0 excluded `reference/` from
  ruff, mypy and pytest discovery; `docs/backlog.md` binds the slice that repairs
  that baseline to remove the exclusion in the same change, so the repaired file
  cannot escape the gate.
- **Compose integration** — independently BLOCKED by the lecture app's Phase 4
  decomposition and missing donor evidence; slice-9 runs the read-only donor
  verification immediately before compose work.
- **Build stage 04 (batch gloss)** — time-bound: API credit expires
  **mid-September 2026**; `docs/plan.md` governs the ordering.

## Next three actions

1. **slice-1 implementation:** fresh orchestrator per PROMPTS.md §NEW SLICE OPEN
   (GitHub-first default using private GitHub mirror, or with
   `handoff/orchestrator-handoff-slice-1.zip` as fallback); verify `Depends: slice-0`
   is merged, then dispatch `tasks/slice-1.md` on `gpt-5.6-terra / T3 / high`
   (fallback `opus-5 / T3 / high`) with `EXPECTED_MAIN_HEAD` supplied explicitly.
2. **Author `tasks/slice-2.md`** — ADR-0002 §6 order 3, Gate 1: verify the spaCy
   separable-particle dependency label and lock the ADR-0001 §13 `CASES` — before
   dispatching slice-1 closure.
3. **slice-1 closure:** PROMPTS.md §Closure worker at `gemini-flash / T1 / low`,
   then print the slice-2 NEW SLICE OPEN prompt and the validated ZIP path.
