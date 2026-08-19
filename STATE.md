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

* `make gate` — **PASS**. Measured fresh on `main` by this cold-review session
  on 2026-08-19:
  `.venv/bin/ruff check .` — all checks passed;
  `.venv/bin/mypy --strict .` — success, no issues in **10 source files**;
  `.venv/bin/pytest -q` — **80 passed** in 6.07s;
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
  rebased, or rewritten. Unblocks only in order: ADR-0004 draft → ADR-0004
  revision (resolving O1–O3) → fresh cold review approval → slice-3
  implementation alignment → fresh gate/report acceptance (`docs/backlog.md`).
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

1. **Start a fresh ADR-0004 revision session to resolve the persisted cold-review objections**
   (AGENTS G7 / PROMPTS.md §Orchestrator CLOSE step 3): a fresh orchestrator
   session to resolve the three blocking cold-review objections (O1 needs_gloss
   redefinition and resolution/meaning-availability state decoupling; O2
   localized user-authored meanings schema, API, validation and contribution
   boundary; O3 generated-row provenance and source derivation carrier under
   AGENTS R11). The revision targets a fresh cold review on close.
2. **Fresh ADR-0004 cold review** (WORKFLOW §7 / AGENTS G7): a fresh orchestrator
   session reading only the repository to verify the revised ADR-0004.
3. **On cold-review approval, return to the existing slice-3 orchestrator** for a
   slice-3 **implementation-alignment brief** against the approved ADR-0004 data
   contract. That brief is authored there, not by a governance or cold-review
   session, and only after approval.
