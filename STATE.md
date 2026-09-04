# STATE

Single entry point for any new session. Maintained by deletion.
Updated only at session CLOSE from repository/gate evidence.

## What landed

* **Wortlaut standalone v2 remains closed, public, published and verified.**
  The canonical full Offline dictionary is v2 SHA-256
  `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
  (945418240 bytes). The existing `dictionary-v2` Release remains unchanged.

* **ADR-0008 remains terminally NON-CONVERGENT / BLOCKED.**
  Its three-review lineage is permanently closed. `tasks/slice-10.md` remains
  immutable historical evidence. No review #4 is permitted.

* **ADR-0009 remains ACCEPTED / FROZEN.**
  Cold review #2 approved the session-scoped Online/Offline dictionary
  architecture. No ADR-0009 cold review #3 is required.

* **slice-0 through slice-8 remain accepted, merged and closed.**

* **Slice 11 remains ACCEPTED, INDEPENDENTLY REVIEWED, MERGED AND CLOSED.**
  It provides the Online dictionary provider infrastructure, deterministic
  routing/shards, fixed Product GitHub Release trust boundary, verified cache
  leases, operation budget, builder and Local/Online differential contract.

* **Slice 12 is ACCEPTED, INDEPENDENTLY REVIEWED, MERGED AND CLOSED.**
  Reviewed code candidate:
  `34d627912562a15e3c7852abc46fdd1aa4a98956`.

  Slice 12 adds the complete session-scoped dictionary product:
  explicit Online/Offline CLI selection; true no-dictionary chooser state;
  trusted Product Online activation only on user choice; Settings switching;
  hardened full Offline install with conservative free-space preflight and real
  progress; exact managed Offline removal; concurrency-safe Online-cache clear;
  restart-after-removal behavior; and full served-product migration onto the
  accepted `DictionaryProvider` contract.

  Online mode now covers lookup, highlight, CSV import, candidate
  materialization, card creation, card rendering/study and export paths without
  a full local dictionary. Browser/API callers cannot configure dictionary
  source URLs, manifests, repositories, hosts, hashes or paths.

  Dictionary mode remains process/session-only. No `online`, `offline` or
  `unconfigured` application preference is persisted.

  Required independent full-diff risk review:
  **PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS**.
  `HISTORY_ACCEPTABLE`; `PROPORTIONATE`.
  No second broad Slice-12 review is required.

  Reviewer notes about dead `_ConnectionLookupOracle` code, repeated mini-corpus
  test construction, and the 120-second progress polling ceiling are explicitly
  NON-BLOCKING and require no Slice-12 follow-up.

  No production Online corpus or `dictionary-online-v2` Release was created by
  Slice 12. The existing `dictionary-v2` Release remains unchanged.

## Gate

* Slice-12 reviewed code candidate
  `34d627912562a15e3c7852abc46fdd1aa4a98956`:
  PASS — frontend unit tests 47 passed; Playwright 25 passed, 0 failed;
  `ruff` clean; `mypy --strict` clean on 63 source files;
  1002 pytest passed; AGENTS R1/R3/R6/R7/R12/R13 PASS;
  MODULES validation PASS for 23 modules; final `make gate` exited 0.

* Mechanical provider-bypass check on the reviewed candidate:
  `app/api.py` contains zero
  `_current_generation.asset.connection` product dictionary-read uses.

* Final merged-main gate after the Slice-12 merge and this STATE commit:
  see `handoff/main-gate.txt`.

## Escalation status

* none active.
* Slice 12 used one implementation lineage with bounded
  orchestrator-directed pre-review corrections and validation-blocker repairs,
  followed by exactly one independent full-diff risk review.
  That review passed with zero blockers. No further Slice-12 review or repair
  cycle is open.

## Sessions since last audit

* 4

## Blocked

* **Slice 13's dependency on Slice 12 is satisfied after this closure.**
  Slice 13 is the publication-only production corpus/release stage.
  Its implementation may not publish anything until the owner explicitly
  authorizes the consequential production publication action.

* The existing `dictionary-v2` Release must not be modified by Slice 13.

* ADR-0008 / Slice-10 remain terminal historical evidence.

* Compose integration remains independently blocked by the lecture-app
  Phase-4/donor-evidence prerequisites associated with Slice 9.

* Full paid Stage-04 production work remains deferred by owner decision.

## Next three actions

1. Open a fresh Slice-13 orchestration session against the final pushed `main`.
   Do not perform another Slice-12 review. Verify normal startup state,
   dependencies and audit triggers.

2. Before any production build/upload/release action, obtain explicit owner
   authorization for Slice 13 publication. Then execute only
   `tasks/slice-13.md`: build and validate the production 577-asset Online
   corpus from the verified v2 dictionary, enforce the release-asset ceiling,
   publish the separate `dictionary-online-v2` Release, and anonymously verify
   the Product trust path. Never modify `dictionary-v2`.

3. After successful Slice-13 publication and final real end-user Online +
   Offline verification, declare the standalone Online/Offline Wortlaut product
   complete. Lecture-app compose integration remains a separate later project.
