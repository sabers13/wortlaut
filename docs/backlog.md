# Backlog

BLOCKED items say what unblocks them. Deferred items cite the ADR that parked
them. REJECTED items are listed so they do not resurface.

## Blocked

- **slice-3 closure — PAUSED by the ADR-0004 governance amendment (2026-08-19).**
  The slice-3 implementation passed Attempt 1 and was accepted report-only under
  `Risk: none` at `7ceea14e39a7c831edfc803632d3c868ea0f3091`; that acceptance
  stands. It is **not merged and not closed**, and `slice/3` must not be merged,
  rebased, or rewritten while this item is open. Cold review through review #3 is
  complete (ADR-0004 APPROVED / FROZEN). Unblocks strictly in this order:

  ```
  ADR-0004 APPROVED / FROZEN
  -> slice-3 Stage-01 / PART-A implementation alignment
  -> fresh gate/report acceptance + required migration-risk review
  -> normal slice-3 closure
  ```

  This is an owner-driven architecture change, **not** a WORKFLOW §5
  implementation failure: no attempt is added to the ladder and the audit counter
  is unchanged. The alignment brief is `tasks/slice-3-alignment.md`.
- **`reference/schema.sql` is intentionally stale with respect to ADR-0004.** It
  still shows `sense.gloss_en NOT NULL`, scalar `note.gloss_user`, and
  `note.status` without the new resolver/meaning-state separation documented in
  ADR-0004; it has no `sense_meaning`, no `sense_meaning_derivation`, no
  `note_meaning_lang`, no `note_user_meaning`, no `lemma.plural_none` marker,
  no lemma/sense semantic refs (`lemma.semantic_ref`, `sense.semantic_ref`),
  no `sense.source_ref`, no durable `note_dictionary_binding` representation,
  no active dictionary version+SHA metadata, and numeric note `lemma_id` /
  `sense_id` still appear as if durable. The governance session that drafted
  ADR-0004 was forbidden from implementation changes, so the mismatch is
  recorded rather than repaired. It is resolved by the owning slice-3 alignment
  (PART A) and slice-7 runtime (PART B) work, not by this governance session;
  until then, read the mismatch as blocked-and-documented, not as an undetected
  contradiction.
- **ADR-0002 D27 and ADR-0003 D27 are two different decisions sharing one ID.**
  ADR-0002 D27 is the two-stage highlight capture contract; ADR-0003 D27 is the
  five-button confidence UI. Both ADRs are accepted and cold-review-approved, so
  repairing the collision means editing accepted ADR bodies and belongs to a
  session with that mandate. Found during ADR-0004 drafting and filed rather than
  resolved in someone's head. ADR-0004 starts at D32 so the collision is not
  compounded. No decision content is in doubt; only the label is ambiguous.
- **`app/` module rewrite** (`resolve, dictionary, examples, render, deck, api`)
  — the design session's delivered code was not recovered into this repo;
  `reference/smoke_test.py` imports it and cannot run. ADR-0002 is now approved.
  Unblocks through the slice sequence in `docs/plan.md` (authority: ADR-0002 §6):
  `resolve.py` + `dictionary.py` before Gate 1, stage 01 + Gate 2 next, then the
  remaining app modules and capture/import/export flows.
- **Compose integration with the lecture app** (reader capture emit +
  `docker-compose.yml` service entry, ADR-0002 D24) — BLOCKED by the lecture
  app's Phase 4 decomposition **and** ADR-0002 §1's missing donor evidence.
  Immediately before compose work, a read-only donor inspection must produce
  `tasks/adr-0002-donor-notes.md`; any contradiction returns to governance. When
  that repo decomposes Phase 4, add one line to *its* backlog pointing here; do
  not file flashcard ADRs into it before then (ADR-0002 §3).
- **Build stage 04 (multilingual offline meaning enrichment; formerly batch
  gap-gloss)** — time-bound, not blocked: the API credit expires
  **mid-September 2026**. Gate 1 → stage 01 → Gate 2 → stages 02–03 must land
  before it. Under ADR-0004 §8 its scope is broadened from
  English gap-filling to: fill missing English meanings; create/simplify German
  learner meanings; create Persian translations; deterministically validate every
  generated localized row; and selectively route flagged rows plus a small random
  sample to a stronger QA model. Broadening the scope does **not** move the
  credit deadline, and the versioned `source='llm_generated_v1'` marking,
  non-masquerade and clean-reversibility rules are unchanged (AGENTS R11).
- **`reference/smoke_test.py` is path-broken as filed** — it does
  `sys.path.insert(0, dirname(__file__))` then imports `app.*` and opens
  `schema.sql` beside itself, i.e. it expects `reference/app/` and
  `reference/schema.sql`. It cannot run from `reference/` against a repo-root
  `app/`. BLOCKED with the `app/` rewrite; fix the paths in the slice that first
  makes the baseline executable, and amend its capture/card/review assertions
  exactly as ADR-0002 §4/§5 and ADR-0003 §5 require.
  slice-0 additionally excluded `reference/` from ruff, mypy and pytest discovery
  in `pyproject.toml`, because `smoke_test.py` cannot type-check while it imports
  a non-existent `app.*` and the directory is outside slice-0's Allowlist. The
  slice that repairs the baseline **must remove that exclusion in the same
  change**, or the repaired file silently escapes the gate that is supposed to
  verify it.

## Deferred (cite: ADR-0001 §14)

- `.apkg` export via genanki (~50 lines; carries scheduling + media that TSV cannot).
- Contribution promotion job at dictionary build (normalised string overlap).
- Compound gloss trimming (`re.split(r"[;,]", g)[0]` per component; demote the
  composed gloss, promote the decomposition). Accepted ADR-0004 D46 supersedes
  this deferred behaviour with the all-components-or-none decomposition.
- `FREQ` from Tatoeba counts (falls out of stage 02 free; absent, example
  ranking degrades to length-only).
- Derived card state via `review_log` replay (also the mechanism that keeps
  ADR-0003's confidence mapping revisable).
- espeak-ng startup check (fail loudly, prefer Wiktionary IPA).
- Multilingual contribution/voting policy (cite: ADR-0004 D42). The existing
  `gloss_contribution` scope — English, one vote per user per lemma, promotion
  at dictionary build (ADR-0001 D10) — stays exactly as accepted and is
  deliberately **not** generalised to German or Persian. Whether and how
  learners contribute DE/FA meanings, and how promotion interacts with three
  provenance regimes, is an undecided design problem, not an oversight.

## Standing

- Convert `[reviewed]` AGENTS rules to `[executable]` gate checks (R2, R8, R9,
  R10 are candidates). Of the `[executable]` rules, R1 and R7 are scaffolded in
  slice-0; R3, R6, R12 and R13 are deferred to the slices that create what they
  govern (`docs/plan.md`; R13 checks land with the D47 owning runtime/smoke
  work).
- `render.back()` with `examples=[]`: tolerated but untested — reachable via
  manual entry (ADR-0001 §6). Add a test in the render slice.
- Confirm build stage 01 populates multi-word separable surface forms
  (`rief an`, `ruft an`) — inflected manual entry depends on it (ADR-0001 §15).

## Rejected (do not resurface)

- `lesson_token` table — ADR-0002 D23.
- `HostContext` host-callback protocol — ADR-0002 D22.
- Mounting the flashcard router inside the lecture app's `api/` — ADR-0002 §3.
- Generic/non-German note types, cloze, configurable templates — ADR-0001 D18.
- Runtime LLM in any form — ADR-0001 D1.
- Implementing Brainscape's proprietary scheduler / replacing FSRS — ADR-0003 §3.
- Parallel `gloss_en` / `gloss_de` / `gloss_fa` columns on `sense` — ADR-0004
  §12; every new meaning language would be a migration over a shipped asset,
  and per-language `source`/`license` has nowhere to live.
- Runtime translation or runtime LLM calls of any kind, cached or not — ADR-0004
  §12, restating ADR-0001 D1 / §9 and AGENTS R1 for three languages.
- LLM-generating the whole dictionary instead of source-first enrichment —
  ADR-0004 §12; discards Wiktionary structured grammar and the attribution chain.
- Separate vocabulary notes per inflected surface form — ADR-0004 §12;
  fragments one FSRS state across a paradigm and duplicates what the resolver
  already does.
