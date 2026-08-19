# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0 through slice-3 are accepted, merged and closed.** slice-0 established
  the repository/gate skeleton; slice-1 landed the canonical resolver/read-only
  dictionary boundary and R3 scaffold; slice-2 locked the accepted Gate-1 spaCy
  separable-verb result; slice-3 landed deterministic Stage-01 Wiktextract →
  SQLite dictionary construction.
* **slice-3's original Attempt-1 acceptance remains preserved.** Its original
  implementation was accepted at
  `7ceea14e39a7c831edfc803632d3c868ea0f3091`. The later owner-driven ADR-0004
  amendment was not a WORKFLOW §5 implementation failure and did not increment
  the attempt ladder.
* **slice-3 ADR-0004 PART-A alignment is landed and independently reviewed.**
  The alignment implementation is
  `7423cb5147d1419dba4480826accf67243258a2d`; the mandatory migration-risk T3
  full-diff review passed at accepted slice head
  `89c9b89b93addd4211a931d5415e5c8d613a6f45`.
* **Stage-01 now carries the accepted ADR-0004 PART-A identity/meaning contract.**
  `lemma.semantic_ref`, `sense.semantic_ref`, `sense.source_namespace`,
  `sense.source_ref`, normalized `sense_meaning`,
  `sense_meaning_derivation`, tri-state noun plural, and deterministic D46
  component semantic bindings are implemented. Numeric dictionary IDs remain
  current-asset caches only; `sense.gloss_en` is no longer the normative meaning
  carrier.
* **ADR-0004 is ACCEPTED / FROZEN.** Cold review #3 was the FINAL CONVERGENCE
  REVIEW; there is no review #4. D36/D45/D46/D47 and their cross-file amendments
  remain accepted.
* **Implementation ownership after slice-3 is unchanged.** slice-4 is ADR-0002
  §6 order 5 / Gate 2. slice-5 owns Stage 02 / Tatoeba indexing. slice-6 owns
  stages 03–05 including offline multilingual enrichment. slice-7 owns PART-B,
  runtime meanings/render/API, durable dictionary bindings, D47 activation/relink
  and R12/R13 runtime enforcement. slice-8 owns smoke/replacement verification.
  slice-9 owns later lecture-app compose integration after its independent host
  prerequisites are satisfied.
* **ADR-0001, ADR-0002, ADR-0003 and ADR-0004 remain accepted.** The existing
  ADR-0002 D27 / ADR-0003 D27 identifier collision remains parked as naming debt;
  no decision content is ambiguous.
* **Two-authority workflow remains binding.** Local Git/terminal is authoritative
  for working-tree/runtime/gate facts; private `origin` is the persistent
  authoritative mirror for committed/pushed state.

## Gate

* **Accepted slice-3 aligned/reviewed gate — PASS on 2026-08-20:**
  `.venv/bin/ruff check .` — all checks passed;
  `.venv/bin/mypy --strict .` — success, no issues in **12 source files**;
  `.venv/bin/pytest -q` — **106 passed**;
  `.venv/bin/python tools/check_agents.py` — R1 (runtime LLM), R3 (resolver cache
  key), R7 (lecture coupling) passed.
* Alignment-targeted verification also passed:
  `tests/test_build_dict_stage01.py` — **23 passed**;
  `tests/test_dictionary.py` — **14 passed**;
  `tests/test_resolve.py` — **22 passed**;
  `tests/test_resolve_spacy.py` — **5 passed**.
* The closure worker runs the final authoritative post-merge/post-STATE
  `make gate`; its stdout+stderr is stored in `handoff/main-gate.txt` and is the
  closure handoff evidence consumed by the next fresh orchestrator.

## Escalation status

* none. slice-3 remained accepted on Attempt 1. The ADR-0004 alignment was an
  owner-driven contract amendment rather than a WORKFLOW §5 failure; its
  `Risk: migration` full-diff review passed.

## Sessions since last audit

* 4    <!-- slice-3 normal closure increments the prior value 3 exactly once. Audit at >= 10 or when a phase-boundary trigger is established at fresh startup. -->

## Blocked

* **ADR-0004 PART-B/runtime schema remains intentionally deferred to slice-7.**
  PART-A is now landed. Remaining work includes `note_meaning_lang`,
  `note_user_meaning`, durable `note_dictionary_binding`, active dictionary
  version+SHA state, resolver/meaning-state separation and D47 runtime
  activation/relink semantics.
* **ADR-0002 D27 / ADR-0003 D27 share one identifier.** Both accepted decisions
  remain valid; repair is separately parked.
* **`reference/smoke_test.py` remains path-broken/excluded.** slice-8 owns the
  repair plus D47 replacement/stale-picker smoke verification.
* **Compose integration remains independently blocked** by the lecture app's
  Phase-4 decomposition and required donor evidence; slice-9 owns that later
  boundary.
* **Build stage 04 remains time-bound to mid-September 2026.** Its multilingual
  enrichment scope is unchanged; Gate 2 and stages 02–03 must precede it.
* **Non-blocking slice-3 review debt remains in `docs/backlog.md`.** T3 N1 is a
  synthetic test-fixture `genitive_sg` bind defect; T3 N2 is future fallback
  fingerprint hardening for potentially volatile upstream numeric bookkeeping.
  Neither blocks Gate 2.

## Next three actions

1. **Open slice-4 with formal startup verification.** Verify the closure
   manifest/final `main` HEAD, clean local tree, origin sanity, fresh `make gate`,
   STATE consistency, both audit triggers, and the brief's exact
   `Depends: slice-3` merged condition.
2. **Supply Gate-2's four local non-repository inputs before dispatch:**
   a real English-edition Wiktextract JSONL, a real German-edition Wiktextract
   JSONL, one UTF-8 file containing 200–300 unique nonblank vocabulary headwords
   from one real German-textbook unit, and a non-empty human-readable unit label.
   These inputs and generated dictionary/misses artifacts stay local and
   uncommitted.
3. **Execute slice-4 / Gate 2 baseline measurement.** The baseline worker is
   `gemini-flash / T1 / low` (fallback `codex-low / T1 / low`) and may modify only
   its briefed measurement tool/test/report. ADR-0002 §6 governs mechanically:
   `<85%` → governance redesign and no Stage 02; `85–<95%` → exactly one explicit
   orchestrator-authored remedy cycle then one rerun; `>=95%` → continue. Gate 2
   is a design gate, not the WORKFLOW §5 retry ladder.
