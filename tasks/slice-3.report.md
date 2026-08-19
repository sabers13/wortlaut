# Slice 3 report

Review: PASS (T3, full diff) — independent review of `main...7423cb5147d1419dba4480826accf67243258a2d`

## NARRATIVE

### 1. Implemented CLI and Output Contract
- Implemented `tools/build_dict.py` exposing the exact subcommand CLI:
  `python tools/build_dict.py stage01 --en-jsonl <path> --de-jsonl <path> --output <path>`.
- The transform processes input JSON Lines dumps line-by-line without loading entire datasets into memory, using standard library modules only.
- Output database contains exactly the stage-01-owned PART A tables (`lemma`, `surface_form`, and `sense`), with schema and column definitions compatible with `reference/schema.sql` and readable by `app.dictionary.Dictionary`. Foreign key checks are enabled (`PRAGMA foreign_keys = ON;`).
- Builds to a temporary sibling file and atomically publishes upon complete success. Fails closed on existing output paths, malformed JSON, invalid field types on participating records, and conflicting gender tags, leaving no target file on error.

### 2. Exact Fixture and Gate Numbers
- `tests/test_build_dict_stage01.py` executes 11 targeted unit and contract tests verifying schema compatibility, deterministic IDs and ordering, POS mappings, form derivation, sense limits, failure modes, and CLI execution:
  - `.venv/bin/pytest -q tests/test_build_dict_stage01.py`: 11 passed in 1.20s.
- Project gate execution (`make gate`):
  - `.venv/bin/ruff check .`: All checks passed.
  - `.venv/bin/mypy --strict .`: Success: no issues found in 12 source files.
  - `.venv/bin/pytest -q`: 91 passed in 6.59s (80 existing + 11 new tests).
  - `.venv/bin/python tools/check_agents.py`: AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling).

### 3. Source and License Attribution Policy
- In compliance with AGENTS R11, every persisted `lemma` and `sense` row carries `source='wiktionary'` and `license='CC BY-SA'`.
- English-edition records own English gloss senses (`sense` table). Senses are de-duplicated and capped at the first 3 glosses per lemma with sequential `ord=0, 1, 2...`. German-edition glosses are not written to `gloss_en`.

### 4. Multi-word Surface Form Evidence (`rief an` / `ruft an`)
- Multi-word separable forms `rief an` (past 3sg) and `ruft an` (present 3sg) are extracted verbatim from Wiktextract `forms` and persisted in `surface_form` associated with lemma `anrufen`.
- Verified via `Dictionary.lookup_surface_form("rief an")` and `Dictionary.lookup_surface_form("ruft an")` returning `anrufen`, confirming inflected manual entry support.

### 5. Stop-and-Ask Conditions
- No Stop-and-ask conditions were encountered.

### 6. Deliberately Deferred Fields and Problems
- Lemma grammatical fields `aux`, `governs`, `reflexive`, `separable`, `particle`, and `freq_rank` are left at NULL or schema defaults (0) in stage 01 per C7.
- Stage 02 Tatoeba indexing (`example`, `example_lemma`), frequency computation, gap finding, and LLM glossing are deferred to stages 02–04.
- User-state PART B tables (`note`, `card`, `review_log`) remain absent from dictionary assets per R9 / C3.

### 7. Work Left Undone
- None for slice-3 scope.

## ADR-0004 Stage-01 alignment amendment

### 1. Amended Commit and Attempt Invariant
- Alignment implementation commit SHA: `7423cb5147d1419dba4480826accf67243258a2d`.
- Accepted Attempt-1 tip (historical baseline, unchanged): `7ceea14e39a7c831edfc803632d3c868ea0f3091`.
- Attempt ladder status: The attempt ladder was NOT incremented (remains Attempt 1, aligned with accepted/frozen ADR-0004 D36/D45/D46/D47 governance alignment amendment). The audit counter is NOT incremented.

### 2. Aligned Schema Tables and Columns
The following PART A schema changes from ADR-0004 were aligned in `reference/schema.sql`, `tools/build_dict.py`, and test fixtures:
- `lemma.semantic_ref TEXT NOT NULL UNIQUE`: Canonical versioned stable reference format `lemma:v1:<sha256>`.
- `lemma.plural_none INTEGER NOT NULL DEFAULT 0 CHECK (plural_none IN (0, 1))`: Tri-state noun plural tracking with schema check `CHECK (plural_none = 0 OR plural IS NULL)`.
- `sense.semantic_ref TEXT NOT NULL UNIQUE`: Canonical versioned stable reference format `sense:v1:<sha256>`.
- `sense.source_namespace TEXT NOT NULL`: Explicit upstream provenance namespace (`wiktextract:enwiktionary` in stage 01).
- `sense.source_ref TEXT NOT NULL`: Stable upstream reference (`senseid:<id>`, `senseids:v1:<hash>`, `wikidata:<qid>`, `wikidata-set:v1:<hash>`, or canonical fingerprint `fingerprint:v1:<hash>`).
- `sense_meaning`: Normalized language-neutral meaning table storing DE/EN/FA learner meanings with explicit provenance (`source`, `license`, `language`, `kind`, `ord`, `text`).
- `sense_meaning_derivation`: Normalized table recording consumption edges from source-backed meanings to generated meanings (`generated_meaning_id`, `source_meaning_id`).
- Removed `sense.gloss_en`: Language-neutral `sense` table decoupled from English gloss text (D36).
- Documented in schema comments that all PART A numeric IDs (`lemma.id`, `sense.id`, `sense_meaning.id`, etc.) are local SQLite database keys only and must never be treated as durable semantic identity (R13).

### 3. Attribution and Derivation Policy (R11 / D45 / D46)
- Every persisted `lemma`, `sense`, and `sense_meaning` row carries non-empty `source` and `license` fields.
- Upstream Wiktionary rows carry `source='wiktionary'` and `license='CC BY-SA'` (or explicit variant).
- Derived/generated meaning rows require versioned markers matching `^llm_generated_v[1-9][0-9]*$` and must have valid, non-self, same-sense derivation edges to source-backed meanings. Generated-to-generated derivation edges and cross-sense edges fail closed.
- Build-time validation `validate_sense_meaning_derivations()` enforces all D45 derivation rules on build completion.

### 4. Tri-State Noun Plural Handling (D36 / A9)
- Known plural: `plural = <form>` and `plural_none = 0`.
- Explicit no-plural (e.g. `tags: ["no-plural"]`, "no plural"): `plural = NULL` and `plural_none = 1`.
- Unknown/unattested plural: `plural = NULL` and `plural_none = 0`.
- Contradictory plural state (both explicit form and `no-plural` tag present) fails closed during dictionary build.

### 5. Verified Golden Test Vectors (A15 #5-#6)
- Lemma semantic ref: `["de","Haus","NOUN","das"]` -> `lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436`
- Lemma semantic ref (verb with null gender): `["de","anrufen","VERB","<null>"]` -> `lemma:v1:0694906fb1cb9a54d2a100d341607d922446d187b0bb250546f06c755a229c8b`
- Sense semantic ref: `["lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436","wiktextract:enwiktionary","senseid:en-house-1"]` -> `sense:v1:2fdd041adad74df1dfcd67a3ed5245c54bb03c20e373f989829e30dc755a70e6`

### 6. Targeted Test and Gate Numbers
- Targeted tests:
  - `tests/test_build_dict_stage01.py`: 23 passed in 2.92s
  - `tests/test_dictionary.py`: 14 passed in 3.36s
  - `tests/test_resolve.py`: 22 passed in 0.02s
  - `tests/test_resolve_spacy.py`: 5 passed in 1.60s
  - Subtotal: 64 passed in 7.90s
- Full project gate (`make gate`):
  - `.venv/bin/ruff check .`: All checks passed!
  - `.venv/bin/mypy --strict .`: Success: no issues found in 12 source files
  - `.venv/bin/pytest -q`: 106 passed in 9.03s
  - `.venv/bin/python tools/check_agents.py`: AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling)

### 7. PART-B Scope Declaration
- No PART-B code was modified. Stage-01 is strictly PART-A dictionary build, dictionary reader, and resolver alignment.

## T3 full-diff review

Result: PASS

Reviewed the full risk-labeled slice diff against current `main` and the
alignment-specific delta from
`7ceea14e39a7c831edfc803632d3c868ea0f3091` to
`7423cb5147d1419dba4480826accf67243258a2d`.

Binding contract: `main:tasks/slice-3-alignment.md` (Risk: migration), read
together with `main` WORKFLOW.md §6, AGENTS.md, PROMPTS.md, STATE.md and
ADR-0001/0002/0003/0004. ADR-0004 was treated as ACCEPTED / FROZEN and was not
reopened.

### Preflight

- `main` and `origin/main` = `0deeac58dffc0c042efb5d8c2c4088ed7d7986fd` (expected).
- local and `origin/slice/3` = `7423cb5147d1419dba4480826accf67243258a2d` (expected).
- accepted baseline `7ceea14e...` is an ancestor of the aligned head.
- `slice/3` is NOT merged into `main`.
- Deviation recorded: the working tree carried one pre-existing untracked file,
  `.freebuff/project-id` (external tooling artifact, not created by this review,
  not covered by `.gitignore`). It is unrelated to the slice, was never staged,
  and is the sole reason the literal clean-tree assertions did not evaluate
  empty. Every integrity-relevant preflight condition passed exactly.

### Full changed-file review

Full slice diff `main...slice/3` and alignment delta both touch exactly:

- `app/dictionary.py`
- `app/resolve.py`
- `reference/schema.sql`
- `tasks/slice-3.report.md`
- `tests/conftest.py`
- `tests/fixtures/wiktextract_stage01_de.jsonl`
- `tests/fixtures/wiktextract_stage01_en.jsonl`
- `tests/test_build_dict_stage01.py`
- `tests/test_dictionary.py`
- `tests/test_resolve.py`
- `tools/build_dict.py`

All are inside the brief Allowlist. `tests/test_resolve_spacy.py` was not
modified and was not required. No unbriefed scope, no dependency-manifest
change, no PART-B implementation, no ADR/STATE/plan/backlog edit.

### Stable-ref canonicalization (A2 / A5)

- `compute_lemma_semantic_ref` applies `unicodedata.normalize("NFC", word)`
  before identity, uses the existing canonical POS map and the stored gender
  domain, and the literal `<null>` sentinel.
- Canonical serialization is exactly
  `json.dumps([...], ensure_ascii=False, separators=(",", ":"))` UTF-8, no newline.
- Golden vectors reproduced by direct execution:
  `["de","Haus","NOUN","das"]` ->
  `lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436`;
  `["de","anrufen","VERB","<null>"]` ->
  `lemma:v1:0694906fb1cb9a54d2a100d341607d922446d187b0bb250546f06c755a229c8b`;
  sense tuple ->
  `sense:v1:2fdd041adad74df1dfcd67a3ed5245c54bb03c20e373f989829e30dc755a70e6`.
- Tests assert the literal payload bytes and literal refs, not merely repeatability.
- Ingest normalizes lemma text to NFC before merge identity and persistence, so
  canonically equivalent spellings cannot produce distinct refs.
- Numeric IDs cannot influence any ref: the ref functions take no numeric input,
  and local ids are assigned after identity computation.

### Source-ref and fallback fingerprint (A3 / A4)

- `sense.source_namespace` exists, is NOT NULL, and Stage-01 value is exactly
  `wiktextract:enwiktionary`; `sense.source` remains provenance only.
- Precedence verified: usable `senseid` -> sense-level Wikidata QID -> fallback
  fingerprint. Identifiers are NFC-normalized, stripped, blank-discarded and
  deduplicated; multiples are sorted and canonically serialized to
  `senseids:v1:` / `wikidata-set:v1:`. Blank or wrong-typed identifiers fall
  through to the next declared path rather than binding a blank ref.
- The fallback hashes a canonical projection, never raw JSON bytes. Only the
  eight declared identity-bearing fields participate; `raw_glosses`, examples,
  translations, synonym/antonym linkage, categories and Wikipedia links were
  executably confirmed to have no effect on the fingerprint.
- Canonicalization applies NFC, casefold, Unicode `P*` -> ASCII space,
  whitespace collapse and strip; dicts use lexical key order; lists are
  canonicalized, empty-discarded, deduplicated and sorted by canonical JSON.
- Whitespace-only and punctuation-only edits leave the ref unchanged; a genuine
  lexical gloss change alters it.
- Asset-local numeric IDs cannot enter the projection: its only input is the raw
  upstream Wiktextract record, and `lemma.id` / `sense.id` / `sense_meaning.id`
  do not exist at that point.
- Collision handling fails closed: a build-scoped seen-set plus the
  `sense.semantic_ref` UNIQUE constraint reject two participating source senses
  that collapse to the same
  `(lemma.semantic_ref, source_namespace, source_ref)`. A degenerate empty
  projection therefore cannot silently bind unrelated senses within a lemma.

### Language-neutral senses and D36 `sense_meaning` (A6 / A7)

- One retained raw Wiktextract `senses[]` distinction produces exactly one
  `sense` row; multiple English gloss strings for that distinction become
  multiple `sense_meaning` rows, verified end-to-end (1 sense / 3 meanings).
- The three-English-meaning cap is per lemma and total, applied over retained
  raw senses in source order and their nonblank glosses in source order with
  text deduplication; a `sense` row is created only when at least one meaning
  survives the cap; `sense.ord` is sequential from 0 in retained source order.
- `sense_meaning` matches the required DDL exactly: id, `sense_id` FK with
  `ON DELETE CASCADE`, language, `kind` CHECK
  `('definition','synonym','translation')`, ord, text, NOT NULL source and
  license, `UNIQUE(sense_id, language, kind, ord)` and
  `ix_sense_meaning(sense_id, language, ord)`. There is no closed DE/EN/FA
  language CHECK or FK, proven by inserting a `fa` row.
- Stage-01 rows are `language='en'`, `kind='translation'`, deterministic `ord`,
  `source='wiktionary'`, `license='CC BY-SA'`.
- `sense.gloss_en` no longer exists in the Stage-01 output schema.
- German-edition text is not heuristically bound as a Stage-01 learner meaning;
  only the English edition contributes senses.

### D45 derivations (A8)

- DDL matches the brief exactly, including `WITHOUT ROWID`, the composite PK,
  `ON DELETE CASCADE` / `ON DELETE RESTRICT`, and the self-edge CHECK.
- The generated marker is `^llm_generated_v[1-9][0-9]*$`. Executed directly:
  `llm_generated_v0` and `llm_generated_v01` are rejected; `v1`, `v2`, `v10` are
  accepted. The earlier report prose that read `[0-9]+` was report-only and has
  been corrected; the code was always correct.
- `validate_sense_meaning_derivations` enforces existence of both sides, the
  generated marker on the generated side, a non-generated source side, nonblank
  source and license on the source side, identical `sense_id`, no self edge and
  no generated->generated edge. Synthetic valid and invalid rows prove each rule.
- The validator runs inside the build transaction before `conn.close()` and
  before the atomic `temp_path.replace(out_path)` publish; on failure the
  temporary sibling is unlinked and no asset is published. Zero edges is valid.

### Tri-state plural (A9)

- Schema carries `plural_none INTEGER NOT NULL DEFAULT 0 CHECK (plural_none IN (0,1))`
  and the table CHECK `plural_none = 0 OR plural IS NULL`.
- All three states verified against a real built asset: Haus -> `Häuser` / 0;
  Milch -> NULL / 1; Berlin -> NULL / 0. Absence of plural evidence never
  implies `plural_none=1`.
- The only accepted explicit no-plural evidence is the literal entry-level
  Wiktextract `no-plural` tag. A simultaneous extracted plural form and
  `no-plural` tag fails closed as contradictory source evidence.

### Per-asset numeric IDs (A10)

`lemma.id`, `sense.id` and `sense_meaning.id` remain local asset keys. They are
documented as such in `reference/schema.sql` and the Stage-01 schema comments,
are never serialized or hashed into a stable ref, and are not used as semantic
tie-breakers on any path the brief governs.

### D46 resolver binding (A11 / A12)

- `LemmaRecord` gains `semantic_ref` and `freq_rank`; `SenseRecord` carries local
  id, `lemma_id`, `ord` and `semantic_ref`; `LookupProtocol` gains `lookup_senses`.
- `ComponentBinding` is frozen and carries lemma text, pos, gender, freq_rank,
  `lemma_ref`, `sense_ref`, `sense_ord`, plus optional local ids as
  current-asset caches only.
- Preceding-component ordering is exactly freq_rank ascending NULL last, pos
  ascending, gender ascending NULL last, `lemma.semantic_ref` lexical ascending —
  in the pure resolver sort key and in the SQL used by
  `lookup_exact` / `lookup_surface_form`. No numeric ID tie-break remains on
  either path.
- Head selection preserves the accepted NOUN-first resolver semantics and then
  falls back to the same stable tuple instead of asset-local id order.
- Source-sense choice is exactly `(sense.ord, sense.semantic_ref)`, verified by a
  test that distinguishes two senses sharing `ord=0`.
- Binding is refused when a stable lemma ref or sense ref is blank/absent; the
  resolver then continues the already-defined deterministic path and ultimately
  falls through to the `needs_gloss` stub rather than fabricating a text-only or
  numeric-ID-only binding.
- `Ref.component_bindings` carries the ordered vector left-to-right with the
  grammatical head last, including through multi-component recursion; the bare
  component strings remain only as a compatibility field.

### Schema and read seam (A13 / A14)

- `reference/schema.sql` PART A now matches the actual Stage-01 build schema for
  all five emitted tables; `surface_form`, `example` and `example_lemma` retain
  their existing stage ownership. PART B was deliberately not repaired or
  implemented and remains the later slice-7 owner.
- `Dictionary` opens the aligned asset read-only via `file:...?mode=ro`; the
  read-only enforcement test still rejects an INSERT.
- `LemmaEntry` exposes `semantic_ref` and `freq_rank`; `SenseEntry` exposes the
  language-neutral identity (id, lemma_id, semantic_ref, source_namespace,
  source_ref, ord, register, source, license) and no longer exposes `gloss_en`.
- `MeaningEntry` plus `get_meanings_for_sense` / `get_meanings_for_lemma` provide
  deterministic localized retrieval ordered by language, kind, ord, then local id
  as the final within-asset fallback.
- No PART-B table or user-DB logic was pulled into `app.dictionary`.

### Stage-01 operational guarantees (A1)

CLI unchanged; streaming line-by-line JSONL; standard library only (argparse,
hashlib, json, re, sqlite3, sys, tempfile, unicodedata); no network, API or LLM
path; refusal to overwrite an existing output; temporary sibling plus atomic
publish with cleanup on failure; fail-closed malformed participating input;
deterministic row construction proven by source-order reversal; source/license
attribution retained; multi-word `rief an` / `ruft an` still resolve; no PART-B
and no example/stage-02 tables emitted; no new dependency.

### Regression compatibility

Exact lookup, surface lookup, gender disambiguation (`der See` / `die See`),
separable-verb handling, the ADR-verified
`Krankenversicherungskarte -> [kranken, versicherung, karte]` split with `die`
inherited from `Karte`, and the Gate-1 real-spaCy cases all still pass. The
`gloss_en` assertions were replaced by equivalent `sense_meaning` assertions
rather than dropped, and the compound-split assertion was widened, not weakened.
No pre-existing assertion was deleted or relaxed.

### Fresh executable verification (at `7423cb51`)

- `tests/test_build_dict_stage01.py`: 23 passed
- `tests/test_dictionary.py`: 14 passed
- `tests/test_resolve.py`: 22 passed
- `tests/test_resolve_spacy.py`: 5 passed
- `git diff --check 7ceea14e..HEAD`: clean
- `make gate`: ruff `All checks passed!`; `mypy --strict` `Success: no issues
  found in 12 source files`; `pytest -q` `106 passed`; `check_agents.py`
  `AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture
  coupling)`. Exit 0.

### Non-blocking observations

None of the following is a binding-contract violation, and none affects
production behaviour or any required proof. They are recorded for the owning
follow-up slice, not as review blockers.

- N1 — `tests/conftest.py`, `create_test_db`: the hand-expanded `lemma_rows`
  tuples carry 24 elements while the INSERT binds 23, skipping index 8. Exactly
  one column is mis-bound: `genitive_sg` receives the constant `0` (stored as
  `'0'`) and the intended `'Sees'` / `'Hauses'` values are dropped. Every other
  column lands correctly. No test asserts `genitive_sg` on this synthetic
  fixture, and the real Stage-01 path independently proves
  `genitive_sg == "Hauses"` against a built asset, so no required behaviour is
  left unproven. The baseline fixture stored NULL here and asserted nothing, so
  this is a new fixture-data defect rather than a weakened assertion.
- N2 — `compute_sense_fallback_ref` passes numeric scalars through verbatim, so a
  number nested inside a projected dictionary (`form_of`, `alt_of`,
  `compound_of`) participates in the fingerprint. This does not breach the brief:
  the exclusion is of asset-local numeric IDs, which cannot reach the projection
  because its only input is the raw upstream record. All four briefed stability
  properties hold. It remains a residual cross-version continuity risk if an
  upstream edition ever adds a volatile numeric field to those structures, and
  ambiguity still fails closed.
- N3 — Two test docstrings over-claim coverage. `test_tri_state_noun_plural`
  cites A15 #24-#27 but exercises only the contradictory case; #24-#26 are
  genuinely covered in `test_stage01_build_and_dictionary_compatibility`.
  `test_d46_preceding_component_selection_order` cites the full four-level tuple
  but only exercises the freq_rank level; the remaining levels are verified by
  direct inspection of the sort key and the SQL ORDER BY clauses.

No unreviewed risk finding remains.
