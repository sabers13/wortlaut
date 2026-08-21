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
| slice-6 | 7 | — | Stages 03–05 and ADR-0004 multilingual enrichment remain unchanged; first Docker/runtime foundation additionally installs and verifies pinned Piper engine plus selected German voice/model at image-build time and records separate distribution classifications/required notices (prerequisite only: no pronunciation API/cache/custom media/human discovery/UI and no bulk audio generation/database); stage 04 completes before mid-September 2026 API-credit expiry. |
| slice-7 | 8 | — | ADR-0003 review/mastery semantics and AGENTS R12/R13 land before browser integration; render/API supports note's selected DE/EN/FA meaning set, Persian RTL, tri-state noun plural on back (ADR-0004 §10), PART-B durable bindings, D47 atomic dictionary activation/relink, and stale-picker HTTP 409 before UI/browser completion; after ADR-0005 is accepted, owns runtime pronunciation feature (note-local custom record/upload persistence, stable pronunciation identity, human-media policy and exact-id discovery, precedence, human/Piper cache, crash-safe replacement and API/render integration). |
| slice-8 | 9 | — | `reference/smoke_test.py` path defect repaired; assertions match ADR-0002 §4/§5, ADR-0003 §5, and ADR-0004 D47 replacement/stale-picker scenarios; after ADR-0005 is accepted, owns end-to-end pronunciation smoke (override/revert, browser-local unsaved preview, unsafe media, identity/replacement cases, human-cache integrity corruption, offline/remote failure and Piper fallback). |
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
- **slice-6 / order 7:** Stages 03–05 and ADR-0004 multilingual enrichment
  remain unchanged. The first Docker/runtime foundation additionally installs
  and verifies the pinned Piper engine plus selected German voice/model at
  image-build time and records their separate distribution classifications/required
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
  browser integration), after ADR-0005 is accepted it owns the runtime
  pronunciation feature: note-local custom record/upload persistence, stable
  pronunciation identity, human-media policy and exact-id discovery, precedence,
  human/Piper cache, crash-safe replacement and API/render integration.
- **slice-8 / order 9 (smoke work):** In addition to the existing smoke work
  (repairing the `reference/smoke_test.py` baseline and end-to-end D47
  replacement/stale-picker verification), after ADR-0005 is accepted it owns
  end-to-end pronunciation smoke: override/revert, browser-local unsaved preview,
  unsafe media, identity/replacement cases, human-cache integrity corruption,
  offline/remote failure and Piper fallback.

## Governance amendment — ADR-0005 revision (2026-08-21)

`docs/adr/0005-pronunciation-audio.md` remains `NEEDS COLD REVIEW`. Cold review #1
recorded blocking objections O1–O5; this governance revision preserves those
objections and applies the explicit remedies without approving the ADR. The next
required governance action is fresh **cold review #2 — focused remedy
verification**.

The slice-6 Piper requirement above is only the pre-runtime image prerequisite
identified by O1 (pinned engine, pinned German voice/model, and distribution
classification verification at image-build time). It does not authorize
pronunciation runtime implementation before ADR approval. No slice-7/8
pronunciation feature implementation begins until ADR-0005 is accepted/frozen.

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
