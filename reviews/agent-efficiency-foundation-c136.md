# Independent Risk Review — Agent Efficiency Foundation

## Candidate

- Branch: `infra/agent-efficiency-foundation-r1`
- SHA: `c136a2ea59ba10ae523c81788edcbdab25913ef3`
- Parent: `115530aedd118a138d3b09bab0fc2ab7b88bf1b5`
- Net diff vs `main` (`17a899e`): 9 files, +3528/-8
  - `A MODULES.toml`
  - `M Makefile`
  - `M PROMPTS.md`
  - `M WORKFLOW.md`
  - `A docs/agent-efficiency-audit.md`
  - `A tests/test_affected_tests.py`
  - `A tests/test_check_modules.py`
  - `A tools/affected_tests.py`
  - `A tools/check_modules.py`
- Commits on top of base main (7):
  - `3553d9c` docs: audit agent and repository efficiency
  - `1638443` docs: converge agent-efficiency audit recommendations (audit HEAD)
  - `f98904e` infra: add dependency-scoped agent validation
  - `ce737db` fix: keep affected tests direct-owner scoped (REJECTED, on recovery branch only)
  - `8fcddd7` Revert "fix: keep affected tests direct-owner scoped"
  - `115530a` fix(infra): make affected validation precise and fail-closed (Repair 1)
  - `c136a2e` fix(infra): preserve test-only validation scope (Repair 2)

The contaminated historical branch `infra/agent-efficiency-foundation` (`ac4f113`) is **not** the review target and is not present in the candidate tree.

## Verdict

**PASS WITH NON-BLOCKING NOTES**

The candidate is infrastructure/governance only, fully validated, and correctly preserves the §16.4 exact-final-candidate full-validation invariant. The new module map, dependency graph validator, focused-test resolver, and governance amendments are coherent and fail-closed. Two minor accuracy notes are recorded below and one documentation/inconsistency note in the audit document — none blocks merge.

## Scope Reviewed

- Full diff `git diff 17a899ef0cc6ccc3f5fca3e55c9b6c7e811979e5..c136a2ea59ba10ae523c81788edcbdab25913ef3`
- 7 commits in candidate lineage
- `MODULES.toml` (213 lines)
- `Makefile` (gate target composition)
- `WORKFLOW.md` (`Required reading:` amendment, §2 brief schema)
- `PROMPTS.md` (Worker OPEN, Risk-label review, Supervised worker template — Required-reading integration)
- `tools/check_modules.py` (584 lines)
- `tools/affected_tests.py` (405 lines)
- `tests/test_check_modules.py` (596 lines, 17 tests)
- `tests/test_affected_tests.py` (606 lines, 23 tests)
- `docs/agent-efficiency-audit.md` (1092 lines, decision rationale)

Application source (`app/`, `frontend/`, `reference/`) was read for targeted import inspection only; not full-diff reviewed (out of scope by Question K).

## Validation Evidence Assessment

**ACCEPTED AS EXACT-CANDIDATE EVIDENCE.**

The provided full-gate certification matches the candidate HEAD exactly, is internally consistent (e.g. 731 pytest = 691 baseline + 17 + 23 new tests; mypy 39 source files = 35 baseline + 4 new Python files), and is reproducible against the worktree at `c136a2e`. Independent re-run of the two new test modules locally passed (40/40). Validator (`tools/check_modules.py`) re-run independently against the candidate tree passes with `MODULES validation passed: 16 modules`. `tools/check_agents.py` re-run independently passes (`R1, R3, R6, R7, R12, R13 PASS`).

Per `WORKFLOW.md §16.4`, the gate numbers are accepted as exact-final-candidate evidence; full `make gate` was not re-run as part of this review (review-only, no rerun permitted per brief).

## Module Map Review

`tools/check_modules.py MODULES.toml` is the single authoritative validator. Independently confirmed:

- 16 module rows; every row has matching `id` field; every row's owned_paths, dependencies, focused_tests, agents_rules are lists of strings.
- Inventory is Git-aware (`git ls-files --cached --others --exclude-standard`) over `app/`, `tools/`, `reference/`, `frontend/src/` + `Dockerfile`. 26 tracked/nonignored-untracked paths under those roots are claimed by **exactly one** module each (independently recomputed).
- `module_metadata` self-ownership of `MODULES.toml`, `tools/check_modules.py`, `tools/affected_tests.py` is enforced by `_check_module_metadata_self` and confirmed by `test_valid_real_modules_toml` ("16 modules PASS").
- `tests/` is not in inventory roots. Test files reference modules via `focused_tests` strings only; ownership of test files is not enforced by the validator. This is a deliberate design: focused_tests are not source-of-truth assets and are excluded from ownership invariants.

**One maintenance-hazard note (LOW, non-blocking):** the `module_metadata` module's `owned_paths` glob does not include the two new test files (`tests/test_check_modules.py`, `tests/test_affected_tests.py`). Adding new test files for existing modules requires no change to MODULES.toml. Adding new tooling scripts requires only updating `module_metadata`'s `owned_paths`. Adding a new source file in any other directory not in `INVENTORY_ROOTS` (e.g. `app/`, `tools/`, `reference/`, `frontend/src/`, `Dockerfile`) would currently be invisible to the validator — the inventory roots must grow alongside new module homes. This is correct but future maintainers should be aware.

## Dependency Graph Review

The audit brief claims the following edges. Each was verified against actual Python `from … import` statements in the relevant module.

| Claim | Status | Evidence |
|---|---|---|
| `runtime_api → audio` | PASS | `app/api.py:from app.audio import …` |
| `runtime_api → deck` | PASS | `app/api.py:from app.deck import …` |
| `runtime_api → dictionary` | PASS | `app/api.py:from app.dictionary import …` |
| `runtime_api → examples` | PASS | `app/api.py:from app.examples import …` |
| `runtime_api → export` | PASS | `app/api.py:from app.export import …` |
| `runtime_api → render` | PASS | `app/api.py:from app.render import …` |
| `runtime_api → resolve` | PASS | `app/api.py:from app.resolve import …` |
| `deck → dictionary` | PASS | `app/deck.py:from app.dictionary import …` |
| `deck → reference` | PARTIAL | `app/deck.py` does NOT import from `reference/`; the dependency is the runtime SQL schema in `reference/schema.sql`. Edge exists in MODULES.toml by design (deck operates against the schema) and is conservative over-selection rather than under-selection. NOT BLOCKING. |
| `dictionary → resolve` | PASS | `app/dictionary.py:from app.resolve import …` |
| `render → dictionary` | PASS | `app/render.py:from app.dictionary import …` (types only, per docstring) |
| `export → render` | PASS | `app/export.py:from app.render import …` |
| `build_dict → resolve` | PASS | `tools/build_dict.py:from app.resolve import …` |
| `build_dict → check_agents` | **FALSE EDGE** (NOTE) | `tools/build_dict.py` does not import or call `tools/check_agents`. The edge causes over-selection: when `tools/check_agents.py` changes, `build_dict`'s stage tests run unnecessarily. NOT under-selection; NOT BLOCKING by the brief's stated criterion. Recommend future maintainer prune this edge in a follow-up. |
| `gate2 → dictionary` | PASS | `tools/gate2_coverage.py:from app.dictionary import …` |
| `gate2 → resolve` | PASS | `tools/gate2_coverage.py:from app.resolve import …` |
| `check_agents → reference` | PASS | `tools/check_agents.py` reads `reference/schema.sql` directly at runtime to enforce R6 |
| `frontend_shell → frontend_api` | PASS | `frontend/src/app.ts` imports `./api/client.ts`, `./api/errors.ts`, `./api/types.ts`, all owned by `frontend_api` |

Computed reverse closure over the actual graph confirms test_mixed_source_and_python_test_keeps_resolve_only and test_mixed_source_and_frontend_test behave as designed.

**False-positive edge impact:** when `tools/check_agents.py` changes, the resolver emits `build_dict` as affected and runs its 5 stage tests. This is over-selection (false positive, more tests than necessary), not under-selection (no tests are missed). Over-selection only costs wall-clock time at iteration; final gate is unaffected.

## Affected Validation Review

The resolver algorithm in `tools/affected_tests.py` is:

1. **Pass 1 — exact focused-test match wins over source ownership.** A path that exactly equals any module's `focused_tests` entry is classified as a test-direct change; reverse closure is **not** triggered.
2. **Pass 2 — source ownership.** A path that matches a module's `owned_paths` glob is added to the source-direct set.
3. **Reverse closure** is computed only over `source_direct` and unioned with `test_direct`.
4. **Final affected set** = `reverse_closure(source_direct) ∪ test_direct`.
5. **Fail-closed** to BROAD/pytest -q (exit 2) on: malformed TOML, missing/invalid id, ambiguous ownership, unowned path, unknown dependency, dependency cycle, missing focused test, git inventory failure, unmapped path.

Independently verified each fail-closed case by running synthetic repos against the resolver:
- malformed TOML → `MODE=BROAD`, exit 2 ✓
- ambiguous ownership (two modules owning same path) → `MODE=BROAD`, exit 2 ✓
- dependency cycle (a → b → a) → `MODE=BROAD`, exit 2 ✓

Required Repair-2 regression tests run and pass:

- `test_frontend_test_only_classified_as_test` (`frontend/src/api/client.test.ts` → `MODULES=frontend_api`, no `frontend_shell`, no test:e2e, no build) — PASS.
- `test_mixed_source_and_python_test_keeps_resolve_only` (`app/audio.py + tests/test_resolve.py` → exactly `audio,resolve,runtime_api`; no dictionary/deck/render/export/build_dict/gate2) — PASS.
- `test_mixed_source_and_frontend_test` (`app/audio.py + frontend/src/api/client.test.ts` → exactly `audio,frontend_api,runtime_api`; no frontend_shell/test:e2e/build) — PASS.

Frontend-only focused work correctly emits `PYTEST=NONE` (verified).

Determinism: `test_deterministic_ordering` verifies that path-input ordering does not affect output. ✓

Iteration-time scope is unchanged: the resolver is a tooling aid. The authoritative `make gate` per `WORKFLOW.md §16.4` continues to require full ruff, full mypy, full pytest, full `check_agents`, and now `check_modules` for any candidate-final validation. The candidate does not weaken this invariant anywhere.

## Validator Review

`tools/check_modules.py` is single-purpose and well-scoped:

- Single `load_and_validate()` entry point shared with `tools/affected_tests.py` (no parallel schema validation; the brief's R2-equivalent for module map).
- Schema checks: missing `id`, non-string `id`, empty `id`, unknown field, missing required field, non-list fields. ✓
- Id uniqueness: both per-table-key and per-effective-id. The Repair-2 behavior `test_mismatched_keys_with_shared_effective_id_reports_duplicate` was inspected (lines 95–151 of `check_modules.py`) and confirmed:
  - Two table keys `[a]` and `[b]` both declaring `id = "shared"` produces **two mismatch diagnostics** (one per key, with the explicit per-key text "does not match its explicit 'id' field 'shared'") and **one duplicate diagnostic** ("duplicate module id 'shared'"). ✓
- Cross-module dependency checks: unknown dependency, self-dependency, duplicate dependency, cycle (DFS-coloured). ✓
- Focused-test path checks: pattern grammar (no `..`, no absolute paths, no backslashes, glob character set), path existence on disk, escape from repo root. ✓
- Ownership checks: Git-aware inventory, glob match per module, ambiguous-ownership and unowned-path diagnostics. ✓
- Module-metadata self-consistency: validator enforces that `MODULES.toml`, `tools/check_modules.py`, `tools/affected_tests.py` are owned solely by `module_metadata`. ✓
- Git inventory failure → `git inventory failure` diagnostic and fail-closed. ✓

The validator is wired into `make gate` as a separate `check-modules` target. The target is appended to the existing chain: `gate: ruff mypy pytest check-agents check-modules`. None of the prior targets is removed or relaxed.

No bypasses detected.

## Governance Review

`WORKFLOW.md §2` adds a `Required reading:` field to the brief schema and includes a clarifying paragraph that:

- "Root `AGENTS.md` and other globally binding files required by current governance remain binding and are not repeated in `Required reading`; `Required reading` narrows task-specific source/ADR/test context, not global invariants." — This correctly preserves global binding.
- "Workers should not broaden context merely 'to be safe' when the brief and `MODULES.toml` give a dependency-closed context set." — Correctly subordinates context-broadening to evidence.
- "Workers MAY inspect outside the declared reading list when concrete evidence reveals an ambiguity or dependency; such expansion should be targeted, not whole-repository rediscovery." — Correctly permits targeted expansion when warranted. This is not a "read too little" failure mode; it requires concrete evidence.
- Retroactivity clause: closed briefs are not rewritten. OPEN briefs gain `Required reading:` at re-dispatch time. ✓

`PROMPTS.md` worker OPEN prompts (implementation and supervised variants) and the Risk-label review prompt are updated to reference `Required reading:` and to reference `MODULES.toml` as an index, with explicit "MODULES.toml and any generated context pack are an INDEX ONLY and must never substitute for evidence." ✓

`WORKFLOW.md §16` (exact-final-candidate full-validation invariant) is unchanged. `WORKFLOW.md §15` (long-command no-monitoring) is unchanged. `WORKFLOW.md §11` (closure failure-closed), `§14.6` (supervised-worker fail-closed), and `§7` (ADR cold-review three-review cap) are unchanged.

The audit doc's claim that "the brief schema and prompts are binding" plus the new "Required reading — scope and binding" paragraph do not create a "skip the global rules" loophole.

No reviewer authority is weakened: Risk-label review (§6) still requires independent full-diff inspection of the pushed branch, and the new wording in PROMPTS.md explicitly states "The reviewer must still independently inspect: the required full diff when governance requires it; binding AGENTS rules; binding ADR sections; exact-final-candidate evidence required by governance. Generated or module metadata never replaces that evidence."

## Audit Document Review

The audit is decision rationale, not machine authority. Reviewed against the implemented design.

**Documentation inconsistency (MEDIUM, non-blocking):** `docs/agent-efficiency-audit.md` lines 569–577 present an "Option C" algorithm sketch:

```
# No automatic dependency closure by default. Conservative.
focused = sorted(set(m.focused_tests for m in directly_owning_modules))
```

This contradicts the actual implementation in `tools/affected_tests.py`, which walks the **transitive reverse closure** over `source_direct` and unions it with `test_direct`. The "Iteration-time focused commands" table (lines 626–640) also implies direct-owner focus only (e.g. `app/resolve.py` → only `tests/test_resolve.py tests/test_resolve_spacy.py`). The actual resolver emits 15 pytest paths for `app/resolve.py` (8 module's worth of reverse closure plus resolve itself). The audit contradicts what the tool actually does.

This is documentation drift. Severity is MEDIUM rather than BLOCKING because:
- The audit is explicitly non-authoritative.
- The implementation is correct, fail-closed, and self-documenting in code.
- The regression tests explicitly verify closure walking.
- A future orchestrator reading both the audit and the implementation code would see the code's behaviour as the source of truth.

However, a future "simplification" attempt that follows the audit's algorithm sketch would under-select tests (driving future unsafe implementation). Recommend a follow-up audit amendment to reconcile the algorithm sketch with the implemented closure-walking behaviour, or remove the "Option C" sketch as superseded.

**Minor historical/recommendation mismatch (LOW, non-blocking):** the audit cites "Tracked files: 101" but the actual count at base `17a899e` is 100. The audit cites "pytest -q 691 passed" (slice-8 base). The candidate's gate is 731 passed (= 691 + 17 + 23 new tests). These are snapshots from different points in the slice timeline, not contradictions.

No statements in the audit imply Markdown is authoritative metadata; the audit explicitly states the opposite. No statements weaken final validation; the audit explicitly preserves full gate + frontend + Playwright. No incorrect AGENTS enforcement claims were found. No deprecated/unsafe language. No missing or dangerous guidance for slice-9.

## Merge History Assessment

**HISTORY_ACCEPTABLE.**

The candidate's seven-commit lineage intentionally preserves:

- The accepted audit (`3553d9c`, `1638443`).
- The original foundation implementation (`f98904e`).
- The rejected direct-owner commit (`ce737db`) — preserved on the recovery branch.
- The revert that neutralizes the rejected commit (`8fcddd7`).
- Repair 1 (`115530a`).
- Repair 2 (`c136a2e`).

The final tree at `c136a2e` is authoritative and was the exact-final-candidate state for the recorded full gate. Replaying/squashing the rejected+revert pair into a new clean commit would:

1. Create a new candidate SHA, invalidating the gate certification (per `WORKFLOW.md §16.4`).
2. Require a fresh full validation of the new candidate.
3. Lose the explicit evidence trail showing what was attempted and rolled back.

Aesthetic preference for a clean history is explicitly insufficient per the brief. The current history is auditable, fully-validated, and shows the deliberate sequencing. **No material governance, correctness, or future-maintenance risk** is created by preserving the rejected+revert pair. The contaminated branch `infra/agent-efficiency-foundation` (`ac4f113`) is preserved separately, not part of this candidate.

## Complexity / ROI Assessment

**PROPORTIONATE.**

The candidate introduces:
- 1 TOML file (213 lines, machine-readable metadata).
- 2 Python tooling scripts (`check_modules.py` 584 LOC, `affected_tests.py` 405 LOC — including docstrings and tests-friendly helpers).
- 2 test modules (`test_check_modules.py` 596 LOC, `test_affected_tests.py` 606 LOC).
- 1 Makefile target addition.
- Small `WORKFLOW.md` and `PROMPTS.md` amendments (additive).

For a 16-module, ~100 tracked-file monorepo with a single frontend, this is the minimum machinery required to make the §16 staged-validation rule mechanically enforceable. No Pants/Bazel/Nx/Turborepo, no repo split, no package explosion, no frontend component split. The validator runs as a single subprocess in `make gate` and the resolver is a CLI invocation, both failing closed on metadata drift.

The audit doc's rejected/deferred list (Pants, Bazel, multi-repo split, nested AGENTS.md, auto-refactor, microservice decomposition) was correctly held back. The candidate does not introduce premature abstractions.

## Blocking Findings

None.

## Non-Blocking Findings

### N1 — `build_dict → check_agents` is a false-positive dependency edge
- **Severity:** LOW (over-selection only, not under-selection)
- **Path:** `MODULES.toml` line 125
- **Evidence:** `tools/build_dict.py` imports `app.resolve`, `tools.resolver_hash`, plus stdlib + `urllib`/`httpx`-style third-party. It does NOT import `tools.check_agents`. The graph claim from the audit brief is "build_dict → check_agents"; the implementation says `dependencies = ["resolve", "check_agents"]`.
- **Impact:** When `tools/check_agents.py` changes, `tools/affected_tests.py` will include `build_dict` and run its 5 stage tests unnecessarily. This is over-selection — extra wall-clock time at iteration only. Final gate is unaffected.
- **Required remedy (non-blocking, follow-up slice):** Remove `"check_agents"` from `modules.build_dict.dependencies` in `MODULES.toml`. Re-run `make gate` to confirm validator still passes.

### N2 — Audit document "Option C" algorithm sketch contradicts implemented closure behaviour
- **Severity:** MEDIUM (documentation drift; could mislead a future "simplify" attempt into under-selection)
- **Path:** `docs/agent-efficiency-audit.md` lines 569–577 and lines 626–640
- **Evidence:** The algorithm sketch says `# No automatic dependency closure by default. Conservative.` and the example table for `app/resolve.py` shows only the resolve module's tests. The implementation in `tools/affected_tests.py` does walk transitive reverse closure and emits 15 pytest paths for `app/resolve.py`.
- **Impact:** Future orchestrators/maintainers reading the audit before reading the implementation may attempt to "simplify" the resolver to match the audit's described algorithm. Such a simplification would under-select tests for changes to leaf modules like `app/resolve.py` (which has 7 reverse dependents).
- **Required remedy (non-blocking, follow-up audit amendment):** Either update the "Option C" algorithm sketch and example table to match the implemented behaviour, or annotate the section as superseded by the implementation, with a pointer to `tools/affected_tests.py` as the source of truth. Update the row "Iteration-time focused commands" to reflect closure behaviour.

### N3 — `deck → reference` is not a Python import edge
- **Severity:** NOTE
- **Path:** `MODULES.toml` line 98
- **Evidence:** `app/deck.py` does not import from `reference/`; the dependency is the runtime SQL schema in `reference/schema.sql`. The edge is correctly recorded as a conceptual/runtime dependency but does not match the literal "imports/uses" definition in `MODULES.toml`'s header comment.
- **Impact:** Conservative over-selection: a change to `reference/smoke_test.py` triggers `deck`'s tests (correct), and transitively `runtime_api`'s tests (since `runtime_api → deck`). Whether `runtime_api` actually needs to be re-tested on a reference change is a domain question. The behaviour is more inclusive than strictly necessary but not incorrect.
- **Required remedy (non-blocking, optional follow-up):** Consider tightening the header comment to "directly imports OR operates against" or moving the runtime-schema coupling to a clearer convention (e.g. a separate `contracts = ["reference"]` list). Not strictly required.

### N4 — `tests/` is excluded from inventory roots by design
- **Severity:** NOTE
- **Path:** `tools/check_modules.py` `INVENTORY_ROOTS` constant
- **Evidence:** `INVENTORY_ROOTS = ("app", "tools", "reference", "frontend/src")`. The 22 `tests/` files are referenced by `focused_tests` strings only and are not subject to ownership validation.
- **Impact:** A new test file added under `tests/` does not need a MODULES.toml row. This is a deliberate design and matches the brief. Future maintainers may need to be aware that new tooling scripts, build scripts, or schema definitions placed outside the four roots + `Dockerfile` would be invisible to the validator.
- **Required remedy:** None. Behavior is correct as designed.

## Final Recommendation

**PASS WITH NON-BLOCKING NOTES.**

The candidate is safe to merge into `main` as the infrastructure foundation for slice 9 and beyond. The new validator and resolver are correctly scoped, fail-closed, and wired into `make gate` without weakening the full-validation invariant. The governance amendments to `WORKFLOW.md` and `PROMPTS.md` are additive and preserve all global bindings. Three minor accuracy notes (`build_dict → check_agents` over-selection edge, audit-doc algorithm sketch contradicts implementation, `deck → reference` non-import edge) are recorded for future maintainers; none blocks merge. The history preserves the rejected commit + revert deliberately; a clean replay would invalidate the recorded gate certification.
