# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE from repository/gate evidence.

## What landed

* **slice-0 through slice-6 are accepted, merged and closed.**
  slice-0 governance/gate; slice-1 resolver/dictionary boundary; slice-2 Gate 1;
  slice-3 Stage-01 + ADR-0004 PART-A alignment; slice-4 Gate 2 (99.00% CONTINUE);
  slice-5 Stage-02 Tatoeba index; slice-6 Stage-03/04/05 infrastructure +
  Piper build prerequisite.

* **slice-7 is ACCEPTED, MERGED AND CLOSED.**
  Standalone runtime application on `main`: complete PART-B user schema;
  FSRS review loop with append-only raw-confidence logging (fsrs==6.3.2,
  learning steps 1/10 min); DE/EN meaning sets, user meanings, D43
  availability; display-time rendering with tri-state noun plural and D46
  all-components-or-none decomposition (`app/render.py`); `DictionaryRuntime`
  atomic activation/relink with value-snapshot reads, all-or-nothing pins,
  cleanup containment, underlying-file identity, role/status consistency, and
  generation-consistent API observations (`app/deck.py`); pronunciation audio
  precedence, sacred custom media, crash-safe replacement, disposable caches,
  exact-id human discovery, Piper boundary (`app/audio.py`); FastAPI app
  factory with R12 browser guards and the full `/vocab` API including
  sanitized Anki TSV export (`app/api.py`; fastapi==0.141.1,
  uvicorn==0.52.4); executable AGENTS checks R1/R3/R6/R7/R12/R13
  (`tools/check_agents.py`). Accepted stage SHAs: S1 `a678f1b`, S2a
  `8cf6367`, S2b `bbf858e`, S3 `3e3e9d8`, S4 `35c70c9`, S5 `b5b7e93`,
  S6 `c6cdb8f`; full-diff repair lineage `d6fbcda` then `3e6898b`.

* **Mandatory WORKFLOW section 6 T3 full-diff review over main...slice/7: PASS**
  within the bounded convergence budget. Review #1 (gpt-5.6-terra): BLOCK, 5
  findings, of which 2 confirmed (API stale-path dictionary reads, critical;
  git diff --check EOF blanks) and 3 rejected with recorded evidence
  (dictionary.py byte-identity to accepted S2a; orchestrator-owned governance
  paths; ADR-0004 section 6.2 commit/API-layer language invariant). Bounded
  repair, then Review #2 (terra): BLOCK on one residual RB1 (PART-B reads
  outside reading() scope). Final mechanical repair, then Review #3 FINAL
  CONVERGENCE (terra): PASS with residual fixed-verified, rejections
  affirmed, regressions clean. Routing notes: GPT quota exhaustion confined
  implementation to gemini-3.7-flash; ox-alpha-free suffered repeated opencode
  server errors (transport, not content); owner directive made terra the last
  reviewer of each cycle.

## Gate

* Fresh gate on slice/7 @ `3e6898b`: PASS — ruff clean, mypy strict,
  667 tests, AGENTS R1/R3/R6/R7/R12/R13.
* Final main gate after closure commits: see `handoff/main-gate.txt`.

## Escalation status

* none active. Slice-7 consumed its authorized budgets exactly: the S2b
  clarified-contract lineage (two gate-fail retries, one tightened
  re-dispatch, one final convergence fix) and the full-diff review lineage
  (one bounded repair plus one final mechanical repair inside the
  three-review cap).

## Sessions since last audit

* 1 (slice-7 closure session; counter incremented exactly once at close)

## Blocked

* Compose integration blocked by lecture-app Phase-4 decomposition (slice-9)
  and the missing donor-evidence file `tasks/adr-0002-donor-notes.md`.
* ADR-0002 D27 / ADR-0003 D27 identifier collision remains naming debt only.
* Full paid Stage-04 production remains deferred by owner decision.

## Next three actions

1. Fresh Slice-8 orchestrator: S8A → S8B → S8C → S8D → S8E → mandatory final
   full-diff review → closure. Slice 8 is not started.
2. Route Slice-8 workers and reviewers through Gemini/GPT entries permitted by
   `/home/saber/.config/orchestrator-v2/routing.json`; do not use stale forward
   routes. No lecture integration yet.
3. Only after Slice-8 closure: read-only donor inspection, then the separately
   gated lecture-app composition/integration work in slice-9.
