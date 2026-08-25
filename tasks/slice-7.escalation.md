# Slice-7 escalation record

- Original brief: tasks/slice-7.md
- Attempt 1 (gpt-5.6-terra / T3 / high): monolithic whole-slice dispatch,
  run `run_e002589566` attempt a1 — deterministic gate FAIL (exit 2). Root
  cause: isolated orch worktree has no `.venv`, so the Makefile falls back to
  system tools and strict mypy cannot resolve `spacy`
  (`import-not-found` x4). Not an implementation defect.
- Attempt 2 (gpt-5.6-terra / T3 / high): same dispatch, attempt a2 —
  implementation substantially complete (~1,120 inserted lines across schema,
  deck, dictionary, render, audio, api, check_agents; targeted ruff/mypy PASS,
  56 targeted tests PASS). Worker STOPped when its provider sandbox blocked
  `git commit` (read-only `.git/worktrees/<id>/index.lock` outside the
  workspace-write scope). The engine captured the candidate (`4724c38`) and the
  gate failed on the same worktree-environment defect as attempt 1.
- The failures agree on: the isolated-worktree gate environment cannot satisfy
  `make gate` (missing project venv ⇒ spaCy unresolvable), independent of
  implementation quality; secondarily, worker-side git commits are impossible
  under the provider sandbox and are unnecessary because the orchestration
  engine captures candidates itself.
- Orchestrator's respecification (WORKFLOW §5.3 ceiling → design split):
  slice-7 implementation is re-dispatched as six gated sub-dispatches accepted
  sequentially onto `slice/7` —
  S1 schema + deck core (A1–A3 deck-side),
  S2 dictionary identity/activation (A5),
  S3 rendering (A4),
  S4 audio (A6),
  S5 app factory/API/security guards (A7),
  S6 executable AGENTS checks + slice report (A8, A10).
  Run gates symlink the authoritative main `.venv` into the worktree before
  `make gate`; workers are forbidden from any git mutation (the engine stages
  and commits candidates). Owner approved the split, chained auto-acceptance
  of gate+review-passing sub-candidates, and the environment measures on
  2026-08-24. The mandatory WORKFLOW §6 T3 full-diff review over the entire
  `main...slice/7` diff remains required before merge and is not replaced by
  per-sub-run reviews.

## Stage S1 review-repair addendum (2026-08-24)

- S1 implementation attempt 1 (`run_a9892eedd7`, candidate `cac2e74`): gate
  PASS; independent gpt-5.6-sol stage review BLOCKED with five findings
  (tracked `.venv` symlink — orchestrator gate-mechanism defect; orphan move
  gated on review history; D43 status-coupled availability; FSRS transition
  outside the review transaction; unenforced non-empty `note_meaning_lang`).
- S1 same-tier retry (attempt 2, `run_2f2f17fcd3`, candidate `f454ca5`): gate
  PASS; all five findings fixed; follow-up gpt-5.6-sol review BLOCKED with
  three narrower residual findings: implicit `meaning_languages=("en",)`
  creation default (contradicts ADR-0004 §6.4/D44); derived-compound component
  vector validated after `bound` filtering, letting a truncated contiguous
  prefix pass (D46 all-components-or-none); deck-deletion membership read
  outside the deletion transaction, allowing a concurrent membership insert to
  lose its Orphaned placement (AGENTS R5).
- Owner disposition (2026-08-24, this chat): one narrow T3 repair dispatch
  reproducing the attempt-2 content plus exactly those three corrections,
  followed by a fresh independent review. If that review BLOCKs again, Stage
  S1 returns to design (split/redesign) with no further repair attempts. This
  addendum documents why the third pass is a bounded repair under the §5.3
  respecification umbrella rather than an uncounted brute-force retry.
- S1 bounded repair (attempt 3, `run_e9735fd409`, candidate `bfe10ef`): gate
  PASS; final stop-or-go gpt-5.6-sol review confirmed F1 and F3 fixed with no
  regressions, but BLOCKED on one structural residual: the D46 vector check
  compared surviving ordinals against the surviving row count (circular), and
  no independently persisted expected component count existed, so trailing-row
  loss still passed as a valid vector.
- Design return per the authorized stop-or-go: owner approved amending
  `tasks/slice-7.md` (A1 item 8 and A5) so derived_compound notes persist an
  expected ordered `component_count` captured at creation and revalidated at
  D47 relink; full-vector validation precedes any binding-status filtering and
  an undeterminable count fails closed. This completes frozen ADR-0004 D46's
  ordered component vector without amending the ADR. Stage S1 is re-dispatched
  fresh from attempt 1 of the amended stage contract per WORKFLOW §5.3.
  Outcome: fresh S1 dispatch (`run_ac40b393db`, candidate `a678f1b`) passed
  gate and the gpt-5.6-sol review (VERDICT: PASS, defeat-check included) and
  was accepted onto `slice/7`.

## Stage S2 ceiling and split (2026-08-24)

- S2 attempt 1 (`run_e9a8cb7f0b`, `ff9fadf`): gate PASS; sol review BLOCKED
  (5): token check outside the write transaction; lookup tokens derived from
  the constructed path instead of active metadata (mixed-state exposure);
  arbitrary `lemma:v*`/`sense:v*` strings accepted as stable identity;
  `asset_token=None` permitted without active metadata; mandated
  corrupted-candidate and single-transaction assertions missing.
- S2 same-tier retry (`run_2c11e3f861`, `efc4d2f`): gate PASS; sol re-review
  BLOCKED (5 second-order findings): runtime-less activation path with a
  call-local lock breaks exclusion; whitespace-stripping bypasses canonical
  ref verification; a private-sentinel default bypasses token validation;
  validate-close-reopen race can bind one asset's relink maps to another's
  SHA/handle; ordering/rollback test evidence too weak.
- T3 ceiling reached per WORKFLOW §5. Owner chose the §5.3 split response:
  Stage S2 divides into **S2a** (candidate asset validation and stable-ref
  verification bound to a single opened content; no PART-B writes) and **S2b**
  (atomic activation/relink and runtime visibility through one runtime
  instance; required `asset_token`; complete-old-or-complete-new reads).
  `tasks/slice-7.md` A5 amended with the structural mechanics. Each sub-stage
  is dispatched fresh from attempt 1 with independent gpt-5.6-sol review.
  Outcome: S2a fresh dispatch passed gate + review after one same-tier retry
  (snapshot-binding corrections) and was accepted (`8cf6367`).

## Stage S2b ceiling and respecification (2026-08-24)

- S2b attempt 1 (`run_38c691320a`, `f08f33d`): gate PASS; sol review BLOCKED
  (4): constructor accepted a raw active asset bypassing metadata reconciliation
  and multi-instance serialization; failure path released the incumbent handle;
  meaning-resolution reads accepted arbitrary dictionary data outside the
  runtime lock; rollback/concurrency test evidence vacuous.
- S2b same-tier retry (`run_10eabe5040`, `fb3bba3`): gate PASS; sol re-review
  BLOCKED (3): shared-lease aliasing via dataclasses.replace could close the
  incumbent connection through the equal-SHA branch; concurrent-reader evidence
  was sequential (no read overlapped activation); rollback snapshot omitted
  last_relinked_at and note.status.
- T3 ceiling reached per WORKFLOW §5. Owner approved tightening A5 with three
  structural requirements: incumbency guarded by lease identity with a
  non-aliasable frozen asset (release only self-produced leases); visibility
  evidence from reads genuinely overlapping an activation; rollback snapshot
  covering every PART-B column activation mutates. S2b re-dispatched fresh from
  attempt 1 of the amended contract with independent review.

## Stage S2b structural close-out (2026-08-24)

- The fresh amended-contract dispatch (`run_255d9cff45`, `b4e1920`) passed the
  gate but its sol review ran live defeat exploits and BLOCKED (4): a forged
  wrapper carrying the produced lease activated with a fake sha256/path;
  reentrant activate() inside an open reading() context closed the held lease
  mid-observation (RLock); concurrency evidence had no synchronization in the
  commit-to-publication window; the rollback fixture never flipped
  binding_status.
- Owner chose structural close-out over threat-model rescoping. A5 amended:
  activation is capability-gated (opaque validator-issued provenance,
  registry-checked, not reproducible by copy/replace); read observations are
  generation-pinned via refcounted leases and always complete against one live
  generation even across concurrent activation; concurrency evidence injects a
  synchronization point between PART-B commit and runtime publication; the
  rollback fixture must include a non-no-op binding_status transition. S2b
  re-dispatched fresh against this contract.
- Close-out attempt 1 (`run_c6d3f64883`, `35afb4c`): gate PASS; sol review
  BLOCKED (3): wrapper-level lease borrow/release could close the incumbent;
  generation pinning covered PART-A only while activation committed PART-B
  mid-observation; capability registry was module-level mutable state.
- Close-out same-tier retry (`run_25c708499c`, `2af0328`): gate FAIL exit -1 —
  orchestrator diagnosis against the worktree isolated a self-deadlock in
  `test_activation_waits_for_full_read_pin_then_publishes_one_generation`: the
  test held a pre-commit pin while waiting on the publication hook, contradicting
  drain-before-transaction. Spec clarification applied to A5 (cross-seam reader
  arrives during the window WITHOUT a pre-commit pin; blocks until publication).
  Fresh dispatch follows; any further failure halts slice-7 for owner consult.
- Clarified close-out dispatch (`run_52b990a44b`, `b6e8a75`): gate PASS
  (deadlock eliminated); sol review BLOCKED (3): same-thread activate() inside
  an open reading() context waits on a count only the outer context can
  decrement (deterministic self-deadlock — refusal via thread-id detection was
  the required semantics); the injected hook sits after commit() where a raise
  cannot be rolled back and leaves committed-new PART-B beside the old
  published asset; the mandated all-column partial-relink rollback fixture was
  absent.
- OWNER HALT (2026-08-24, honored per the recorded stop commitment): slice-7
  pauses with S1 + S2a accepted on `slice/7`. S2b is NOT accepted; its four
  candidates remain unaccepted on orch branches as diagnostic evidence. A fresh
  governance session must first resolve the D47 runtime design — capability-
  gated activation, generation-pinned/refcounted reads, readers-writer drain
  semantics, post-commit hook containment — then amend `tasks/slice-7.md` A5
  mechanics before any further S2b implementation. Resume state: base for the
  resumed S2b work is this branch's HEAD; stages S3–S6 unchanged.

## Stage S2b governance resolution — D47 runtime design (2026-08-24)

Fresh governance consultation held against `main` `eb42ccf` and `slice/7`
`0488a96`, with S1 (`a678f1b`) and S2a (`8cf6367`) frozen and not reopened.

**Verdict: IMPLEMENTABLE_WITH_BRIEF_CLARIFICATION.** Frozen ADR-0004 D47 needs
no amendment. Every blocking defect traced to `tasks/slice-7.md` A5 mechanics
that were added during the failed cycles, not to the ADR.

- ROOT CAUSE. `DictionaryAsset` was made to carry four roles at once —
  validation result, authority to activate, owner of a SQLite handle, and the
  runtime's published generation. Each review defeat exploited a seam between
  two of those roles (forge the value to gain the authority; `dataclasses.
  replace` the value to alias the handle; hold the value across a swap to pair
  old PART-A with new PART-B). Every repair added a guard on the *outside* of
  that conflation — a provenance capability, an `id()`-keyed weakref registry,
  a `generation.asset is not asset` recheck — so each fix created a fresh
  second-order surface. Compounding it, A5 simultaneously mandated
  drain-before-transaction AND always-completing generation-pinned reads; those
  are contradictory, and the contradiction produced both the test self-deadlock
  and the same-thread reentrancy deadlock. The defects were structural, not
  workmanship.

- RESOLUTION. Remove the untrusted input instead of gating it, and remove the
  drain instead of reconciling it:
  1. Activation accepts a PATH, never an asset. The runtime calls the accepted
     S2a validator itself, and the asset never crosses a public boundary in
     either direction. No capability, no registry, no module-global mutable
     state — a forged or copied wrapper has no activation path to reach.
  2. A read pin is acquired atomically over BOTH databases: a generation pin
     plus an open deferred read transaction on a WAL user DB. Every observation
     is internally consistent by construction.
  3. No drain. The runtime lock is held only ACROSS the PART-B commit and the
     runtime publication; readers take it only to pin. Pre-seam readers observe
     complete-old, cross-seam readers block until publication and observe
     complete-new, and activation never waits on a reader.
  4. Reentrancy is refused before any work, by owning-thread pin depth, on a
     plain `Lock` (never an `RLock`).
  5. After the commit returns, publication is unconditional and infallible.
     Production runs NO caller-supplied callback there, so post-commit failure
     is not an API failure mode; a private test-only seam probe provides the
     synchronization point for evidence, and a process death in that window
     converges on the committed `active_dictionary_metadata` row via managed-
     directory restart recovery.

- WHY THIS IS NOT AN ADR WEAKENING. D47's binding text is "an atomic relink
  transaction swaps handles under an exclusive lock" (§6.6) and its stated
  purpose is to prevent stale ID collisions, wrong-sense binding, and mixed
  runtime states. The handle swap still happens under an exclusive lock;
  generation pinning provides a strictly STRONGER per-observation guarantee
  than draining, since every read is a consistent snapshot that also cannot
  fail or stall. "Drain all pre-commit pins" appears nowhere in ADR-0004 — it
  was A5 wording. D47 itself already anticipates readers holding pre-swap
  state: that is precisely why §6.6 mandates the asset-token HTTP 409
  round-trip, which is the write-side protection that makes a complete-old
  observation safe. A strict drain reading is also operationally defective
  (activation becomes indefinitely starvable by any reader), so it cannot have
  been the intent.

- ADDITIONAL FINDING. ADR-0004 §6.6 states normatively that the user-data/deck
  layer owns activation and that `app/dictionary.py` never accesses user state.
  `DictionaryRuntime` therefore belongs in `app/deck.py`; `tests/test_dictionary
  .py::test_no_part_b_table_references` already enforces this mechanically.
  A5 now records the ownership explicitly so the resumed attempt cannot drift.

- A5 amended in `tasks/slice-7.md` (activation owner/layering, path-only
  activation input, generation identity and lease ownership, dual-database read
  pins, no-drain seam exclusion, reentrancy refusal, total transaction and
  publication ordering, infallible publication and crash convergence, total
  failure semantics, relink outcome table, whole-table non-vacuous rollback
  evidence). No ADR, application code, or test was modified by this
  consultation. S2b is re-dispatched fresh from attempt 1 of the amended
  contract per WORKFLOW §5.3.

### S2b clarification self-review (2026-08-24, same governance session)

Owner-directed narrow self-review of the proposed clarification before
acceptance. Direction (IMPLEMENTABLE_WITH_BRIEF_CLARIFICATION) upheld; five
internal inconsistencies in the first draft were repaired in A5:

1. **Lock/hook contradiction.** The draft forbade holding the runtime lock
   during "any user hook" while placing an injected synchronization point
   inside the commit-to-publication seam. Resolved by separating the two
   notions: NO user, plugin, application, or caller-supplied callback ever runs
   under the runtime lock (no hook parameter, no registration API, no extension
   point), and the seam synchronization is a single PRIVATE, TEST-ONLY internal
   seam probe that production callers can neither supply nor invoke.
2. **Same-thread reentrancy evidence.** The draft's T1 let a worker thread
   activate while a different thread held the pin, which proves nothing. A5 now
   mandates that ONE worker thread itself run
   `with runtime.reading(): runtime.activate_dictionary(...)` — and the same
   for `close()` — with the main thread proving termination by
   `join(timeout=...)`.
3. **WAL ownership.** The draft required WAL without saying who establishes it,
   creating a hidden dependency on `tests/conftest.py` or S5. `DictionaryRuntime`
   construction now issues `PRAGMA journal_mode=WAL` itself, verifies SQLite
   returned `wal`, and fails construction otherwise. PART-B runtime
   configuration, not a schema change.
4. **Crash-recovery path.** `active_dictionary_metadata.active_filename` is a
   filename, not a durable absolute path, so the draft's "adopt the recorded
   filename" was unimplementable. A5 now defines one managed dictionary
   directory derived from the initial `dict_path.parent`; candidates must
   resolve inside it (traversal, separators, and escaping symlinks rejected);
   `active_filename` stores only the managed filename; restart recovery
   resolves `managed_dir / active_filename`, revalidates through S2a, requires
   an exact `active_sha256` match, and fails construction closed otherwise. No
   schema column added, no allowlist broadening.
5. **Post-commit error semantics.** A5 now states that the production
   activation API cannot fail after its commit returns, and that the test seam
   probe's post-publication re-raise is test instrumentation rather than
   documented API failure semantics. The rollback fixture's failure injection
   is likewise private and test-only, and fires strictly BEFORE the commit.

Full re-read of the amended A5 and the required-test list found no residual
contradiction: no "drain" language, no public hook surface, no capability
registry, and the seam probe is referenced consistently in the ordering,
publication, and evidence bullets. Verdict unchanged:
IMPLEMENTABLE_WITH_BRIEF_CLARIFICATION. No ADR, application code, test,
schema, or STATE file was modified.

## Stage S2b resume round 2 — bounded repair BLOCKED; owner halt (2026-08-25)

Resumed from `d6f304a` per owner instruction: exactly ONE bounded T3 repair
reproducing candidate `4fefdda` plus corrections for exactly the nine
independent-review findings, followed by ONE fresh independent gpt-5.6-sol
review. Stop condition reached; S2b halted again.

- Transport incident (`run_a6ea268a1f`, opencode-go/deepseek-v4-pro): the
  worker aborted ~8 seconds in — its first tool call targeted the
  authoritative checkout (`/home/saber/projects/flashcard`) and the opencode
  sandbox auto-rejected the external-directory access; zero changes, no
  candidate, no gate execution. Owner classified this a transport/sandbox
  correction that does NOT consume the authorized attempt (failures agree:
  dispatch-prompt defect, not implementation), and ordered re-dispatch with
  worktree-relative-only prompt discipline (never reference or touch the
  authoritative checkout; gate owned by the engine).
- Bounded repair (`run_e1cfe3a7e6`, opencode-go/deepseek-v4-pro, T3,
  max-attempts 1): candidate `5e0bd4a` on `orch/run_e1cfe3a7e6/a1`.
  Deterministic gate PASS (authoritative venv toolchain). Scope verified by
  the orchestrator: only `app/deck.py` (+581/−1) and
  `tests/test_dictionary.py` (+1296) differ; `app/dictionary.py` and
  `tests/test_deck.py` byte-identical to base; nothing outside the four-path
  allowlist.
- Independent adversarial review (`run_109be0d891`, codex/gpt-5.6-sol, fresh
  cold reviewer, read-only VERDICT.md contract): **VERDICT: BLOCK**. Findings
  2–9 verified FIXED under live defeat attempts. Finding 1 NOT FIXED, plus
  two new blockers:
  - **Finding 1 / N1 — read-view encapsulation.** `_ReadingView` stores the
    live `_Generation` (in `__slots__`) and its typed accessors traverse
    `_generation.asset`; the validator handle, raw SQLite connection,
    `execute`, and `close` therefore remain reachable through nominally
    private attributes. `PRAGMA query_only` can be switched back off on the
    reachable connection, after which PART-B writes and `COMMIT` succeed —
    defeating the read-only clause and post-commit publication infallibility.
    The candidate's own regression test retrieves `_connection` directly.
  - **N2 — pin-acquisition failure atomicity.** `reading()` increments
    `generation.pins` before opening the reader connection; if
    `sqlite3.connect` raises, the try/cleanup has not begun, leaving a
    phantom pin (and no view). The generation can then never reach zero
    pins: `close()` retires it but never closes it.
  - **N3 — activation/close serialization point.** Activation performs
    type/version checks and managed-path resolution/validation BEFORE
    acquiring `_activation_lock`, contradicting A5's fixed total order
    (reentrancy refusal -> activation lock -> validate candidate) and letting
    filesystem validation race a concurrent `close()`.
- OWNER HALT (option B, 2026-08-25, honored): no further repair dispatched;
  candidate `5e0bd4a` NOT accepted; S3 not started. Orchestrator assessment
  (non-authoritative): all three residuals are mechanical implementation
  defects; none indicates the amended no-drain / path-only A5 design itself
  is defective.
- Retained diagnostic evidence: repair candidate `orch/run_e1cfe3a7e6/a1`
  (`5e0bd4a`); review record `orch/run_109be0d891/a1` (VERDICT.md, `fc2b29c`);
  all earlier S2b candidates and reviews retained. Cleanup deferred until
  slice-7 closes.
- NEXT SESSION MANDATE — fresh, narrowly scoped governance consultation
  restricted to the three remaining S2b runtime-boundary issues:
  1. **Reading-view encapsulation:** the public/yielded view must not make
     `_Generation`, `DictionaryAsset`, SQLite connections, `close()`,
     `execute()`, or other mutation-capable internals reachable, including
     through nominally-private attributes.
  2. **Pin acquisition failure atomicity:** define ordering so a failure
     opening the PART-B read connection cannot leave a generation pin or
     thread pin-depth increment behind.
  3. **Activation/close serialization:** define where `_activation_lock`
     begins so managed-path resolution/validation cannot race `close()`,
     while preserving the same-thread reentrancy-first rule.
  Do not reopen ADR-0004 D47 unless the consultation proves a genuine new
  architectural decision is required. The outcome amends
  `tasks/slice-7.md` A5 mechanics before any S2b re-dispatch.
