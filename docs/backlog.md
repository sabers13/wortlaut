# Backlog

BLOCKED items say what unblocks them. Deferred items cite the ADR that parked
them. REJECTED items are listed so they do not resurface.

## Blocked

- **ADR-0005 pronunciation audio:** ADR-0005 remains `NEEDS COLD REVIEW`; cold review #1 O1–O5 have been revised and the exact next governance action is fresh cold review #2 — focused remedy verification. No slice-7/8 pronunciation feature implementation begins until the ADR is accepted/frozen.

  O1 changed the sequencing contract: slice-6 owns only the image-build/runtime Piper prerequisite — pinned engine, pinned German voice/model, license/classification/attribution/integrity verification and runtime-image availability. This is not pronunciation feature implementation. It adds no bulk audio, pronunciation DB/API/cache/custom media/human discovery/UI. Runtime pronunciation remains slice-7 and E2E pronunciation smoke remains slice-8.
- **`reference/schema.sql` remains intentionally stale only for ADR-0004
  PART-B/runtime state.** The accepted and T3-reviewed slice-3 alignment resolves
  the PART-A dictionary shape: stable lemma/sense semantic refs,
  `sense.source_ref` / `source_namespace`, `sense_meaning`,
  `sense_meaning_derivation`, `lemma.plural_none`, and removal of normative
  `sense.gloss_en`. The remaining mismatch is owned by slice-7: scalar
  `note.gloss_user`, resolver/meaning-state separation, `note_meaning_lang`,
  `note_user_meaning`, durable `note_dictionary_binding`, active dictionary
  version+SHA metadata, and runtime enforcement that numeric dictionary IDs are
  caches rather than durable semantic identity.
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
- **slice-3 T3 N1 test-fixture repair:** `tests/conftest.py:create_test_db` currently has an off-by-one lemma INSERT binding in its synthetic test DB: the 24-element tuples feed a 23-column INSERT, so `genitive_sg` receives constant `0` and intended values such as `Sees` / `Hauses` are dropped. The independent T3 reviewer verified the real Stage-01 builder persists `genitive_sg` correctly, so this is non-blocking test-fixture debt, not a Stage-01 data defect. Repair before a future test relies on that fixture field.
- **slice-3 T3 N2 fallback-identity hardening:** the A4 fallback fingerprint canonicalizer intentionally accepts scalar numbers found in included raw Wiktextract distinction structures. Current asset-local SQLite IDs provably cannot enter because fingerprinting happens on the raw upstream sense before local IDs exist, so the accepted contract is satisfied. If future real upstream shapes place volatile numeric bookkeeping inside included nested fields (`form_of`, `alt_of`, `compound_of`, etc.), explicitly exclude those upstream bookkeeping keys before relying on cross-version continuity.

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
