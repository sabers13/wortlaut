# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0, slice-1, slice-2 accepted and merged 2026-08-19** (ADR-0002 §6
  orders 1–3), each on Attempt 1 under `Risk: none`. They established the
  repository skeleton and the authoritative `make gate` (ruff, `mypy --strict`,
  pytest, executable AGENTS checks); the pure resolver ladder + compound splitter
  in `app/resolve.py`, the read-only PART A reader in `app/dictionary.py`, the
  canonical resolver SHA-256 helper and executable R3; and ADR-0001 §13 Gate 1,
  where the real `de_core_news_md` 3.8.0 probe under spaCy 3.8.15 observed
  `dep=svp` and confirmed the existing `SVP_DEP = "svp"` needed no resolver edit.
  slice-2 closure left `main` at `063a733f0e07d857e820870ac8a4b79989cf3c32`; this
  session's documentation commits sit directly on top of it and are pushed. The
  live `main` HEAD is deliberately not restated here — read it from the repository.
* **slice-3 implementation ACCEPTED but NOT merged and NOT closed.** Branch
  `slice/3` at `7ceea14e39a7c831edfc803632d3c868ea0f3091`, pushed to
  `origin/slice/3`, accepted on **Attempt 1**, report-only, `Risk: none` (so
  WORKFLOW §6 required no full-diff review). It implements ADR-0002 §6 order 4 /
  build stage 01: the deterministic offline Wiktextract JSONL → SQLite
  `lemma`/`sense`/`surface_form` transform, with `rief an` / `ruft an` multi-word
  separable surface forms proven, `source='wiktionary'` / `license='CC BY-SA'` on
  every row, and fail-closed no-overwrite output. Its own worker gate recorded
  ruff clean, `mypy --strict .` over 12 source files, `pytest -q` 91 passed
  (80 existing + 11 new), and R1/R3/R7 passing. **That acceptance stands.**
* **ADR-0004 cold-reviewed 2026-08-19 — OBJECTIONS filed (O1, O2, O3); `NEEDS COLD REVIEW` stays.**
  `docs/adr/0004-multilingual-learner-meanings.md` (D32–D42) makes DE/EN/FA
  learner meanings a per-note, non-empty display selection over German
  vocabulary: language-neutral senses plus a normalized localized-meaning
  relation instead of `sense.gloss_en`; German learner meanings (synonym-first,
  ≈A2–B1); English source-first; Persian generated offline against a
  disambiguated sense with RTL presentation; stage 04 broadened to five offline
  jobs under two LLM **roles**; tri-state noun plural on the card back; inflected
  forms resolving to the canonical lemma. The target language stays German and
  ADR-0001 D18 is not reopened. **AGENTS R1 is unchanged: zero LLM at runtime.**
  Cross-file amendment records were added to ADR-0001, ADR-0002, `AGENTS.md`
  (C3, R11), `docs/plan.md` and `docs/backlog.md`, each marked pending because
  ADR-0004 is unaccepted. Cold review identified three blocking contract gaps:
  O1 (needs_gloss overloaded between resolution and meaning availability),
  O2 (missing user-authored meaning schema/API/validation), and O3 (missing
  derivation carrier for generated-row CC BY-SA provenance).
* **ADR-0004 revision resolving O1–O3 landed in the working tree 2026-08-19**
  (governance revision, supervised local worker under WORKFLOW §14). ADR-0004
  remains **`NEEDS COLD REVIEW`** and is extended to D32–D45: **D43** keeps
  `note.status` as the persisted resolver outcome (`resolved | derived_compound |
  needs_gloss`) and adds the computed, non-persisted `meaning_state = none |
  partial | complete` (learner-facing "needs meaning" = `meaning_state='none'`);
  **D44** normalizes DE/EN/FA user meanings as `note_user_meaning` with a
  language-keyed `user_meanings` override and a language-bearing `/vocab/gloss`
  POST/DELETE API, superseding scalar `note.gloss_user` (D10 stays English-only);
  **D45** adds `sense_meaning_derivation` for generated-row provenance, license
  traversal, and rollback. `AGENTS.md` R11 and the ADR-0001/ADR-0002 pending
  supersession records, `docs/plan.md`, and `docs/backlog.md` were amended
  accordingly. `reference/schema.sql` remains intentionally stale. This is a
  governance revision, **not** a WORKFLOW §5 attempt: no attempt is added and
  the audit counter is unchanged.
* **ADR-0004 fresh post-O1–O3 cold review 2026-08-19 — OBJECTIONS O4–O5 filed; `NEEDS COLD REVIEW` stays.**
  O1–O3 were verified resolved. O4 finds D43 incomplete for
  `status='derived_compound'`: its selected-language availability predicate only
  recognizes note-local user meaning or a direct `sense_id`/`sense_meaning`,
  while the retained compound decomposition/gloss path can provide derived
  meaning without a direct sense. O5 finds dictionary replacement unsafe and
  undefined: D43 requires automatic recomputation against a replacement asset,
  but no cross-version stable numeric sense identity or mandatory fail-closed
  relink contract exists. No implementation dispatch is allowed. The next
  governance action is an ADR-0004 revision resolving O4–O5, followed by a fresh
  cold review.
* **Supervised Worker Fallback governance workflow adopted 2026-08-19**
  (`WORKFLOW.md` §0/§1/§14, `AGENTS.md` G3/G8/G11, `PROMPTS.md`). Distinguishes
  project decision authority (retained by primary ChatGPT orchestrator),
  execution authority (supervised local worker in authoritative local checkout),
  evidence authority (authoritative checkout for local execution/gate facts,
  private GitHub mirror for persistent committed state), and transport relay
  (owner ferrying prompts/evidence). Enables the primary ChatGPT chat to orchestrate
  governance and slice workflows cold without direct local terminal access by
  dispatching machine-verifiable briefs to a local worker.
* **`reference/schema.sql`, `app/`, `tools/` and the `slice/3` branch are
  deliberately unchanged** by governance sessions and are implementation-stale
  against ADR-0004. The staleness is recorded in `docs/backlog.md`, not silently
  carried.
* **Two Authorities / GitHub-first transport is active.** Local Git/terminal is
  authoritative for machine state, working tree, installed runtime dependencies
  and fresh gates; private `origin` (`sabers13/flashcard`) is the persistent
  mirror for committed/pushed context. Push synchronization is fail-closed.
* **ADR-0001/0002/0003 remain accepted.** ADR-0004 is the only active
  `NEEDS COLD REVIEW` marker.

## Gate

* `make gate` — **PASS**. Measured fresh on `main` by the ADR-0004 post-O1–O3
  cold-review close on 2026-08-19:
  `.venv/bin/ruff check .` — all checks passed;
  `.venv/bin/mypy --strict .` — success, no issues in **10 source files**;
  `.venv/bin/pytest -q` — **80 passed**;
  `.venv/bin/python tools/check_agents.py` — R1 (runtime LLM), R3 (resolver cache
  key), R7 (lecture coupling) pass. R6 and R12 remain deliberately unscaffolded
  until their owning later slices.
* These are `main` numbers and are **lower than the slice-3 worker's** (12 source
  files, 91 passed) **by design**: slice-3 is accepted but unmerged, so its
  `tools/build_dict.py` and 11 stage-01 tests are not on `main`. The divergence is
  expected evidence of the paused closure, not a regression.
* This governance session wrote no `handoff/` artifact. `handoff/main-gate.txt`
  still records the slice-2 closure gate; the next authoritative post-closure
  evidence is produced by slice-3's closure worker, which cannot run yet.

## Escalation status

* none. slice-3 was accepted on **Attempt 1** at its brief-selected
  `gpt-5.6-terra / T3 / high` route; the ladder is at position 0 for every task.
  The ADR-0004 governance amendment is an **owner-driven architecture decision
  taken after acceptance**, not an implementation failure: it adds no attempt,
  triggers no escalation, and increments no counter.

## Sessions since last audit

* 3    <!-- unchanged: non-slice governance sessions do not increment it. Audit at >= 10 or a phase boundary. -->

## Blocked

* **slice-3 closure — PAUSED by ADR-0004.** `slice/3` must not be merged,
  rebased, or rewritten. Unblocks only in order: ADR-0004 draft → O1–O3 cold
  review → O1–O3 revision → post-revision cold review O4–O5 → ADR-0004 revision
  resolving O4–O5 → fresh cold review approval → slice-3 implementation
  alignment → fresh gate/report acceptance (`docs/backlog.md`).
* **`reference/schema.sql` is intentionally stale** against ADR-0004 §6/§10 —
  `sense.gloss_en NOT NULL`, no localized-meaning relation, no per-note
  meaning-language table, no explicit "no normal plural" marker. Repaired by the
  slice-3 alignment work, not by a governance session.
* **ADR-0002 D27 / ADR-0003 D27 share one decision ID** — filed in
  `docs/backlog.md`; both ADRs are accepted, so the repair needs a session with a
  mandate to edit accepted ADR bodies.
* **`reference/smoke_test.py`** — path-broken and excluded from discovery;
  `docs/plan.md` assigns the repair to slice-8, which must remove the
  `pyproject.toml` exclusion in the same change.
* **Compose integration** — independently BLOCKED by the lecture app's Phase 4
  decomposition and missing donor evidence; slice-9 performs the read-only donor
  verification immediately before compose work.
* **Build stage 04** — time-bound: API credit expires **mid-September 2026**;
  now covers multilingual enrichment under ADR-0004 §8. `docs/plan.md` governs
  the sequence.

## Next three actions

1. **Fresh ADR-0004 revision session** (AGENTS G7) — resolve blocking objections
   O4–O5 in the ADR and every cross-file amendment required by their remedies.
   Preserve O1–O5 and all existing resolution records. Do not dispatch
   implementation. Close to another fresh ADR-0004 cold review.
2. **Fresh ADR-0004 cold review** (WORKFLOW §7 / AGENTS G7) — review the
   O4–O5 revision from repository-only context. No implementation dispatch until
   it approves and removes `NEEDS COLD REVIEW`.
3. **Only after approval, return to the existing slice-3 orchestrator** for the
   implementation-alignment brief against the accepted ADR-0004 contract.
   `slice/3` remains fixed at
   `7ceea14e39a7c831edfc803632d3c868ea0f3091` until that alignment work begins.
