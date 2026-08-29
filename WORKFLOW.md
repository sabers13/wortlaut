# Workflow — Base Variant (no Fable)

One orchestrator, fungible workers, tiered routing. The repo is the memory.

**The authority split:** the local Git repository remains authoritative for execution
state, working tree cleanliness, installed dependencies/models, runtime behavior, and
fresh gate evidence. A private GitHub repository is the persistent authoritative mirror
for committed repository state and is the default source every orchestrator uses to
inspect committed files, branches, reports, task briefs, governance documents, commit
history, and committed review ranges.

**The invariant:** at any moment, a person or agent who has read only this file and
`STATE.md` can pick up the next action correctly. If that is false, `STATE.md` is
stale — and a stale `STATE.md` is worse than none, because it gets trusted.

---

## 0. Project bindings — EDIT THIS SECTION PER PROJECT

| Binding | Value |
| --- | --- |
| Gate command | `make gate` (created by slice-0: ruff, mypy --strict, pytest -q, executable AGENTS checks) |
| State file | `STATE.md` |
| Rules file | `AGENTS.md` (conventions, prohibitions, governance) |
| Decisions dir | `docs/adr/` |
| Backlog | `docs/backlog.md` |
| Briefs dir | `tasks/` |
| Remote mirror | `origin` (private GitHub repository) |
| Handoff transport | GitHub-first (default), local validated ZIP (fallback / immutable snapshot) |

### Two authorities with non-overlapping responsibility

The split between local execution and remote committed context is strict and binding:

**Local repository / terminal is authoritative for:**
- `git status` and uncommitted/untracked files;
- the actual checked-out branch;
- fresh `git rev-parse` verification when execution depends on it;
- installed Python packages, spaCy models, local services, databases, caches,
  credentials, environment variables, and other machine state;
- `make gate` and all fresh executable verification;
- branch creation, implementation, commits, merges, and other mutations unless
  an existing workflow explicitly assigns them elsewhere.

**Private GitHub mirror is authoritative for committed/pushed state available there:**
- committed source and documentation;
- `WORKFLOW.md`, `AGENTS.md`, `STATE.md`, `PROMPTS.md`, ADRs, plans and backlog;
- task briefs and worker reports;
- pushed branches and commit SHAs;
- commit history;
- committed file contents;
- committed diff/range inspection when WORKFLOW permits such inspection (§6).

**Critical rule:** GitHub presence does **not** prove a clean local working tree, local
runtime state, or a fresh passing gate. Under supervised-worker fallback (§14), fresh
local execution facts (git status, gate output, ref comparisons) are established by a
supervised local worker in the authoritative local checkout and returned to the orchestrator.

### Model table — edit when your subscriptions/tokens change

| Tier | Model(s) | Use for |
| --- | --- | --- |
| ORCH | Opus 5 **or** GPT 5.6 sol (whichever has tokens) | Orchestration only — never code |
| T3 (top) | GPT 5.6 terra / Opus 5 (full) | Judgment, cross-cutting, new patterns |
| T2 (mid) | Claude Code (Sonnet) / Codex | Multi-file work inside known architecture |
| T1 (cheap) | Gemini Flash / Codex low | Mechanical, gate-verified, tight allowlist |

Models within a tier are interchangeable. Rotating the orchestrator between Opus 5
and GPT 5.6 is safe **only because** all state lives in files — never let either
one become the memory.

---

## 1. Roles

**Orchestrator (chat).** Plans, writes briefs, reviews reports and machine-verifiable
evidence (never diffs unless risk-labeled, §6), maintains docs. The primary orchestrator
(ChatGPT) remains authoritative for all project decisions: interpreting governance,
determining session progression, drafting briefs, architecture reasoning, evaluating
worker outputs, requesting retries, and approving closure. It does **not** require direct
local shell access when operating under the supervised-worker fallback (§14). Read-only
with respect to code. Every brief it emits MUST carry a `Model:` line (§3). It never
assesses "how hard" a task feels — it applies §4 and §5 mechanically.

**Workers (fungible).** Codex, Claude Code, Gemini Flash — all start **cold** from
a brief. The brief is the whole context. No worker is ever the memory. A task that
cannot be executed cold is a task that is not yet specified — return it to the
orchestrator.

**Supervised local worker (delegated executor).** A worker session with terminal access
to the authoritative local checkout, executing explicit shell commands and edits
delegated by the orchestrator. It is authoritative for local runtime/gate/git facts,
but possesses **zero project decision authority**: it cannot alter architecture, expand
scope, waive failures, or accept its own work (§14).

**Closure worker (mechanical).** A separate T1 worker that performs
already-authorized slice closure: merge, STATE.md write (verbatim content
authored by the orchestrator), final gate, handoff packaging and archive validation
in `handoff/`, and remote push synchronization (`git push origin main` and slice
branch). It makes **zero decisions** — any ambiguity, mismatch, or nonzero exit
(including push failure) is a STOP-and-report, never a judgment call. See §11.

**You.** The courier — and **not the routine terminal operator**. In supervised-worker
fallback (§14), you paste printed prompts from the orchestrator to the local worker, and
paste returned machine-verifiable evidence from the worker back to the orchestrator. This
is a first-class supported project workflow, not an exception. Zero composition: if you
are writing a prompt or interpreting git output by hand, a step was skipped somewhere.
The owner does not routinely upload handoff ZIPs, `.diff` files, or `.md` reports when
pushed to the private GitHub mirror. Normal git/shell/gate/diff/merge work is placed in
worker prompts as **complete terminal procedures** — actual commands with fail conditions,
never "check the branch" or "run the gate". Critical checks must be executable, not prose
(clean working tree, expected `main` HEAD, expected slice HEAD, nonzero gate exit →
STOP).

**Concurrency: strict one-writer invariant.** Only one agent/process may mutate
the repository working tree at a time. The orchestrator does not edit docs while
a worker is modifying the repo. Close a writer before opening the next.

**Session ownership.** A logical orchestration session consists of one primary
orchestrator chat, one or more cold/local execution workers, and relayed evidence. The
primary orchestration chat owns the task lifecycle from startup through acceptance and
closure. Workers are fungible and replaceable: if a worker fails or loses context, the
orchestrator dispatches a fresh worker against verified repository state.

---

## 2. Brief schema

Every brief in `tasks/<ID>.md` contains, exhaustively:

```
Task:        <concrete, single outcome>
Allowlist:   <exhaustive file list — anything else is a scope violation>
Acceptance:  <gate numbers / tests that prove completion>
Stop-and-ask:<conditions where the worker halts and reports>
Risk:        <none | migration | auth-security | public-api | data-loss>
Model:       <worker> / <tier> / <effort>
Why:         <one line — which §4 row triggered this routing>
Fallback:    <same-tier alternative if primary is out of tokens>
```

The `Why` line is mandatory: it makes routing auditable. When routing turns out
wrong, fix the rubric row it cites, not the vibe.

---

## 3. Routing — the Model line

Format: `Model: gemini-flash / T1 / low` etc.

**Fallbacks stay within tier.** Out of tokens on a T3 task ⇒ wait or switch to the
other T3 model. Never silently downgrade tier — a downgrade is a routing decision
and gets its own `Why`.

---

## 4. Routing rubric

| Axis | T1 OK when… | Escalate when… |
| --- | --- | --- |
| Verification | Gate/tests catch failure automatically | Failure detectable only by judgment |
| Blast radius | Tight allowlist, reversible, one module | Cross-cutting; touches API/migrations/security |
| Spec completeness | Brief leaves zero decisions to the worker | Worker must exercise design judgment |
| Novelty | Existing pattern to copy | New pattern being established (it will be copied) |

Highest triggered row wins. **Gates subsidize cheap models**: the tighter the gate,
the lower the tier you can route — keep the executable rules sharp and T1 stays
usable.

**Effort rule:** high effort buys reasoning; it is wasted on mechanical work. Fully
specified + gate-verified ⇒ low effort even on a big model. Many simultaneous
constraints ⇒ high effort even on a mid model.

---

## 5. Escalation ladder

1. **Failure 1:** retry same tier. Brief amended with the failure evidence.
2. **Failure 2:** escalate one tier. Never a third attempt at the same tier.
3. **Ceiling (T3 failed):** the task is misspecified, not under-modeled. Return to
   the orchestrator as a **design** problem: split the slice, tighten the
   allowlist, or write the missing ADR. Then re-dispatch from step 1.

Every attempt is **counted, not absorbed**. The orchestrator logs
`Escalation status:` in `STATE.md` at close (see PROMPTS.md). A slice that took
three dispatches but shows zero attempts means the counter is being gamed — audit
the orchestrator's CLOSE output.

---

## 6. Risk labels and committed review

Labels are a **lookup, not a judgment** — assigned at brief-writing time by
file-path match:

| Label | Applies when the allowlist touches… |
| --- | --- |
| `migration` | Schema/data migration files |
| `auth-security` | Auth, secrets handling, permission checks |
| `public-api` | Anything importable/callable by external consumers |
| `data-loss` | Deletes, overwrites, irreversible transforms |

A risk-labeled brief ships with a pre-committed T3 review pass of the **full
diff** (the one exception to reviewer-never-reads-the-diff). The review is decided
before execution precisely so a clean report cannot talk anyone out of it. Treat a
risk label like a failing test: no merge until the review line in the report is
filled.

**Review transport:**
- When GitHub is available and the branch is pushed, the designated T3 reviewer
  reads the full diff of branch `slice/<ID>` against `main` directly from GitHub.
- If GitHub is unavailable or offline, the reviewer inspects the diff via local
  git diff (`git diff main...slice/<ID>`) or an uploaded `.diff` file.
- **Permission boundary:** GitHub availability does **not** authorize the
  orchestrator to inspect the full diff for non-risk slices. The report-only
  boundary in §1 remains binding.

---

## 7. ADR cold-review convergence rule

Architecture errors need an independent catcher. Any decision that creates or
substantively modifies an ADR is reviewed by a **fresh, cold** orchestrator
session that reads only the repository (see PROMPTS.md §ADR cold review). Cold
review exists to detect concrete architecture defects, not to optimize an ADR
until no better design can be imagined.

A single ADR **lineage** may receive at most **three cold-review sessions**. A
lineage is the same underlying architectural decision/problem scope through its
draft and revision history. Renumbering an ADR, rewriting wording, moving the
same unresolved design to another file, or otherwise cosmetically repackaging it
does not reset the count. A materially new architectural decision introduced
after an earlier ADR has been accepted may start a new lineage; this exception
must not be used to bypass the cap.

The three reviews have different scopes:

1. **Cold review #1 — broad architecture challenge.** Review internal
   contradictions, conflicts with accepted ADRs/AGENTS/WORKFLOW, unsafe data or
   API semantics, non-executable sequencing, materially understated costs,
   inadequately supported alternatives, and missing failure-state or ownership
   contracts. Genuine blockers return to revision.
2. **Cold review #2 — focused remedy verification.** Verify review-1 objections
   are actually resolved, inspect direct knock-on contradictions caused by those
   remedies, and catch a serious material correctness/executability/integrity
   defect genuinely missed by review #1. It is not another unrestricted redesign
   pass. Optional refinements do not qualify as blockers.
3. **Cold review #3 — FINAL CONVERGENCE REVIEW.** This is the last cold review
   permitted for the lineage. Its default outcome is approval/freeze when the
   architecture is coherent enough to implement. It may block only for a severe
   defect involving data corruption/data loss, security or integrity failure,
   architecture impossible or non-executable as specified, direct contradiction
   with a binding invariant/accepted ADR/required external contract, or a
   failure-state/atomicity defect capable of materially incorrect persistent
   state.

Review #3 must not block for wording/style, naming preferences, implementation
details safely owned by a slice, optimizations, additional test ideas,
speculative future requirements, merely preferable alternatives, rare
non-destructive cases that already fail closed safely, or opportunities to make
an executable contract more elegant.

**There is no fourth ordinary cold review for the same ADR lineage.** If review
#3 finds no severe blocker, approve the ADR, remove `NEEDS COLD REVIEW`, freeze
the architecture, and resume implementation.

If review #3 still finds a severe blocker, the reviewer records terminal
**final-convergence blockers** (`F1`, `F2`, ...) under the ADR's existing
`## Cold review` section. Each record states the concrete severe defect, why it
meets the review-3 severity threshold, and the required
simplify/split/descope direction. These are terminal evidence, not ordinary
objections that lead to another same-lineage revision. Replace
`NEEDS COLD REVIEW` with **`NON-CONVERGENT / BLOCKED`** and permanently close
that lineage.

A NON-CONVERGENT / BLOCKED lineage is not substantively revised and sent through
review #4. Recovery requires either abandoning/descoping the affected product
scope or creating a genuinely new **successor ADR lineage** whose architecture
is materially simpler, narrower, split, or otherwise materially different. The
successor must explicitly identify and supersede the blocked lineage. Cosmetic
renaming, file movement, wording cleanup, or preservation of substantially the
same unresolved architecture does not create a new lineage. A legitimate
successor starts at cold review #1 and receives its own three-review cap; this is
not review #4 because the prior lineage remains terminally closed.

**Cold review is defect detection, not architecture optimization.** The existence
of a better imaginable design is not itself a blocker. Non-blocking improvements
belong to the owning implementation slice, `docs/backlog.md`, or no action.

---

## 8. Session hygiene

- **Chain rule:** every CLOSE prints the next session's OPEN prompt, placeholders
  filled. You never compose prompts.
- **Point, never paste.** Handoffs are repository, commit, and file pointers to the
  authoritative private GitHub mirror. Pasting state or uploading redundant files
  costs tokens for the 90% that is irrelevant and dilutes attention across all of it.
- **No `/compact`.** It summarises lossily. End the session and start clean.
- **Transition signals** (any one ⇒ close): re-reads a file it already read ·
  contradicts an earlier decision from the same session · re-derives an
  established conclusion · past ~half the context window.
- A decision that exists only in conversation is already lost. CLOSE step 4 in
  PROMPTS.md is the one that matters; everything else is recoverable from git.

---

## 9. Do not

- Do not let the orchestrator write code, or a worker write docs/ADRs
  (exception: the closure worker writing orchestrator-authored STATE.md
  content verbatim, §11).
- Do not dispatch a brief without `Model:` + `Why:` + `Fallback:` lines.
- Do not retry a third time at the same tier.
- Do not downgrade tier as a token workaround without a logged `Why`.
- Do not merge a risk-labeled slice whose review line is empty — green gate or not.
- Do not keep a closed session open "just in case".
- Do not continue an orchestrator chat into the next slice after successful
  closure (§10).
- Do not hand the owner routine terminal commands — that work goes into worker
  prompts (§1).
- Do not emit a reusable orchestrator prompt without an owner-facing
  `## Next step` immediately after it (§10; PROMPTS.md header) — a prompt
  without one is an incomplete dispatch.
- Do not ask the owner to upload handoff ZIPs, reports, or diff files when the
  required commits/branch are pushed and accessible on the private GitHub repository.
- Do not treat GitHub presence as proof of clean local working tree, local
  runtime dependencies, or fresh passing gate execution (§0, §10).
- Do not inspect full diffs on non-risk slices merely because GitHub makes them
  visible (§1, §6).
- Do not commit or push secrets, credentials, `.env`, local databases (`*.sqlite`),
  `.venv`, model caches, or user data (§13, AGENTS G9).
- Do not produce a handoff without successful remote push synchronization (or
  validated fallback ZIP when offline) (§11).
- Do not let the closure worker resolve anything — STOP-and-report only (§11).
- Do not proactively monitor, narrate progress, or repeatedly poll healthy long-running commands unless explicitly instructed by the owner/orchestrator (§15).
- Do not rerun the full repository gate after every small edit during
  implementation or repair — validate in stages (§16): focused checks during
  iteration, one full validation when the candidate is believed final, and a
  fresh full validation whenever the candidate changes after the last success.

---

## 10. Per-slice orchestrator lifecycle

The canonical lifecycle — everything in this section serves it:

```
fresh orchestrator (reads GitHub committed state) → implementation worker
→ orchestrator review/retries → mechanical closure worker → final main gate
→ STATE update → handoff packaging + remote push → exact next-chat prompt
→ current orchestrator ends → fresh orchestrator for next slice
```

**One-time pre-repository bootstrap.** The normal slice lifecycle requires an
existing Git repository and `main` HEAD. If `.git` does not exist, no slice
worker may be dispatched yet and the normal Worker OPEN preflight is not
applicable. A non-slice orchestrator instead dispatches exactly
PROMPTS.md §Repository bootstrap worker to a T1 terminal worker. That procedure
is mechanical and fail-closed: it verifies the target is not already in a Git
work tree, required governance files and Git identity exist before mutation,
runs `git init -b main`, commits the pre-existing tree, verifies a clean `main`,
and prints the resulting `main` HEAD. It is not a slice attempt, does not
increment the audit counter, does not require a gate that slice-0 has not yet
created, and never turns the owner into the terminal operator. After it
succeeds, slice-0 uses that printed SHA as its initial expected `main` HEAD.

- **One orchestrator conversation per slice** — from dispatch through retries,
  review, acceptance, and closure. Retries and blocked attempts stay in the
  same chat; a fresh chat happens only after **successful closure**, never
  after an implementation failure.
- **The chat ends after successful slice closure.** It may not continue into
  the next slice. Before stopping, it must print the exact next-chat prompt
  (`NEW SLICE OPEN`, PROMPTS.md) identifying the pushed `main` HEAD, repository
  identity, and fallback ZIP path, followed by an owner-facing `## Next step`.
- **GitHub-first orchestrator startup:** When a GitHub remote/integration is
  available, every new orchestrator uses the private GitHub repository as the
  default persistent source for committed project context (`STATE.md`,
  `WORKFLOW.md`, `AGENTS.md`, `docs/plan.md`, `docs/backlog.md`, `docs/adr/`,
  previous slice report, and `tasks/<NEXT>.md`). It must not ask the owner to
  upload a handoff ZIP merely to obtain files that are already committed and
  pushed.
- **Fresh-orchestrator startup is a formal verification stage**, before any
  dispatch:
  1. Manifest / expected `main` HEAD equals actual local `git rev-parse main`
     (via a read-only terminal worker).
  2. Working tree cleanliness (`git status --porcelain` is empty).
  3. Remote sanity check (`git remote get-url origin` / `git fetch --dry-run origin`
     if remote is configured).
  4. Fresh gate verification: worker runs `make gate`, capturing stdout and
     stderr, confirming clean passing status.
  5. `STATE.md` agrees with disk: escalation status, audit counter, blocked items.
  6. Both audit triggers checked: phase boundary reached, or `Sessions since last audit` ≥ 10.
  7. **The brief's actual `Depends:` field** — every listed dependency verified
     merged in the local Git repository, never assumed to be "the previous slice".
- **Fallback startup transport:** If GitHub is unavailable, disconnected, stale,
  missing the required branch, or otherwise cannot provide the required committed
  state, the existing validated handoff ZIP in `handoff/` remains the fail-closed
  fallback startup material.
- **Pre-dispatch repository contradictions are not implementation failures.**
  Repairing a stale file before Attempt 1 does not count as an attempt on the
  §5 ladder. But **cross-file contradictions block dispatch until durably
  repaired in files** — the orchestrator may not mentally pick which file is
  right and continue.
- **`## Next step` rule (all prompt types).** Every reusable orchestrator
  prompt — repository bootstrap, implementation, retry, governance/repair,
  escalation, review, closure, audit, `NEW SLICE OPEN` — is immediately followed by an owner-facing
  `## Next step` that says: exactly what to do next; which worker/model/session
  receives the prompt; whether a fresh conversation is required; what repository
  identity / branch / commit to target (or fallback ZIP to attach); and what
  evidence to return. The `## Next step` stays **outside** the prompt block, so
  owner instructions never leak into what a worker executes.

---

## 11. Closure and handoff — mechanical, fail-closed

After the orchestrator accepts a slice, it dispatches the **closure worker**
(T1, complete procedure in the prompt — PROMPTS.md §Closure worker). The worker:

1. Verifies, executably: clean working tree; `main` HEAD equals the expected
   SHA (i.e. **`main` has not moved** since acceptance); the slice branch HEAD
   equals the accepted SHA. Any mismatch → STOP.
2. Merges (`--no-ff`), then writes the orchestrator-authored STATE.md content
   **verbatim** and commits it.
3. Runs the **final authoritative gate on `main` after all closure commits** —
   including the STATE.md commit — capturing stdout **and stderr** to
   `handoff/main-gate.txt`. Nonzero exit → STOP: no handoff exists.
4. Generates `handoff/git-log.txt` and authors `handoff/MANIFEST.md`.
5. Packages the handoff ZIP snapshot in `handoff/orchestrator-handoff-slice-<NEXT>.zip`:
   governance files (`WORKFLOW.md`, `AGENTS.md`, `PROMPTS.md`, `STATE.md`), `docs/adr/`,
   `docs/plan.md`, `docs/backlog.md`, the **next** brief, the previous slice's report,
   `handoff/git-log.txt`, `handoff/main-gate.txt`, and the manifest. Missing required
   file → STOP.
6. Validates the ZIP after creation (archive integrity test) and re-checks the
   manifest's `main` HEAD against `git rev-parse main`. Mismatch → STOP.
7. **Remote push synchronization:** pushes updated `main` (and slice branch) to
   `origin` (`git push origin main && git push origin slice/<ID>`). Nonzero exit on
   push → STOP: handoff fails closed.
8. Prints the final `main` HEAD, remote push status, next brief path, and fallback
   ZIP path, then stops.

**Manifest requirements:** the **actual final `main` HEAD** (post-closure);
review status reflecting the slice type — risk-labeled →
`PASS (ORCHESTRATOR, full diff)`, risk-none → `NOT REQUIRED (risk-none)`;
audit counter equal to the committed STATE.md; next brief path and dependency.

**Audit counter:** normal slice closure increments `Sessions since last audit`
in STATE.md **exactly once**. Worker, preflight, donor-inspection, and
governance-repair activity does not increment it. The audit triggers checked at
every fresh startup: phase boundary, or counter ≥ 10.

**Fail closed:** a missing file, failing gate, moved `main`, push failure, or
invalid ZIP means there is **no successful handoff** — the closure worker reports,
and the orchestrator (same chat, per §10) resolves and re-dispatches closure.

**First-slice startup exception:** the very first slice has no prior closure, so
its fresh orchestrator starts from the repo itself, not a ZIP or prior push.
Repository bootstrap (§10 / PROMPTS.md §Repository bootstrap worker) must already
have created `main`. Because no prior slice could have produced a manifest or
`main-gate.txt`, NEW SLICE OPEN uses the bootstrap worker's printed `main` HEAD
in place of those two checks and verifies STATE.md records Gate = none. Every
closure from slice-0 onward produces the normal manifest, final gate evidence,
remote push synchronization, and fallback handoff ZIP.

---

## 12. Donor repositories

Current donors: `~/projects/german app` (gate tooling and executable-check
patterns; also the future compose-integration host) and `~/projects/flashcard
app` (design-session artifacts, already superseded by `docs/adr/`).

- Reuse model: **inspect → adapt the generic primitive → flashcard-native code
  and tests**. A donor must never become a runtime dependency.
- Donor inspection is **read-only**: no modification of either repository, no
  branches, no commits. It does not count as a slice attempt on the §5 ladder.
- Inspection uses the **complete local repo**, not a possibly-incomplete remote.
  The orchestrator does not inspect donors itself — it generates a prompt for a
  local worker that has the full repository.
- Donor-specific machinery (the lecture app's FABLE/orchestrator governance,
  content-boundary checks scoped to its rules, its web persistence layer) is
  **excluded by default** unless explicitly required by a brief.
- Donor reuse cannot silently change scope. If reuse needs a new dependency, an
  allowlist change, an ADR change, or a contract change, it returns to
  governance first — brief amended or ADR written before code moves.

---

## 13. Privacy, remote sanity, and ignored material

- **Repository privacy:** the repository is expected to be **private** unless the
  owner deliberately changes that decision.
- **Ignored materials invariant:** `.gitignore` must strictly prevent committing
  or pushing credentials, API keys/tokens, `.env` files, local runtime databases
  (`*.sqlite`, `*.db`), `.venv`, model/downloader caches, temporary files, and
  machine-specific state (AGENTS G9).
- **Remote sanity checking:** startup and closure sanity checks use configured
  remotes (`git remote get-url origin`, `git fetch --dry-run origin`) without
  hardcoding owner-specific URLs or printing/storing credentials.

---

## 14. Supervised worker fallback

The supervised worker fallback is a first-class, supported project execution strategy
allowing the primary ChatGPT conversation to remain the project orchestrator even when it
lacks direct access to the local filesystem and terminal.

```
+-------------------------------------------------------------------------------+
| PRIMARY ORCHESTRATOR (ChatGPT chat)                                           |
| Decision Authority: architecture, governance, briefs, evaluation, acceptance  |
+------------------------------------+------------------------------------------+
                                     |
               (Dispatches brief)    |    (Returns machine-verifiable evidence)
                                     v    |
+------------------------------------+----+-------------------------------------+
| OWNER (Courier / Transport Relay)                                             |
| Relays: orchestrator prompt -> local worker; local evidence -> orchestrator   |
+------------------------------------+------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
| SUPERVISED LOCAL WORKER (Terminal / IDE session in local repo checkout)       |
| Execution Authority: runs commands, edits within allowlist, runs make gate   |
+------------------------------------+------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
| AUTHORITATIVE LOCAL CHECKOUT               PRIVATE GITHUB MIRROR              |
| Local git/gate/runtime/filesystem facts    Persistent committed/pushed state  |
+-------------------------------------------------------------------------------+
```

### 14.1 The authority and responsibility model

The repository distinguishes three distinct authorities plus the transport relay:

1. **Decision Authority (Primary Orchestrator):**
   The primary ChatGPT orchestration chat retains sole authority for:
   - interpreting `WORKFLOW.md`, `AGENTS.md`, and project contracts;
   - deciding what task or session comes next;
   - composing worker briefs and defining exhaustive allowlists;
   - architectural and governance reasoning;
   - evaluating returned worker evidence and reports;
   - requesting retries or escalating along the §5 ladder;
   - accepting or rejecting worker deliverables;
   - deciding when a slice or governance session may proceed to closure;
   - authoring next-session prompts and STATE.md content.
   The orchestrator does **not** need direct local terminal access to exercise this authority.

2. **Execution Authority (Supervised Local Worker):**
   A worker with terminal/filesystem access to the authoritative local checkout is
   authoritative for facts that can only be established locally:
   - `git status` and working tree cleanliness;
   - actual checked-out branch and `git rev-parse` ref values;
   - local vs. remote comparisons after `git fetch`;
   - installed dependencies, models, and machine environment;
   - runtime execution and `make gate` results;
   - filesystem mutations, commits, merges, and pushes.
   **Prohibition on self-authorization:** The worker performs *only* work expressly
   delegated by the orchestrator. It does not gain project decision authority merely
   because it has local terminal access. It may not silently redesign architecture,
   alter workflow rules, expand allowlists, accept its own implementation, waive
   failing checks, or invent next steps.

3. **Evidence Authority:**
   - The **authoritative local checkout** is the sole source of local execution facts,
     working tree state, and fresh gate evidence.
   - The **private GitHub mirror** is the persistent authoritative mirror for
     committed and pushed state (`STATE.md`, ADRs, briefs, history, pushed refs).
   - Under no circumstances is GitHub redefined as authoritative for runtime/gate execution.

4. **Transport Layer (Owner):**
   When no direct tool integration connects the orchestrator to the local environment,
   the owner acts strictly as a transport relay:
   ```
   orchestrator prompt -> local worker
   local worker result -> orchestrator
   ```
   The owner is the transport courier, not the verifier or terminal operator. The owner
   is never asked to manually interpret git or gate outputs, analyze diffs, decide
   retries, or make architectural choices.

### 14.2 Evidence relay protocol

When operating across the transport relay:
- The worker's exact command outputs, exit statuses, ref SHAs, and gate numbers are
  returned verbatim to the orchestrator.
- The orchestrator accepts returned output as local execution evidence only when the
  worker explicitly identifies the authoritative checkout and supplies the required
  commands, outputs, exit codes, and relevant SHAs.
- Pasted worker summaries without machine-verifiable evidence are not trusted. The
  orchestrator must demand missing evidence or issue a retry brief if evidence is
  incomplete.
- The worker must never ask the owner to interpret Git/gate results when the worker can
  evaluate and format that evidence itself.

### 14.3 Supervised worker brief requirements

Every brief dispatched to a supervised worker must be explicit, self-contained, and
follow the canonical brief schema (PROMPTS.md §Supervised local worker):

- **Authoritative repository path:** Target checkout location.
- **Expected branch & starting ref:** Expected branch and exact starting HEAD SHA.
- **Clean tree requirement:** Executable assertion that `git status --porcelain` is empty.
- **Allowed files (Allowlist):** Exhaustive file list — anything changed outside is a
  scope violation.
- **Forbidden files/actions:** Explicit prohibitions (e.g. no application edits in
  governance sessions, no rebase/delete of accepted branches).
- **Exact task:** Concrete, unambiguous implementation or verification steps.
- **Required checks & gate:** Exact gate commands and pass criteria.
- **Commit/push authorization:** Explicit declaration of whether the worker is authorized
  to commit and push, with the required commit messages.
- **Long-command execution rule:** Supervised workers obey the no-monitoring default (§15),
  launching long-running commands once with maximum blocking wait and remaining silent while
  healthy and running.
- **Required final evidence:** Exact formatted output required in the worker's report.
- **STOP conditions:** Explicit conditions causing immediate halt and report.

### 14.4 Commit and push protocol

When a task explicitly authorizes a supervised worker to commit and push:
1. **Scope verification:** Worker verifies `git status --porcelain` matches exactly the
   authorized allowlist.
2. **Pre-commit validation:** Worker runs required checks (`git diff --check`, `make gate`).
3. **Commit:** Worker commits with the exact message specified by the orchestrator.
4. **Post-commit gate:** Worker verifies gate passes on the committed tree.
5. **Push:** Worker pushes the authorized ref (`git push origin <branch>`).
6. **Push verification:** Worker fetches and verifies local HEAD equals remote ref.
7. **Evidence return:** Worker reports full commit SHA, gate numbers, and ref equality
   evidence back to the orchestrator.

The orchestrator reviews the returned evidence before declaring the operation complete.

### 14.5 Separation of duties and no self-review

Separation of duties is an absolute invariant across all workflows:
- **No implementation self-review:** An implementation worker that creates or modifies
  code may not declare a slice accepted merely because `make gate` passes. The primary
  orchestrator reviews the report and evidence to decide acceptance or retry.
- **Governance and ADR work:** The primary orchestrator designs and decides ADR and
  governance revisions. A supervised local worker may apply those exact edits to the local
  checkout and commit them, but does not become the decision maker.
- **Cold review remains separate:** When repository policy (WORKFLOW §7 / AGENTS G7)
  requires a fresh cold review, that review must be conducted in a separate fresh
  orchestrator session that reads only the repository. Supervised execution does not
  waive or merge the cold-review requirement.

### 14.6 Fail-closed conditions

The supervised fallback must fail closed (STOP and report) rather than inferring success
when any required local condition or evidence is unmet. At minimum, a worker must halt
immediately on:
- unexpected starting HEAD SHA;
- dirty working tree where a clean start is required;
- checked-out branch differing from expected;
- remote ref mismatch or unexpected local/remote divergence;
- moved accepted slice ref;
- any nonzero exit from `make gate` or test suite;
- commit or push failure;
- any file modified outside the brief's allowlist;
- evidence inconsistent with the claimed execution outcome.

The orchestrator reviews the failure evidence and issues a narrowly scoped retry.

### 14.7 Read-only supervised workers

The orchestrator may dispatch read-only supervised workers for:
- startup verification and preflight checks;
- gate re-runs and benchmark measurements;
- Git ref, log, and remote status inspection;
- donor repository inspection (§12);
- closure verification;

without transferring decision authority to the worker.

---

## 15. No-monitoring default for long-running commands

Long-running shell and tool operations do not require continuous LLM attention.
Unless the owner or orchestrator explicitly requests monitoring or progress updates
for the current task, workers MUST NOT proactively monitor, narrate, or repeatedly
poll a running command.

### 15.1 Scope and examples

This rule applies to all supervised workers, terminal workers, closure workers,
governance workers, and automated execution prompts across the repository.
Examples of long-running operations subject to this rule include:

- `make gate` and full test suites (`pytest`);
- Docker and Podman image builds;
- package installations and dependency resolution;
- remote downloads and model fetching;
- dictionary and database builds (e.g. Wiktextract, Tatoeba, multilingual indexing);
- schema migrations or database indexing jobs;
- large file hashing, checksum calculation, and integrity validation;
- any other command or tool execution expected to consume substantial wall-clock time.

### 15.2 Default execution behavior

When executing a long-running command:

1. **Launch once:** Start the command exactly once.
2. **Maximum blocking timeout:** Use the longest practical blocking execution timeout
   supported by the execution environment or tool interface.
3. **Prohibited while running:** While the process is running, workers MUST NOT:
   - emit "still running", "waiting", "in progress", or similar intermediate progress messages;
   - repeatedly invoke status, process-list, or task-management tools merely to observe progress;
   - repeatedly poll the process or check its liveness;
   - re-read repository files or browse the workspace while waiting;
   - perform unrelated model reasoning merely because the process has not yet exited;
   - launch duplicate copies of the same command;
   - cancel or restart a healthy command simply because it is taking wall-clock time.
4. **Resume conditions:** Resume model reasoning and execution ONLY when one of the
   following occurs:
   - the command completes;
   - the command fails (nonzero exit or runtime error);
   - a genuine configured execution timeout or hang threshold is reached;
   - execution reaches an explicit decision point requiring orchestrator judgment;
   - the owner or orchestrator explicitly asks for a status check or progress update.
5. **Preserve evidence:** Preserve final `stdout`, `stderr`, and exit status for the
   required task evidence and reports.
6. **Async/background handles and result retrieval:** If the execution interface cannot
   block until completion and returns an asynchronous/background handle:
   - prefer a blocking wait primitive configured with the longest practical wait interval;
   - do not perform frequent polling;
   - if a subsequent retrieval call is technically required to obtain the final result
     or status, make only the minimum number of retrieval calls necessary;
   - technically necessary final-result retrieval is not considered prohibited monitoring.
7. **No idle narration:** Do not send user-facing progress messages solely because a
   command remains healthy and unfinished.

### 15.3 Explicit owner override

An explicit instruction from the owner or orchestrator overrides this default for that
specific task.

Examples of explicit overrides:
- `"monitor this command"`
- `"keep me updated"`
- `"check progress every ..."`
- `"tell me if it is still running"`

Any such override is **task-local only**. It applies solely to the specific command or
task requested and does not permanently disable or alter the repository-wide
no-monitoring default.

### 15.4 Token-efficiency principle and rationale

A running local process consumes wall-clock time, not useful model reasoning. Repeated
LLM wake-ups that only establish "still running" increase token and model usage and
consume conversation context without producing new task evidence.

Therefore:

> **SILENCE WHILE HEALTHY AND RUNNING IS THE DEFAULT.**

---

## 16. Staged validation — focused iteration, full verification at the end

Normative for all implementation, repair, and review-repair work in this
repository. This is an **efficiency rule, not a safety reduction**: it changes
*when* full validation runs, never *whether* the final candidate is fully
validated.

### 16.1 During iteration — focused validation first

While implementing or repairing, workers MUST NOT repeatedly run the full
repository gate after every small edit. Use the smallest meaningful validation
first:

- tests covering the directly changed module/subsystem, e.g.
  `pytest -q tests/test_feature.py`, optionally narrowed with
  `pytest -q tests/test_feature.py -k relevant_behavior`;
- nearby regression tests covering directly affected behavior;
- targeted lint/type checks where possible (e.g. `ruff check <paths>`,
  `mypy <paths>`).

A full-gate rerun during iteration is permitted only when the change is
unusually broad or focused tests cannot provide meaningful confidence.

### 16.2 Candidate believed final — one full validation

Run the repository's complete authoritative validation exactly once for the
final candidate: `make gate`, plus any slice-specific required validation
(frontend/build/E2E, APKG, Playwright, etc.) mandated by the slice brief.
Slice-specific validation is additive; focused checks never replace it, and
focused checks alone never certify a candidate for acceptance.

### 16.3 Failure and repair loop

If full validation fails:

1. inspect the failure;
2. repair it;
3. confirm the repair with focused validation;
4. rerun full validation only once the resulting candidate is believed final
   again.

The same loop applies to independent review and review-repair cycles:

    review finding → repair → focused verification → candidate ready
    → one full validation → re-review / acceptance as required

### 16.4 Invalidation invariant (mandatory)

> **NO FINAL ACCEPTANCE / MERGE / RELEASE WITHOUT SUCCESSFUL FULL VALIDATION
> OF THE EXACT FINAL CANDIDATE.**

Any code change after the most recent successful full validation invalidates
that result: it no longer certifies the candidate. An earlier passing gate
result can never substitute for a fresh full validation of the final state.

The intended iteration loop:

    implement → focused tests → repair → focused tests
    → candidate final → full validation → submit/accept

Not:

    edit → full suite → edit → full suite → edit → full suite

### 16.5 Non-negotiables

This rule does not remove `make gate`, does not make focused tests sufficient
for final acceptance, does not permit merge on targeted tests alone, does not
allow an earlier gate result to survive later code changes, and does not weaken
independent review, risk review (§6), escalation or cold-review limits (§5,
§7), slice-specific validation requirements, or any fail-closed condition
(§11, §14.6). Long-command execution (§15) applies unchanged: full gates are
launched once with the longest practical blocking timeout, without polling or
narration while healthy.
