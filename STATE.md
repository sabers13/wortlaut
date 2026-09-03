# STATE

Single entry point for any new session. Maintained by deletion.
Updated only at session CLOSE from repository/gate evidence.

## What landed

* **Wortlaut standalone v2 remains closed, public, published and verified.**
  The canonical full Offline dictionary is v2 SHA-256
  `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
  (945418240 bytes). The existing `dictionary-v2` Release remains unchanged.

* **ADR-0008 remains terminally NON-CONVERGENT / BLOCKED.**
  Its three-review lineage is permanently closed. `tasks/slice-10.md` is
  immutable historical evidence. No review #4 is permitted.

* **ADR-0009 is ACCEPTED / FROZEN.**
  Cold review #2 approved the materially simpler session-scoped Online
  dictionary architecture. No ADR-0009 cold review #3 is required.

* **slice-0 through slice-8 are accepted, merged and closed.**
  They established the repository/gates, dictionary and build pipeline,
  standalone runtime/API, browser product, capture/import/export flows,
  user-state safety, rendering/audio/review behavior, and agent-efficiency
  module infrastructure.

* **Slice 11 is ACCEPTED, INDEPENDENTLY REVIEWED, MERGED AND CLOSED.**
  Reviewed code candidate:
  `ad5d05330a2196d35c33858cf234896cba831247`.

  Slice 11 adds the ADR-0009 provider-level Online dictionary infrastructure:
  `DictionaryProvider`, Local and Online providers, exact deterministic
  lookup/entry/example routing, manifest validation, scalable Bloom membership
  filtering, trusted fixed-repository GitHub Release transport, verified
  immutable shard cache leases, single-flight failure propagation, clear-cache
  coordination, the 32-new-remote-lookup-shard operation budget, deterministic
  256 lookup / 256 entry / 64 example / 1 membership-filter builder topology,
  and Local-vs-Online differential evidence.

  No startup chooser, Settings product behavior, persisted dictionary-mode
  preference, production Online corpus, or Online GitHub Release was created.

  Required independent full-diff risk review:
  **PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS**.
  `HISTORY_ACCEPTABLE`; `PROPORTIONATE`.
  There is no additional Slice-11 review.

* **Slice-11 review carry-forward is NON-BLOCKING.**
  Slice 12 should account for the two implementation-adjacent observations while
  performing its already-required provider migration:
  (1) project provider hit types use `lemma_id` while resolver records use `id`,
  so use a mechanical adapter;
  (2) make Online surface lookup follow Local surface-only semantics rather than
  allowing the lemma-table pre-query to suppress a valid surface fallback.
  The remaining reviewer observations are optional test/documentation/cache
  refinements and are not blockers.

## Gate

* Slice-11 exact reviewed code candidate
  `ad5d05330a2196d35c33858cf234896cba831247`:
  PASS — `ruff` clean; `mypy --strict` clean on 60 source files;
  971 pytest passed; AGENTS R1/R3/R6/R7/R12/R13 PASS;
  MODULES validation PASS for 22 modules.

* Focused Slice-11 final evidence:
  transport 32 passed; cache 15 passed; differential 42 passed;
  builder 9 passed; manifest 22 passed; routing 30 passed.

* Independent reviewer reruns:
  routing + manifest 52 passed; builder + cache 24 passed;
  exact/folded lookup closure spot-check PASS.

* Final merged-main gate after the Slice-11 merge and this STATE commit:
  see `handoff/main-gate.txt`.

## Escalation status

* none active.
* Slice 11 used one implementation lineage followed by bounded
  orchestrator-directed corrections before its single required independent
  risk review. The independent review passed with zero blockers; no additional
  review/repair cycle is open.

## Sessions since last audit

* 3

## Blocked

* **Slice 12 is no longer blocked by Slice 11.**
  Its declared dependencies — ADR-0009 accepted/frozen and Slice 11
  accepted/merged — are satisfied after this closure. It is the next feature
  slice.

* **Slice 13 remains blocked on accepted and merged Slice 12.**
  Slice 13 is publication-only. Production Online shard generation and GitHub
  Release publication remain prohibited until Slice 12 is accepted/closed and
  publication is explicitly authorized.

* ADR-0008 / Slice-10 remain terminal historical evidence.

* Compose integration remains independently blocked by the lecture-app
  Phase-4/donor-evidence prerequisites associated with Slice 9.

* Full paid Stage-04 production work remains deferred by owner decision.

## Next three actions

1. Open a fresh Slice-12 orchestration session against the final pushed `main`.
   Do not perform another Slice-11 review. Slice 12 owns session-only
   Online/Offline startup, chooser/Settings, full `app/api.py` provider
   migration, deterministic Online-fixture E2E, and the two relevant
   non-blocking Slice-11 carry-forward items recorded above.

2. After Slice 12 is accepted and mechanically closed, Slice 13 may be prepared
   as the publication-only production corpus/release stage. Production
   publication remains a separate consequential authorization.

3. Slice 9 / compose integration remains independent and should resume only
   after its existing lecture-app/donor prerequisites are satisfied.
