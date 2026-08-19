# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0 accepted and merged 2026-08-19** (ADR-0002 §6 order 1). Branch
  `slice/0` at `584e05f3762e1dd16de9e99a1d048b42e7da31b5`, accepted on Attempt 1;
  `Risk: none`. It established the repository skeleton and the authoritative
  `make gate` covering ruff, `mypy --strict`, pytest, and executable AGENTS
  checks.
* **slice-1 accepted and merged 2026-08-19** (ADR-0002 §6 order 2). Branch
  `slice/1` at `8d0507b349110b002e381ecd93729a012c5946f5`, accepted on Attempt 1;
  `Risk: none`, so WORKFLOW §6 required no full-diff review. It landed the pure
  resolver ladder and compound splitter in `app/resolve.py`, the read-only PART A
  SQLite dictionary reader in `app/dictionary.py`, the canonical resolver
  SHA-256 helper, and executable AGENTS R3 enforcement.
* **Gate-1 runtime provisioning governance repair landed 2026-08-19.**
  `pyproject.toml` now records `spacy>=3.8.0,<3.9.0` and the exact
  `de_core_news_md` 3.8.0 wheel dependency. The local project environment was
  provisioned with spaCy 3.8.15 / model 3.8.0 and verified before slice-2
  Attempt 1. This was pre-dispatch governance repair: no slice attempt and no
  audit-counter increment.
* **slice-2 accepted and merged 2026-08-19** (ADR-0002 §6 order 3 / ADR-0001
  §13 Gate 1). Branch `slice/2` at
  `5ef6fb2b622a359d8564a4c4f7f7544e563d44c4`, accepted on Attempt 1;
  `Risk: none`, so WORKFLOW §6 required no full-diff review. The real
  `de_core_news_md` 3.8.0 probe under spaCy 3.8.15 observed `dep=svp` for `an`
  headed by `rufe` and `kommt`; the existing module-level `SVP_DEP = "svp"` was
  already correct and required no resolver edit. `tests/test_resolve_spacy.py`
  now locks exactly the five ADR-0001 §13 real-model cases through the existing
  slice-1 resolver seam. Worker CLOSE evidence: ruff clean;
  `mypy --strict .` clean over 10 source files; pytest 80 passed; executable
  AGENTS R1, R3 and R7 passed.
* **`tasks/slice-3.md` authored** — ADR-0002 §6 order 4 / build stage 01.
  It specifies the deterministic offline Wiktextract JSONL → SQLite
  `lemma`/`sense`/`surface_form` build consumed by Gate 2, including
  attribution, deterministic merge/IDs, multi-word separable surface forms,
  fail-closed output behavior, and synthetic executable fixtures.
  `Depends: slice-2`; `Risk: none`; route
  `gpt-5.6-terra / T3 / high`, fallback `opus-5 / T3 / high`.
* **Two Authorities / GitHub-first transport is active.** Local Git/terminal is
  authoritative for machine state, working-tree state, installed runtime
  dependencies and fresh gates. Private `origin` (`sabers13/flashcard`) is the
  persistent authoritative mirror for committed/pushed project context.
  Routine handoff ZIP, report and diff uploads are no longer required when the
  relevant pushed GitHub state is accessible; the validated ZIP remains the
  immutable offline fallback. Push synchronization is fail-closed.
* **ADR-0001/0002/0003 remain accepted and unmodified.** No active
  `NEEDS COLD REVIEW` marker exists.

## Gate

* `make gate` — PASS on accepted slice-2 work: ruff all checks passed;
  `mypy --strict .` success over 10 source files; `pytest -q` 80 passed;
  `tools/check_agents.py` passes R1 (runtime LLM), R3 (resolver cache key), and
  R7 (lecture coupling). R6 and R12 remain deliberately unscaffolded until
  their owning later slices. The closure worker refreshes the authoritative
  post-closure stdout+stderr evidence at `handoff/main-gate.txt` after this
  STATE commit; handoff exists only if that final main gate passes.

## Escalation status

* none — slice-2 accepted on Attempt 1 at its brief-selected T1/low route.
  The missing-spaCy startup STOP, dependency provisioning repair, failed first
  provisioning procedure, successful governance-repair retry, formal startup
  verification, and slice-3 brief materialization were governance/mechanical
  operations, not §5 implementation attempts.

## Sessions since last audit

* 3    <!-- incremented exactly once by slice-2 closure. Audit at >= 10 or a phase boundary. -->

## Blocked

* **`reference/smoke_test.py`** — the filed smoke baseline remains path-broken
  and excluded from normal discovery. `docs/plan.md` assigns its repair to
  slice-8; that repair must remove the exclusion in the same change.
* **Compose integration** — independently BLOCKED by the lecture app's Phase 4
  decomposition and missing donor evidence; slice-9 performs the read-only donor
  verification immediately before compose work.
* **Build stage 04 (batch gloss)** — time-bound: API credit expires
  **mid-September 2026**; `docs/plan.md` governs the sequence.

## Next three actions

1. **slice-3 startup:** open a fresh orchestrator via PROMPTS.md §NEW SLICE OPEN,
   GitHub-first against private `sabers13/flashcard`; formally verify the
   closure `main` HEAD, clean local tree, remote synchronization, fresh
   `make gate`, STATE/disk consistency, both audit triggers, and the actual
   `Depends: slice-2` ancestry. Verify the accepted slice-2 report is present
   and records the Gate-1 `svp` evidence required by the slice-3 precondition.
2. **slice-3 build stage 01 implementation:** dispatch `tasks/slice-3.md` on
   `gpt-5.6-terra / T3 / high` (fallback `opus-5 / T3 / high`). Implement only
   the deterministic maintainer-side Wiktextract JSONL → SQLite
   `lemma`/`sense`/`surface_form` stage and its synthetic executable fixtures;
   no real dump, network, runtime API, stage-02, or user-state work.
3. **Before slice-3 closure, author `tasks/slice-4.md`** for ADR-0002 §6 order 5
   / ADR-0001 Gate 2. Preserve the normative coverage thresholds verbatim:
   `<85%` returns to governance; `85–<95%` receives the already-specified
   splitter/fuzzy remedy once and reruns; `>=95%` continues. Set its exhaustive
   allowlist, risk lookup, and Model/Why/Fallback from WORKFLOW at brief-writing
   time.
