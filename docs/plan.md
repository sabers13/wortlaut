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
| slice-3 | 4 | — | Stage 01 output carries the schema/attribution contract Gate 2 consumes. **Closure BLOCKED** by the ADR-0004 governance amendment below: the accepted Attempt-1 implementation must be aligned to the multilingual meaning contract before it merges. |
| slice-4 | 5 | — | §6 order 5's thresholds govern verbatim. A design gate, not a §5 retry ladder: `<85%` returns to governance. |
| slice-5 | 6 | — | Stage 02 imports `app/resolve.py`; cache keys include its SHA-256 (AGENTS R2/R3). |
| slice-6 | 7 | — | Packaged dictionary path is reproducible; stages 03–05 include the ADR-0004 multilingual offline meaning enrichment (EN gap fill, DE learner meanings, FA translations, deterministic validation, selective QA); stage 04 completes before the mid-September 2026 API-credit expiry. |
| slice-7 | 8 | — | ADR-0003 review/mastery semantics and AGENTS R12 land before browser integration. Render/API must also support the note's selected DE/EN/FA meaning set, Persian RTL, and tri-state noun plural on the back (ADR-0004 §10) before UI/browser completion. |
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

## Governance amendment — ADR-0004 (2026-08-19)

`docs/adr/0004-multilingual-learner-meanings.md` was drafted by a non-slice
governance session and carries `NEEDS COLD REVIEW`. It is **not accepted**;
nothing below is implementable until a fresh cold review approves it
(WORKFLOW §7, AGENTS G7).

**No slice ID or §6 order in the table above is renumbered.** This amendment adds
one blocking condition and three scope notes; the sequence is unchanged.

- **slice-3 closure is paused.** Its implementation was accepted on Attempt 1 at
  `7ceea14e39a7c831edfc803632d3c868ea0f3091` under `Risk: none` and remains
  accepted. It cannot close until ADR-0004 is cold-reviewed **and** the
  implementation is aligned with the new multilingual data contract (a
  language-neutral `sense` plus a normalized localized-meaning relation, in place
  of `sense.gloss_en`).
- **This is an owner-driven governance amendment, not a failed WORKFLOW §5
  attempt.** It adds no attempt to the ladder and does not increment the audit
  counter. The alignment brief is authored by the existing slice-3 orchestrator,
  after cold review — not here.
- **slice-4 remains Gate 2**, in its existing position: Gate 2 measures stage-01
  dictionary coverage *before* the expensive later stages, and ADR-0004 does not
  move it. Its thresholds are unchanged. ADR-0002 §6 order 5 remains their sole
  authority; the block below is a **non-normative** reproduction kept here so a
  plan reader cannot mis-sequence the gate. **If the two ever differ, §6 wins and
  this file is defective.**

```
<85%    -> STOP; governance redesign, no stage 02
85-<95% -> apply the already-specified splitter/fuzzy remedy once, rerun;
           if rerun is still >=85%, record it and continue; <85% -> STOP
>=95%   -> continue
```

- **slice-5 is unchanged**: build stage 02 / Tatoeba index, importing
  `app/resolve.py` and keying its cache on the resolver SHA-256 (AGENTS R2/R3).
- **slice-6's stages 03–05 now include multilingual offline meaning enrichment**
  under ADR-0004 §8. The mid-September 2026 API-credit constraint on stage 04 is
  unchanged by the broadening.
- **Later render/API work** (slice-7 onward) must support the note's selected
  DE/EN/FA meaning set, Persian RTL presentation, and noun-plural-on-the-back
  tri-state rendering before UI/browser completion.

### Operational defaults for the offline build (non-normative)

ADR-0004 D37 specifies **roles**, not products. The current operational
occupants, recorded here so they are not mistaken for architecture:

```
bulk generation:                     GPT-5.6 Luna
selective semantic QA/correction:    GPT-5.6 Terra
```

Swapping either is an operational change and needs no ADR. Prices, cost
estimates, and expected coverage percentages are likewise non-normative; real
counts are measured during the build and recorded in the owning slice's report.
