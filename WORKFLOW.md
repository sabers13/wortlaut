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
runtime state, or a fresh passing gate.

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

**Orchestrator (chat).** Plans, writes briefs, reviews reports (never diffs),
maintains docs. When GitHub access is available, reads committed repository state
directly from the private GitHub repository without requiring the owner to upload
handoff ZIPs, markdown reports, or briefs. Read-only with respect to code. Every
brief it emits MUST carry a `Model:` line (§3). It never assesses "how hard" a task
feels — it applies §4 and §5 mechanically.

**Workers (fungible).** Codex, Claude Code, Gemini Flash — all start **cold** from
a brief. The brief is the whole context. No worker is ever the memory. A task that
cannot be executed cold is a task that is not yet specified — return it to the
orchestrator.

**Closure worker (mechanical).** A separate T1 worker that performs
already-authorized slice closure: merge, STATE.md write (verbatim content
authored by the orchestrator), final gate, handoff packaging and archive validation
in `handoff/`, and remote push synchronization (`git push origin main` and slice
branch). It makes **zero decisions** — any ambiguity, mismatch, or nonzero exit
(including push failure) is a STOP-and-report, never a judgment call. See §11.

**You.** The courier — and **not the routine terminal operator**. You paste
printed prompts between surfaces. Zero composition: if you are writing a prompt
by hand, a CLOSE step was skipped somewhere. The owner does not routinely upload
handoff ZIPs, `.diff` files, or `.md` reports when pushed to the private GitHub
mirror. Normal git/shell/gate/diff/merge work is placed in worker prompts as
**complete terminal procedures** — actual commands with fail conditions, never
"check the branch" or "run the gate". Critical checks must be executable, not prose
(clean working tree, expected `main` HEAD, expected slice HEAD, nonzero gate exit →
STOP).

**Concurrency: strict one-writer invariant.** Only one agent/process may mutate
the repository working tree at a time. The orchestrator does not edit docs while
a worker is modifying the repo. Close a writer before opening the next.

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

## 7. ADR two-pass rule (this variant's ceiling compensation)

Without a super-model, architecture errors have no upstream catcher. Compensate
structurally: any decision that creates or modifies an ADR is drafted in one
orchestrator session, then reviewed by a **fresh, cold** orchestrator session that
reads only the repo (see PROMPTS.md §ADR review). Cold review catches
context-contamination errors, which is most of them.

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
