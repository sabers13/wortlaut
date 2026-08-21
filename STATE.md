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
* **ADR-0006 cold review #1 is BLOCKED with O1–O7 recorded.** `NEEDS COLD REVIEW`
  remains. The blockers cover the actual Stage-01 source-sense lineage for
  DE→FA, pre-acceptance authority, FA multi-translation cardinality/order,
  deterministic DE source-row eligibility, ambiguous Batch-create recovery,
  bounded multi-manifest Batch partitioning, and ownership/failure handling for
  the Persian human-review sample. A separate ADR revision session must resolve
  them before fresh cold review #2.
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
* **ADR-0006 cold-review close did not establish a new authoritative local
  `make gate` result in this session.** The connected GitHub mirror is
  authoritative for the committed governance result, but WORKFLOW's authority
  split does not permit remote repository state to stand in for a fresh local
  gate or local working-tree cleanliness. Fresh local gate evidence is therefore
  required at the next supervised/local execution checkpoint before any
  implementation dispatch.

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

* **ADR-0006 / Slice-6 source-first enrichment is governance-blocked.** Cold
  review #1 recorded O1–O7. Do not dispatch architecture-changing Slice-6 work
  from the pending ADR. The next action is a separate ADR-0006 revision session,
  followed by fresh cold review #2 under WORKFLOW §7 / AGENTS G7.
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
* **Build Stage 04 remains time-bound to mid-September 2026.** The governance
  blocker now precedes any paid canary or production run; no paid Persian or
  DE/EN production work is authorized while ADR-0006 remains unaccepted.
* **Non-blocking slice-3 review debt remains in `docs/backlog.md`.** T3 N1 is the
  synthetic fixture `genitive_sg` bind defect; T3 N2 is future fallback
  fingerprint hardening for potentially volatile upstream numeric bookkeeping.

## Next three actions

1. **Open a separate ADR-0006 revision session.** Read O1–O7 from
   `docs/adr/0006-source-first-persian-and-batch-enrichment.md`; preserve the
   objection text; resolve each objection explicitly in the ADR and required
   cross-file governance contracts without implementing Slice-6.
2. **After revision, open fresh cold review #2 — FOCUSED REMEDY VERIFICATION.**
   Verify O1–O7 remedies plus direct knock-on contradictions only; optional
   redesign/refinement is not a blocker under WORKFLOW §7.
3. **Only after ADR-0006 acceptance**, resume Slice-6 from formal startup/local
   verification against the accepted Stage-02 asset and fresh `make gate`
   evidence. No paid API run is authorized by the governance review itself.
