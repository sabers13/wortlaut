# Implementation plan — ADR-0002 §6 sequencing

Authority: `docs/adr/0002-standalone-and-integration.md` §6, normative for what
each order does and for the sequence, and not restated here. This file adds only
the slice ID each order becomes, entry conditions beyond §6's generic one (the
preceding order accepted), and the rule blocking the next. **§6 order N (N >= 1)
is slice-(N-1); order 0 is pre-slice and has no ID** — `Depends:` verification
and `tasks/<NEXT>.md` naming key on the slice ID, never the order number.

## Sequence

| Slice | §6 order | Entry condition | Exit / blocking rule |
| --- | --- | --- | --- |
| — pre-slice | 0 | Planning artifacts exist; `.git` is absent | Worker returns `BOOTSTRAP MAIN HEAD: <sha>` with clean `main`. Out of the §5 attempt counter; runs no gate. |
| slice-0 | 1 | Order 0 returned its HEAD; the fresh orchestrator ran the first-slice startup exception against that exact SHA | `make gate` exists and passes ruff, `mypy --strict`, `pytest -q`, and executable AGENTS checks. No application feature work. |
| slice-1 | 2 | — | Resolver/dictionary contract and the R3 scaffold are gate-verified before Gate 1. |
| slice-2 | 3 | — | Accepted spaCy label plus tests locking the ADR-0001 §13 cases. Failure is fixed before any dictionary build work. |
| slice-3 | 4 | — | Stage 01 output carries the schema/attribution contract Gate 2 consumes. |
| slice-4 | 5 | — | §6 order 5's thresholds govern verbatim. A design gate, not a §5 retry ladder: `<85%` returns to governance. |
| slice-5 | 6 | — | Stage 02 imports `app/resolve.py`; cache keys include its SHA-256 (AGENTS R2/R3). |
| slice-6 | 7 | — | Packaged dictionary path is reproducible; stage 04 completes before the mid-September 2026 API-credit expiry. |
| slice-7 | 8 | — | ADR-0003 review/mastery semantics and AGENTS R12 land before browser integration. |
| slice-8 | 9 | — | The `reference/smoke_test.py` path defect is repaired here; assertions match ADR-0002 §4/§5 and ADR-0003 §5. |
| slice-9 | 10 | Lecture app Phase 4 decomposition complete | Read-only, out-of-ladder donor inspection (WORKFLOW §12 / AGENTS G6) writes `tasks/adr-0002-donor-notes.md` first; any contradiction returns to governance. Compose work starts only if donor evidence agrees and the host blocker is gone. |

## Dispatch boundaries

- Order 0 is the next action now, is not a slice, and increments no counter.
  `tasks/slice-0.md` is the only brief authored in the planning session.
- **Each slice orchestrator authors the next slice's brief before dispatching
  closure.** PROMPTS.md §Closure worker step 8 packages `tasks/<NEXT>.md` and
  STOPs when it is missing, so an unauthored next brief is a failed closure.
- Later slices are not pre-routed here: exhaustive allowlist, WORKFLOW §6
  path-based risk lookup, and Model/Why/Fallback are set at brief-writing time.
- slice-9 begins with the donor-inspection worker; compose stays blocked until
  its evidence and the host-phase prerequisite are both satisfied.
