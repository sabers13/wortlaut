# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0 through slice-4 are accepted, merged and closed.** slice-0 established
  the repository/gate skeleton; slice-1 landed the canonical resolver/read-only
  dictionary boundary and R3 scaffold; slice-2 locked Gate 1; slice-3 landed
  deterministic Stage-01 Wiktextract → SQLite construction plus accepted
  ADR-0004 PART-A alignment; slice-4 completed ADR-0002 §6 order 5 / Gate 2.
* **Gate 2 passed its final accepted decision point.** The real textbook baseline
  measured **189/200 = 94.50%** and mechanically entered `REMEDY_REQUIRED`.
  Exactly one authorized deterministic lexical-piece coverage remedy was then
  applied and rerun once, producing **198/200 = 99.00%** with final disposition
  `CONTINUE`. The two remaining misses were `hundertundeins` and
  `das Nebenfach`. There is no second Gate-2 remedy cycle.
* **The real Stage-01 asset consumed by Gate 2 was successfully hardened against
  real Wiktextract input.** At slice-4 evidence time it had SHA-256
  `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`,
  767926272 bytes, 1118636 lemma rows, 480221 sense rows and 577141
  sense_meaning rows.
* **Stage-01 retains the accepted ADR-0004 PART-A identity/meaning contract.**
  Stable lemma/sense semantic refs, source namespace/ref, normalized
  `sense_meaning`, derivation provenance, tri-state noun plural and deterministic
  D46 component semantic bindings remain landed. Numeric dictionary IDs are
  current-asset keys only.
* **ADR-0004 remains ACCEPTED / FROZEN.** Cold review #3 was the FINAL
  CONVERGENCE REVIEW; there is no review #4.
* **Next implementation ownership is unchanged.** slice-5 owns Stage 02 /
  deterministic Tatoeba example indexing. slice-6 owns stages 03–05 including
  offline multilingual enrichment. slice-7 owns PART-B/runtime meanings,
  render/API, durable dictionary bindings, D47 activation/relink and R12/R13.
  slice-8 owns smoke/replacement verification. slice-9 owns later lecture-app
  compose integration.
* **Two-authority workflow remains binding.** Local Git/terminal is authoritative
  for working-tree/runtime/gate facts; private `origin` is the persistent
  authoritative mirror for committed and pushed state.

## Gate

* **Accepted slice-4 Gate-2 evidence — PASS on 2026-08-20:**
  baseline **189/200 = 94.50%** → `REMEDY_REQUIRED`;
  one-time remedy rerun **198/200 = 99.00%** → `CONTINUE`.
* Slice-4 remedy verification passed:
  `tests/test_gate2_coverage.py` — **37 passed**;
  `tests/test_build_dict_stage01.py` — **46 passed**;
  full pre-closure `make gate` — **166 pytest tests passed**;
  direct-script remedy subprocess PASS;
  PYTHONPATH not required;
  no `app/` modification;
  `git diff --check` PASS.
* The closure worker runs the final authoritative post-merge/post-STATE
  `make gate`; stdout and stderr are stored in `handoff/main-gate.txt` and become
  the startup evidence for the fresh slice-5 orchestrator.

## Escalation status

* **none.** Slice-4's historical first implementation ladder reached the
  WORKFLOW §5 T3 ceiling while hardening real Stage-01/measurement execution and
  therefore returned to design. The resulting design-reset task succeeded, Gate 2
  then completed normally, and no active escalation remains. The historical
  ladder is closed.

## Sessions since last audit

* 5    <!-- slice-4 normal closure increments the prior value 4 exactly once. Audit at >= 10 or when a phase-boundary trigger is established at fresh startup. -->

## Blocked

* **ADR-0004 PART-B/runtime schema remains intentionally deferred to slice-7.**
  Remaining work includes note-local multilingual meaning state, durable
  dictionary bindings, active dictionary version+SHA state and D47 runtime
  activation/relink semantics.
* **ADR-0002 D27 / ADR-0003 D27 share one identifier.** Both accepted decisions
  remain valid; repair remains parked naming debt.
* **`reference/smoke_test.py` remains path-broken/excluded.** slice-8 owns its
  repair plus D47 replacement/stale-picker smoke verification.
* **Compose integration remains independently blocked** by the lecture app's
  Phase-4 decomposition and required donor evidence; slice-9 owns that boundary.
* **Build stage 04 remains time-bound to mid-September 2026.** Gate 2 is now
  complete; Stage 02 and Stage 03 still precede the multilingual enrichment run.
* **Non-blocking slice-3 review debt remains in `docs/backlog.md`.** T3 N1 is the
  synthetic fixture `genitive_sg` bind defect; T3 N2 is future fallback
  fingerprint hardening for potentially volatile upstream numeric bookkeeping.

## Next three actions

1. **Open slice-5 with formal startup verification.** Verify this closure's final
   main HEAD/manifest, clean local tree, origin sanity, fresh `make gate`, STATE
   consistency, both audit triggers, and `Depends: slice-4` merged.
2. **Establish slice-5's required local Stage-02 inputs before dispatch.** Verify
   or re-establish the accepted Stage-01 asset, then supply deterministic German
   and English Tatoeba sentence projections, the DE→EN links projection, a
   non-empty export/date label and the current verified Tatoeba license label.
   Record their SHA-256 values; keep all source/build/cache assets local and
   uncommitted.
3. **Dispatch slice-5 Stage-02 implementation** per `tasks/slice-5.md` to
   `claude-code / T2 / high` (fallback `codex / T2 / high`). Stage 02 imports the
   canonical resolver, uses `tools.resolver_hash` for cache identity, indexes
   Tatoeba examples deterministically, and does not perform Stage 03+ work.
