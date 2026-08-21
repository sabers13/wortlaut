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
* **ADR-0005 is ACCEPTED / FROZEN.** Cold review #2 — FOCUSED REMEDY
  VERIFICATION — approved the O1–O5 remedies. O1–O5 and their resolution history
  remain preserved. Slice-6 owns only the Piper image-build/runtime
  prerequisite; slice-7 owns runtime pronunciation; slice-8 owns pronunciation
  E2E smoke.
* **ADR-0006 is ACCEPTED / FROZEN.** Cold Review #2 — FOCUSED REMEDY
  VERIFICATION — verified O1–O7 remedies, checked their direct knock-on
  contradictions, and found no qualifying blocker. Its §10 supersession of the
  listed ADR-0004 provisions is active; ADR-0004 remains frozen and binding
  elsewhere. Direct canonical English-edition FA evidence is primary,
  German-Wiktionary is optional/fail-closed fallback, FA sets are deterministic,
  DE eligibility is conservative, Batch manifests are bounded/correlated, and
  owner source acceptance remains a hard gate. ADR acceptance itself authorizes
  no paid production work.
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
* **ADR-0006 Cold Review #2 governance persistence uses fresh local gate
  evidence.** Its acceptance commit is valid only with the supervised worker's
  pre-mutation, pre-commit and post-commit `make gate` PASS evidence plus
  clean-tree/push equality returned in the review receipt; the GitHub mirror is
  not substituted for local execution evidence.

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

* 6    <!-- non-slice ADR cold review does not increment this counter -->

## Blocked

* **Slice-6 paid production remains blocked by ADR-0006 D71 owner gates,
  not by ADR governance.** Architecture-changing Slice-6 implementation may begin
  only after formal startup/local verification on accepted main. No paid
  production submission is authorized until the source-acceptance, coverage/gap,
  DE queue/canary/QA, current Batch capability/limit, manifest/cost, and explicit
  orchestrator-authorization gates are satisfied.
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
* **Build Stage 04 remains time-bound to mid-September 2026.** ADR-0006
  governance is closed, but paid canary/production work remains subject to its
  explicit owner gates; acceptance itself authorizes no paid run.
* **Non-blocking slice-3 review debt remains in `docs/backlog.md`.** T3 N1 is the
  synthetic fixture `genitive_sg` bind defect; T3 N2 is future fallback
  fingerprint hardening for potentially volatile upstream numeric bookkeeping.

## Next three actions

1. Open the formal Slice-6 orchestrator/startup session against the accepted
   ADR-0006 governance commit on `main`.
2. Verify the authoritative local checkout, origin synchronization, accepted
   Stage-02 asset SHA/bytes/integrity/counts, dependencies, and a fresh
   `make gate` before any Slice-6 dispatch.
3. Only if startup passes, dispatch Slice-6 Attempt 1 under `tasks/slice-6.md`.
   ADR acceptance authorizes no paid canary or production run; those remain
   behind the explicit Slice-6 / ADR-0006 gates.
