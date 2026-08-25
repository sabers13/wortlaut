# Slice-7 S2b — narrow runtime-boundary governance consultation report

Governance-only consultation of 2026-08-25. Fresh session held against
`slice/7` `9deb5e5` with `main` unchanged at `eb42ccf5144b70e1baeef1e7623a5ba17475a8e1`;
S1 (`a678f1b`) and S2a (`8cf6367`) frozen and not reopened. Scope restricted to
exactly the three residuals of the blocked bounded repair candidate. No
application code or tests were modified; no worker was dispatched from this
session.

Outcome applied in this session:

- `tasks/slice-7.md` A5 amended with exactly three clauses (VALUE-SNAPSHOT
  READING VIEW; PIN ACQUISITION IS ALL-OR-NOTHING; normative phase placement
  in TRANSACTION AND PUBLICATION ORDERING);
- `tasks/slice-7.escalation.md` appended with the resolution record;
- committed on `slice/7` as `eec4800`, then owner-directed pre-push
  correction of the value-snapshot clause folded into the same governance
  commit, amended to `91c8134`; this report was corrected in the same
  amendment to mirror the final contract — inert immutable snapshot with no
  active/revocation flag, copied values readable after context exit,
  payload-only purity certification, fresh copied backing mappings, exact
  acquisition order, clarified reentrancy probe — and its worker prompt
  updated accordingly;
- push to `origin` NOT performed (owner approval pending; AGENTS G9 wants the
  amended brief pushed before any subsequent chat consumes it).

## Startup verification — PASSED

| Check | Result |
|---|---|
| Branch | `slice/7` |
| HEAD == `origin/slice/7` | `9deb5e5` == `9deb5e5` |
| `origin/main` | `eb42ccf5144b70e1baeef1e7623a5ba17475a8e1` |
| Working tree | completely clean at consult start |
| S1 `a678f1b`, S2a `8cf6367` | both verified ancestors of `slice/7` |
| Candidate not integrated | verified — stronger: `5e0bd4a` resolves to no commit object in this repository; the retained candidate is `orch/run_e1cfe3a7e6/a1` = full SHA `5e0bd4390fa401f732d72952540dc17e4a2dab52` (short `5e0bd43`). The round-2 record's `5e0bd4a` is a one-character transcription slip for this same commit; corrected in the escalation appendendum. |
| S3–S6 | not started — no commits after S2a; `app/deck.py` at HEAD contains no `DictionaryRuntime`; `tests/test_dictionary.py` at HEAD contains no runtime tests |

Corpus read in full: WORKFLOW.md, AGENTS.md, STATE.md, tasks/slice-7.md,
tasks/slice-7.escalation.md, tasks/slice-7.orchestration-report.md,
tasks/slice-7.s2b-resume-report.md, docs/adr/0004-multilingual-learner-meanings.md
(incl. §6.6 D47), app/deck.py, app/dictionary.py, tests/test_dictionary.py,
tests/test_deck.py — plus, read-only as retained diagnostic evidence, the
blocked candidate's `app/deck.py` on `orch/run_e1cfe3a7e6/a1`.

## A. ROOT CAUSE

Why the three residuals survived the previous implementation despite the larger
A5 clarification: that round fixed the *architecture* — path-only activation,
no-drain generation pinning, reentrancy refusal, infallible publication. The
residuals are of a different kind: each is a **placement defect inside a single
method or object**, in territory the clarified A5 did not explicitly constrain,
so worker discretion filled the gap.

1. **Reading-view encapsulation.** A5 said what the view must not *expose*
   ("read results and `asset_token` only") but not what it may *contain*. The
   worker drew the boundary at the naming level: typed public accessors over
   private slots `_generation`/`_connection` holding the live `_Generation`
   and raw SQLite connection. In Python that is reachability, not
   encapsulation — `view._generation.asset.connection.execute(...)` plus
   `PRAGMA query_only=OFF` remained one attribute chain away; the candidate's
   own regression test retrieving `_connection` proves the boundary was
   underscore-based.
2. **Pin-acquisition failure atomicity.** A5 required pin + read transaction
   "in one atomic step under the runtime lock" but did not enumerate failure
   ordering *inside* the step. The implementation incremented
   `generation.pins` before the first fallible operation (`sqlite3.connect`)
   and began try/cleanup one statement too late — "atomic" was implemented as
   "under one lock", not all-or-nothing with respect to the pin. Result: a
   failed connect left a phantom pin, so `close()` retires the generation but
   never closes it.
3. **Activation/close serialization.** A5's total order was read as governing
   only the expensive tail: argument checks and managed-path filesystem
   resolution ran before `_activation_lock`, letting validation race
   `close()` and making error precedence on a closed runtime nondeterministic.
   The publication-time `_closed` recheck prevented corruption but not the
   ordering-contract violation.

None of the three contradicts path-only activation, no-drain, dual-database
pins, plain-Lock ordering, or post-commit publication infallibility. The
amended design stands.

## B. MINIMAL CORRECTED CONTRACT

### Issue 1 — VALUE-SNAPSHOT READING VIEW (delete authority, don't hide it)

Any design where the view can perform dynamic reads must store some reference
chain to a connection, and every Python hiding mechanism — private slots,
closures (`__closure__`/`cell_contents` are introspectable), proxies — stays
reachable. The smallest robust boundary is therefore the one with nothing to
hide. The yielded object is an INERT IMMUTABLE VALUE SNAPSHOT holding ONLY
copied values:

- `asset_token: str | None`;
- copied PART-A ref→id mappings;
- one materialized immutable mapping
  `{(note_id, role, component_ord): (cached_lemma_id|None, cached_sense_id|None)}`
  read by the runtime INSIDE the pinned deferred read transaction at pin time
  (this SELECT also fixes the snapshot).

No `_Generation`, no `DictionaryAsset`, no connection/cursor, NO callable of
any kind, no reference to the runtime, and NO mutable liveness or revocation
mechanism such as an active flag — the context lifetime governs resource and
pin ownership only, never the lifetime of already-copied values. Copied
values MAY remain readable after context exit precisely because they are
stale immutable values: after exit the snapshot has no connection, no pin,
no runtime reference, no callback, no mutation capability, and no ability to
perform a fresh read, so it can never observe anything new and
complete-old/complete-new semantics are unaffected. Snapshot mappings MUST
be genuine copies — a `MappingProxyType` over a FRESH dict built exclusively
from primitive key/value data during snapshot construction, or an equivalent
tuple/frozenset representation — never a mapping shared with
`DictionaryAsset`, `_Generation`, the runtime, or any other
authority-bearing object. Purity is certified over STORED INSTANCE PAYLOAD
only (declared slots/fields and containers stored therein), not over
`dir()`/`__class__`/descriptor graphs. Extension rule for later stages: more
materialized immutable values under the pin, never resources, connections,
callables, or flags. Cost: one bounded table read per `reading()` context —
trivial at single-user scale.

### Issue 2 — PIN ACQUISITION IS ALL-OR-NOTHING (acquire-all-then-publish)

Under the runtime lock, EXACTLY this order: closed check → acquire/configure
reader connection → `BEGIN DEFERRED` → materialize the PART-B snapshot →
copy the PART-A value mappings → ONLY THEN increment generation pin +
calling-thread pin depth → release the runtime lock → yield the inert value
snapshot. Any failure before the counter increments closes whatever reader
resource was acquired and leaves generation pins and thread depth unchanged.
Release after a successful yield runs exactly once: roll back and close the
PART-B reader transaction/connection; decrement each counter exactly once
under the runtime lock; close a retired generation's handle exactly once
when its pin count reaches zero.

### Issue 3 — NORMATIVE PHASE PLACEMENT (exact total order)

```
(1) same-thread reentrancy refusal        <- ONLY pre-lock work
(2) acquire _activation_lock
(3) runtime-lock closed check, release    <- runtime lock never held during validation
(4) argument/type validation              <- after closed check: closed dominates TypeError
(5) managed-path resolution/validation
(6) candidate validation (one open, no reopen)
(7) BEGIN IMMEDIATE -> relink -> metadata upsert -> pre-commit probe
(8) [runtime lock: defensive closed recheck -> commit -> seam probe (captured)
     -> publish + retire incumbent -> release]
(9) release activation lock, close write connection
```

Three precisions beyond the sketched shape: argument/type checks sit AFTER
the closed verification (a closed runtime deterministically reports closed
regardless of arguments); the commit-time closed recheck is retained
defensively even though concurrent `close()` cannot in fact interleave (it
needs the activation lock this thread holds); and phase (1)'s reentrancy
probe inspects the calling thread's OWN runtime-owned thread-local pin
depth, optionally under a brief runtime-lock acquire/release that FULLY
RELEASES before `_activation_lock` is taken — `_activation_lock` is NEVER
acquired while holding the runtime lock.

Verified against existing constraints: lock order activation-before-runtime
only; readers take only the runtime lock; no-drain unchanged;
complete-old/complete-new unchanged (PART-B snapshot fixed at pin by the
materializing SELECT; PART-A pinned by the generation pin); close semantics
unchanged; reentrancy-first preserved verbatim.

## C. INVARIANTS (mechanically testable)

- **I1 View payload purity:** the stored instance payload of any yielded
  snapshot — declared slots/fields and containers stored therein — contains
  only primitives and immutable containers of primitives (plus a
  snapshot-construction `MappingProxyType`); nowhere in stored payload a
  `sqlite3.Connection`/`Cursor`, `DictionaryAsset`, `_Generation`,
  `DictionaryRuntime`, any callable/function/method/closure, or any mutable
  authority-bearing object. Class objects, descriptors, and other Python
  implementation metadata are outside the certified graph.
- **I2 View inertness:** no mutable liveness or revocation mechanism on the
  snapshot; accessors mutate nothing; copied values may remain readable
  after context exit as stale immutable values incapable of fresh reads.
- **I2a Snapshot mappings are copies:** fresh backing built exclusively from
  primitive key/value data during snapshot construction; no backing mapping
  shared with `DictionaryAsset`, `_Generation`, the runtime, or any other
  authority-bearing object.
- **I3 Pin atomicity:** failure injected at connect/configure / BEGIN /
  PART-B materialization / PART-A copy ⇒ pins == 0, thread depth == 0, no
  open connection left.
- **I4 Release symmetry:** every successful `reading()` decrements exactly
  once; a retired generation's handle closes exactly once at zero pins;
  `close()` with no live pins closes the current handle.
- **I5 Order:** (a) closed runtime beats invalid paths/types; (b) while
  candidate validation runs under the activation lock, concurrent `close()`
  and bad-argument `activate()` block until it completes; (c) same-thread
  `with reading(): activate/close` terminates with the distinct reentrancy
  error (`join(timeout)`).
- **I6 No mixed state:** pre-seam readers complete-old, cross-seam readers
  complete-new (regression-anchored by existing mandated evidence).

## D. REQUIRED TESTS (only these additions)

1. **T1 payload-purity walker** over the snapshot's stored instance payload +
   negative control injecting a forbidden object into the SAME walker helper
   (proves the helper detects it, i.e. is not vacuous);
2. **T2 snapshot-copy/no-shared-backing**: mutating source mappings behind a
   stub asset after snapshot construction leaves the snapshot unchanged;
3. **T3 acquisition-failure injection** at each acquisition step (connect/
   configure, BEGIN, PART-B materialization, PART-A copy) asserting I3;
4. **T4 success-path symmetry** asserting I4 (validator stub records
   exactly-once handle close);
5. **T5 serialization evidence** asserting I5(a)/(b) with bounded joins, plus
   the already-mandated same-thread reentrancy termination tests as regression
   anchor.

All previously mandated S2b evidence (whole-table non-vacuous rollback,
overlapping-read visibility, seam containment, managed-directory rejection,
restart recovery) remains required and unchanged.

## E. SCOPE — next S2b attempt allowlist

Exactly the prior four-path allowlist: `app/deck.py` +
`tests/test_dictionary.py` carry the corrections; `app/dictionary.py` and
`tests/test_deck.py` expected byte-identical to base. Nothing else. No schema
change, no ADR change, no new dependency.

## F. GOVERNANCE VERDICT

**IMPLEMENTABLE_WITH_NARROW_A5_CLARIFICATION.**

ADR-0004 D47 needs no amendment; none of the three residuals touches path-only
activation, no-drain generation pinning, dual-database read pins, plain-Lock
ordering, or post-commit publication infallibility. Executed edits:
`tasks/slice-7.md` A5 (three clauses) and `tasks/slice-7.escalation.md`
(resolution record), committed as `eec4800`, then amended in-place (pre-push,
unpushed history rewrite) to `91c8134` with the owner-directed value-snapshot
correction. Verdict unchanged.

---

## Exact next S2b worker prompt (NOT executed by this session)

```
SLICE-7 STAGE S2b — ATTEMPT 1 OF THE CORRECTED CONTRACT (bounded-runtime repair lineage)

Repository (authoritative local checkout): /home/saber/projects/flashcard
Engine-dispatched via orch; you work ONLY inside your assigned orch candidate
worktree. NEVER reference, read, or touch the authoritative checkout path.
Workers are FORBIDDEN from every git mutation (no add/commit/branch/checkout);
the orchestration engine stages and commits candidates.

Base ref: branch slice/7 @ 91c8134 (verified by engine). STOP if your worktree
base differs. Working tree must start clean.

READ FIRST (in your worktree): AGENTS.md, tasks/slice-7.md (A5 as amended at
91c8134 — VALUE-SNAPSHOT READING VIEW, PIN ACQUISITION IS ALL-OR-NOTHING,
TRANSACTION AND PUBLICATION ORDERING phase placement), ADR-0004 §6.6 (D47),
app/deck.py, app/dictionary.py, tests/test_dictionary.py, tests/test_deck.py,
reference/schema.sql.

TASK: Implement DictionaryRuntime in app/deck.py per amended A5 in full, plus
its evidence suite in tests/test_dictionary.py. Reproduce the accepted S1/S2a
behavior contract exactly; change nothing in them. The implementation must
satisfy ALL of amended A5, and in particular the three corrected mechanics:

M1 VALUE-SNAPSHOT READING VIEW. The object yielded by reading() is an INERT
   IMMUTABLE VALUE SNAPSHOT holding ONLY copied values: asset token string,
   copied PART-A ref-to-id mappings, and a materialized mapping {(note_id,
   role, component_ord): (cached_lemma_id|None, cached_sense_id|None)} read
   INSIDE the pinned deferred transaction at pin time. NO _Generation, NO
   DictionaryAsset, NO SQLite connection/cursor, NO bound method or closure
   reaching either, NO reference to the runtime, and NO mutable liveness or
   revocation mechanism such as an active flag. Copied values MAY remain
   readable after context exit as stale immutable values; after exit there
   is no connection, no pin, no runtime reference, no callback, no mutation
   capability, and no fresh-read ability. Snapshot mappings must be genuine
   copies: MappingProxyType over a FRESH dict built exclusively from
   primitive key/value data during snapshot construction, or equivalent
   tuple/frozenset form — never shared backing with DictionaryAsset,
   _Generation, the runtime, or any other authority-bearing object. Do not
   rely on private-name conventions.

M2 PIN ACQUISITION IS ALL-OR-NOTHING. Under the runtime lock, EXACTLY this
   order: closed check -> acquire/configure reader connection -> BEGIN
   DEFERRED -> materialize the PART-B snapshot -> copy the PART-A value
   mappings -> ONLY THEN increment generation pin + calling-thread pin depth
   -> release the runtime lock -> yield the inert value snapshot. Any failure
   before the counter increments closes whatever reader resource was acquired
   and leaves pins and thread depth untouched. Release after a successful
   yield runs exactly once: roll back and close the PART-B reader
   transaction/connection; decrement each counter exactly once under the
   runtime lock; close a retired generation's handle exactly once when its
   pin count reaches zero.

M3 NORMATIVE PHASE PLACEMENT. activate_dictionary: (1) same-thread reentrancy
   refusal is the ONLY pre-lock work — implemented by inspecting the calling
   thread's OWN runtime-owned thread-local pin depth, optionally under a
   brief runtime-lock acquire/release that FULLY RELEASES before (2);
   _activation_lock is NEVER acquired while holding the runtime lock;
   (2) acquire _activation_lock; (3) runtime-lock closed check then release;
   (4) argument/type validation; (5) managed-path resolution/validation;
   (6) candidate validation (one open, no reopen); (7) BEGIN IMMEDIATE,
   relink, metadata upsert, pre-commit probe; (8) [runtime lock: defensive
   closed recheck, commit, seam probe (captured), publish + retire incumbent,
   release]; (9) unlock, close write connection. close(): reentrancy refusal
   first, then the SAME activation lock, then runtime-lock idempotent close.
   Lock order activation-before-runtime, never reverse; readers take only
   the runtime lock; plain Locks, never RLock; no-drain semantics unchanged;
   post-commit publication infallible; total pre-commit failure semantics
   unchanged.

Also carry forward, unchanged from A5: path-only activation (TypeError on an
asset), managed directory + traversal/separator/symlink rejection on RAW text
before normalization, restart recovery failing construction closed, WAL
establishment owned by the runtime, monotonic non-aliased generations,
lease-free pin accounting, relink outcome table incl. whole-vector
invalidation and missing-vector fail-closed, note.status written only for
{resolved, derived_compound, needs_gloss}, last_relinked_at stamped on every
written row, private test-only seam probe (captured exception, re-raised only
after publication), private pre-commit failure injection strictly BEFORE
commit.

REQUIRED NEW EVIDENCE (in addition to all previously mandated S2b evidence):
E1 payload-purity walker: inspect the snapshot's STORED INSTANCE PAYLOAD
   (declared slots/fields and containers stored therein); assert every
   reached value is NoneType/bool/int/float/str/bytes/tuple/frozenset or a
   snapshot-construction MappingProxyType over primitive data; assert
   absence of sqlite3.Connection/Cursor, DictionaryAsset, _Generation,
   DictionaryRuntime, and ANY callable/function/method/cell anywhere in
   stored payload; class objects/descriptors are outside the certified
   graph; include a negative control injecting a forbidden object into the
   SAME walker helper, proving detection.
E2 snapshot-copy/no-shared-backing: mutating source mappings behind a stub
   asset after snapshot construction leaves the snapshot unchanged.
E3 failure injection at EACH acquisition step (connect/configure, BEGIN,
   PART-B materialization, PART-A copy): assert pins == 0, thread depth == 0,
   no leaked connection, error propagates.
E4 success symmetry: counters return to zero; retired-generation handle
   closes EXACTLY ONCE (stub validator records close count); runtime.close()
   closes the current handle.
E5 serialization: (a) after close(), activate_dictionary raises the closed
   error even for a nonexistent path AND for a wrong-type argument;
   (b) blocking-validation fixture: while candidate validation is blocked
   under the activation lock, a concurrent close() and a concurrent
   bad-argument activate() are BLOCKED (join(timeout) bounded waits, never
   unbounded Barrier.wait) and complete only after validation finishes;
   (c) the mandated same-thread reentrancy termination tests (ONE worker
   thread runs with runtime.reading(): activate/close; main thread
   join(timeout) + is_alive assertions).
E6 all previously mandated evidence remains: whole-table non-vacuous rollback
   (binding_status transition proven to differ), overlapping-read visibility
   across a real activation, seam containment, managed-directory rejection
   cases incl. sub/../name rejected on raw text, restart-recovery SHA
   mismatch fails construction, stale-token 409 path readiness.

ALLOWLIST (exhaustive): app/deck.py, app/dictionary.py, tests/test_dictionary.py,
tests/test_deck.py. Expected diff: app/deck.py and tests/test_dictionary.py
only; app/dictionary.py and tests/test_deck.py MUST remain byte-identical to
base. Anything else is a scope violation -> STOP.

FORBIDDEN: modifying schema, ADRs, AGENTS/WORKFLOW/STATE/PROMPTS, docs/,
tools/, pyproject.toml; opening dictionary files directly in deck.py outside
the validator; module-global mutable state; RLock; caller-supplied callbacks
under the runtime lock; reading earlier rejected S2b candidate worktrees
(orch/run_* is read-forbidden entirely).

GATE (engine-run, venv-linked): make gate with authoritative .venv toolchain
must PASS (ruff, mypy --strict, pytest, check_agents).

STOP-AND-REPORT: base ref mismatch; dirty start; any allowlist violation;
any requirement needing a file outside the allowlist; any conflict with
amended A5 or ADR-0004 D47; gate failure you cannot attribute to environment.

REPORT BACK: exact base SHA; files changed with line counts; gate stdout/stderr
tail and exit code; per-mechanic (M1-M3) and per-evidence (E1-E6) confirmation
with test names; any deviation is a STOP, not a choice.
```

## Next step

This governance session is complete and ends here per WORKFLOW §10 (fresh chat
after resolved governance, before implementation resumes).

1. **Approve the push**: owner authorizes `git push origin slice/7` so
   `91c8134` (amended A5 + escalation resolution) and the corrected consult
   report reach the private mirror before anything consumes them — AGENTS G9
   requires this before the next session reads the brief.
2. **Open a fresh slice-7 orchestrator session** (new chat). Startup
   verification: branch `slice/7`, HEAD = the amended consultation-report
   commit whose parent is `91c8134`, clean tree, `origin/main` still
   `eb42ccf…`. It dispatches the worker prompt above verbatim as the S2b
   attempt-1 orch task (T3 implementation, independent gpt-5.6-sol review,
   engine-owned gates/commits, worktree-relative discipline).
3. Worker gate/review evidence decides whether S2b proceeds to acceptance,
   another bounded cycle, or halt. S3–S6 remain untouched until S2b is
   accepted.
