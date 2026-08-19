# Workflow — Base Set (no Fable)

Four files, all of which go into the project root:

| File | Role |
| --- | --- |
| `README.md` | This file — install + bootstrap. Delete after day 1 if you want. |
| `WORKFLOW.md` | The rules: roles, routing rubric, escalation ladder, risk labels, ADR two-pass review |
| `PROMPTS.md` | Every OPEN/CLOSE prompt, paste verbatim |
| `STATE.template.md` | Copy to `STATE.md` — the single entry point for every session |

This set is for projects with no Fable budget, or small enough that the ADR
cold-review rule is enough ceiling. The escalation ladder tops out at T3 and
resolves by orchestrator respecification (WORKFLOW.md §5.3).

---

## Install

1. Copy `WORKFLOW.md` and `PROMPTS.md` into the project root, names unchanged.
2. Copy `STATE.template.md` to `STATE.md` in the project root.
3. Fill `WORKFLOW.md` §0: gate command, paths, and the model table (edit the
   model table again whenever your subscriptions/tokens change).
4. If the project has no `AGENTS.md` yet, create one containing only:

   ```
   # AGENTS — conventions and prohibitions. Every rule states the defect that caused it.
   ```

---

## Day 1 — bootstrap

The chain rule has a cold-start problem: session zero has no previous CLOSE to
print its OPEN. This is the **only** prompt you ever compose by hand. Open your
orchestrator (Opus 5 or GPT 5.6 sol — whichever has tokens) with:

```
Read WORKFLOW.md, AGENTS.md and STATE.md (currently the template).

This is session zero. Task: interview me about this project until you can write
(1) STATE.md's first real "Next three actions", (2) the initial plan outline, and
(3) the first brief per WORKFLOW.md §2 with Model/Why/Fallback. Then close per
PROMPTS.md §Orchestrator CLOSE.
```

From here on, you never compose a prompt again. Every CLOSE prints the next OPEN
with placeholders filled. If you find yourself writing one by hand, a CLOSE step
was skipped — go back and run it.

---

## Your three permanent jobs

1. **Courier:** paste printed prompts between surfaces, unedited.
2. **Ladder integrity:** if a slice took three dispatches but STATE.md shows zero
   attempts, the orchestrator is absorbing failures — call it out.
3. **Contradiction sensor:** when two files disagree (an ADR vs a report), file
   it in `docs/backlog.md` as BLOCKED. Do not resolve it in your head.
