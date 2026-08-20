# Slice 5 — Stage 02: deterministic Tatoeba example indexing

Task:        Implement ADR-0001 §12 build Stage 02 against the accepted Stage-01
             dictionary asset. Index German Tatoeba sentences into `example`
             and `example_lemma` using the canonical `app/resolve.py` resolver,
             preserve per-row attribution, and make every reusable Stage-02
             cache artifact depend on the canonical resolver SHA-256.

Depends:     slice-4

## Entry condition

slice-4 / Gate 2 is accepted, merged and closed with final post-remedy
disposition `CONTINUE`.

Before implementation dispatch, the slice-5 orchestrator must verify the normal
WORKFLOW §10 startup checks and supply these LOCAL, uncommitted inputs:

- `STAGE02_STAGE01=<accepted Stage-01 SQLite asset>`
- `TATOEBA_DE_TSV=<UTF-8 German sentence projection>`
- `TATOEBA_EN_TSV=<UTF-8 English sentence projection>`
- `TATOEBA_DE_EN_LINKS_TSV=<UTF-8 DE→EN link projection>`
- `TATOEBA_EXPORT_LABEL=<non-empty human-readable export/date label>`
- `TATOEBA_LICENSE=<current verified Tatoeba sentence-export license label>`

The accepted local Stage-01 asset from slice-4 had, at slice-4 evidence time:

- SHA-256:
  `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`
- bytes: `767926272`
- lemma rows: `1118636`
- sense rows: `480221`
- sense_meaning rows: `577141`

If that exact local asset is still present, it may be reused after executable
checksum/row-count/`PRAGMA quick_check` verification.

If it is absent or differs, do not silently substitute another Stage-01 asset.
Return to the orchestrator to establish a fresh accepted Stage-01 input and its
provenance before dispatch.

The three Tatoeba projections are maintainer-side local inputs and are never
committed.

Projection schemas are exact:

`TATOEBA_DE_TSV`
```
<positive Tatoeba sentence id>\t<nonblank German sentence text>
```

`TATOEBA_EN_TSV`
```
<positive Tatoeba sentence id>\t<nonblank English sentence text>
```

`TATOEBA_DE_EN_LINKS_TSV`
```
<German sentence id>\t<English sentence id>
```

One record per line, no header.

They must be deterministic projections of one official Tatoeba export edition.
The orchestrator records file SHA-256 values and the export label before
dispatch.

The implementation does NOT download Tatoeba automatically.

The current license must be checked against the official Tatoeba download page
before real-data execution because ADR-0001 §8 explicitly requires license
verification before shipping. Any material mismatch with the accepted
attribution contract returns to governance rather than being silently relabeled.

## Allowlist

Implementation may modify/create only:

- `tools/build_dict.py`
- `tests/test_build_dict_stage02.py`
- `tasks/slice-5.report.md`

No other tracked path is allowed.

In particular do NOT modify:

- `app/resolve.py`
- `app/dictionary.py`
- `tools/resolver_hash.py`
- `tools/check_agents.py`
- `reference/schema.sql`
- dependencies
- ADRs
- AGENTS.md
- WORKFLOW.md
- Stage-01 tests
- Stage-01 source inputs
- user-data/runtime code

## Acceptance

### A1 — CLI

Extend the existing maintainer build CLI with Stage 02:

```text
python tools/build_dict.py stage02 \
  --stage01 <stage01.sqlite> \
  --de-tsv <de-sentences.tsv> \
  --en-tsv <en-sentences.tsv> \
  --links-tsv <de-en-links.tsv> \
  --output <stage02.sqlite> \
  --cache-dir <cache-dir> \
  --license <verified-license-label>
```

Also support:

```text
--spacy-model de_core_news_md
--n-process 8
```

with those values as defaults.

Tests may use `--n-process 1`.

The Stage-02 command:

- performs no network access;
- downloads nothing;
- requires no API key;
- refuses to overwrite `--output`;
- never mutates `--stage01`;
- leaves no completed output on failure.

### A2 — Stage-01 preservation

Stage 02 starts by validating and copying the supplied Stage-01 dictionary into
a new output artifact.

It must not modify Stage 01 in place.

Before indexing:

- source file exists;
- SQLite opens read-only;
- `PRAGMA quick_check` returns `ok`;
- required PART-A tables exist:
  `lemma`, `surface_form`, `sense`, `sense_meaning`,
  `sense_meaning_derivation`, `example`, `example_lemma`.

A pre-existing `example` row with `source='tatoeba'` means the supplied input is
not a clean Stage-01 asset for this stage and is a hard error.

Existing non-Tatoeba PART-A data is preserved byte-for-byte logically.

Output publication is atomic: build into a temporary sibling and rename only
after complete validation.

### A3 — Input validation

All three projections are strict UTF-8.

German/English sentence rows require exactly:

- positive integer sentence id;
- one tab delimiter separating id from text;
- nonblank text after stripping outer whitespace.

Duplicate sentence IDs in either sentence projection are hard errors.

Link rows require exactly two positive integer IDs.

Every link must reference:

- an existing German ID from the German projection;
- an existing English ID from the English projection.

Duplicate DE→EN link pairs are hard errors.

Malformed/dangling rows fail closed.

Input order must not change final database content.

### A4 — Canonical resolver only

Stage 02 imports resolver functionality from:

`app.resolve`

It does not copy or reimplement lemma-resolution, separable-verb, surface-form,
or compound logic.

German sentence NLP uses spaCy and processes the sentence corpus through:

`nlp.pipe(...)`

with the configured `n_process`.

For each parsed German sentence, evaluate its tokens through canonical
`app.resolve.resolve_token`.

This is the R2 boundary.

The index may persist an `example_lemma` association only for a resolver result
that provides an actual existing dictionary `lemma_id`.

Do not invent numeric lemma identities for `derived_compound` results whose
`lemma_id` is `None`.

Deduplicate repeated lemma IDs within one sentence before persistence.

The separable-verb acceptance regression must prove that a sentence such as:

`Ich rufe dich morgen an.`

indexes the dictionary lemma `anrufen` through the canonical resolver rather
than indexing only `rufen`.

### A5 — Example persistence

Process German source sentences in ascending Tatoeba sentence-ID order so local
SQLite row allocation is deterministic.

Persist an `example` row only when the German sentence resolves to at least one
indexable dictionary lemma.

For every persisted example:

- `de` = exact supplied German text;
- `en` = deterministic linked English translation, or NULL;
- `source` = `tatoeba`;
- `source_ref` = decimal string of the German Tatoeba sentence ID;
- `license` = exact nonblank supplied `--license`;
- `token_count` = count of spaCy tokens excluding only whitespace tokens;
- `has_proper` = 1 iff at least one non-space token has POS `PROPN`, else 0.

English translation selection is deterministic:

- collect all linked English sentence IDs for the German sentence;
- if none exist, `en=NULL`;
- otherwise choose the lowest numeric English sentence ID;
- persist that English sentence's exact supplied text.

Do not machine-translate missing English text.

### A6 — Inverted index

For every persisted example and every deduplicated resolved dictionary lemma ID,
insert one:

`example_lemma(lemma_id, example_id)`

association.

No orphan `example_lemma` row is permitted.

No duplicate `(lemma_id, example_id)` row is permitted.

A sentence with zero indexable resolved dictionary lemmas is not persisted as an
unreachable example row.

### A7 — Attribution

Every Stage-02 `example` row has non-empty:

- `source='tatoeba'`
- `source_ref`
- `license`

This is AGENTS R11.

Do not attribute Tatoeba rows as Wiktionary.

Do not persist audio or any other Tatoeba asset in this slice.

### A8 — Resolver-hash cache key

Stage-02 caching is required.

The canonical resolver hash authority is:

`tools.resolver_hash.get_resolver_hash`

Stage 02 MUST import and call that helper.

It MUST NOT independently hash `app/resolve.py`.

Every reusable Stage-02 cache artifact key must include the FULL canonical
resolver SHA-256.

The cache identity must also include deterministic SHA-256 values for:

- Stage-01 SQLite input;
- German sentence projection;
- English sentence projection;
- DE→EN links projection;

and must distinguish at least:

- Stage-02 cache-format/version;
- spaCy model name;
- supplied license label.

Changing resolver bytes MUST yield a different cache key.

Changing any input file MUST yield a different cache key.

Changing the spaCy model name MUST yield a different cache key.

Do not key on mtimes, absolute paths, or input ordering.

Cache files live only beneath the supplied `--cache-dir`.

### A9 — Cache behavior

On a valid exact-key cache hit:

- do not rerun spaCy;
- validate the cached SQLite asset with `PRAGMA quick_check`;
- verify required Stage-02 rows/tables are structurally readable;
- publish a copy to the requested output atomically;
- never overwrite output.

On a cache miss:

- build Stage 02;
- fully validate the completed temporary output;
- atomically publish the cache artifact;
- atomically publish the requested output.

A corrupt matching cache artifact fails closed.

Do not silently ignore corruption and rebuild under the same cache key.

A partial failed build must not masquerade as a completed cache hit.

### A10 — Frequency is explicitly deferred

Do NOT update `lemma.freq_rank` in this slice.

Do NOT add a `freq` table.

The accepted backlog explicitly defers Tatoeba-derived frequency counts.

Stage 02 in slice-5 owns examples/indexing only.

### A11 — Determinism

Given identical:

- Stage-01 bytes;
- Tatoeba projections;
- resolver bytes;
- spaCy model;
- license label;

two clean Stage-02 cache-miss builds must produce logically identical:

- Tatoeba `example` rows;
- `example_lemma` rows;
- selected English translations;
- source/source_ref/license;
- token_count;
- has_proper.

Tests must compare logical rows, not rely on SQLite file byte-for-byte identity.

Reordering the input TSV rows must not change logical Stage-02 output.

### A12 — Real-data execution

The slice-5 worker must execute one real Stage-02 cache-miss build against the
orchestrator-supplied real projections.

It must record:

- Stage-01 SHA-256;
- all three Tatoeba projection SHA-256 values;
- export label;
- license label;
- resolver full SHA-256;
- spaCy model;
- n_process;
- Stage-02 output SHA-256 and bytes;
- input German sentence count;
- input English sentence count;
- link count;
- persisted Tatoeba example count;
- example rows with English translation count;
- untranslated persisted example count;
- `example_lemma` association count;
- distinct indexed lemma count;
- cache key;
- whether real execution was cache hit or miss.

The required acceptance run is a cache MISS.

Then execute a second invocation with the exact same inputs and a new output
path to prove an exact-key cache HIT.

The cache-hit invocation is verification, not a WORKFLOW retry.

The two outputs must have identical logical Stage-02 Tatoeba rows.

Do not commit either real SQLite asset, Tatoeba projections, or cache files.

### A13 — Tests

`tests/test_build_dict_stage02.py` must cover at minimum:

1. valid strict German sentence projection;
2. valid strict English sentence projection;
3. malformed sentence row rejected;
4. duplicate sentence ID rejected;
5. malformed link rejected;
6. dangling DE link rejected;
7. dangling EN link rejected;
8. duplicate link pair rejected;
9. input order independence;
10. deterministic lowest-ID English translation choice;
11. untranslated German sentence persists with `en=NULL` when it has an
    indexable lemma;
12. sentence with no indexable lemma is not persisted;
13. repeated lemma resolution within a sentence creates one association;
14. `source='tatoeba'`;
15. nonblank source_ref;
16. exact supplied license;
17. token_count;
18. has_proper;
19. canonical `resolve_token` path is exercised;
20. separable `rufe ... an` indexes `anrufen`;
21. derived result with no numeric lemma_id does not invent an association;
22. Stage-01 input remains unchanged;
23. output overwrite refused;
24. failure leaves no completed output;
25. canonical resolver hash helper is used;
26. resolver-content change changes cache key;
27. Stage-01-content change changes cache key;
28. each Tatoeba input-content change changes cache key;
29. spaCy model change changes cache key;
30. cache miss publishes completed cache;
31. exact-key cache hit avoids NLP rebuild;
32. corrupt cache fails closed;
33. cache-hit and cache-miss outputs are logically equal;
34. Stage 01 regression tests remain passing;
35. `make gate` / AGENTS R3 check passes.

### A14 — Report

Create `tasks/slice-5.report.md`.

Its NARRATIVE records:

- decisions not already specified by this brief;
- any Stop-and-ask condition hit;
- problems noticed but not fixed;
- work left undone.

Executable evidence records all A12 real-data counts/hashes and:

- targeted Stage-02 pytest count;
- Stage-01 regression pytest count;
- full `make gate` pytest count;
- `git diff --check`;
- exact changed-file allowlist;
- final branch HEAD;
- push status.

Do not record private absolute machine paths.

## Stop-and-ask

STOP and return to the slice-5 orchestrator if:

- `Depends: slice-4` is not merged;
- Gate-2 final post-remedy disposition is not `CONTINUE`;
- any required local Stage-02 input is absent;
- current Tatoeba licensing materially conflicts with the accepted attribution
  contract;
- the supplied Stage-01 asset cannot be verified as accepted input;
- satisfying Stage 02 requires changing `app/resolve.py`,
  `app/dictionary.py`, `reference/schema.sql`, dependencies, ADRs, AGENTS,
  WORKFLOW, or any path outside the Allowlist;
- real Tatoeba projections do not match the briefed projection schemas;
- the canonical resolver cannot produce stable numeric lemma IDs needed by the
  example index;
- `de_core_news_md` is absent or cannot process the supplied German sentences;
- any requested operation would overwrite an existing output/cache asset;
- Stage-02 attribution cannot be filled nonblank per row;
- cache correctness cannot be satisfied using `tools.resolver_hash`;
- real Stage-02 execution fails.

Do not solve a Stop-and-ask condition by changing architecture.

## Risk

Risk: none

## Why-risk

WORKFLOW §6 path lookup: the implementation allowlist contains the existing
maintainer-only offline dictionary builder, a new Stage-02 test module, and its
report. It touches no schema/migration file, auth/security path, externally
callable runtime API, user database, or destructive transform of an existing
artifact. Stage 01 is read-only input; Stage 02 publishes a new disposable
dictionary asset and refuses overwrite.

## Model

Model: claude-code / T2 / high

## Why

WORKFLOW §4:

- Verification is strongly executable;
- blast radius is tight;
- but Stage 02 establishes a new reusable offline indexing/cache pattern and
  coordinates spaCy, canonical resolver semantics, attribution, deterministic
  SQLite persistence, multi-input hashing, and cache invalidation.

The novelty/multiple-constraint rows therefore route above T1.

## Fallback

Fallback: codex / T2 / high

## Worker implementation constraints

1. Read the complete brief before editing.
2. Read AGENTS R2/R3/R9/R11.
3. Read ADR-0001 §§8, 10, 12 and the accepted Gate-1/Stage-01 reports.
4. Import canonical resolver functions; do not duplicate them.
5. Import `tools.resolver_hash`; do not independently hash resolve.py.
6. No automatic data downloads.
7. No frequency implementation.
8. No Stage 03+ work.
9. No runtime app/UI/API work.
10. Real Tatoeba/SQLite/cache artifacts remain ignored and uncommitted.

## Required report scaffold

```markdown
# Slice 5 report

## NARRATIVE

### Stage-02 inputs
Export label:
License:
Stage-01 SHA-256:
German projection SHA-256:
English projection SHA-256:
Links projection SHA-256:
Resolver SHA-256:
spaCy model:
n_process:

### Real cache-miss build
German sentences:
English sentences:
Links:
Persisted examples:
Examples with EN:
Examples without EN:
example_lemma rows:
Distinct indexed lemmas:
Output SHA-256:
Output bytes:
Cache key:
Cache result: MISS

### Exact-key cache-hit verification
Cache result: HIT
Logical output equality:

### Verification
Stage-02 targeted tests:
Stage-01 regression tests:
make gate:
git diff --check:
Allowlist:
Push:

### Stop-and-ask
None or exact condition.

### Work left undone
```

Populate only from executable evidence.

## T3-ceiling design reset — resolver containment and Stage-02 lookup parity

### Ceiling result

The original slice-5 implementation ladder exhausted:

- Attempt 1: T2 Failure 1 — infrastructure interruption during the real
  Stage-02 cache MISS.
- Attempt 2: T2 Failure 2 — systemd-oomd killed the real cache-MISS tmux
  execution scope.
- Attempt 3: T3 worker-reported PASS, subsequently rejected during orchestrator
  report-only acceptance by executable post-pass evidence.

Attempt 3 is therefore the terminal T3 failure for the original ladder.

Per WORKFLOW §5 this is not followed by Attempt 4.

The prior task is classified as misspecified and has returned to design.

The redesigned task is re-dispatched from Design-reset Attempt 1 with a new
attempt ladder. The original three attempts remain permanently recorded and are
not renumbered or absorbed.

### What succeeded before the design reset

Attempt 3 successfully established the bounded-memory real-data execution path.

Its real Stage-02 run completed:

- real cache MISS: PASS;
- exact-key cache HIT: PASS;
- MISS/HIT cache key equality: PASS;
- both SQLite `PRAGMA quick_check`: `ok`;
- targeted Stage-02 tests: 50 passed;
- Stage-01 regression tests: 46 passed;
- full `make gate`: 216 passed;
- AGENTS R3: PASS;
- `git diff --check`: PASS.

The original real-data evidence was:

- Stage-01 SHA-256:
  `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`
- German projection SHA-256:
  `093c75b568e6bc10b637a903c2e253e54670144ad25ab527490fb1278f08744c`
- English projection SHA-256:
  `9ed0e241964b6ab28b1961192fc014eac9ba12dc851462a8264dce276246f139`
- DE→EN links SHA-256:
  `4ce5d9123141d3c93ef6c104ef498198067d594028d81446cc47712074ca0d97`
- export:
  `Tatoeba weekly export 2026-08-15`
- license:
  `CC BY 2.0 FR`
- resolver SHA-256:
  `b09ee526951fdd28bfcfffbe3f43253c21e627e731e66d1daffeb3ca34fddc2d`
- spaCy model:
  `de_core_news_md`
- real acceptance `n_process`:
  `1`
- CLI default `n_process`:
  `8`
- original cache key:
  `stage02:v1:0be1d3165dfe261b2c5706226948990b62030aa1b86c424e3e3c76cca747ef57`
- output SHA-256:
  `070cb12a0461f70266ca1414e257e66d656cafce80c62aea8fb7a54e6dd27316`
- output bytes:
  `4830187520`
- persisted examples:
  `777657`
- examples with English:
  `494939`
- examples without English:
  `282718`
- example_lemma rows:
  `296004868`
- distinct indexed lemmas:
  `112759`
- incomplete attribution:
  `0`
- orphan associations:
  `0`.

These successful execution facts remain historical evidence. They do NOT make
the Stage-02 asset acceptable after the post-pass semantic failure below.

### Post-pass acceptance failure

A read-only orchestrator acceptance probe against the completed Attempt-3 MISS
asset found:

- Tatoeba examples: `777657`;
- token-count sum: `7293617`;
- average token count: `9.378964`;
- maximum token count: `255`;
- example_lemma rows: `296004868`;
- distinct indexed lemmas: `112759`;
- associations/example: `380.636795`;
- associations/token: `40.584098`.

A deterministic first/middle/last sample of 90 examples then produced:

- canonical unique lemma IDs mean: `517.344444`;
- canonical unique lemma IDs median: `12`;
- canonical unique lemma IDs maximum: `15186`;
- missing expected canonical associations: `94`;
- unexpected cross-sentence foreign hits: `0`;
- exact sampled persisted-association mismatches: `55 / 90`.

The absence of cross-sentence foreign hits rules out simple batch-to-batch
association leakage, but the persisted Stage-02 index is not behaviorally equal
to the canonical resolver result.

### Forensic result

A second read-only forensic probe established:

- Stage-01 `PRAGMA quick_check`: `ok`;
- Stage-02 `PRAGMA quick_check`: `ok`;
- duplicate Stage-01 `(lemma, pos, gender)` groups: `0`;
- duplicate Stage-01 `semantic_ref` groups: `0`;
- sampled cases with missing canonical expected associations: `55`.

Therefore the failure is NOT caused by duplicate canonical Stage-01 lemma
identity.

Observed canonical resolver fan-out included:

1. Sentence:
   `Was ist das?`

   The punctuation token `?`, spaCy POS `PUNCT`, resolved to 28 numeric lemma
   IDs spanning unrelated nouns/proper nouns.

2. Sentence:
   `Die Großeltern haben Geschenke für ihre Enkelkinder mitgebracht.`

   Token `haben`, spaCy POS `AUX`, resolved to `15168` numeric lemma IDs,
   spanning suffix entries, multi-word verb phrases, and unrelated entries.

3. Stage-02/live-resolver parity mismatches included canonical IDs such as:

   - `Ihr`, POS `DET`;
   - `Ists`, POS `NOUN`;

   returned by the live canonical resolver but absent from the persisted
   `example_lemma` association set for sampled sentences.

The evidence supports:

- Stage-01 identity multiplicity: NO;
- canonical resolver surface-form fan-out: YES;
- Stage-02 lookup/persistence behavioral mismatch against the canonical runtime
  resolver: YES.

### Root cause boundary

The existing canonical resolver implementation applies its surface-form POS
filter only when at least one surface result has the requested POS.

When surface-form matches exist but NONE has the requested POS, the resolver
retains and returns the entire mismatched surface result set.

That behavior permits a token such as `haben` tagged `AUX` or punctuation tagged
`PUNCT` to fall through into unrelated surface-form dictionary rows.

This is a canonical resolver implementation defect, not a Stage-01 identity
collision.

Separately, Stage-02's memory-bounded lookup implementation does not yet have an
executable behavioral-parity contract proving that, for the same dictionary
asset, it returns exactly the same lookup results as `app.dictionary.Dictionary`
to `app.resolve.resolve_token`.

The original slice-5 A4 requirement mandated the canonical resolver but did not
make that lookup-oracle parity executable. That omission allowed the persisted
index and live runtime resolver to disagree while the original gate remained
green.

### Architecture decision

No ADR is reopened.

The accepted architecture remains unchanged:

- `app.resolve` is the one canonical resolver;
- dictionary knowledge is injected through `LookupProtocol`;
- `app.dictionary.Dictionary` remains the runtime read-only SQLite
  implementation;
- Stage-02 must use the same canonical `resolve_token`;
- no second resolver is permitted.

The design reset repairs implementation semantics and makes oracle parity
executable. It does not introduce a new resolution architecture.

### Redesigned task — Phase A: cheap resolver/parity repair

Before ANY new real Stage-02 build, repair and prove resolver semantics using
small executable tests.

Phase A may modify only:

- `app/resolve.py`
- `tools/build_dict.py`
- `tests/test_resolve.py`
- `tests/test_build_dict_stage02.py`
- `tasks/slice-5.report.md`

No schema, dependency, ADR, AGENTS, WORKFLOW, runtime API, user DB, Stage-01
builder, Stage-01 test, or unrelated path may change.

#### A. Strict surface-form POS containment

When `resolve_word(..., pos=P)` receives surface-form matches:

- if `P` is not `None`, only surface-form rows whose dictionary POS equals `P`
  may be returned from that surface-form step;
- if zero surface-form rows match `P`, the resolver MUST NOT return rows of
  another POS merely because they share the surface string;
- with zero same-POS surface matches, resolution continues to the existing next
  ladder step/fallback;
- when `pos=None`, existing unfiltered surface-form behavior remains unchanged.

Add regression tests proving:

- a requested POS with only wrong-POS surface matches does not return those
  mismatched rows;
- a mixture of matching and nonmatching POS surface rows returns only the
  requested POS;
- punctuation with no `PUNCT` dictionary match cannot acquire unrelated numeric
  lemma IDs through surface-form fallback;
- existing exact, separable-verb, compound, and stub regressions remain passing.

Do not invent a second resolver and do not bypass `resolve_token`.

#### B. Stage-02 lookup-oracle parity

The memory-bounded Stage-02 lookup implementation may remain optimized, but for
the same SQLite asset its resolver-facing behavior MUST be equivalent to
`app.dictionary.Dictionary`.

Executable tests must prove parity for at least:

- `lookup_exact`;
- `lookup_surface_form`;
- `lookup_senses`;

including:

- case-sensitive and case-insensitive lookup cases;
- two rows whose lemma text differs only by capitalization;
- requested POS filtering;
- requested gender filtering where applicable;
- deterministic ordering;
- result deduplication;
- sense ordering.

Also run both lookup implementations through canonical `resolve_token` over the
same synthetic tokens and require identical numeric lemma-ID sets.

Do not solve parity by importing or copying resolver logic into
`tools/build_dict.py`.

#### C. Real Stage-01 cheap preflight

Before any real Stage-02 rebuild, use the preserved accepted Stage-01 SQLite
asset read-only with `de_core_news_md`, `n_process=1`, and canonical
`resolve_token`.

For the forensic regression sentences above:

- punctuation `?` must not return unrelated numeric dictionary IDs;
- `haben` tagged `AUX` must not return surface-form rows whose dictionary POS is
  not `AUX`;
- Stage-02's lookup adapter and `app.dictionary.Dictionary` must produce
  identical resolver numeric-ID sets token-by-token.

This is a read-only cheap preflight and is NOT a Stage-02 build.

#### D. Resolver-hash invalidation

Because `app/resolve.py` changes, the canonical resolver SHA-256 MUST change.

The redesigned Stage-02 cache key computed from the same real inputs must
therefore differ from:

`stage02:v1:0be1d3165dfe261b2c5706226948990b62030aa1b86c424e3e3c76cca747ef57`

Do not manually version-bump merely to force inequality.

The change must arise through the existing canonical
`tools.resolver_hash.get_resolver_hash` dependency.

### Phase-A verification gate

Before a new real corpus build is authorized, require:

- targeted resolver tests PASS;
- targeted Stage-02 tests PASS;
- Stage-01 regression tests PASS unchanged;
- real Stage-01 forensic preflight PASS;
- Stage-02/runtime lookup parity PASS;
- new resolver hash recorded;
- new real-input cache key recorded and different from the defective key;
- `git diff --check` PASS;
- full `make gate` PASS;
- exact allowlist PASS.

If any Phase-A requirement fails, STOP and return to the slice-5 orchestrator.

DO NOT start a real Stage-02 corpus build in Phase A.

### Redesigned task — Phase B: real rebuild only after orchestrator authorization

A real Stage-02 rebuild is intentionally deferred until the orchestrator accepts
the complete Phase-A evidence.

Phase B will:

- preserve and reverify the accepted Stage-01 input and Tatoeba projections;
- use a fresh design-reset run directory and fresh cache;
- use the repaired canonical resolver;
- use the parity-proven Stage-02 lookup implementation;
- perform one required real cache MISS and one exact-key HIT;
- require logical MISS/HIT equality;
- rerun the post-pass sentence-local sanity probe before acceptance;
- record real counts/hashes;
- replace the defective historical Attempt-3 evidence in the current report
  with an explicit superseding design-reset result while preserving all original
  attempt history.

The defective Attempt-3 Stage-02 output is historical evidence, not a candidate
for reuse as the Phase-B cache or final asset.

### Redesigned attempt routing

The new ladder begins at:

`Design-reset Attempt 1`

Phase-A Model:

`gpt-5.6-terra / T3 / high`

Fallback:

`opus-5 / T3 / high`

Risk:

`none`

Why:

The repair touches the canonical resolver and the Stage-02 resolver-facing
oracle boundary. Errors can be internally self-consistent while semantically
wrong, as the exhausted original ladder proved. This is the same core resolver
boundary originally routed T3 and therefore remains T3 despite the tightened
tests.

No lower-tier fallback is authorized.

Phase B is not authorized by this design-reset record alone. It requires an
explicit orchestrator continuation after Phase-A acceptance.

### Storage/evidence rule

Until Phase-A acceptance, do not delete:

- the accepted Stage-01 SQLite asset;
- the Attempt-3 MISS SQLite used for forensic evidence.

No new real Stage-02 build is authorized in Phase A.

After Phase-A acceptance, the orchestrator may authorize a separate mechanical
cleanup of redundant failed-run/cache/HIT artifacts before the Phase-B rebuild
so disk space is recovered without losing required evidence.
