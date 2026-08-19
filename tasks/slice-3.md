# Slice 3 — Build stage 01: deterministic Wiktextract → Gate-2 dictionary core

Task:        Implement ADR-0001 §12 build stage 01 as a maintainer-only, deterministic, offline JSONL-to-SQLite transform that produces the `lemma`, `sense`, and `surface_form` dictionary core consumed by slice-4 Gate 2. The output must match the existing PART A/read-only `app.dictionary` contract, carry Wiktionary source/license attribution, preserve real inflected forms including multi-word separable forms, and require no runtime/network/LLM path.
Depends:     slice-2
Precondition: `make gate` passes on `main`; slice-2 is accepted and merged; `tasks/slice-2.report.md` records Gate 1 `svp` evidence and all five ADR-0001 §13 cases passing. This slice does not require a real multi-GB Kaikki dump to be present: executable acceptance uses committed small JSONL fixtures. A later maintainer run supplies real dump paths.
Allowlist:   `tools/build_dict.py`, `tests/test_build_dict_stage01.py`, `tests/fixtures/wiktextract_stage01_en.jsonl`, `tests/fixtures/wiktextract_stage01_de.jsonl`, `tasks/slice-3.report.md`
Acceptance:  (C1) `tools/build_dict.py` exposes exactly the stage-01 CLI `python tools/build_dict.py stage01 --en-jsonl <path> --de-jsonl <path> --output <path>`. It reads both inputs line-by-line as JSON Lines; it performs no download, HTTP call, API/LLM call, environment-secret read, or source-dump mutation. The output path must not already exist; an existing target is a hard error rather than an overwrite. (C2) Only records with `lang_code == "de"`, a non-empty string `word`, and a non-empty string `pos` enter the build. Redirect/no-POS records and other languages are ignored. Entry identity is deterministic `(word, canonical_pos, gender)`. Canonical POS mapping is fixed in this brief: `noun→NOUN`, `proper_noun→PROPN`, `name→PROPN`, `verb→VERB`, `aux→AUX`, `adj→ADJ`, `adv→ADV`, `prep→ADP`, `postp→ADP`, `pron→PRON`, `det→DET`, `num→NUM`, `conj→CCONJ`, `particle→PART`, `intj→INTJ`; any other non-empty POS becomes `raw_pos.upper()` rather than being silently dropped. (C3) The output SQLite contains exactly the stage-01-owned PART A tables `lemma`, `surface_form`, and `sense`, with column names/types/defaults/uniqueness/foreign-key relationships compatible with the corresponding three tables in `reference/schema.sql` and readable by the existing `app.dictionary.Dictionary`. Stage 01 must not create PART B/user tables and must not create `example`/`example_lemma`, which are owned by stage 02. Foreign keys are enabled during the build. (C4) IDs and rows are deterministic independent of EN-vs-DE input ordering: merge records by the identity in C2, sort identities deterministically before assigning lemma IDs, sort/de-duplicate surface forms per lemma before insertion, and assign sense IDs/`ord` deterministically. Running the parser against fixtures containing the same logical records in different source order must produce the same queried row contents and ordering. No assertion requires byte-identical SQLite files. (C5) English-edition input owns English gloss senses. For each merged lemma, traverse its English-source `senses` in source order, take each non-empty `glosses` string in order, de-duplicate identical gloss text, and retain at most the first three glosses total, matching ADR-0001's three-sense cap. Persist `ord=0,1,2...`, `source='wiktionary'`, and `license='CC BY-SA'`. Every persisted sense must have non-empty `source` and `license` (AGENTS R11). German-edition gloss text is not written into `gloss_en`. (C6) Both EN and DE inputs may contribute surface forms. For each `forms` item, persist a non-empty string `form` unless it is `"-"` or exactly equal to the headword; de-duplicate per lemma. The fixtures must prove multi-word forms `rief an` and `ruft an` survive verbatim for `anrufen`, satisfying the standing backlog check for inflected manual-entry support. Surface-form insertion may not invent forms absent from input. (C7) Populate the stage-01 lemma columns deterministically from Wiktextract fields without guessing missing data. `lemma=word`, `pos=canonical_pos`, `source='wiktionary'`, `license='CC BY-SA'`. Gender comes only from an unambiguous entry-level tag among `masculine→der`, `feminine→die`, `neuter→das`; zero matches gives NULL and multiple conflicting matches is a hard record error. `ipa` is the first non-empty `sounds[].ipa` in source order and then `ipa_source='wiktionary'`; absent IPA leaves both NULL. From `forms[].tags`, choose the lexicographically smallest matching form when multiple candidates meet the same exact tag predicate: plural = contains `plural`; genitive singular = contains both `genitive` and `singular`; present 3sg = contains `present`, `third-person`, `singular`; preterite 3sg = contains `past`, `third-person`, `singular` and does not contain `participle`; Partizip II = contains `past` and `participle`; comparative = contains `comparative`; superlative = contains `superlative`. Fields whose source evidence is absent remain NULL/default. This slice does not guess `aux`, `governs`, `reflexive`, `separable`, or `particle`. (C8) Parsing is fail-closed for malformed participating data: invalid JSON reports input path + 1-based line number; a participating field with the wrong JSON type reports path/line/field; conflicting gender tags error rather than picking one; an output-path collision errors before any output replacement. Records deliberately ignored by C2 do not become errors merely because irrelevant fields are malformed. A failed build leaves no completed output at the requested path. (C9) The implementation uses only the Python standard library plus existing repository modules; no dependency/version change and no `pyproject.toml` edit is allowed. Build code stays under `tools/`; no build dependency enters the runtime `app/` graph. `app/resolve.py` is not reimplemented or copied. Stage 02's resolver import/cache-hash obligations remain for slice-5 and are not pulled forward. (C10) `tests/test_build_dict_stage01.py` uses only committed tiny fixture JSONL and pytest temp paths. It proves: both source files merge into one deterministic lemma identity; exact schema compatibility needed by `app.dictionary`; max-three English senses and R11 source/license fields; DE glosses are not mislabelled as English; surface-form de-duplication; literal `rief an`/`ruft an`; POS mapping; gender/IPA/form-derived fields; ignored non-German/redirect records; malformed JSON/type/conflicting-gender/output-exists failures; no PART B/example tables; and output can be opened read-only by `Dictionary` and used for exact/surface lookups. No fixture, generated SQLite DB, Kaikki dump, cache, or machine path is committed outside the Allowlist. (C11) `make gate` passes; `git diff --check` passes; changed paths over `$EXPECTED_MAIN_HEAD...HEAD` plus untracked files stay wholly inside the Allowlist. R1/R3/R7 continue to pass. No real dictionary dump is committed. (C12) Before Worker CLOSE, create `tasks/slice-3.report.md` with the exact scaffold below; Worker CLOSE fills only NARRATIVE. The narrative records the CLI/output contract, exact fixture/gate numbers, source/license policy, multi-word surface-form evidence, Stop-and-ask conditions, deliberately deferred fields/problems, and work left undone.
Stop-and-ask: A real Kaikki/Wiktextract record shape needed for the C1–C10 contract cannot be represented by the documented `word`/`pos`/`lang_code`/`senses[].glosses`/`forms[].form`+`tags`/`sounds[].ipa` subset without changing this brief; Stage 01 would need a new package/dependency; satisfying the contract requires changing `app/`, `reference/schema.sql`, an ADR/AGENTS/WORKFLOW rule, or any file outside the Allowlist; the existing `Dictionary` seam cannot read the stage-01 SQLite without application changes; deterministic EN/DE merge identity is ambiguous under the stated key; real required attribution cannot be represented by existing `source`/`license`; any operation would overwrite an existing build/output file; `EXPECTED_MAIN_HEAD` or `Depends:` verification fails; or the brief leaves a design choice the worker cannot resolve mechanically.
Risk:        none
Why-risk:    WORKFLOW.md §6 is a path/consumer lookup. This slice adds maintainer-only build tooling, tiny test fixtures, tests, and a report. It does not change an externally callable runtime/API surface, schema/data migration file, auth/security code, user data, or an existing data artifact; the stage-01 CLI refuses to overwrite an existing output. No risk row matches, so no committed full-diff review is required.
Model:       gpt-5.6-terra / T3 / high
Why:         WORKFLOW.md §4 Novelty triggers T3 because this is the first offline dictionary-build-stage pattern and later stages will copy its artifact/error/reproducibility conventions. Verification is executable and the allowlist is tight, but the slice simultaneously carries source normalization, EN/DE merge, schema compatibility, attribution, deterministic IDs/forms/senses, malformed-input behavior, and no-overwrite constraints; under the effort rule those simultaneous constraints justify high reasoning effort.
Fallback:    opus-5 / T3 / high

## Worker implementation constraints

1. Start only after the slice-3 orchestrator supplies the exact verified
   `EXPECTED_MAIN_HEAD`. Create `slice/3` from that HEAD; a mismatch is STOP.
2. Read `reference/schema.sql`, `app/dictionary.py`, ADR-0001 §12, AGENTS R1/R2/R3/R9/R11,
   and this brief before editing. They define the already-accepted boundaries;
   do not amend them.
3. Stage 01 is a streaming transform. Do not load a real dump wholesale into
   memory. Tests may read their tiny fixtures however pytest requires, but the
   production JSONL path processes records line by line.
4. Do not download Kaikki/Wiktionary data in tests or implementation. The real
   dump path is owner/maintainer-supplied at execution time.
5. Do not install Wiktextract itself. The inputs are its already-extracted JSONL.
6. Output creation is fail-closed: build to a temporary sibling path and publish
   to the requested output only after successful parse/schema/insertion/commit.
   The requested path must be absent before starting and must never be replaced.
7. Do not execute all of `reference/schema.sql`, because that would create PART B
   user tables. Create only the three C3 stage-01 tables with compatible DDL.
8. `source='wiktionary'` and `license='CC BY-SA'` are the canonical Stage-01 row
   attribution strings for this repository. Do not silently introduce edition-
   specific source names or a license-version choice.
9. No real-build output belongs in Git. Fixture data is synthetic/minimal and
   exists only to make the source contract executable.
10. Do not add stage 02 examples/frequency/resolver-index work, Gate 2 thresholds,
    gap finding, LLM glossing, packaging/release downloading, API/runtime code,
    or user-state work.

## Exact report scaffold

Create before Worker CLOSE:

```markdown
# Slice 3 report

## NARRATIVE
```

Populate only `## NARRATIVE`.

## Required terminal verification before Worker CLOSE

The slice-3 orchestrator will supply `EXPECTED_MAIN_HEAD`.

Run all of:

```sh
: "${EXPECTED_MAIN_HEAD:?STOP: EXPECTED_MAIN_HEAD was not supplied}"

test "$(git branch --show-current)" = "slice/3" || {
  echo "STOP: not on slice/3"; exit 1; }

test "$(git rev-parse main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: main differs from expected main HEAD"; exit 1; }

test "$(git merge-base slice/3 main)" = "$EXPECTED_MAIN_HEAD" || {
  echo "STOP: slice/3 base differs from expected main HEAD"; exit 1; }

make gate

.venv/bin/pytest -q tests/test_build_dict_stage01.py

git diff --check "$EXPECTED_MAIN_HEAD"...HEAD

outside="$({
  git diff --name-only "$EXPECTED_MAIN_HEAD"...HEAD
  git ls-files --others --exclude-standard
} |
grep -vxF \
  -e tools/build_dict.py \
  -e tests/test_build_dict_stage01.py \
  -e tests/fixtures/wiktextract_stage01_en.jsonl \
  -e tests/fixtures/wiktextract_stage01_de.jsonl \
  -e tasks/slice-3.report.md || true)"

test -z "$outside" || {
  echo "STOP: scope violation:"
  printf '%s\n' "$outside"
  exit 1
}

test -f tasks/slice-3.report.md || {
  echo "STOP: tasks/slice-3.report.md missing"
  exit 1
}

test "$(sed -n '1p' tasks/slice-3.report.md)" = "# Slice 3 report" || {
  echo "STOP: report header incorrect"
  exit 1
}

test "$(sed -n '3p' tasks/slice-3.report.md)" = "## NARRATIVE" || {
  echo "STOP: report NARRATIVE heading incorrect"
  exit 1
}
```
