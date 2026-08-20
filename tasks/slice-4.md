# Slice 4 — Gate 2: real-textbook Stage-01 dictionary coverage

Task:        Execute ADR-0002 §6 order 5 / ADR-0001 §13 Gate 2 against a real Stage-01 dictionary asset and 200–300 vocabulary headwords from one real German-textbook unit. Produce a deterministic coverage receipt and misses list. This slice is a design gate: baseline coverage `<85%` returns to governance; `85% <= coverage < 95%` requires exactly one separately orchestrated splitter/fuzzy remedy cycle in this same slice before a rerun; `coverage >=95%` continues directly. No stage-02 work may start before Gate 2 reaches its accepted decision point.

Depends:     slice-3

Precondition: slice-3 is accepted, merged and closed. The slice-4 orchestrator supplies all four non-repository inputs before dispatch: `GATE2_EN_JSONL=<real English-edition Wiktextract JSONL>`, `GATE2_DE_JSONL=<real German-edition Wiktextract JSONL>`, `GATE2_WORDS_FILE=<UTF-8 file containing 200–300 unique vocabulary headwords from one real textbook unit, one entry per line>`, and non-empty `GATE2_UNIT_LABEL=<human-readable textbook/unit label>`. Those source files remain local and uncommitted. Missing/invalid inputs block dispatch rather than becoming synthetic substitutes.

Allowlist:
- `tools/gate2_coverage.py`
- `tests/test_gate2_coverage.py`
- `tasks/slice-4.report.md`

Acceptance:
(C1) Add `tools/gate2_coverage.py`, a deterministic local-only measurement CLI:

`python tools/gate2_coverage.py --dictionary <stage01.sqlite> --words <words.txt> --misses-out <misses.txt>`

It imports and uses the canonical `app.dictionary.Dictionary` and `app.resolve.resolve_word`; it does not copy or reimplement resolution logic.

(C2) The word file is UTF-8 and, after stripping leading/trailing whitespace and rejecting blank lines, must contain between 200 and 300 entries inclusive. Duplicate normalized input lines are a hard error rather than being silently removed because changing the denominator would bias the gate.

(C3) Textbook entries are evaluated exactly as follows. Strip surrounding whitespace. If an entry has the exact form `der <term>`, `die <term>`, or `das <term>` with a non-empty remainder, evaluate `<term>` with that article passed as the resolver gender hint. Otherwise evaluate the complete stripped entry unchanged. Do not stem, fuzzy-match, translate, spell-correct, split punctuation, or otherwise massage baseline input.

(C4) Resolve every entry through `resolve_word(term, dictionary, gender=gender_hint)`. An entry is a hit iff at least one returned reference has `status` equal to `resolved` or `derived_compound`. It is a miss iff no returned reference has either status. Preserve input order in the misses output.

(C5) The CLI prints machine-readable JSON containing at least: `total`, `hits`, `misses`, exact unrounded `coverage_ratio`, a display percentage, and the misses-output path. Threshold decisions use integer arithmetic, never rounded display percentages:
- `100 * hits < 85 * total` -> `GOVERNANCE_REDESIGN_REQUIRED`
- `85 * total <= 100 * hits < 95 * total` -> `REMEDY_REQUIRED`
- `100 * hits >= 95 * total` -> `CONTINUE`

(C6) The CLI refuses to overwrite an existing `--misses-out` path. Measurement failure leaves no completed misses file. It performs no network call, download, LLM/API call, secret read, user-DB mutation, or dictionary mutation.

(C7) `tests/test_gate2_coverage.py` proves: 200 and 300 inputs are accepted; 199/301 rejected; blank and duplicate input rejected; article/gender normalization; exact hit; surface-form hit; derived-compound hit using a fully stable D46 component binding; miss classification; deterministic misses order; no rounded-threshold error at both 85% and 95% boundaries; and output-collision failure.

(C8) For the real Gate-2 run, first build a fresh local Stage-01 asset using the accepted slice-3 CLI:

`python tools/build_dict.py stage01 --en-jsonl "$GATE2_EN_JSONL" --de-jsonl "$GATE2_DE_JSONL" --output build/gate2/stage01.sqlite`

`build/` is already ignored. Do not commit the real Wiktextract dumps, textbook word list, generated SQLite asset, or generated misses file.

(C9) Run the coverage CLI against that fresh real asset and the supplied real textbook-unit list. Record in `tasks/slice-4.report.md`: unit label; input word count; hits; misses; exact ratio; display percentage; threshold decision; SHA-256 of the textbook word-list file; Stage-01 lemma/sense/sense_meaning row counts; exact misses count; and the complete command/gate evidence. Do not record private absolute machine paths.

(C10) Gate decision is mechanical:
- baseline `<85%`: write `Decision: GOVERNANCE_REDESIGN_REQUIRED`, commit/push the measurement/report, then STOP. This is an ADR-0002 design-gate outcome, not a WORKFLOW §5 implementation failure. Stage 02 is forbidden.
- baseline `85% <= coverage <95%`: write `Decision: REMEDY_REQUIRED`, commit/push the baseline measurement/report, then STOP and return the exact misses and measurement evidence to this slice's orchestrator. Do NOT invent or implement the fuzzy/splitter remedy in this worker. The orchestrator must issue one explicit remedy amendment/dispatch inside slice-4, after which Gate 2 is rerun exactly once. This branch is a design-gate branch, not a WORKFLOW §5 failure.
- baseline `>=95%`: write `Decision: CONTINUE`; no remedy is permitted or needed.
- after the one authorized 85–<95 remedy cycle: rerun once; result `<85%` -> governance redesign; result `>=85%` -> record the rerun and continue, exactly as ADR-0002 §6 specifies. There is no second Gate-2 remedy cycle.

(C11) `make gate` and `git diff --check` pass. Real input/output artifacts stay untracked/ignored and outside the commit. No existing application/schema code changes are permitted by this baseline brief.

(C12) `tasks/slice-4.report.md` contains:
- baseline input/evidence;
- baseline decision;
- if applicable, a clearly separated one-time remedy/rerun amendment authored only after orchestrator dispatch;
- Stop-and-ask conditions;
- work left undone;
- explicit statement that Gate 2 is ADR-0002 §6 order 5 and not the WORKFLOW §5 retry ladder.

Stop-and-ask:
- any `Depends:` verification fails;
- one of the four required Gate-2 inputs is absent;
- the real textbook list is not 200–300 unique nonblank entries;
- the word list is not from one real textbook unit as attested by the supplied `GATE2_UNIT_LABEL`;
- the real Wiktextract inputs cannot be consumed by accepted Stage-01 without changing slice-3's contract;
- Stage-01 build fails;
- satisfying baseline measurement requires changing `app/`, `reference/schema.sql`, dependencies, ADRs, AGENTS, WORKFLOW, or any path outside the Allowlist;
- baseline result is 85–<95 and no explicit orchestrator remedy amendment has yet been issued;
- a requested operation would overwrite an existing real/generated input or output;
- the Gate-2 procedure cannot classify an observed vocabulary entry without inventing preprocessing not specified here.

Risk:        none

Why-risk:    WORKFLOW.md §6 path lookup: the baseline Gate-2 allowlist contains one maintainer-only measurement tool, its tests, and its report. It touches no schema/migration, auth/security code, public external API contract, destructive transform, user data, or existing data artifact. The tool refuses output overwrite. If the 85–<95 branch requires an `app/` remedy, the orchestrator must author a separate explicit remedy amendment and recompute its Risk label before dispatch.

Model:       gemini-flash / T1 / low

Why:         WORKFLOW.md §4: the baseline Gate-2 procedure is fully specified, deterministic, tightly allowlisted, and automatically verified; the threshold decision is integer arithmetic with no implementation judgment. The branch that might require design/code judgment is deliberately returned to the orchestrator rather than delegated.

Fallback:    codex-low / T1 / low

## Worker implementation constraints

1. Read `app/resolve.py`, `app/dictionary.py`, `tools/build_dict.py`, ADR-0001 Gate 2, ADR-0002 §6, AGENTS R2/R3/R9/R11/R13, and this brief before editing.
2. Do not edit `app/resolve.py`, `app/dictionary.py`, `tools/build_dict.py`, schema, dependencies, or governance files.
3. The real textbook word list and real Wiktextract dumps are local evaluation inputs, not repository fixtures.
4. Build the real Stage-01 asset under `build/gate2/`; never commit it.
5. Do not download data automatically.
6. Do not implement stage 02.
7. Do not apply fuzzy matching or splitter changes during baseline measurement.
8. The 85–<95 branch returns to the slice-4 orchestrator for one explicit remedy amendment. That return is not a WORKFLOW §5 failure.
9. The `<85%` branch returns to governance. Do not attempt to rescue the design.
10. Preserve the exact ADR-0002 thresholds and sequence.

## Required report scaffold

Create:

```markdown
# Slice 4 report

## NARRATIVE

### Gate-2 baseline
Unit:
Words SHA-256:
Total:
Hits:
Misses:
Coverage ratio:
Display coverage:
Decision:

### Gate-2 remedy/rerun
Not applicable unless baseline is 85–<95 and an explicit orchestrator remedy amendment is later issued.

### Stop-and-ask
None or exact condition.

### Work left undone
```

Populate from executable evidence only.

## Failure-1 retry amendment — real Wiktextract multi-gender records

### Attempt-1 evidence

Attempt 1 reached the required real Stage-01 build and failed before Gate-2
measurement with:

Error during stage 01 build: Conflicting gender tags ['der', 'die'] for 'April'

The participating real German-edition Wiktextract record had:

- word: April
- pos: name
- tags containing both feminine and masculine

Attempt 1 otherwise had:

- Gate-2 implementation tests: 18 passed
- full make gate: PASS
- 124 total pytest tests passed
- no app/schema/governance modification
- no Gate-2 measurement occurred

This is WORKFLOW §5 Failure 1, not an ADR-0002 Gate-2 threshold branch.

### Retry contract

For Attempt 2 only, extend the implementation allowlist to:

- tools/gate2_coverage.py
- tests/test_gate2_coverage.py
- tasks/slice-4.report.md
- tools/build_dict.py
- tests/test_build_dict_stage01.py

The historical slice-3 brief remains unchanged.

The following slice-3 Stage-01 behavior is superseded for the current
implementation:

Old behavior:
multiple supported entry-level gender tags are a hard record error.

New required behavior:
a participating Wiktextract record containing more than one distinct supported
gender tag must deterministically expand into one lemma identity per supported
gender.

Supported mapping remains exactly:

- masculine -> der
- feminine -> die
- neuter -> das

Rules:

1. Zero supported gender tags:
   retain the existing single identity with gender NULL.

2. Exactly one supported gender:
   retain the existing single identity with that gender.

3. Multiple distinct supported genders:
   create/merge one accumulator identity for each distinct gender.

4. Canonical expansion order, whenever iteration order matters:
   der, die, das.

5. Identity remains:
   (word, canonical_pos, gender)

6. The same source-backed record data applies to every expanded identity:
   - IPA
   - no-plural evidence
   - forms
   - form-derived fields
   - English-edition senses/meanings
   - source/license attribution

7. Do not synthesize any value absent from the source record.

8. Do not discard or skip a real record merely because it has multiple supported
   gender tags.

9. Existing merge semantics still apply if another source record resolves to the
   same (word, canonical_pos, gender) identity.

10. All other Stage-01 fail-closed behavior remains unchanged:
    malformed JSON, invalid participating field types, output collision,
    contradictory plural evidence, invalid derivation data, etc.

### Required regression tests

Attempt 2 must replace the obsolete conflicting-gender-fails test with executable
coverage proving:

- a real-shape record:
    word="April"
    pos="name"
    lang_code="de"
    tags=["feminine", "masculine", "noun"]
  builds successfully;

- the resulting dictionary has exactly two April/PROPN lemma identities:
    gender der
    gender die

- both identities preserve the applicable source-backed record data;

- deterministic output is preserved;

- no NULL-gender duplicate is created for that record;

- existing single-gender and zero-gender behavior remains unchanged.

### Retry classification

Attempt 2 remains:

Model: gemini-flash / T1 / low
Fallback: codex-low / T1 / low
Risk: none

Why-risk:
tools/build_dict.py remains maintainer-only offline build tooling. It creates a
new output, refuses overwrite, does not modify source dumps or user data, does
not touch schema/migrations/auth/public runtime API, and therefore matches no
WORKFLOW §6 risk row.

Attempt 2 must rerun the fresh real Stage-01 build from the same supplied real
Gate-2 inputs.

Do not filter the source JSONL to remove multi-gender records.

Do not condition any preprocessing on the 200-word textbook list.

If another real-data incompatibility appears, STOP and return it as Failure 2.
Do not self-retry.

## Failure-2 escalation amendment — fallback sense identity collision

### Attempt-2 evidence

Attempt 2 was the same-tier Failure-1 retry.

The multi-gender repair passed its executable tests and allowed the real
Stage-01 build to progress beyond the Attempt-1 `April` failure.

The real Stage-01 build then stopped before Gate-2 measurement with:

Duplicate sense semantic_ref
'sense:v1:e7b80a9fedccd6026102882cf06798f838d9654bcf85624489104b69fc726059'
for lemma 'Ahnenpasses'

The participating English-edition Wiktextract record contained two distinct
raw senses:

1. genitive singular of `Ahnenpass`
   form_of word = `Ahnenpass`

2. genitive singular of `Ahnenpaß`
   form_of word = `Ahnenpaß`

The existing fallback string canonicalization applies Unicode `casefold()`.
That maps German `ß` to `ss`, causing both distinct linkage spellings to
collapse to the same canonical `form_of` value and therefore the same fallback
source_ref and sense.semantic_ref.

No Gate-2 coverage measurement occurred.

This is WORKFLOW §5 Failure 2.

### Escalation

WORKFLOW §5 now requires escalation one tier.

Attempt 3:

Model: claude-code / T2 / high
Fallback: codex / T2 / high
Risk: none

There must not be another T1 implementation attempt.

Why:
the repair remains inside known Stage-01 architecture but now affects durable
D47 sense identity canonicalization and must preserve existing stable-ref,
determinism, provenance, and fail-closed semantics simultaneously.

Why-risk:
the implementation allowlist still touches maintainer-only build tooling,
tests, the Gate-2 measurement tool, and its report. It touches no schema or
migration file, auth/security path, public runtime API path, destructive user
data transform, or existing mutable data artifact. No WORKFLOW §6 risk row
matches.

### Binding identity repair for Attempt 3

The duplicate/ambiguity guard MUST remain fail-closed.

Do NOT:
- ignore duplicate semantic refs;
- discard either source sense;
- merge the two senses;
- select one arbitrarily;
- use source line number as identity;
- use source list position / sense ordinal as identity;
- add a collision counter;
- hash raw JSON bytes;
- condition identity on the Gate-2 textbook word list.

Those approaches create unstable or order-dependent cross-version identities
and violate D47.

The upstream source-ref selection priority remains unchanged:

1. usable senseid;
2. usable sense-level Wikidata;
3. fallback canonical fingerprint.

`senseid:` and `wikidata:` source-ref behavior is unchanged.

#### Fallback versioning

Preserve the existing `fingerprint:v1:` algorithm unchanged for fallback
senses whose included projection contains none of these identity-bearing
linkage fields:

- form_of
- alt_of
- compound_of
- taxonomic

This minimizes unnecessary stable-ref churn for ordinary fallback senses.

When at least one of those identity-bearing linkage fields survives projection,
use a new deterministic:

`fingerprint:v2:<lowercase 64-char sha256>`

Do NOT rewrite already-defined `fingerprint:v1` semantics.

#### fingerprint:v2 projection fields

Use the same allowed top-level distinction fields as the accepted A4 contract:

- glosses
- tags
- topics
- form_of
- alt_of
- compound_of
- qualifier
- taxonomic

No new raw-data field is added merely to rescue a collision.

Excluded fields remain excluded as under A4.

#### fingerprint:v2 canonicalization

Container canonicalization remains deterministic:

- dictionary keys sorted lexically;
- lists canonicalized element-by-element;
- canonical empties removed;
- duplicate canonical elements removed;
- remaining list elements sorted by canonical JSON encoding;
- final projection serialized using:
  json.dumps(
      projection,
      ensure_ascii=False,
      sort_keys=True,
      separators=(",", ":"),
  )
- UTF-8;
- no trailing newline.

For the NON-linkage fields:

- glosses
- tags
- topics
- qualifier

retain the existing A4 cosmetic string normalization:

1. NFC;
2. casefold();
3. Unicode punctuation-category characters -> ASCII space;
4. collapse whitespace;
5. strip.

For the identity-bearing linkage fields:

- form_of
- alt_of
- compound_of
- taxonomic

canonicalize all contained strings conservatively:

1. NFC;
2. collapse whitespace runs to one ASCII space;
3. strip leading/trailing whitespace;
4. preserve lexical case;
5. preserve punctuation/code-point spelling;
6. DO NOT casefold.

This means, for example:

`Ahnenpass` != `Ahnenpaß`

inside `form_of`.

The goal is to preserve source-backed lexical linkage distinctions while still
making container representation deterministic.

#### Required invariants

- compute_sense_semantic_ref remains unchanged.
- lemma.semantic_ref remains unchanged.
- source_namespace remains unchanged.
- numeric IDs remain local-only.
- source/license behavior remains unchanged.
- malformed/ambiguous duplicate refs still fail closed.
- if two genuinely different source senses STILL produce the same final
  source_ref under the new contract, the real build must STOP rather than guess.

### Required Attempt-3 tests

Attempt 3 must add executable regression coverage proving:

1. Existing `fingerprint:v1` cosmetic-stability tests remain passing for
   fallback senses without identity-bearing linkage fields.

2. A fallback sense containing `form_of` uses `fingerprint:v2:`.

3. These two source senses generate different source_ref values:

   {"glosses":["genitive singular of Ahnenpass"],
    "tags":["form-of","genitive","singular"],
    "form_of":[{"word":"Ahnenpass"}]}

   {"glosses":["genitive singular of Ahnenpaß"],
    "tags":["form-of","genitive","singular"],
    "form_of":[{"word":"Ahnenpaß"}]}

4. Their sense.semantic_ref values are also distinct for the same lemma.

5. A real-shape `Ahnenpasses` record containing both senses builds successfully
   and persists two distinct senses when both survive the existing learner-
   meaning cap.

6. Reordering keys/list metadata does not change either v2 ref.

7. NFC-equivalent linkage spelling gives the same v2 ref.

8. Linkage lexical spelling differences are not erased by casefold or
   punctuation removal.

9. Existing duplicate-ref fail-closed test remains; do not weaken or delete it.

10. Multi-gender regression from Failure 1 remains passing.

### Real-data retry rule

Attempt 3 must rerun the real Stage-01 build using exactly the same owner-supplied
Gate-2 inputs.

It must not edit or preprocess those local JSONL files.

If another real-data incompatibility occurs:
STOP and return exact evidence.
Do not invent another repair inside the worker.

Gate-2 threshold branches remain unchanged and have still not been reached.
