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

## Stage S2b governance resolution — narrow runtime-boundary consult (2026-08-25)

Fresh, narrowly scoped governance consultation held against `slice/7` `9deb5e5`
(`main` unchanged at `eb42ccf`; S1 `a678f1b` and S2a `8cf6367` frozen), restricted
to exactly the three residuals of the blocked bounded repair. Evidence base: the
resume-round-2 record above, the retained candidate worktree
`orch/run_e1cfe3a7e6/a1`, and its review record `orch/run_109be0d891/a1`.
Record correction: the candidate's full SHA is
`5e0bd4390fa401f732d72952540dc17e4a2dab52` (short form `5e0bd43`); the
round-2 record's `5e0bd4a` is a one-character transcription slip referring to
this same retained commit.

**Verdict: IMPLEMENTABLE_WITH_NARROW_A5_CLARIFICATION.** Frozen ADR-0004 D47
needs no amendment. None of the three residuals touches path-only activation,
no-drain generation pinning, dual-database read pins, plain-Lock ordering, or
post-commit publication infallibility; all three are placement defects inside
single methods/objects where the previous A5 clarification stated an invariant
but left its mechanical realization to worker discretion.

- ROOT CAUSE (why they survived the larger A5 clarification). (1) A5 said what
  the reading view must not EXPOSE but not what it may CONTAIN, so the worker
  drew the boundary at the naming level — typed public accessors over private
  slots holding the live `_Generation` and raw connection — which in Python is
  reachability, not encapsulation (`view._generation.asset.connection` plus
  `PRAGMA query_only=OFF` remained one attribute chain away; the candidate's
  own regression test retrieved `_connection`). (2) A5 required pin + read
  transaction "in one atomic step under the runtime lock" but did not
  enumerate failure ordering inside the step; the implementation incremented
  `generation.pins` before the first fallible operation and began cleanup one
  statement too late, so a failed `sqlite3.connect` left a phantom pin that
  `close()` retires but never closes. "Atomic" was implemented as "under one
  lock", not as all-or-nothing with respect to the pin. (3) A5's total order
  was read as governing only the expensive tail: argument checks and
  managed-path filesystem resolution ran before `_activation_lock`, letting
  validation race `close()` and making error precedence on a closed runtime
  nondeterministic. The publication-time closed recheck prevented corruption
  but not the ordering-contract violation.

- RESOLUTION (amended into A5, three clauses only).
  1. VALUE-SNAPSHOT READING VIEW: the yielded view holds only copied immutable
     values — asset token string, the pinned generation's immutable ref-to-id
     mappings, a materialized mapping of every `note_dictionary_binding` row's
     cached ids keyed by `(note_id, role, component_ord)` read inside the
     pinned deferred transaction at pin time, and an internal active flag only
     the runtime clears. No `_Generation`, no `DictionaryAsset`, no SQLite
     connection/cursor, no bound method or closure reaching either, no
     reference to the runtime — transitively through every attribute.
     Accessors raise after context exit. Future stages extend the view only by
     materializing more immutable values under the pin. Authority is deleted,
     not hidden: any design retaining dynamic reads must store some reference
     chain to a connection, and every Python hiding mechanism (private slots,
     closures via `__closure__`, proxies) stays introspectable, so copied
     values are the smallest boundary that makes the property structural.
     Cost: one bounded table read per `reading()` context (single-user scale).
  2. PIN ACQUISITION IS ALL-OR-NOTHING (acquire-all-then-publish): inside the
     runtime lock, all fallible acquisitions (connect, configure,
     `query_only=ON`, `BEGIN DEFERRED`, materialization read) precede any pin
     or thread-depth increment; counters increment once, infallibly, only
     after everything succeeded; any failure closes partially acquired
     resources exactly once and leaves counters untouched; every success has
     exactly one matching release (counters once, reader connection once,
     retired-generation handle exactly once at zero pins).
  3. NORMATIVE PHASE PLACEMENT for activation/close: reentrancy refusal is the
     ONLY pre-lock work; then activation lock -> runtime-lock closed check
     (released before validation) -> argument/type validation ->
     managed-path resolution -> candidate validation (one open, no reopen) ->
     relink transaction -> [runtime lock: defensive closed recheck, commit,
     seam probe, publish, release] -> unlock, close write connection.
     `close()` takes the same activation lock after its own reentrancy
     refusal, so no validation phase can race it; a closed runtime reports the
     closed error ahead of any path/type error. Lock order activation-before-
     runtime unchanged; readers take only the runtime lock; no-drain,
     complete-old/complete-new, and infallible publication unchanged.

- REQUIRED NEW TESTS (only these; all previously mandated S2b evidence remains
  required): view-graph purity walker with planted-object vacuity control;
  post-exit accessor raising; failure injection at each acquisition step
  asserting zero pin/depth residue and no leaked connection; success-path
  release symmetry including exactly-once retired-handle close; serialization
  evidence that a closed runtime dominates path/type errors and that
  concurrent `close()` and bad-argument activation block while candidate
  validation runs inside the activation lock (bounded joins); the already
  mandated same-thread reentrancy termination tests remain the regression
  anchor.

- SCOPE of the next S2b attempt (unchanged four-path allowlist):
  `app/deck.py` + `tests/test_dictionary.py` carry the corrections;
  `app/dictionary.py` and `tests/test_deck.py` expected byte-identical to
  base. No schema change, no ADR change, no new dependency. S2b re-dispatches
  fresh from attempt 1 of this corrected contract with independent
  gpt-5.6-sol review, venv-linked gates, workers never touching git, and
  worktree-relative sandbox discipline.

### Pre-push narrow correction to the value-snapshot contract (2026-08-25)

Owner-directed final correction before push, restricted to the
VALUE-SNAPSHOT READING VIEW clause of A5. The verdict
IMPLEMENTABLE_WITH_NARROW_A5_CLARIFICATION is unchanged; no other S2b
decision is reopened; no application code, tests, ADRs, or STATE were
touched. Because `eec4800` had NOT been pushed, the correction was folded
into the same local governance commit (history rewrite; the consult-report
commit is rebased on top).

- REVOCABLE LIVENESS REMOVED. The first draft contradicted its own purpose:
  it deleted authority from the yielded object yet kept a runtime-cleared
  `_active` flag and raise-after-exit semantics. If nominally-private
  attributes are reachable, the flag is reachable too, so revocable liveness
  reintroduced a mutable internal boundary rather than deleting it.
  Corrected contract: the snapshot is INERT and immutable; copied values MAY
  remain readable after context exit as stale immutable values; after exit
  there is no connection, no generation pin, no runtime reference, no
  callback, no mutation capability, and no ability to perform a fresh read;
  the context lifetime governs resource/pin ownership only. The active flag,
  raise-after-exit, and the corresponding post-exit test are deleted.
- PURITY WALKER MADE PRECISE. Purity is certified over STORED INSTANCE
  PAYLOAD only — the declared slots/fields constituting the snapshot's
  stored state and containers stored therein — not over `dir()`/
  `__class__`/descriptor graphs, which encounter class objects and callables
  on any ordinary Python value. Permitted payload: primitives and immutable
  containers of primitives (plus a snapshot-construction `MappingProxyType`
  per the copy rule below). Forbidden anywhere in stored payload: SQLite
  connection/cursor, `DictionaryAsset`, `_Generation`, `DictionaryRuntime`,
  any callable/function/method/closure, any mutable authority-bearing
  object. Class objects, descriptors, and other implementation metadata are
  outside the certified graph. The negative control injects a forbidden
  object into the SAME payload-walker helper and proves detection.
- SNAPSHOT MAPPINGS MUST BE COPIES. `MappingProxyType` alone is a read-only
  view of its backing mapping. The snapshot must use `MappingProxyType` over
  a FRESH dict built exclusively from primitive key/value data during
  snapshot construction, or an equivalent tuple/frozenset representation,
  sharing no backing mapping with `DictionaryAsset`, `_Generation`, the
  runtime, or any other authority-bearing object.
- PIN ORDERING WORDING EXACTED. Under the runtime lock: closed check ->
  acquire/configure reader connection -> `BEGIN DEFERRED` -> materialize the
  PART-B snapshot -> copy the PART-A value mappings -> ONLY THEN increment
  generation pin + same-thread pin depth -> release runtime lock -> yield
  the inert value snapshot. Any failure before the counter increments closes
  whatever reader resource was acquired and leaves both counters unchanged.
  Release after a successful yield: close the PART-B reader
  transaction/connection; decrement counters exactly once under the runtime
  lock; close a retired generation exactly once when its pin count reaches
  zero.
- REENTRANCY PROBE CLARIFIED. Phase (1) of the activation order inspects the
  calling thread's OWN runtime-owned thread-local pin depth, optionally
  under a brief runtime-lock acquire/release that fully releases before the
  activation lock is taken; `_activation_lock` is NEVER acquired while
  holding the runtime lock.
- Re-read of the corrected three-clause A5 clarification found no residual
  contradiction: no revocable state on the snapshot, no shared backing
  mappings, walker and negative control defined over the same helper,
  ordering clauses mutually consistent, no-drain and publication
  infallibility untouched. Where the earlier consult report
  (`tasks/slice-7.s2b-runtime-boundary-consult.md`) conflicts with this
  correction (post-exit raising evidence, attribute-graph walker
  definition), the amended A5 and this addendum govern.

## Stage S2b corrected-contract cycle — gate-PASS/review-BLOCK twice; one bounded repair consumed; owner halt (2026-08-25)

Fresh implementation dispatched from `04671c8` against the corrected contract
(A5 as amended at `91c8134`; consult report `4fbb4d7`), using the consult
report's exact worker prompt with only the base-ref line updated to the
authoritative HEAD. Transport notes: owner redirected all routing away from
opencode (quota exhausted) to Gemini/GPT models for the remainder of the
slice; an initial opencode launch was aborted by the owner before any
candidate existed, leaving zombie row `run_f47bd97290` (retained; cleanup
deferred).

- Attempt 1 (`run_75ac68111d`, codex/gpt-5.6-terra, T3, max-attempts 1):
  candidate `56e5270` on `orch/run_75ac68111d/a1`. Deterministic gate PASS
  (authoritative venv toolchain). Scope verified: only `app/deck.py`
  (+441/−1 region) and `tests/test_dictionary.py` (+520); `app/dictionary.py`
  and `tests/test_deck.py` byte-identical to base.
- Independent adversarial review (`run_b41d67a8ef`, codex/gpt-5.6-sol):
  **VERDICT: BLOCK**. Areas 1/2/6/11/12 (payload purity, fresh-copy backing,
  reentrancy-first, post-commit containment, managed-path/restart/WAL) held.
  Seven findings: N1 teardown-failure pin stranding; N2 vacuous configure-case
  acquisition-failure evidence; N3 phase-9 writer close inside the activation
  lock; N4 missing cross-seam reader evidence; N5 multi-direct-row resolved
  overwrite; N6 rollback companion reusing the failed DB instead of an
  independent copy; N7 dict/user path aliasing unchecked.
- Owner disposition: all seven classified as existing-contract
  implementation/evidence defects; authorized EXACTLY ONE bounded T3 repair
  reproducing `56e5270` plus corrections for exactly N1–N7 (+ non-blocking
  FIFO-ordering test hardening), followed by ONE fresh independent review.
- Bounded repair (`run_2a156e73aa`, codex/gpt-5.6-terra, max-attempts 1):
  candidate `6a120c0` on `orch/run_2a156e73aa/a1`. Deterministic gate PASS.
  Scope verified under the same policy; repair delta vs `56e5270`: 491+/106−
  confined to the two expected files.
- Fresh independent review (`run_1e4c209ab9`, codex/gpt-5.6-sol):
  **VERDICT: BLOCK**. FIXED: N2, N3, N5, N6, FIFO. NOT FIXED: N1 (teardown
  evidence lacks rollback-alone/close-alone successful-body cases), N4
  (cross-seam evidence asserts binding ids only — never the same snapshot's
  new asset token/PART-A pairing), N7 (resolved-path string comparison misses
  hard-link aliases). NEW: B1 writer-close error after commit/publication
  surfaces as activation failure, contradicting post-commit infallibility;
  B2 rollback raise skips candidate close and masks the primary failure;
  B3 schema-permitted stray direct row on a derived_compound note keeps
  serving dictionary meanings despite fail-closed activation. Regression
  sweep: previously held invariants HELD; E-suite/R9/R13 flagged solely via
  those items.
- OWNER HALT (2026-08-25): the corrected-contract cycle's one permitted
  repair is CONSUMED; candidate `6a120c0` NOT accepted; S3–S6 not started.
  Owner classification of residuals: N1/N4 evidence gaps (mechanical, no new
  architecture); N7 hard-link identity bypass (implementation safety defect;
  new architecture only if the existing contract genuinely cannot express
  underlying-file identity); B2 cleanup/exception-ordering defect; B3
  fail-closed derived-compound defect; **B1 GOVERNANCE QUESTION** — A5 says
  activation cannot fail after commit returns while phase 9 closes the
  writer connection after publication and close() itself may raise; the
  contract must explicitly define post-publication cleanup semantics before
  another implementation attempt.
- NEXT SESSION MANDATE — fresh narrow governance consult, primarily B1
  (post-publication cleanup semantics), secondarily confirming whether the
  existing contract can express underlying-file identity (N7) without an
  architectural change; no further implementation dispatch until it resolves.
  Retained diagnostic evidence: `orch/run_75ac68111d/a1` (`56e5270`),
  `orch/run_b41d67a8ef/a1` (VERDICT.md), `orch/run_2a156e73aa/a1`
  (`6a120c0`), `orch/run_1e4c209ab9/a1` (VERDICT.md), zombie row
  `run_f47bd97290`. Session audit artifact:
  `tasks/slice-7.s2b-corrected-cycle-report.md`.

## Stage S2b narrow governance resolution — B1 post-publication cleanup + N7 expressibility (2026-08-25)

Fresh slice-7 orchestrator session resolved the recorded B1 governance question
and the N7 contract-expressibility question against `slice/7` `f33ac79`
(`main` unchanged at `eb42ccf`; S1 `a678f1b`, S2a `8cf6367` frozen; corrected
contract `91c8134` and consult report `4fbb4d7` ancestors). Scope restricted to
exactly B1 and N7; the D47 architecture is not reopened.

**Verdict: NARROW A5 CLARIFICATION — no ADR change required.**

- **B1 (post-publication cleanup semantics).** A5 already declares the
  production activation API cannot fail after its commit returns, but phase (9)
  releases the activation lock and closes the dedicated write connection after
  publication, and `close()` itself may raise — leaving teardown failure
  semantics unstated. Verified against SQLite semantics (after a successful WAL
  commit the transaction is durable; a later connection-close failure cannot
  un-commit it), Python connection lifecycle, and resource-ownership
  invariants: containing post-publication teardown exceptions creates no
  materially incorrect persistent state. Clarified contract, now frozen in A5
  as CLEANUP CONTAINMENT AND EXACTLY-ONCE RELEASE: before the commit returns,
  any failure rolls back and releases every acquired resource exactly once,
  with rollback/release failures captured and suppressed so the PRIMARY
  exception propagates unmasked (repairs B2's ordering defect); after the
  commit returns successfully and publication has completed, phase-(9)
  teardown is infallible from the caller's perspective — exceptions are
  captured and discarded, never propagated, never reported as activation
  failure. Success is reported solely on completed commit + publication.
- **N7 (hard-link / underlying-file identity bypass).** Expressible as a
  narrow existing-contract invariant: filesystem identity (`st_dev`/`st_ino`
  via `os.stat`, or equivalent such as `os.path.samefile`) fully detects
  hard-link aliases and distinct paths to one inode using ordinary machinery.
  No new trust/identity architecture is required → classified RB1/RB2
  implementation work under the corrected contract, NOT RD1. Frozen in A5 as
  UNDERLYING-FILE IDENTITY under the managed-directory bullet: every accepted
  candidate and the restart-recovery target must be rejected when it
  identifies the same underlying filesystem object as the configured user
  database; string/path comparison alone is a defect.
- **B3 (stray-row fail-closed)** frozen in A5 as ROLE/STATUS CONSISTENCY:
  availability is established only through the binding role matching the
  note's persisted resolver status; schema-permitted stray rows of the other
  role never create availability.
- **N1/N4 evidence sharpening** frozen into the existing A5 bullets:
  release-symmetry/teardown evidence must cover every exit shape (normal,
  body-exception/rollback, closed-while-pinned); cross-seam evidence must
  assert the same snapshot's asset token + PART-A mappings + PART-B binding
  ids together as one single-generation pairing.

Amended files: `tasks/slice-7.md` (A5 only) and this record. No application
code, tests, schema, ADR, or STATE content was modified by this resolution.
S2b implementation convergence resumes from attempt 1 of the clarified frozen
contract per the review-budget policy; the residuals N1/N4/N7/B2/B3 are now
explicitly regression-tested requirements, not open questions.

## Stage S2b implementation convergence — ACCEPTED (2026-08-25)

Executed by the same fresh orchestrator session that resolved B1/N7 above,
against base `4c6e533`. Routing constraint changed mid-session by owner
directive: GPT quota exhausted — only Gemini (`antigravity/gemini-3.7-flash`)
and ox (`opencode/opencode-go/ox-alpha-free`) routes permitted for the
remainder of the slice.

- Attempt 1 (`run_6dbab25275`, gemini-3.7-flash): candidate `c04e0df`;
  gate FAIL — four mechanical mypy --strict errors in new test code only.
- Attempt 2 (§5 Failure-1 same-tier retry, `run_c0ae2529be`, seeded from
  `c04e0df`): candidate `22e9b14`; mypy PASS; gate FAIL — six pytest failures.
  Orchestrator diagnosis against the frozen contract classified ALL SIX as
  test-harness/fixture defects plus two small implementation conformance
  deviations (off-contract 3-tuple snapshot binding values; unmandated silent
  reader-connect fallback defeating E3 injection). No persistent-state or
  concurrency defect.
- §5.3 tightened re-dispatch (`run_fb0aed85ed`, seeded from `22e9b14`, with
  per-defect directives R-A/R-B/T-1..T-5): candidate `02d458e`; 570/571 — one
  residual harness defect surfaced (E3 step-c patched immutable
  `sqlite3.Connection`), previously masked by the step-a failure.
- Final convergence fix (`run_4416ff99a9`, seeded from `02d458e`, E3 proxy
  directive only): candidate `bbf858e` — full gate PASS (ruff, mypy strict 20
  files, 571 tests, AGENTS checks). Scope verified: only `app/deck.py` and
  `tests/test_dictionary.py` differ from base; `app/dictionary.py` and
  `tests/test_deck.py` byte-identical.
- Independent adversarial Review #1: three opencode/ox-alpha-free dispatches
  failed at TRANSPORT level (repeated `Unexpected server error`, zero
  candidate each time — attempts not consumed); with GPT quota-banned and ox
  down, review fell back to a FRESH COLD `antigravity/gemini-3.7-flash`
  session (`run_7a32b6614b/a1`, VERDICT.md committed `04b07c6`) under an
  explicit extra-skepticism protocol. **VERDICT: PASS** — zero RB1/RB2/RB3/
  RD1; all E1–E15 independently defeat-tested; regression sweep confirms
  S1/S2a preservation and byte-identity; one trivial RN1 (non-blocking).
  Same-family fallback is a disclosed deviation from the SHOULD-level
  cross-family preference, forced by the outage + owner quota ban; the
  mandatory WORKFLOW §6 T3 full-diff review remains ahead and will restore
  cross-family coverage if ox recovers.
- **S2b explicitly accepted**: `orch accept run_4416ff99a9` integrated
  candidate `bbf858efe72caa636a6085cbaaa0302571318b29` onto `slice/7`;
  post-integration authoritative gate PASSED. Residuals N1/N4/N7/B2/B3 and
  B1 are closed by the accepted implementation and its evidence suite.
- Next: S3 rendering (A4) → S4 audio (A6) → S5 app factory/API/guards (A7) →
  S6 executable checks + report (A8/A10) → mandatory full-diff T3 review over
  `main...slice/7` → slice-7 acceptance → mechanical closure.
