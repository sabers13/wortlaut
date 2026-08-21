# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0 through slice-5 are accepted, merged and closed.** slice-0
  established the repository/gate skeleton; slice-1 landed the canonical
  resolver/read-only dictionary boundary and R3 scaffold; slice-2 locked Gate 1;
  slice-3 landed deterministic Stage-01 Wiktextract construction plus accepted
  ADR-0004 PART-A alignment; slice-4 completed Gate 2; slice-5 completed
  deterministic Stage-02 Tatoeba example indexing.
* **Gate 2 remains passed at its final accepted decision point.** The real
  textbook baseline measured **189/200 = 94.50%**, triggering the one authorized
  deterministic lexical-piece remedy. Its single rerun measured
  **198/200 = 99.00% → CONTINUE**. No further Gate-2 remedy cycle exists.
* **The accepted Stage-01 asset remains the Stage-02 parent.** Its SHA-256 is
  `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`;
  it has 1118636 lemma rows, 480221 sense rows and 577141 sense_meaning rows
  under the accepted ADR-0004 PART-A stable semantic-reference contract.
* **Stage-02 real-data execution is accepted.** The repaired deterministic
  cache MISS and exact-key HIT produced byte-identical SQLite assets with
  SHA-256
  `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`
  and size `945410048` bytes. The accepted asset contains 777295 persisted
  Tatoeba examples, 6504849 `example_lemma` associations, 99537 distinct indexed
  lemmas, and token-count sum 7292286. Attribution defects and orphan
  associations are both zero.
* **The Stage-02 resolver-containment repair is accepted.** `app/resolve.py`
  remains the single canonical resolver. Stage-02 uses an ephemeral disk-backed
  indexed lookup accelerator to preserve runtime Dictionary lookup semantics
  without per-token full scans of the real Stage-01 tables. The accepted
  resolver SHA-256 is
  `0e7663bf351d177bbc3ac176f1508c549e396bed67e5c3c0928f8d8ad3cbda08`.
* **The deterministic Stage-02 acceptance sanity probe passed.** First/middle/last
  source-ref ordered sample: 90 examples, 745 expected associations, 745 actual,
  0 mismatches, 0 missing expected IDs, 0 unexpected persisted IDs. The
  punctuation and AUX-`haben` forensic cases pass and runtime/Stage-02
  token-by-token parity passes.
* **ADR-0004 remains ACCEPTED / FROZEN.** Cold review #3 was the FINAL
  CONVERGENCE REVIEW; there is no ADR-0004 review #4.
* **ADR-0005 cold review #1 recorded O1–O5; this governance revision preserves
  those objections and applies their explicit remedies. ADR-0005 remains
  `NEEDS COLD REVIEW`; it is neither approved nor frozen.**
  The O1 sequencing remedy gives slice-6 only the Piper image-build/runtime
  prerequisite in addition to its existing stages 03–05 work. Runtime
  pronunciation is still slice-7; E2E pronunciation smoke is still slice-8.
* **Next implementation ownership is slice-6.** It owns stages 03–05, including
  deterministic multilingual enrichment queue construction, maintainer-only
  offline DE/EN/FA generation/validation/selective QA, final dictionary
  packaging and the first Dockerfile with the Piper build prerequisite. Phase A
  explicitly stops before any paid full Stage-04 generation run.
* **Two-authority workflow remains binding.** Local Git/terminal is authoritative
  for working-tree/runtime/gate/local-asset facts; private `origin` is the
  persistent authoritative mirror for committed and pushed state.

## Gate

* **Accepted slice-5 final evidence — PASS:**
  - real Stage-02 cache MISS: PASS / exit 0;
  - exact-key cache HIT: PASS / exit 0;
  - MISS/HIT SHA-256:
    `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`;
  - MISS/HIT byte identity: PASS;
  - MISS/HIT logical equality: PASS;
  - 90-example acceptance sanity: 0 mismatches;
  - Stage-02 targeted tests: **54 passed**;
  - resolver tests: **25 passed**;
  - Stage-01 regression tests: **46 passed**;
  - full accepted pre-closure `make gate`: **223 pytest tests passed**;
  - AGENTS executable checks: **R1, R3, R7 PASS**;
  - `git diff --check`: PASS.
* The slice-6 brief persistence worker reran `make gate` successfully before
  committing `tasks/slice-6.md`.
* The slice-5 closure worker runs the final authoritative post-merge/post-STATE
  `make gate`; stdout and stderr are stored in `handoff/main-gate.txt` and become
  startup evidence for the fresh slice-6 orchestrator.

## Escalation status

* **none active.** Historical slice-5 execution is fully closed:
  original Attempt 1 = T2 Failure 1 (infrastructure interruption);
  original Attempt 2 = T2 Failure 2 (systemd-oomd);
  original Attempt 3 = T3 ceiling failure discovered during acceptance because
  resolver/surface parity produced pathological cross-POS associations.
  The resulting design reset then had Design-reset Attempt 1 = Failure 1 when
  correct lookup semantics proved operationally non-executable through repeated
  full SQLite scans. Design-reset Attempt 2 repaired the Stage-02-only lookup
  complexity, passed its bounded preflight, then passed real MISS/HIT and final
  acceptance. There is no remaining retry or escalation.

## Sessions since last audit

* 6    <!-- slice-5 normal closure increments the prior value 5 exactly once. Audit at >= 10 or when a phase-boundary trigger is established at fresh startup. -->

## Blocked

* **ADR-0005 pronunciation audio remains `NEEDS COLD REVIEW` and blocks
  pronunciation implementation.** Cold review #1 recorded O1–O5; this
  governance revision applies the explicit remedies without approving the ADR.
  The next required action is fresh cold review #2 — focused remedy verification.
  No slice-7/8 pronunciation feature implementation begins until ADR-0005 is
  accepted/frozen.
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
* **Build Stage 04 remains time-bound to mid-September 2026.** Stage 02 is now
  accepted; slice-6 Stage 03 and its explicit Phase-A authorization boundary
  precede any paid multilingual enrichment execution.
* **Non-blocking slice-3 review debt remains in `docs/backlog.md`.** T3 N1 is the
  synthetic fixture `genitive_sg` bind defect; T3 N2 is future fallback
  fingerprint hardening for potentially volatile upstream numeric bookkeeping.

## Next three actions

1. **Open a fresh ADR-0005 cold review #2 — focused remedy verification — against
   the committed/pushed governance revision. Do not open slice-6 first.**
2. **Verify ADR-0005 governance closure.** Only after ADR-0005 reaches an
   approving outcome and repository state is closed/pushed may the slice-6
   startup verification resume.
3. **Open slice-6 with formal startup verification and input check, conditional
   on action 2.** Verify HEAD/manifest, clean local tree, origin sanity, fresh
   `make gate`, STATE consistency, both audit triggers, `Depends: slice-5` merged,
   and the accepted Stage-02 local input before Phase-A dispatch.
