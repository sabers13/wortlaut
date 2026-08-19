# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from `git log` and gate output — never from
memory of a conversation.

## What landed
- <commit-level summary, newest first>

## Gate
- <gate numbers as of last close — the command and its output, verbatim>

## Escalation status
- none    <!-- or: 2 attempts on <task-ID>, ladder position T2 — next failure escalates -->

## Blocked
- <item> — BLOCKED by <what>, unblocked when <condition>

## Next three actions
1. <concrete, dispatchable — this is what the next OPEN prompt targets>
2. <…>
3. <…>
