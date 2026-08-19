# Backlog

BLOCKED items say what unblocks them. Deferred items cite the ADR that parked
them. REJECTED items are listed so they do not resurface.

## Blocked

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
- **Build stage 04 (batch gap-gloss)** — time-bound, not blocked: the API
  credit expires **mid-September 2026**. Gate 1 → stage 01 → Gate 2 →
  stages 02–03 must land before it.
- **`reference/smoke_test.py` is path-broken as filed** — it does
  `sys.path.insert(0, dirname(__file__))` then imports `app.*` and opens
  `schema.sql` beside itself, i.e. it expects `reference/app/` and
  `reference/schema.sql`. It cannot run from `reference/` against a repo-root
  `app/`. BLOCKED with the `app/` rewrite; fix the paths in the slice that first
  makes the baseline executable, and amend its capture/card/review assertions
  exactly as ADR-0002 §4/§5 and ADR-0003 §5 require.

## Deferred (cite: ADR-0001 §14)

- `.apkg` export via genanki (~50 lines; carries scheduling + media that TSV cannot).
- Contribution promotion job at dictionary build (normalised string overlap).
- Compound gloss trimming (`re.split(r"[;,]", g)[0]` per component; demote the
  composed gloss, promote the decomposition).
- `FREQ` from Tatoeba counts (falls out of stage 02 free; absent, example
  ranking degrades to length-only).
- Derived card state via `review_log` replay (also the mechanism that keeps
  ADR-0003's confidence mapping revisable).
- espeak-ng startup check (fail loudly, prefer Wiktionary IPA).

## Standing

- Convert `[reviewed]` AGENTS rules to `[executable]` gate checks (R2, R8, R9,
  R10 are candidates). Of the `[executable]` rules, R1 and R7 are scaffolded in
  slice-0; R3, R6 and R12 are deferred to the slices that create what they
  govern (`docs/plan.md`).
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
