# Slice 0 — repository skeleton and gate infrastructure

Task:        Create the Python repository skeleton and the project gate so `make gate` is the single authoritative local verification command; do not implement flashcard application behaviour.
Depends:     none
Precondition: The one-time repository bootstrap has succeeded, and the fresh slice-0 orchestrator has verified the exact bootstrap `main` HEAD using PROMPTS.md's first-slice exception.
Allowlist:   `.gitignore`, `pyproject.toml`, `Makefile`, `tools/check_agents.py`, `tests/test_check_agents.py`, `tasks/slice-0.report.md`
Acceptance:  (A1) Plain `make gate`, with no PATH prefix or wrapper, exits 0 and runs, without masking failures, all four required classes from WORKFLOW.md §0: ruff, `mypy --strict`, `pytest -q`, and executable AGENTS checks. The Makefile resolves its own interpreter — `.venv/bin/python` when that file exists, else `python3` — so the identical command works in the closure worker's final gate and at fresh-orchestrator startup, which both run it bare. (A2) The type-check step is exactly `mypy --strict .` from the repository root, with `.venv` and tool caches excluded in `pyproject.toml`; no path list is enumerated anywhere. A not-yet-created `app/` therefore passes, later `app/*.py` files are covered without a Makefile edit, and no placeholder application module is added solely to satisfy mypy or ruff. (A3) The executable-rule checker enforces the executable contracts that are checkable today against the real tree: R1 runtime-LLM prohibition (`pyproject.toml` runtime deps and `app/` imports) and R7 zero lecture-app coupling. It must fail closed on malformed/unreadable files it is supposed to inspect. Three executable rules are deliberately **not** scaffolded here; AGENTS.md's header already permits this (`[executable]` rules "are (or will be) enforced by a `make gate` check"), so no AGENTS edit is required. R3's stage-02 resolver-hash check belongs to ADR-0002 §6 order 2. R6's `review_log` constraints belong to the slice creating the application schema — `reference/schema.sql` is a filed reference artifact, not the app's schema of record. R12's browser-boundary checks belong to the slice creating the `/vocab` API, which §6 order 8 already names as R12's implementation point. Scaffolding R6 or R12 now means authoring fake schema and route files, which Stop-and-ask below classes as inventing application behaviour. (A4) `tests/test_check_agents.py` includes positive and representative negative fixtures proving the checker rejects at least one violation for each of R1 and R7 instead of merely passing the current mostly-empty tree. (A5) `pyproject.toml` supplies the development tooling needed by the gate and introduces no runtime LLM SDK; no application feature dependency is added unless it is required solely to execute the slice-0 gate. (A6) `.gitignore` covers local virtualenv/cache/build/test artifacts created by the documented setup — including `.venv/` and the `handoff/` directory — without ignoring governance, source, tests, or task reports. `handoff/` is named explicitly because PROMPTS.md §Closure worker writes `handoff/main-gate.txt` and `handoff/git-log.txt` into the repository and commits neither, so an unignored `handoff/` would leave the tree permanently dirty and fail the `git status --porcelain` preflight of every session after slice-0 closure. (A7) No `app/*.py`, dictionary-build stage, Dockerfile, API route, schema migration, or feature implementation is added in this slice. (A8) Over the committed range `$EXPECTED_MAIN_HEAD...HEAD` plus any untracked files, `git diff --check` exits 0 and every path is inside the Allowlist. The check is on the range, not the working tree: Worker CLOSE commits by work unit, so `git status --short` is empty by then and a working-tree check would pass by finding nothing. (A9) Before Worker CLOSE, create `tasks/slice-0.report.md` with a `## NARRATIVE` section; Worker CLOSE then fills only that section with decisions not in the brief, stop-and-ask conditions hit, problems noticed but not fixed, and work left undone.
Stop-and-ask: Any requirement would need a file outside the Allowlist; the gate cannot be made to run as `make gate`; satisfying an executable AGENTS rule requires inventing application behaviour or changing an ADR/AGENTS/WORKFLOW contract; a new runtime dependency beyond gate tooling appears necessary; the bootstrap/main precondition fails; or the brief is insufficient to choose a fail-closed verification implementation.
Risk:        none
Model:       gpt-5.6-terra / T3 / high
Why:         WORKFLOW.md §4 Novelty row triggers escalation because this slice establishes the repository/gate pattern later slices will copy; §0 assigns new patterns to T3, and the effort rule selects high for the simultaneous gate/rule/fail-closed constraints.
Fallback:    opus-5 / T3 / high

## Worker implementation constraints

1. Start only after the slice-0 orchestrator supplies the verified bootstrap
   `main` HEAD. Create `slice/0` from that exact HEAD; if `main` differs, STOP.
2. Keep gate tooling deterministic and local. A check that cannot inspect a file
   it claims to govern must fail rather than silently skip that file.
3. Do not make the current absence of `app/` the enforcement mechanism. The
   checker/gate must remain effective automatically when later slices add
   application files.
4. Do not implement the ADR-0002 §6 order-2 R3 cache-key scaffold early. The
   slice-0 gate may invoke a checker that has no R3 stage-02 assertion yet; that
   assertion is added with `resolve.py`/`dictionary.py` in the next ordered work.
5. The report file is a process artifact in this slice's Allowlist. Create this
   exact scaffold before Worker CLOSE, then populate only its NARRATIVE section:

   ```markdown
   # Slice 0 report

   ## NARRATIVE
   ```

## Required terminal verification before Worker CLOSE

Run all of the following; any nonzero exit is STOP-and-report. The orchestrator
must supply `EXPECTED_MAIN_HEAD` from the exact bootstrap receipt in the worker
dispatch; the worker must not infer it:

```sh
: "${EXPECTED_MAIN_HEAD:?STOP: EXPECTED_MAIN_HEAD was not supplied}"
test "$(git branch --show-current)" = "slice/0" || {
  echo "STOP: not on slice/0"; exit 1; }
test "$(git rev-parse main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: main differs from expected bootstrap main HEAD"; exit 1; }
test "$(git merge-base slice/0 main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: slice/0 base differs from expected bootstrap main HEAD"; exit 1; }
make gate
git diff --check "$EXPECTED_MAIN_HEAD"...HEAD
outside="$({ git diff --name-only "$EXPECTED_MAIN_HEAD"...HEAD
             git ls-files --others --exclude-standard; } |
           grep -vxF -e .gitignore -e pyproject.toml -e Makefile \
             -e tools/check_agents.py -e tests/test_check_agents.py \
             -e tasks/slice-0.report.md || true)"
test -z "$outside" || {
  echo "STOP: scope violation:"; echo "$outside"; exit 1; }
```

If `.venv` does not already exist, the worker may create it as an ignored local
execution artifact and install the development dependencies declared by
`pyproject.toml`; `.venv` must remain untracked and must not appear in the final
diff.
