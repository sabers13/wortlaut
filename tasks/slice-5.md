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
