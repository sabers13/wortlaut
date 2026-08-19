# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

- **Pre-bootstrap governance repair completed 2026-08-19** (non-slice, docs
  only, no dispatch, no ADR touched). `docs/backlog.md` de-staled; `docs/plan.md`
  thinned to what ADR-0002 §6 does not carry, rows labelled with slice IDs (§6
  order N is slice-(N-1)), next-brief-before-closure recorded, and the file added
  to the ZIP contents in WORKFLOW §11 step 4 / PROMPTS.md §Closure worker step 8.
- **`tasks/slice-0.md` is cold-executable.** Bare `make gate` (Makefile resolves
  `.venv/bin/python`, else `python3`); scope check over
  `$EXPECTED_MAIN_HEAD...HEAD` plus untracked files; `mypy --strict .`; checker
  scaffolds R1 and R7 only, R3/R6/R12 deferred to the slices creating what they
  govern, per AGENTS.md's "are (or will be) enforced" header.
- **ADR-0001/0002/0003 remain accepted and unmodified.** ADR-0002 §6 is still
  `docs/plan.md`'s authority; no active `NEEDS COLD REVIEW` marker exists.

## Gate

- none — `.git` and `Makefile` are still absent. `make gate` is created by
  slice-0, so no project gate can run before bootstrap and slice-0 execution.

## Escalation status

- none — zero dispatches to date; repository bootstrap is pre-slice and does not
  count as an attempt.

## Sessions since last audit

- 0    <!-- non-slice governance sessions do not increment this counter. -->

## Blocked

- **Normal slice lifecycle** — `.git`, `main`, commits, and git log are still
  absent. Planning and its repair are complete; unblocks when the exact one-time
  `PROMPTS.md` §Repository bootstrap worker succeeds and returns
  `BOOTSTRAP MAIN HEAD: <sha>`.
- **`app/` code / `reference/smoke_test.py`** — application modules remain absent
  and the filed smoke baseline is path-broken. Sequencing is in `docs/plan.md`;
  implementation starts only after bootstrap and slice-0.
- **Compose integration** — independently BLOCKED by the lecture app's Phase 4
  decomposition and missing donor evidence; slice-9 runs the read-only donor
  verification immediately before compose work.
- **Build stage 04 (batch gloss)** — time-bound: API credit expires
  **mid-September 2026**; `docs/plan.md` governs the ordering.

## Next three actions

1. **Repository bootstrap worker:** dispatch exactly PROMPTS.md §Repository
   bootstrap worker to `gemini-flash / T1 / low` (fallback
   `codex-low / T1 / low`); return only STOP evidence or
   `BOOTSTRAP MAIN HEAD: <sha>`. No gate and no slice attempt.
2. **Fresh slice-0 orchestrator:** after bootstrap succeeds, use canonical NEW
   SLICE OPEN with that exact bootstrap HEAD and no prior handoff ZIP; perform
   first-slice startup verification before any implementation dispatch.
3. **slice-0 implementation:** dispatch `tasks/slice-0.md` only from that fresh
   orchestrator, on its `gpt-5.6-terra / T3 / high` Model line (same-tier Opus
   fallback); it authors `tasks/slice-1.md` before dispatching closure.
