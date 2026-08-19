# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

- **Repository bootstrap succeeded 2026-08-19** (pre-slice, out of the §5
  ladder, no gate). `f379e2df062a51ad836e4ad132bc30415570905c` —
  `chore: bootstrap repository`, the initial commit on `main`, committing the
  pre-existing governance tree. It is the only commit; `main` is the only branch.
- **Pre-dispatch repair 2026-08-19** (slice-0 orchestrator startup, WORKFLOW §10
  — repair before Attempt 1, not a §5 attempt). This file's `## Gate` reason, its
  `.git`-absent blocked item and its bootstrap action were authored before
  bootstrap ran and contradicted disk; `docs/backlog.md`'s "Repo is not a git
  repository" item was stale for the same reason. `tasks/slice-0.md` A6 now also
  names `handoff/`: PROMPTS.md §Closure worker writes `handoff/main-gate.txt`
  and `handoff/git-log.txt` into the repo and commits neither, so an unignored
  `handoff/` would fail the `git status --porcelain` preflight of every session
  after slice-0 closure.
- **Planning is complete and cold-executable.** `docs/plan.md` carries the slice
  IDs (ADR-0002 §6 order N is slice-(N-1); order 0 is pre-slice), the
  next-brief-before-closure rule, and the ZIP contents alignment with WORKFLOW
  §11 step 4. `tasks/slice-0.md` uses bare `make gate`, scopes its checks over
  `$EXPECTED_MAIN_HEAD...HEAD` plus untracked files, types with `mypy --strict .`,
  and scaffolds R1 and R7 only — R3, R6 and R12 are deferred to the slices that
  create what they govern, per AGENTS.md's "are (or will be) enforced" header.
- **ADR-0001/0002/0003 remain accepted and unmodified.** ADR-0002 §6 is still
  `docs/plan.md`'s authority; no active `NEEDS COLD REVIEW` marker exists.

## Gate

- none — no project gate exists yet. `Makefile`, `pyproject.toml`, `tools/` and
  `tests/` are absent on `main`; `make gate` is created by slice-0, so the first
  gate numbers land at slice-0 closure.

## Escalation status

- none — zero implementation dispatches to date. Repository bootstrap and the
  slice-0 startup verification and repair are pre-dispatch work and do not count
  as attempts (WORKFLOW §10).

## Sessions since last audit

- 0    <!-- non-slice governance sessions do not increment this counter. -->

## Blocked

- **`app/` code / `reference/smoke_test.py`** — application modules remain absent
  and the filed smoke baseline is path-broken. Sequencing is in `docs/plan.md`;
  implementation starts only after slice-0.
- **Compose integration** — independently BLOCKED by the lecture app's Phase 4
  decomposition and missing donor evidence; slice-9 runs the read-only donor
  verification immediately before compose work.
- **Build stage 04 (batch gloss)** — time-bound: API credit expires
  **mid-September 2026**; `docs/plan.md` governs the ordering.

## Next three actions

1. **slice-0 implementation:** dispatch `tasks/slice-0.md` from the slice-0
   orchestrator chat on its `gpt-5.6-terra / T3 / high` Model line (fallback
   `opus-5 / T3 / high`), supplying `EXPECTED_MAIN_HEAD` explicitly as this
   repair commit's `main` HEAD — the brief forbids the worker inferring it.
2. **Author `tasks/slice-1.md`** — ADR-0002 §6 order 2: `app/resolve.py` +
   `app/dictionary.py` plus the executable R3 stage-02 cache-key scaffold —
   before dispatching closure; PROMPTS.md §Closure worker step 8 STOPs without it.
3. **slice-0 closure:** dispatch PROMPTS.md §Closure worker at
   `gemini-flash / T1 / low`, then print the slice-1 NEW SLICE OPEN prompt and
   the validated ZIP path, each with its `## Next step`.
