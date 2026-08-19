# Slice 1 — resolution ladder, dictionary reader, and the executable R3 scaffold

Task:        Implement `app/resolve.py` (resolution ladder + deterministic compound splitter, no I/O) and `app/dictionary.py` (read-only dictionary-asset reader), and extend the executable AGENTS checker with the R3 stage-02 cache-key scaffold. No HTTP routes, no user-database access, no build stage, no example ranking, no rendering.
Depends:     slice-0
Precondition: `make gate` exists on `main` and passes bare, with ruff, `mypy --strict .`, `pytest -q`, and `tools/check_agents.py` enforcing R1 and R7. The slice-1 orchestrator supplies the verified `EXPECTED_MAIN_HEAD`.
Allowlist:   `app/__init__.py`, `app/resolve.py`, `app/dictionary.py`, `tools/resolver_hash.py`, `tools/check_agents.py`, `tests/conftest.py`, `tests/test_resolve.py`, `tests/test_dictionary.py`, `tests/test_check_agents.py`, `pyproject.toml`, `tasks/slice-1.report.md`
Acceptance:  (B1) `app/resolve.py` implements ADR-0001 §10's four-step ladder — exact `(lemma, pos[, gender])`, surface form, deterministic compound split, then `status='needs_gloss'` stub — and performs **no I/O of any kind**: no SQLite, no filesystem reads, no network, no subprocess. ADR-0001 §10 fixes the dependency direction as `dictionary → resolve`, so the "is this lemma known?" oracle the splitter and the exact/surface steps require is **injected** into `app/resolve.py` by the caller as an explicit lookup protocol/callable, and `app/dictionary.py` supplies the SQLite-backed implementation of that protocol. `app/resolve.py` must not import `app.dictionary`, `sqlite3`, or any module that opens a file. (B2) The compound splitter is deterministic longest-known-head with exactly the Fugenelemente `s, es, n, en, er, e, ns`, hardcoded and exceptionless per ADR-0001 §10, and compound gender equals head gender. It reproduces the ADR's verified case: `Krankenversicherungskarte -> ['kranken', 'versicherung', 'karte']` with gender `die` inherited from `Karte`. A resolved compound carries `status='derived_compound'` per `reference/schema.sql`'s `note.status` domain. (B3) The separable-verb dependency label is a single module-level constant in `app/resolve.py` — `SVP_DEP = "svp"` — referenced everywhere the label is needed and defined nowhere else. ADR-0001 §13 Gate 1 verifies that string, and Gate 1 is ADR-0002 §6 order 3 (slice-2), **not this slice**: do not add the §13 `CASES` lock here, and do not treat the current value as verified. Structure the code so slice-2 changes exactly one constant. (B4) `make gate` runs offline and hermetically: it must not download a spaCy model, reach the network, or fail when `de_core_news_md` is absent. Model loading is lazy, and every ladder/splitter test drives `app/resolve.py` through the injected lookup protocol and token-like test doubles rather than a real pipeline load. Do **not** satisfy this with skip markers — a skipped test masks failure, which A1's "without masking failures" forbids. Tests requiring the real model belong to slice-2. (B5) `app/dictionary.py` reads only PART A of `reference/schema.sql` — `lemma`, `surface_form`, `sense`, `example`, `example_lemma` — opens the dictionary database read-only, and never opens, imports, references, or writes any PART B user table (`note`, `card`, `review_log`, `deck`, `note_deck`, `gloss_contribution`). AGENTS R9 makes these separate files; ADR-0001 §10's `api → deck → render → dictionary → resolve` puts user state above `dictionary`. Tests build their fixture database from PART A DDL inside the test tree; do not import, execute, or depend on the path of `reference/smoke_test.py`, which is a filed, path-broken artifact repaired in a later slice. (B6) espeak/IPA synthesis, audio, and TTS are **out of scope**: `app/dictionary.py` returns the stored `ipa`/`ipa_source` columns and spawns no subprocess. ADR-0002 §6 order 2 names the resolution ladder and compound splitter only; the espeak fallback is a `docs/backlog.md` Standing item. (B7) `tools/resolver_hash.py` provides the single canonical SHA-256-of-`app/resolve.py` helper, computed over the file's raw bytes. It is the only definition of that hash in the repository; ADR-0001 §12's inline example is illustrative, not a licence to recompute it in a second place, because two definitions is exactly the divergence AGENTS R2 exists to prevent. (B8) `tools/check_agents.py` gains an R3 check that is fail-closed and non-vacuous today: it fails if `app/resolve.py` is missing or unreadable; it fails if a SHA-256 over `app/resolve.py` is computed anywhere outside `tools/resolver_hash.py`; and it fails if a stage-02 build module exists and constructs a cache key without calling that helper. Stage 02 is ADR-0002 §6 order 6 and does not exist yet, so the third clause is dormant — but it must activate automatically when the module appears, never by editing the checker, and it must fail closed on a file it cannot parse or read. The existing R1 and R7 checks keep passing unchanged. (B9) `tests/test_check_agents.py` proves the R3 check with synthetic fixtures written into a temporary tree: a stage-02-shaped module that caches **without** the resolver hash is rejected; one that caches **with** it is accepted; a second, independent SHA-256 of `app/resolve.py` is rejected; and an unparseable or unreadable inspected file is rejected rather than skipped. `tests/test_resolve.py` and `tests/test_dictionary.py` cover each ladder step including the stub fallthrough, the ADR's compound case, gender disambiguation (`der See`/`die See`), and a surface-form hit. (B10) `pyproject.toml` adds only what this slice's gate needs, keeps `mypy --strict .` and ruff clean, and introduces no LLM SDK into the runtime dependency graph — AGENTS R1's check must still pass and must not false-positive on spaCy, which is not an LLM SDK. (B11) No API route, app factory, `app/examples.py`, `app/render.py`, `app/deck.py`, `app/export.py`, `app/api.py`, Dockerfile, build stage, migration, or user-database code is added. (B12) Over the committed range `$EXPECTED_MAIN_HEAD...HEAD` plus any untracked files, `git diff --check` exits 0 and every path is inside the Allowlist. (B13) Before Worker CLOSE, create `tasks/slice-1.report.md` containing exactly the scaffold in constraint 4 below; Worker CLOSE then fills only its NARRATIVE section.
Stop-and-ask: Any requirement would need a file outside the Allowlist; the injected-lookup seam in B1 cannot satisfy both the ladder and `resolve.py`'s no-I/O rule; making the R3 check non-vacuous appears to require inventing stage-02 behaviour, a build cache format, or a schema/route that does not exist; spaCy cannot be installed or configured without a network fetch at gate time; an ADR/AGENTS/WORKFLOW contract would have to change; the `EXPECTED_MAIN_HEAD` precondition fails; or the brief is insufficient to choose a fail-closed implementation.
Risk:        none
Why-risk:    WORKFLOW.md §6 is a file-path lookup over the Allowlist, not a judgment. No path is a schema/data migration; none handles auth, secrets, or permission checks; none deletes, overwrites, or irreversibly transforms data. `app/` carries no external consumer at this order — there is no packaging, no HTTP route (ADR-0002 §6 order 8) and no compose integration (order 10), and AGENTS R7 forbids the lecture app importing this code at all. No row matches, so no §6 pre-committed full-diff review is attached.
Model:       gpt-5.6-terra / T3 / high
Why:         Two WORKFLOW.md §4 rows trigger and the highest wins. **Verification:** separable-verb and compound-split faults fail silently and self-consistently — lookups succeed and the answers are wrong (ADR-0001 D3, Gate 1; AGENTS R2) — so the gate cannot catch the defect this slice is most likely to produce. **Novelty:** this establishes the `app/` module pattern, the injected-lookup seam that C2's dependency direction rests on, and the R3 checker shape that R6 and R12 will copy. §0 assigns new patterns to T3; the effort rule selects high for the simultaneous no-I/O, hermetic-gate, and fail-closed-checker constraints.
Fallback:    opus-5 / T3 / high

## Worker implementation constraints

1. Start only after the slice-1 orchestrator supplies the verified `main` HEAD.
   Create `slice/1` from that exact HEAD; if `main` differs, STOP.
2. Do not make the current absence of a stage-02 module the enforcement
   mechanism for R3. The check must become effective automatically when a later
   slice adds that module, with no edit to `tools/check_agents.py`.
3. A check that cannot inspect a file it claims to govern must fail, not skip.
4. Create this exact scaffold before Worker CLOSE, then populate only NARRATIVE:

   ```markdown
   # Slice 1 report

   ## NARRATIVE
   ```

## Required terminal verification before Worker CLOSE

Run all of the following; any nonzero exit is STOP-and-report. The orchestrator
supplies `EXPECTED_MAIN_HEAD` in the dispatch; the worker must not infer it:

```sh
: "${EXPECTED_MAIN_HEAD:?STOP: EXPECTED_MAIN_HEAD was not supplied}"
test "$(git branch --show-current)" = "slice/1" || {
  echo "STOP: not on slice/1"; exit 1; }
test "$(git rev-parse main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: main differs from expected main HEAD"; exit 1; }
test "$(git merge-base slice/1 main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: slice/1 base differs from expected main HEAD"; exit 1; }
make gate
git diff --check "$EXPECTED_MAIN_HEAD"...HEAD
outside="$({ git diff --name-only "$EXPECTED_MAIN_HEAD"...HEAD
             git ls-files --others --exclude-standard; } |
           grep -vxF -e app/__init__.py -e app/resolve.py -e app/dictionary.py \
             -e tools/resolver_hash.py -e tools/check_agents.py \
             -e tests/conftest.py -e tests/test_resolve.py \
             -e tests/test_dictionary.py -e tests/test_check_agents.py \
             -e pyproject.toml -e tasks/slice-1.report.md || true)"
test -z "$outside" || {
  echo "STOP: scope violation:"; echo "$outside"; exit 1; }
```
