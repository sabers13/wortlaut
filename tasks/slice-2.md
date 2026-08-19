# Slice 2 — Gate 1: verify the spaCy separable-particle label and lock the resolver cases

Task:        Execute ADR-0001 §13 Gate 1 against the real `de_core_news_md` model, make the empirically observed separable-particle dependency label the single `SVP_DEP` value in `app/resolve.py`, and lock the exact ADR-0001 §13 `CASES` as real-model resolver tests. No dictionary build work, no stage 01, no stage 02, no API, no user-state work.
Depends:     slice-1
Precondition: `make gate` passes on `main`; slice-1 is merged; and a read-only startup/pre-dispatch check proves `spacy.load("de_core_news_md")` succeeds in the existing project environment without downloading anything. If the model is absent, startup STOPs before Attempt 1: dependency/model provisioning returns to governance and is not invented by this slice.
Allowlist:   `app/resolve.py`, `tests/test_resolve.py`, `tests/test_resolve_spacy.py`, `tasks/slice-2.report.md`
Acceptance:  (C1) Before changing `SVP_DEP`, the worker runs ADR-0001 §13's real-model probe with `spacy.load("de_core_news_md")` over exactly `Ich rufe dich morgen an.`, `Der Zug kommt um acht an.`, and `Ich rufe laut.` and records in the report the spaCy version, model package/name/version from the loaded pipeline metadata, and the printed token text/POS/dep/head evidence. No mock, token double, hardcoded parse, or model download can substitute for this empirical probe. (C2) The dependency label empirically linking `an` to the finite verb in both separable cases is consistent. `app/resolve.py` then has exactly one module-level separable-particle label definition, `SVP_DEP = "<observed label>"`, and every resolver use references that constant. If the two separable examples disagree, the relevant `an` token is absent, or the dependency relation cannot be identified unambiguously, STOP-and-ask rather than choosing a label. (C3) `tests/test_resolve_spacy.py` loads the real `de_core_news_md` model and locks **exactly** ADR-0001 §13's five `CASES`, in this order and with these expected resolver outputs: `("Ich rufe dich morgen an.", "rufe", "anrufen")`, `("Der Zug kommt um acht an.", "kommt", "ankommen")`, `("Ich rufe dich morgen an.", "an", "anrufen")`, `("Ich rufe laut.", "rufe", "rufen")`, `("Sie interessiert sich für Musik.", "interessiert", "interessieren")`. The test parses each sentence with the real model, locates the named token, exercises the existing resolver/token-resolution seam already provided by slice-1, and asserts the expected resolved lemma. Do not create a second resolver or a test-only reconstruction algorithm. (C4) The CASES test is mandatory gate coverage: no `skip`, `skipif`, `xfail`, try/except fallback, fake model, or network/download-on-miss behavior. If `de_core_news_md` cannot load, the test fails. `make gate` itself performs no network access. (C5) The control case `Ich rufe laut.` remains non-separable (`rufen`), so a label or implementation that makes ordinary `rufen` separable fails. The reflexive control resolves `interessiert` to `interessieren`. D11 candidate-generation behavior and every slice-1 ladder/compound test continue to pass unchanged. (C6) Apart from changing the single `SVP_DEP` constant if the empirical probe requires it, `app/resolve.py`'s slice-1 resolution ladder, injected lookup seam, compound splitter, no-I/O property, and dependency direction are unchanged. Do not refactor merely to make the Gate 1 test convenient. (C7) This slice does not install or download a spaCy model, change dependency/version policy, build dictionary data, add stage 01/02 code, alter `app/dictionary.py`, add HTTP/API/app-factory code, touch user data/schema, repair `reference/smoke_test.py`, or modify ADR/AGENTS/WORKFLOW contracts. Any such need is Stop-and-ask. (C8) Existing executable AGENTS checks continue passing, including R1, R3 and R7; `mypy --strict .` and ruff remain clean; all existing tests plus the new real-model Gate 1 tests pass under bare `make gate`. (C9) Over the committed range `$EXPECTED_MAIN_HEAD...HEAD` plus any untracked files, `git diff --check` exits 0 and every changed path is inside the Allowlist. (C10) Before Worker CLOSE, create `tasks/slice-2.report.md` containing exactly the scaffold in constraint 4 below; Worker CLOSE fills only its NARRATIVE section. The NARRATIVE records the empirical model/version/dep evidence, whether `SVP_DEP` changed, Stop-and-ask conditions encountered, problems deliberately not fixed, and work left undone.
Stop-and-ask: `de_core_news_md` is absent or cannot load locally; satisfying Gate 1 would require downloading/installing a model or changing dependency/version policy; the two separable examples do not expose one consistent dependency label; the exact ADR-0001 §13 CASES do not pass through the existing slice-1 resolver seam; testing them would require a second resolver or substantive resolver redesign; a requirement needs a file outside the Allowlist; an ADR/AGENTS/WORKFLOW contract would have to change; `EXPECTED_MAIN_HEAD` fails; or the brief is insufficient to choose a mechanical implementation.
Risk:        none
Why-risk:    WORKFLOW.md §6 is a file-path/consumer lookup, not a difficulty judgment. This Gate 1 slice touches the existing internal resolver plus tests/report only; it introduces no route or package surface for an external consumer, no schema/data migration, no auth/secrets/permission code, and no delete/overwrite/irreversible data transform. No §6 row matches, so no committed full-diff review is required.
Model:       gemini-flash / T1 / low
Why:         All WORKFLOW.md §4 rows remain T1. **Verification:** the ADR-prescribed real-model probe plus five mandatory real-model CASES make a wrong label/resolver result executable and fail-closed instead of judgment-only. **Blast radius:** one existing internal constant plus tests under a tight reversible allowlist. **Spec completeness:** ADR-0001 §13 fixes the three probe sentences and all five CASES; inconsistent or unavailable model evidence is Stop-and-ask, so the worker chooses no design. **Novelty:** slice-1 already established the resolver seam and test pattern; this slice only verifies and locks that existing pattern. The effort rule therefore selects low.
Fallback:    codex-low / T1 / low

## Worker implementation constraints

1. Start only after the slice-2 orchestrator supplies the verified
   `EXPECTED_MAIN_HEAD`. Create `slice/2` from that exact HEAD; if `main`
   differs, STOP.
2. The real spaCy-model observation happens before any edit to `SVP_DEP`.
   Preserve its stdout in the report evidence.
3. The five ADR `CASES` are normative test data. Do not alter, add, remove,
   weaken, parametrically rewrite into different expected semantics, or replace
   them with token doubles.
4. Create this exact scaffold before Worker CLOSE, then populate only NARRATIVE:

   ```markdown
   # Slice 2 report

   ## NARRATIVE
   ```

## Required terminal verification before Worker CLOSE

Run all of the following; any nonzero exit is STOP-and-report. The orchestrator
supplies `EXPECTED_MAIN_HEAD` in the dispatch; the worker must not infer it:

```sh
: "${EXPECTED_MAIN_HEAD:?STOP: EXPECTED_MAIN_HEAD was not supplied}"

test "$(git branch --show-current)" = "slice/2" || {
  echo "STOP: not on slice/2"; exit 1; }

test "$(git rev-parse main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: main differs from expected main HEAD"; exit 1; }

test "$(git merge-base slice/2 main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: slice/2 base differs from expected main HEAD"; exit 1; }

.venv/bin/python - <<'PY'
import spacy

nlp = spacy.load("de_core_news_md")
print("SPACY_VERSION:", spacy.__version__)
print("MODEL_NAME:", nlp.meta.get("name"))
print("MODEL_VERSION:", nlp.meta.get("version"))
for sentence in [
    "Ich rufe dich morgen an.",
    "Der Zug kommt um acht an.",
    "Ich rufe laut.",
]:
    print(f"\n{sentence}")
    for token in nlp(sentence):
        print(
            f"{token.text:12} {token.pos_:6} "
            f"dep={token.dep_:10} head={token.head.text}"
        )
PY

make gate

git diff --check "$EXPECTED_MAIN_HEAD"...HEAD

outside="$({
  git diff --name-only "$EXPECTED_MAIN_HEAD"...HEAD
  git ls-files --others --exclude-standard
} |
grep -vxF \
  -e app/resolve.py \
  -e tests/test_resolve.py \
  -e tests/test_resolve_spacy.py \
  -e tasks/slice-2.report.md || true)"

test -z "$outside" || {
  echo "STOP: scope violation:"
  printf '%s\n' "$outside"
  exit 1
}
```
