# Prompts — Base Variant (no Fable), per-slice lifecycle

Paste these verbatim. Placeholders in `<angle brackets>` are filled by the
*previous* session's CLOSE (chain rule) — if you are filling one by hand, a
CLOSE step was skipped.

**The `## Next step` rule (normative, WORKFLOW.md §10).** Every reusable
orchestrator prompt below MUST be followed immediately by an owner-facing
`## Next step` that states: exactly what to do next; which worker/model/session
receives the prompt; whether a fresh conversation is required; what to attach
(handoff ZIP, briefs); and what evidence/output to return to the orchestrator.
The `## Next step` stays **outside** the prompt block so owner instructions
never become worker instructions. A reusable prompt without it is an
**incomplete dispatch**. This applies to every prompt type: repository
bootstrap, implementation, retry, governance/repair, escalation, review/risk,
closure, audit, and `NEW SLICE OPEN`.

---

## Orchestrator — NEW SLICE OPEN (canonical; printed by the previous slice's closure)

````
Read WORKFLOW.md, AGENTS.md and STATE.md from the attached handoff ZIP. The ZIP
is the authoritative startup material — do not rely on any previous chat's
memory. (First-slice exception: slice-0 has no ZIP; read the repo after the
one-time repository bootstrap worker has succeeded.)

You are the orchestrator for slice-<ID>, and this chat owns it from dispatch
through retries, review, acceptance, and closure. Startup is a formal
verification stage (WORKFLOW.md §10) — run it before any dispatch:

1. Manifest final main HEAD == `git rev-parse main` (via a read-only worker if
   a terminal is needed).
2. main-gate.txt in the ZIP shows a passing gate, stderr included; have a
   worker re-run <gate command> and compare numbers.
3. STATE.md agrees with disk: escalation status, audit counter, blocked items.
4. Audit triggers: phase boundary reached, or `Sessions since last audit` >= 10
   -> run the §Audit prompt first; no dispatch this session.
5. Read tasks/<ID>.md and verify EVERY entry in its `Depends:` field is merged.
   Do not assume the dependency is simply the previous slice.

For slice-0 only, there is no prior manifest or `main-gate.txt`: replace checks
1–2 with a read-only terminal worker running exactly:

```
test "$(git rev-parse main)" = "<bootstrap main HEAD>" || {
  echo "STOP: main differs from bootstrap receipt"; exit 1; }
test -z "$(git status --porcelain)" || {
  echo "STOP: working tree is not clean"; exit 1; }
sed -n '/^## Gate$/,/^## /p' STATE.md | grep -q '^- none' || {
  echo "STOP: STATE.md does not record Gate = none"; exit 1; }
```

Then perform checks 3–5 normally.

Any check fails, or any cross-file contradiction exists -> STOP and report;
repair durably in files before dispatch (repairs are not §5 attempts).

Then dispatch the implementation worker per the brief's Model line, with the
complete terminal procedure (commands + fail conditions). Retries and
escalations stay in this chat. After acceptance (and the §6 risk review if
labeled), dispatch the closure worker per PROMPTS.md §Closure worker. After a
validated handoff ZIP exists, print the next NEW SLICE OPEN prompt + ZIP path,
each with its ## Next step, then end this chat. Apply WORKFLOW.md mechanically;
cite rubric rows, never feel.
````

## Next step (template the closure prints under this prompt)

For **slice-0**, open a **fresh** orchestrator chat (ORCH model per WORKFLOW.md
§0) with terminal/read access to the repository **after** the one-time bootstrap
worker succeeded. Attach **no prior handoff ZIP**: none exists. Fill
`<bootstrap main HEAD>` in the prompt with the exact `BOOTSTRAP MAIN HEAD: <sha>`
receipt, paste the prompt above, and continue there.

For **slice-1 and later**, open a **fresh** orchestrator chat (ORCH model per
WORKFLOW.md §0), attach the validated `<zip path>` produced by the previous slice
closure, paste the prompt above, and continue there. In either case, return
nothing to this chat — it is closed.

---

## Orchestrator — OPEN (non-slice: question / checkpoint / governance)

```
Read WORKFLOW.md, AGENTS.md and STATE.md.

I'm at <checkpoint | question | governance>. <one line of context>

Apply WORKFLOW.md mechanically: every brief carries Model/Why/Fallback per
§3–§4; escalations are counted per §5, never absorbed; risk labels per §6 are
file-path lookups. Every reusable prompt you emit is followed by an owner-facing
## Next step (§10). Do not assess task difficulty by feel — cite the rubric row.

Stop and report if STATE.md disagrees with what you find on disk rather than
reconciling silently.
```

---

## Repository bootstrap worker (one-time, before slice-0)

Use only when `.git` does not yet exist. This is a mechanical pre-slice
operation, not an implementation attempt. Send it to a T1 terminal worker; the
owner only ferries the prompt and returned receipt (WORKFLOW.md §10, AGENTS G3).

```
Read AGENTS.md and STATE.md. You are the one-time repository bootstrap worker.
Perform ONLY the commands below, in order. Any failed check or nonzero command
means STOP immediately and report the step/output; do not repair or improvise.

1  test ! -e .git || { echo "STOP: .git already exists"; exit 1; }
2  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
     echo "STOP: target is already inside a Git work tree"; exit 1
   fi
3  for f in WORKFLOW.md AGENTS.md PROMPTS.md STATE.md docs/backlog.md; do
     test -f "$f" || { echo "STOP: missing $f"; exit 1; }
   done
4  test -n "$(git config --get user.name)" || {
     echo "STOP: git user.name is not configured"; exit 1; }
   test -n "$(git config --get user.email)" || {
     echo "STOP: git user.email is not configured"; exit 1; }
5  git init -b main
6  git add -A
7  test -n "$(git diff --cached --name-only)" || {
     echo "STOP: nothing staged for initial commit"; exit 1; }
8  git commit -m "chore: bootstrap repository"
9  test "$(git branch --show-current)" = "main" || {
     echo "STOP: initial branch is not main"; exit 1; }
10 git rev-parse --verify HEAD >/dev/null
11 test -z "$(git status --porcelain)" || {
     echo "STOP: working tree not clean after bootstrap"; exit 1; }
12 printf 'BOOTSTRAP MAIN HEAD: '; git rev-parse HEAD

Do not create a slice branch, do not run a gate, and do not modify file content.
`make gate` is created by slice-0; absence of a gate is expected here.
```

## Next step

Send the prompt above to `gemini-flash / T1 / low` (fallback
`codex-low / T1 / low`) in a fresh worker session with terminal access to the
repo. Return to the orchestrator only the STOP report or the exact
`BOOTSTRAP MAIN HEAD: <sha>` receipt. Do not run these commands yourself.

---

## Worker — OPEN (implementation; all workers: Codex, Claude Code, Gemini Flash — always cold)

The orchestrator fills this with the **complete terminal procedure** — branch
commands, gate command, and executable fail conditions. "Check the branch" is
not a procedure.

```
Read AGENTS.md, then tasks/<ID>.md. Execute it on branch slice/<ID>.

Terminal procedure (run exactly; nonzero exit on any check = STOP and report):
  git status --porcelain          # must be empty before starting
  git checkout -b slice/<ID> <expected main HEAD>   # STOP if main HEAD differs
  <implementation per brief>
  <gate command>                  # STOP on nonzero exit; record numbers

The Allowlist block is exhaustive — anything changed outside it is a scope
violation. Stop and report on any Stop-and-ask condition rather than resolving
it yourself. You have no context beyond these files by design; if the brief is
insufficient to execute, that is a Stop-and-ask condition, not a license to
guess.
```

## Worker — CLOSE

```
Run <gate command>. Record the numbers, including stderr.

Commit by work unit — one logical change per commit, verification evidence in
the message. Then fill in ONLY the NARRATIVE section of tasks/<ID>.report.md:
decisions not in the brief, stop-and-ask conditions hit, problems noticed but
not fixed, work left undone. If the brief carried a Risk label, add the line
"Review: PENDING (T3, full diff)" at the top.

Print the report path, the branch HEAD SHA, and the gate numbers, then stop.
```

## Next step (orchestrator writes under every worker dispatch)

Send the prompt above to `<worker model / tier / effort>` in a fresh worker
session with terminal access to the repo. Return here: the report path, branch
HEAD SHA, and gate numbers, verbatim.

Interrupted mid-slice? Next worker opens with the same brief plus:
`Work already in progress on branch slice/<ID>; check git status before starting.`

---

## Closure worker (mechanical — dispatched after orchestrator acceptance)

The orchestrator fills every `<...>` and authors the full STATE.md content
inside the prompt. The worker decides nothing (WORKFLOW.md §11).

```
You are the mechanical closure worker for slice-<ID>. Perform ONLY the steps
below, in order. Any check that fails means STOP immediately and report the
step and output — you are not authorized to resolve anything.

1  git status --porcelain                      # non-empty -> STOP
2  test "$(git rev-parse main)" = "<expected main HEAD>"        || STOP  # main moved
3  test "$(git rev-parse slice/<ID>)" = "<accepted slice HEAD>" || STOP
4  git checkout main && git merge --no-ff slice/<ID> -m "<merge msg>"
5  Overwrite STATE.md with EXACTLY the content between the markers below.
   Commit: "slice-<ID> close: STATE update"
   ---STATE BEGIN---
   <orchestrator-authored STATE.md content, complete file, audit counter
    already incremented by exactly one>
   ---STATE END---
6  <gate command> > handoff/main-gate.txt 2>&1   # FINAL gate, AFTER the STATE
                                                 # commit; nonzero exit -> STOP
7  git log --oneline -25 > handoff/git-log.txt
8  Assemble handoff/orchestrator-handoff-slice-<NEXT>.zip containing:
   WORKFLOW.md AGENTS.md PROMPTS.md STATE.md docs/adr/ docs/plan.md
   docs/backlog.md tasks/<NEXT>.md tasks/<ID>.report.md handoff/git-log.txt
   handoff/main-gate.txt handoff/MANIFEST.md
   Any listed file missing -> STOP. No handoff exists on STOP.
9  Validate: python3 -c "import zipfile;
   assert zipfile.ZipFile('<zip>').testzip() is None" ; and verify
   MANIFEST.md's final main HEAD equals `git rev-parse main` -> else STOP.
10 Print the ZIP path and final main HEAD, then stop.
```

**MANIFEST.md template** (orchestrator authors it; closure worker packages it):

```
# HANDOFF MANIFEST — closes slice-<ID>, opens slice-<NEXT>
Final main HEAD:  <actual post-closure SHA — never a predicted one>
Review:           PASS (ORCHESTRATOR, full diff)   # risk-labeled slices
                  NOT REQUIRED (risk-none)         # risk-none slices
Gate:             PASS — see main-gate.txt (stdout+stderr)
Sessions since last audit: <n — must equal committed STATE.md>
Next brief:       tasks/<NEXT>.md  (Depends: <verbatim from the brief>)
```

## Next step (orchestrator writes under the closure dispatch)

Send the prompt above to a T1 worker (`gemini-flash / T1 / low`, fallback
`codex-low / T1 / low`) with terminal access. Return here: the ZIP path and
final main HEAD, or the STOP report verbatim. On success this chat prints the
NEW SLICE OPEN prompt and ends.

---

## ADR cold review (WORKFLOW.md §7)

Open a **fresh** orchestrator session (other model of the ORCH pair if available):

```
Read WORKFLOW.md, AGENTS.md, STATE.md, and docs/adr/<ID>. You have no other
context, deliberately.

Review this ADR against the repo as it exists on disk: internal contradictions,
conflicts with prior ADRs or AGENTS.md, costs understated, alternatives
dismissed without evidence. You are the only catcher above this decision — do
not defer.

Output: either "APPROVED — remove NEEDS COLD REVIEW" or a numbered objection
list written into the ADR under ## Cold review. Then close per Orchestrator
CLOSE (non-slice).
```

## Next step

Open a fresh chat with the **other** ORCH model, paste the prompt, no
attachments beyond repo access. Return here: APPROVED or the objection list.

---

## Risk-label review (WORKFLOW.md §6)

Open a T3 session:

```
Read AGENTS.md, tasks/<ID>.md, tasks/<ID>.report.md, then the FULL diff of
branch slice/<ID> against main.

This slice is risk-labeled <label>. The gate is green; you are here for what
the gate cannot see: idempotency, partial-failure states, rollback safety, and
divergence between what the report claims and what the diff does.

Output: fill the "Review:" line in the report with PASS or a numbered blocker
list. No merge until this line is filled. Then stop.
```

## Next step

Send to a fresh T3 session (`<model>`) with repo terminal access. Return here:
the filled Review line, verbatim. Closure cannot be dispatched before it.

---

## Audit (fresh orchestrator, when a startup trigger fires)

```
Read WORKFLOW.md, AGENTS.md, STATE.md, docs/adr/, docs/backlog.md, and
`git log --oneline -50`. This is an audit session — no dispatch.

Verify: STATE.md's "What landed" against git log; gate numbers against a fresh
gate run; escalation counts against dispatch history in reports; every NEEDS
COLD REVIEW resolved; no cross-file contradictions. File contradictions in
docs/backlog.md as BLOCKED — do not resolve them in your head.

Close: reset `Sessions since last audit` to 0 in STATE.md content you author
(committed via a closure-style worker), and print the pending NEW SLICE OPEN.
```

## Next step

Open a fresh ORCH chat, attach the current handoff ZIP, paste the prompt.
Return: nothing — its close prints the next prompt.

---

## Donor inspection (read-only; WORKFLOW.md §12)

```
Read tasks/<ID>.md §Donor. Inspect the COMPLETE local repository at
<donor path> — read-only. Do not modify either repository, create branches, or
commit anywhere.

Extract: <the generic primitive named in the brief>. Output: a note in
tasks/<ID>.donor-notes.md describing the primitive, what must be adapted to be
flashcard-native, and any dependency/allowlist/contract change reuse would
require. A required change is a governance return, not something you apply.
```

## Next step

Send to a local worker with access to `<donor path>` (not the orchestrator —
it never inspects donors itself). Return here: the donor-notes path. This does
not count as a slice attempt and does not touch the audit counter.

---

## Orchestrator — CLOSE (non-slice sessions only: governance, planning, ADR work)

Slice chats do NOT use this — their closure runs through the closure worker
(§Closure worker) and ends with NEW SLICE OPEN. This CLOSE is for sessions that
touched only docs.

```
Session close, per WORKFLOW.md §8. Do these in order, then stop.

1. Update STATE.md from the repo and <gate command> output — never from memory
   of what was discussed. Delete what is no longer true rather than appending.
   Keep it to one screen. It must contain: what landed, current gate numbers,
   blocked items and why, next three actions, the audit counter (unchanged —
   non-slice sessions do not increment it), and:
     Escalation status: <n> attempts on <task-ID>, ladder position <tier> — or "none"

2. Any decision made this session that is not yet in a file — write it now:
     convention or prohibition -> AGENTS.md
     architectural choice     -> docs/adr/  (mark: NEEDS COLD REVIEW)
     parked item              -> docs/backlog.md (BLOCKED + what unblocks it)

3. If any ADR was created or substantively modified this session, the
   next-session block below MUST target an ADR cold review (see §ADR review),
   before any dispatch. An approving cold review's own review-status record and
   the immediate administrative removal of `NEEDS COLD REVIEW` do not by
   themselves trigger another cold review. Any other substantive ADR content
   change still does. An objecting review follows AGENTS G7: revision next, then
   a fresh cold review.

4. Do not summarise the session. STATE.md is the summary.

5. Print ONLY the next session's prompt (NEW SLICE OPEN if the next action is a
   slice; otherwise the appropriate template), placeholders filled from what
   you just recorded, followed by its ## Next step.
```

---

## Escalation file (written by the orchestrator at ladder position 2→3)

`tasks/<ID>.escalation.md`:

```
- Original brief: tasks/<ID>.md
- Attempt 1 (<model/tier/effort>): <failure>, report at <path>
- Attempt 2 (<model/tier/effort>): <failure>, report at <path>
- The failures <agree | contradict> on: <point>
- Orchestrator's respecification: <split | tightened allowlist | missing ADR>
```

In this variant the ladder ceiling resolves by **respecification** (§5.3), then
re-dispatch from attempt 1 of the new brief(s). All of it inside the same
slice chat (§10) — escalation never opens a fresh orchestrator.
