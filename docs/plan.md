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
| slice-3 | 4 | — | Stage 01 output carries the schema/attribution contract Gate 2 consumes, including the accepted ADR-0004 PART-A alignment. Order 4 closes normally after its required migration-risk full-diff review passes, then Gate 2 may begin. |
| slice-4 | 5 | — | §6 order 5's thresholds govern verbatim. A design gate, not a §5 retry ladder: `<85%` returns to governance. |
| slice-5 | 6 | — | Stage 02 imports `app/resolve.py`; cache keys include its SHA-256 (AGENTS R2/R3). |
| slice-6 | 7 | — | **ADR-0006 is `ACCEPTED / FROZEN`; its §10 supersession record is active.** ADR-0004 remains frozen and binding except where §10 explicitly supersedes it. Stages 03–05 use direct exact Persian evidence on the persisted English-edition canonical source sense, optional German-Wiktionary fallback only through an exact bridge, source acceptance/coverage STOP, conservative DE source eligibility with generation on uncertainty, and bounded correlated Batch manifests. The Piper image-build prerequisite remains separately scoped; no paid production run proceeds until all ADR gates are met. |
| slice-7 | 8 | — | ADR-0003 review/mastery semantics and AGENTS R12/R13 land before browser integration; render/API supports note's selected DE/EN/FA meaning set, Persian RTL, tri-state noun plural on back (ADR-0004 §10), PART-B durable bindings, D47 atomic dictionary activation/relink, and stale-picker HTTP 409 before UI/browser completion; owns runtime pronunciation feature (note-local custom record/upload persistence, stable pronunciation identity, human-media policy and exact-id discovery, precedence, human/Piper cache, crash-safe replacement and API/render integration). |
| slice-8 | 9 | — | `reference/smoke_test.py` path defect repaired; assertions match ADR-0002 §4/§5, ADR-0003 §5, and ADR-0004 D47 replacement/stale-picker scenarios; owns end-to-end pronunciation smoke (override/revert, browser-local unsaved preview, unsafe media, identity/replacement cases, human-cache integrity corruption, offline/remote failure and Piper fallback). |
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

`docs/adr/0004-multilingual-learner-meanings.md` was approved and frozen at cold
review #3 — FINAL CONVERGENCE REVIEW. `NEEDS COLD REVIEW` is removed.

**No slice ID or §6 order in the table above is renumbered.** This amendment adds
one blocking condition and three scope notes; the sequence is unchanged.

- **slice-3 ADR-0004 alignment requirement is satisfied.** The original
  Attempt-1 implementation was accepted at
  `7ceea14e39a7c831edfc803632d3c868ea0f3091`. The owner-driven PART-A alignment
  then landed at `7423cb5147d1419dba4480826accf67243258a2d` and the mandatory
  migration-risk T3 full-diff review passed at accepted slice head
  `89c9b89b93addd4211a931d5415e5c8d613a6f45`. No WORKFLOW §5 attempt or audit
  increment was added by the governance alignment. The accepted alignment
  provides PART-A stable lemma/sense semantic references
  (`lemma.semantic_ref`, `sense.semantic_ref`), `sense.source_ref`, deterministic
  D46 component semantic-binding data, D36/D45 `sense_meaning` /
  `sense_meaning_derivation`, and the tri-state noun plural contract
  (`lemma.plural`, `lemma.plural_none`). No governance blocker remains; normal
  slice-3 closure completes order 4. Runtime activation/API work remains outside
  slice-3.
- **This is an owner-driven governance amendment, not a failed WORKFLOW §5
  attempt.** It adds no attempt to the ladder and does not increment the audit
  counter. The alignment brief is `tasks/slice-3-alignment.md`.
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
- **slice-6 / order 7:** This ADR-0004 amendment originally left Stages 03–05
  multilingual enrichment unchanged. Accepted ADR-0006 now supersedes ADR-0004
  only as listed in ADR-0006 §10. The first Docker/runtime foundation additionally
  installs and verifies the pinned Piper engine plus selected German voice/model
  at image-build time and records their separate distribution classifications/required
  notices. This is prerequisite only: no pronunciation API/cache/custom
  media/human discovery/UI and no bulk audio generation/database. The
  mid-September 2026 API-credit constraint on stage 04 is unchanged.
- **slice-7 / order 8 (runtime app work):** In addition to the existing
  ADR-0003/ADR-0004 runtime work (PART-B durable dictionary bindings, active
  dictionary version+SHA metadata, `note_meaning_lang`, `note_user_meaning`,
  supersession of scalar `note.gloss_user`, D43/D46 read/render behaviour,
  user-meaning precedence, Persian RTL, tri-state noun plural rendering, the
  language-bearing `/vocab/gloss` POST/DELETE endpoint, stable picker refs plus
  dictionary asset token, stale-token HTTP 409 rejection, D47 atomic
  activation/relink/rollback, and AGENTS R12/R13 runtime enforcement before
  browser integration), under accepted ADR-0005 it owns the runtime
  pronunciation feature: note-local custom record/upload persistence, stable
  pronunciation identity, human-media policy and exact-id discovery, precedence,
  human/Piper cache, crash-safe replacement and API/render integration.
- **slice-8 / order 9 (smoke work):** In addition to the existing smoke work
  (repairing the `reference/smoke_test.py` baseline and end-to-end D47
  replacement/stale-picker verification), under accepted ADR-0005 it owns
  end-to-end pronunciation smoke: override/revert, browser-local unsaved preview,
  unsafe media, identity/replacement cases, human-cache integrity corruption,
  offline/remote failure and Piper fallback.

## Governance amendment — ADR-0005 approval (2026-08-21)

`docs/adr/0005-pronunciation-audio.md` was approved and frozen at cold review #2 —
**FOCUSED REMEDY VERIFICATION**. `NEEDS COLD REVIEW` is removed and ADR-0005 is
`ACCEPTED / FROZEN`. Cold review #2 approved the O1–O5 remedies and confirmed
cross-file coherence.

The pronunciation scope assignments are active:
- **slice-6** owns the Piper build/runtime prerequisite only (pinned engine,
  pinned German voice/model, and distribution classification verification at
  image-build time); no pronunciation API/database/cache/custom media/human
  discovery/UI work enters slice-6;
- **slice-7** owns the runtime pronunciation feature;
- **slice-8** owns end-to-end pronunciation smoke.

ADR-0005 does not change Stage-04 multilingual meaning-generation scope or
the mid-September 2026 API-credit expiry boundary; accepted ADR-0006 separately
governs the Persian/source-first and Batch amendments recorded below.

## Governance activation — ADR-0006 (2026-08-21)

ADR-0006 is `ACCEPTED / FROZEN` after Cold Review #2 — FOCUSED REMEDY
VERIFICATION. It does not reopen ADR-0004. Its §10 supersession record is active;
ADR-0004 remains binding everywhere not explicitly superseded there.

- Persian is ingested source-first from the direct exact
  English-edition canonical source relation; German-Wiktionary is optional
  fallback only through a proven exact cross-edition bridge, then coverage report
  and owner STOP.
  Persian LLM generation is zero unless a later explicit owner decision permits
  a separately bounded policy.
- Stage-03 must not reuse the historical 480,221 Persian LLM jobs. Persian source
  ingestion occurs before final generated DE/EN queue materialization.
- Existing suitable source-backed German learner meanings are preserved; only
  unsuitable/missing learner wording produces one isolated German request.
- Every generated item stays one model request. Production Batch
  is bounded deterministic transport with manifest-first upload/correlation,
  per-manifest durability, exact-one ambiguous reconciliation, and fail-closed
  output joining. Current provider/model support, limits, and cost are checked
  immediately before paid use, not frozen architecture.
- The historical Persian canary remains preserved and retired evidence. The
  former Persian model-comparison prerequisite is historical unless a future
  owner decision authorizes Persian LLM fallback.

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
