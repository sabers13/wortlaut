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

## Failure-3 same-tier retry amendment — canonical-equivalent fallback senses

### Attempt-3 evidence

Attempt 3 was the first T2 implementation attempt after two T1 failures.

The Failure-2 fingerprint:v2 repair progressed the real Stage-01 build beyond
the Ahnenpasses collision.

The next real-build failure was:

Duplicate sense semantic_ref
'sense:v1:499f3666879448681186d3242b7569e700ef731408b3be7bfdd5c3a64ab0054b'
for lemma 'Freimaurer'

Read-only diagnosis proved one English Wiktextract record contained two senses:

Sense 0:
- glosses = ["Freemason"]
- tags = ["masculine", "strong"]
- links = [["Freemason", "Freemason"]]

Sense 1:
- glosses = ["freemason"]
- tags = ["masculine", "strong"]
- links = [["freemason", "freemason"]]

Both currently produce exactly:

fingerprint:v1:acaf6bce09b1e3d64f44e3766fb55f5c176b03cacb9e3bc7f7c6f34dd63b01bc

and therefore the same sense.semantic_ref.

The only raw differences are:
- capitalization in glosses;
- capitalization in links.

`links` is deliberately excluded from the accepted A4 fallback projection.

For ordinary fingerprint:v1 fields, A4 intentionally applies casefold and
cosmetic punctuation/whitespace normalization.

Therefore these two senses are canonical-equivalent under the accepted v1
identity contract. This is NOT evidence that fingerprint:v1 needs another
identity expansion.

No Gate-2 coverage measurement occurred.

This is the first T2 implementation failure.

### Retry classification

WORKFLOW §5 requires one same-tier T2 retry before T3 escalation.

Attempt 4:

Model: claude-code / T2 / high
Fallback: codex / T2 / high
Risk: none

If Attempt 4 fails as an implementation attempt, that is the second T2 failure
and the next implementation dispatch escalates to T3.

### Fingerprint contracts remain unchanged

Attempt 4 MUST NOT modify:

- fingerprint:v1 canonicalization;
- fingerprint:v2 canonicalization;
- fingerprint:v1/v2 version-selection rules;
- senseid source-ref behavior;
- Wikidata source-ref behavior;
- compute_sense_semantic_ref;
- lemma.semantic_ref;
- source_namespace.

The Ahnenpass/Ahnenpaß v2 regression must remain passing.

The final duplicate/ambiguous stable-ref guard remains fail-closed.

### New canonical-duplicate rule

A narrow coalescing rule is permitted ONLY while processing the `senses[]`
array of one participating English-edition Wiktextract record.

For two raw senses within that SAME source record:

1. Both must resolve through the fallback path.
   Their source refs must begin with:
   - `fingerprint:v1:`
   or
   - `fingerprint:v2:`

2. Neither may be using:
   - senseid:
   - senseids:v1:
   - wikidata:
   - wikidata-set:v1:

3. Compute the complete canonical fallback projection bytes using the exact
   canonicalization/version rules already used to create their fallback refs.

4. If:
   - fallback version is the same;
   - canonical projection bytes are byte-for-byte identical;
   - resulting fallback source_ref is identical;

   then they represent one canonical-equivalent source distinction for Stage-01
   persistence.

5. Keep the FIRST occurrence in the raw `senses[]` source order.

6. Skip each later canonical-equivalent duplicate from:
   - sense-row creation;
   - semantic-ref duplicate checking;
   - learner-meaning creation.

7. The retained first sense keeps its original source-backed learner-meaning
   text exactly as accepted Stage-01 currently does.

For the diagnosed Freimaurer source order, this means:

retained meaning:
  Freemason

later cosmetic duplicate:
  freemason

is not persisted as a second sense/meaning.

This is deterministic because A6 already treats raw `senses[]` source order as
normative for retained source senses and learner meanings.

### Critical scope boundary

This coalescing rule applies ONLY to duplicate fallback senses inside the SAME
participating source record.

Do NOT coalesce duplicate refs across separate source records.

Do NOT coalesce explicit upstream senseid/Wikidata duplicates.

Do NOT coalesce two fallback senses whose canonical projection bytes differ.

Any such duplicate final semantic_ref remains a hard BuildDictError.

Do NOT:
- add links to the A4 fingerprint;
- add raw source line number;
- add sense array index to identity;
- add collision counters;
- hash raw JSON;
- choose a duplicate based on Gate-2 vocabulary;
- change the textbook inputs;
- disable duplicate stable-ref validation.

### Required Attempt-4 tests

Attempt 4 must prove:

1. The real-shape Freimaurer record with both senses builds successfully.

2. Exactly ONE persisted Freimaurer sense is produced for those two
   canonical-equivalent raw senses.

3. Exactly ONE English learner meaning from that pair is persisted.

4. The retained learner meaning is the first raw source text:
   `Freemason`.

5. The retained source_ref remains the existing expected fingerprint:v1 value;
   no new fingerprint version is introduced.

6. Repeated fallback senses within one raw record that differ only by accepted
   v1 cosmetic normalization coalesce.

7. Canonical-equivalent fingerprint:v2 senses within one source record also
   coalesce if their complete v2 canonical projection bytes are identical.

8. Two fallback senses within one source record whose canonical projection
   bytes differ do NOT coalesce.

9. Duplicate explicit `senseid` values continue to fail closed.

10. Duplicate explicit Wikidata identity continues to fail closed or preserves
    the existing fail-closed behavior.

11. A duplicate fallback source_ref appearing across separate source records is
    NOT silently coalesced; existing global duplicate validation remains
    authoritative.

12. Ahnenpass vs Ahnenpaß still produces two distinct fingerprint:v2 source
    refs and two distinct semantic refs.

13. April multi-gender regression remains passing.

14. Existing fingerprint:v1 cosmetic-stability tests remain unchanged and pass.

15. Existing general duplicate-semantic-ref failure test remains; do not weaken
    or delete it.

### Real-data retry

Attempt 4 reruns the real Stage-01 build exactly once using the same supplied
Gate-2 inputs.

Do not preprocess or alter those inputs.

If the real build fails again:
STOP.
Do not repair further in that worker.

That failure is the second T2 failure and returns to the orchestrator for T3
escalation.

If the build succeeds, continue to the existing slice-4 Gate-2 baseline
measurement exactly once.

The 85% / 95% threshold branches remain unchanged.

## Failure-4 T3 escalation amendment — ambiguous upstream sense identifiers

### Attempt-4 evidence

Attempt 4 was the second and final T2 implementation attempt.

The canonical-equivalent fallback-sense repair progressed the real Stage-01
build beyond the prior Freimaurer collision.

The next real-build failure was:

Duplicate sense semantic_ref
'sense:v1:01e0eddbab389880247bc574469f9b58e12dc6e647007984845c6c8c95bfc9bc'
for lemma 'Konjunktion'

The participating English-Wiktionary source record contained two distinct raw
senses with the same explicit upstream sense identifier:

sense 0:
- glosses = ["conjunction"]
- senseid = ["de:grammar"]

sense 1:
- glosses = ["conjunction", "coordinating conjunction"]
- tags = ["specifically"]
- senseid = ["de:grammar"]

The two senses are not canonical-equivalent fallback duplicates.

The upstream value `de:grammar` is therefore ambiguous within this lemma:
it is present, but it does not uniquely identify one semantic distinction.

No Gate-2 coverage measurement occurred.

Attempt 4 is T2 Failure 2.

### Escalation classification

WORKFLOW §5 requires escalation to T3.

Attempt 5:

Model: gpt-5.6-terra / T3 / high
Fallback: opus-5 / T3 / high
Risk: none

Why:
the next repair affects interpretation of D47 durable source-side semantic
identity and requires simultaneous reasoning about explicit identifier priority,
ambiguity scope, fallback stability, source-order independence, the existing
fingerprint contracts, and cross-version identity.

There is no further T2 implementation attempt.

If Attempt 5 fails as an implementation attempt, WORKFLOW §5 reaches its T3
ceiling. Do not retry T3. Return to the orchestrator as a design problem.

Why-risk:
the implementation allowlist remains maintainer-only offline build tooling,
tests, Gate-2 measurement tooling and report. No schema/migration file,
auth/security path, externally callable runtime API, destructive user-data
operation, or existing mutable data artifact is touched. No WORKFLOW §6 risk
row matches.

### Interpretation of "usable upstream identifier"

The existing identity priority remains:

1. usable senseid / senseids candidate;
2. usable sense-level Wikidata candidate;
3. deterministic fallback fingerprint.

The word `usable` is now made executable.

An explicit source identifier is usable for one raw sense ONLY when its
canonical candidate source_ref is unambiguous within the final Stage-01 lemma
identity to which that raw sense belongs.

Lemma identity remains exactly:

(word normalized as already specified, canonical_pos, gender)

Do not broaden ambiguity scope across unrelated lemma identities.

The same upstream value may legitimately occur under different lemmas because
sense.semantic_ref is namespaced by lemma.semantic_ref.

### Required ambiguity algorithm

Source-ref selection for English raw senses must be resolved
deterministically at lemma-identity scope, not greedily one sense at a time.

For each final lemma identity:

1. Gather all participating English-edition raw senses contributing to that
   lemma identity before final source-ref assignment.

2. For every raw sense, independently compute its cleaned senseid candidate
   using the already-accepted normalization and serialization rules.

3. Count each non-empty canonical senseid candidate source_ref across ALL raw
   English senses for that lemma identity.

4. A senseid candidate occurring exactly once is usable.

5. A senseid candidate occurring more than once is ambiguous.

6. EVERY raw sense carrying that ambiguous candidate must treat senseid as
   unusable. Do not allow the first occurrence to keep it and only demote later
   occurrences; that would make identity source-order-dependent.

7. For senses whose senseid candidate is absent or ambiguous, evaluate the
   Wikidata candidate using the same uniqueness rule at the SAME lemma-identity
   scope.

8. A Wikidata candidate occurring exactly once among the relevant senses is
   usable.

9. A Wikidata candidate occurring more than once is ambiguous for every member
   carrying that candidate.

10. If neither priority yields a usable explicit identifier, use the existing
    fallback fingerprint algorithm.

This gives the effective priority:

unique senseid
    -> unique Wikidata
        -> existing fingerprint:v1 or fingerprint:v2

### Important stability properties

Do NOT create a hybrid source_ref such as:
- senseid + line number;
- senseid + source-order index;
- senseid + collision counter.

Do NOT arbitrarily allow one member of an ambiguous senseid group to keep the
explicit ID.

Do NOT hash raw JSON.

Do NOT mutate the source JSONL.

Do NOT condition ambiguity resolution on the textbook words.

Do NOT disable final duplicate semantic-ref validation.

Do NOT change:
- lemma.semantic_ref;
- compute_sense_semantic_ref;
- source_namespace;
- fingerprint:v1 canonicalization;
- fingerprint:v2 canonicalization;
- same-record canonical-equivalent fallback coalescing.

The Ahnenpass/Ahnenpaß v2 correction remains binding.

The Freimaurer same-record fallback coalescing correction remains binding.

The April multi-gender correction remains binding.

### Learner-meaning order/cap

Ambiguous-ID demotion changes only source identity selection.

It does NOT by itself merge, reorder or remove distinct raw senses.

Existing A6 source-order and max-three learner-meaning behavior remains
unchanged after the already-authorized canonical-equivalent fallback dedupe.

For the diagnosed Konjunktion record, both raw senses remain distinct because
their fallback projections differ.

### Required Attempt-5 regressions

Attempt 5 must prove at minimum:

1. A unique senseid still produces exactly the existing:
   senseid:<identifier>
   source_ref.

2. Multiple usable IDs within one raw sense still preserve the existing
   senseids:v1 behavior.

3. Two distinct raw senses in one lemma identity carrying the same canonical
   senseid candidate mark that candidate ambiguous for BOTH senses.

4. Neither member is allowed to retain the ambiguous explicit source_ref.

5. If those two senses have no usable Wikidata identifier, each falls through
   independently to its existing fallback fingerprint.

6. The diagnosed Konjunktion shape builds successfully.

7. Konjunktion produces two distinct persisted source senses when both survive
   the existing learner-meaning cap.

8. Their final source_ref values differ.

9. Their sense.semantic_ref values differ.

10. Their meanings remain source-backed and correctly associated:
    - conjunction
    - conjunction / coordinating conjunction according to existing A6 meaning
      persistence semantics.

11. Ambiguous senseid + one unique usable Wikidata candidate falls through to
    that Wikidata candidate rather than directly to fallback.

12. A duplicated Wikidata candidate is likewise ambiguous and falls through to
    fallback for every member carrying it.

13. Ambiguity detection works across separate English raw entry records that
    merge into the SAME lemma identity, not merely within one JSONL line.

14. The same senseid candidate appearing under two DIFFERENT lemma identities
    does not make either candidate ambiguous merely because the text is globally
    reused.

15. Source ordering does not decide which member keeps an ambiguous identifier;
    reversing contributing raw-record order yields the same resolved identities.

16. Explicit IDs that are unique continue to take priority over fallback.

17. Existing explicit duplicate-ID fail-closed test is superseded only where
    its old expectation assumed a duplicated source ID was automatically usable.
    Replace that narrow obsolete expectation with ambiguity-demotion tests.

18. Final duplicate-semantic-ref validation remains tested and fail-closed for
    any ambiguity that survives the complete identity-resolution procedure.

19. Freimaurer regression remains passing.

20. Ahnenpass/Ahnenpaß regression remains passing.

21. April multi-gender regression remains passing.

22. Existing v1/v2 golden and cosmetic-stability tests remain passing.

### Real-data execution

Attempt 5 reruns the same real Stage-01 build exactly once after targeted tests
and `make gate` pass.

If the real build fails again for another incompatibility:
STOP immediately.

Do not repair further in that T3 worker.

That is the WORKFLOW §5 T3 ceiling and returns to design.

If the real build succeeds:
continue to the existing real Gate-2 baseline measurement exactly once.

Gate-2 threshold behavior remains unchanged:
- <85 -> GOVERNANCE_REDESIGN_REQUIRED
- 85..<95 -> REMEDY_REQUIRED
- >=95 -> CONTINUE
