# STATE

Single entry point for any new session. Maintained by deletion.
Updated only at session CLOSE from repository/gate evidence.

## What landed

* **Wortlaut standalone Online/Offline is COMPLETE, PUBLIC, PUBLISHED AND
  VERIFIED.**

  The standalone application now has both production dictionary modes:

  - Offline:
    GitHub Release `dictionary-v2`, release id `381651690`,
    asset `dictionary-v2.sqlite` id `541973166`,
    945418240 bytes, SHA-256
    `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.

  - Online:
    GitHub Release `dictionary-online-v2`, release id `383167908`,
    579 uploaded files total: 577 corpus assets plus production manifest and
    attribution. The Release target remains the reviewed pre-publication
    candidate `aafbd58142dc5c4710010eb650fe7179178233b3`.

  Both modes use the same logical dataset / asset token:

  `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.

  Production Online manifest SHA-256:

  `e3565f0f087ced0b16aca3d3f5d93ce73c20166bc998ab61ede88cd6c390dd24`.

  The public Online Release passed anonymous verification with no GitHub
  authentication token. The existing `dictionary-v2` Release remained
  unchanged throughout Slice 13.

* **ADR-0008 remains terminally NON-CONVERGENT / BLOCKED.**
  Its lineage is permanent historical evidence. No review #4 is permitted.

* **ADR-0009 remains ACCEPTED / FROZEN.**
  No ADR-0009 cold review #3 is required.

* **slice-0 through slice-8 remain accepted, merged and closed.**

* **Slice 11 remains ACCEPTED, INDEPENDENTLY REVIEWED, MERGED AND CLOSED.**
  It provides deterministic Online dictionary provider infrastructure,
  routing/shards, the fixed GitHub Product trust boundary, verified immutable
  cache leases, the operation budget, builder, and Local/Online differential
  contract.

* **Slice 12 remains ACCEPTED, INDEPENDENTLY REVIEWED, MERGED AND CLOSED.**
  Its original independent full-diff review passed with non-blocking notes and
  zero blockers. No second broad Slice-12 review is required.

  A later real post-publication smoke exposed one narrow explicit-Online
  launcher defect. The bounded repair
  `9125b1459227123adf54572e7aa10b3b1a6569f9`
  corrected startup precedence so explicit:

      --dictionary-mode online

  no longer requires the 945 MB Offline dictionary and now binds the trusted
  Online provider immediately rather than starting `unconfigured`.

  That repair is contained in the accepted final Slice-13 tree.

* **Slice 13 is ACCEPTED, INDEPENDENTLY REVIEWED, PUBLISHED, INTEGRATED,
  MERGED AND CLOSED.**

  Reviewed pre-publication candidate:

  `aafbd58142dc5c4710010eb650fe7179178233b3`.

  Required final independent full-diff risk review:

  **PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS**.

  The review phase is CLOSED. No second broad Slice-13 review is required.

  Final accepted Slice-13 branch HEAD after publication receipt and the bounded
  explicit-Online repair integration:

  `e3d7bfe887f2e2d9f19da6cc9b35dee952dec611`.

  The exact committed combined tree passed real Product smoke with NO overlay:

  - explicit Online on a fresh data directory:
    starts directly in `online` mode;
    `canonical_offline_present = false`;
    no `/use-online` call is required;
    `GET /vocab/lookup?q=Haus` returns HTTP 200 with valid candidates;
    no full Offline dictionary is created;

  - default first-run startup with no Offline dictionary:
    starts `unconfigured`;
    Online cache contains zero downloaded files before user choice;
    `POST /vocab/settings/dictionary/use-online` activates trusted Online;
    subsequent `Haus` lookup returns HTTP 200.

  The product therefore satisfies the intended end-user session model:
  users can run Online without the 945 MB Offline database, optionally download
  Offline, switch safely during a session, and preserve cards/reviews/user
  state. Dictionary mode remains session/process-only and is not persisted.

## Gate

* Final accepted integrated Slice-13 candidate
  `e3d7bfe887f2e2d9f19da6cc9b35dee952dec611`:

  - focused launcher tests: 37 passed
  - focused Slice-12 Settings tests: 25 passed
  - `ruff`: PASS
  - `mypy --strict`: PASS on 64 source files
  - pytest: 1007 passed, 164 warnings
  - AGENTS: R1/R3/R6/R7/R12/R13 PASS
  - MODULES validation: 23 modules PASS
  - `make gate`: exit 0

* Production differential after the earlier CF2 repair:
  1179 / 1179 PASS.

* Public Online corpus:
  577 corpus assets; 579 total Release files; anonymous Product-path
  verification PASS.

* Final merged-main gate after Slice-13 merge and this STATE commit:
  see `handoff/main-gate.txt`.

## Escalation status

* none active.
* Slice 13 required one final independent full-diff risk review.
  It passed with zero blockers and the review phase closed.
* The later explicit-Online startup defect was handled as one bounded
  post-publication repair followed by exact combined-tree integration
  verification. It did not reopen a broad Slice-12 or Slice-13 review cycle.
* No standalone repair, implementation, review, or publication cycle remains
  open.

## Sessions since last audit

* 5

## Blocked

* **No blocker remains for the standalone Wortlaut Online/Offline product.**
  The standalone product is complete.

* Compose integration in `tasks/slice-9.md` remains a separate future project
  boundary. It must not start until its lecture-app Phase-4 and donor-evidence
  prerequisites are actually satisfied.

* ADR-0008 / Slice-10 remain terminal historical evidence.

* Full paid Stage-04 enrichment remains deferred by owner decision.

## Next three actions

1. Stop standalone feature work. Do not create Slice 14 merely to continue
   improving a product that has reached its declared standalone finish line.

2. Keep `tasks/slice-9.md` dormant until the lecture app is independently ready
   and every compose-integration prerequisite in that brief can be verified.
   When that future boundary is reached, use a fresh orchestration session.

3. Treat any later cleanup, optimization, or optional enhancement as future
   maintenance/versioned work. Do not reopen accepted Slice 11, Slice 12,
   Slice 13, ADR-0008, or ADR-0009 merely for optional improvements.
