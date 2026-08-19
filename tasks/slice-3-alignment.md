# Slice 3 alignment — ADR-0004 Stage-01 / PART-A

Task:        Align the already-accepted slice-3 Stage-01 implementation at `7ceea14e39a7c831edfc803632d3c868ea0f3091` with accepted/frozen ADR-0004 D36/D45/D46/D47 PART-A requirements without reopening the original Attempt-1 acceptance. Preserve the existing deterministic offline Stage-01 CLI/build behaviour while replacing the English-gloss-as-sense model with language-neutral senses plus localized meaning rows, adding stable cross-version semantic references and explicit source-side sense identity, implementing the PART-A information needed for deterministic D46 component bindings, and repairing only PART A of `reference/schema.sql`.

Depends:     accepted slice-3 Attempt-1 `7ceea14e39a7c831edfc803632d3c868ea0f3091`; accepted/frozen ADR-0004 on current `main`.

Precondition: The orchestrator supplies exact current `main` HEAD after ADR-0004 approval persistence. Local and origin `slice/3` must still equal `7ceea14e39a7c831edfc803632d3c868ea0f3091`. Working tree must be clean. Do NOT merge, rebase, reset or rewrite `slice/3`; append alignment commits to that accepted tip only. The owner-driven ADR amendment is not a WORKFLOW §5 failure and adds no attempt/audit increment.

Allowlist:
- `tools/build_dict.py`
- `app/dictionary.py`
- `app/resolve.py`
- `tests/conftest.py`
- `tests/test_build_dict_stage01.py`
- `tests/test_dictionary.py`
- `tests/test_resolve.py`
- `tests/test_resolve_spacy.py` only if required to preserve Gate-1 compatibility after the resolver data-shape extension
- `tests/fixtures/wiktextract_stage01_en.jsonl`
- `tests/fixtures/wiktextract_stage01_de.jsonl`
- `reference/schema.sql`
- `tasks/slice-3.report.md`

Risk:        migration

Why-risk:    WORKFLOW.md §6 is a path lookup. This alignment explicitly changes `reference/schema.sql`, so the `migration` risk label applies even though the accepted Attempt-1 implementation was `Risk: none`. A T3 full-diff review is therefore mandatory before merge.

Model:       gpt-5.6-terra / T3 / high

Why:         WORKFLOW.md §4 Novelty and blast-radius rows trigger T3. This establishes the durable semantic-identity serialization, source-ref canonicalization, normalized PART-A meaning model, derivation validator, and stable D46 resolver-binding representation that later slices consume. The task has simultaneous schema, deterministic identity, provenance, resolver and backwards-compatibility constraints.

Fallback:    opus-5 / T3 / high

## Scope boundary

This alignment owns ONLY Stage-01 / PART-A and the minimal read-only
dictionary/resolver seam necessary to expose that PART-A identity.

Explicitly OUT OF SCOPE:

- `note_meaning_lang`
- `note_user_meaning`
- `note_dictionary_binding`
- active dictionary version/SHA persistence
- user-DB migrations
- D47 candidate activation/relink/rollback
- `/vocab/*`
- picker asset-token behaviour
- rendering
- `meaning_state`
- R13 runtime checks
- slice-7 runtime semantics
- slice-8 replacement/stale-picker smoke
- stages 02–05
- multilingual LLM generation
- Gate-2 threshold execution

Gate 2 remains ADR-0002 §6 order 5 / slice-4 in its existing position and with
unchanged thresholds.

## A1 — Preserve the accepted Stage-01 execution contract

Keep the existing CLI exactly:

`python tools/build_dict.py stage01 --en-jsonl <path> --de-jsonl <path> --output <path>`

Preserve:

- line-by-line JSONL processing;
- no network/download/API/LLM path;
- standard library only;
- temporary sibling output + atomic publish;
- refusal to overwrite an existing requested output;
- fail-closed malformed participating input;
- no PART-B/example tables from Stage 01;
- multi-word surface forms including `rief an` / `ruft an`;
- deterministic row construction;
- source/license attribution.

The alignment changes the PART-A data model, not those accepted operational
properties.

## A2 — Lemma stable semantic identity

Add:

`lemma.semantic_ref TEXT NOT NULL UNIQUE`

Numeric `lemma.id` remains a per-asset local key only.

The identity input is exactly:

`(target_lang='de', nfc_lemma_text, canonical_pos, gender_or_null_sentinel)`

Use:

- `unicodedata.normalize("NFC", word)` for `nfc_lemma_text`;
- existing canonical POS mapping;
- existing stored gender domain (`der | die | das | NULL`) so the accepted
  resolver seam is not gratuitously redesigned;
- the literal string `"<null>"` as the canonical NULL-gender sentinel.

For semantic identity, normalize participating lemma text to NFC before merge
identity and persistence so canonically equivalent Unicode spellings cannot
produce duplicate semantic refs.

Canonical serialization is EXACTLY UTF-8 encoding of:

`json.dumps([target_lang, nfc_lemma_text, pos, gender_token], ensure_ascii=False, separators=(",", ":"))`

No trailing newline. No spaces inserted by JSON formatting.

Reference form:

`lemma:v1:<lowercase 64-char sha256 hex>`

Golden vector:

payload:
`["de","Haus","NOUN","das"]`

ref:
`lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436`

Second golden vector:

payload:
`["de","anrufen","VERB","<null>"]`

ref:
`lemma:v1:0694906fb1cb9a54d2a100d341607d922446d187b0bb250546f06c755a229c8b`

Tests must assert the literal payload bytes and literal refs, not merely
"same result twice".

## A3 — Sense identity namespace

ADR-0004 §6.6 names `sense.source_namespace`; the conceptual §6.1 DDL omitted
the column. Settle it here.

Add to `sense`:

`source_namespace TEXT NOT NULL`

For Stage-01 senses sourced from the `--en-jsonl` Wiktextract/English-Wiktionary
input, the exact identity namespace is:

`wiktextract:enwiktionary`

Do not overload `sense.source` with this value. `source` remains provenance;
`source_namespace` is an identity namespace.

Stage 01 continues to use the English-edition source as the language-neutral
sense-distinction source. German-edition records may continue contributing
lemma grammar/forms. Mapping German-edition learner text onto those language-
neutral senses belongs to the later multilingual enrichment owner and is not
invented here.

## A4 — `sense.source_ref`

Add:

`sense.source_ref TEXT NOT NULL`

Numeric `sense.id` remains a per-asset local key only.

For each participating raw English Wiktextract `senses[]` record:

1. Prefer usable upstream `senseid` values.
2. If no usable `senseid` exists, prefer usable sense-level Wikidata QID(s).
3. Otherwise create the fallback canonical sense-distinction fingerprint below.

Usable identifier strings are NFC-normalized and stripped; blank entries are
discarded; duplicates are removed.

Exactly one `senseid`:

`senseid:<identifier>`

Multiple `senseid` values:

- sort unique values lexically;
- canonical JSON serialize the array with
  `ensure_ascii=False, separators=(",", ":")`;
- source ref:
  `senseids:v1:<sha256 hex>`.

If no `senseid`, apply the same rule to `wikidata`:

`wikidata:<QID>`

or

`wikidata-set:v1:<sha256 hex>`

if multiple.

### Fallback fingerprint

Fallback source ref:

`fingerprint:v1:<lowercase sha256 hex>`

The fingerprint is computed from a canonical semantic projection of the raw
sense-distinction record. It MUST NOT hash raw JSON bytes.

Included sense-distinction fields, when present:

- `glosses`
- `tags`
- `topics`
- `form_of`
- `alt_of`
- `compound_of`
- `qualifier`
- `taxonomic`

Excluded deliberately:

- asset-local numeric IDs;
- JSON object key order;
- source whitespace/layout;
- `raw_glosses`;
- examples;
- translations;
- synonyms/antonyms/other linkage lists;
- categories;
- Wikipedia links;
- localized/generated `sense_meaning` rows;
- derivation rows;
- any later build enrichment.

Canonical string normalization for the fallback projection:

1. NFC;
2. `casefold()`;
3. replace every Unicode punctuation-category character (`P*`) with ASCII space;
4. collapse all whitespace runs to one ASCII space;
5. strip leading/trailing space.

Canonical containers:

- dictionaries: lexical key order;
- lists: canonicalize elements, discard canonical empties, deduplicate, then
  sort by their canonical JSON encoding;
- null/empty values are omitted;
- final serialization:
  `json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`
  encoded as UTF-8 without newline.

Required quality tests:

- cosmetic whitespace changes do NOT change fallback source_ref;
- punctuation-only changes do NOT change fallback source_ref;
- JSON key/list ordering of unordered projected metadata does NOT change it;
- a genuine lexical change in a normalized gloss DOES change it;
- if two different participating source senses collapse to the same
  `(lemma.semantic_ref, source_namespace, source_ref)`, fail closed rather than
  choosing one.

This cosmetic-stability behaviour is a quality target, not a destructive
continuity guess: collisions/ambiguity fail closed.

## A5 — `sense.semantic_ref`

Add:

`sense.semantic_ref TEXT NOT NULL UNIQUE`

Identity tuple exactly:

`(lemma.semantic_ref, sense.source_namespace, sense.source_ref)`

Canonical serialization exactly:

`json.dumps([lemma_ref, source_namespace, source_ref], ensure_ascii=False, separators=(",", ":"))`

UTF-8, no newline.

Reference:

`sense:v1:<lowercase 64-char sha256 hex>`

Golden vector:

lemma_ref:
`lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436`

source_namespace:
`wiktextract:enwiktionary`

source_ref:
`senseid:en-house-1`

payload:
`["lemma:v1:422ce86c59a6f587a848cff402a6498aa90417ab966fcae166b4f02cbe6c6436","wiktextract:enwiktionary","senseid:en-house-1"]`

ref:
`sense:v1:2fdd041adad74df1dfcd67a3ed5245c54bb03c20e373f989829e30dc755a70e6`

Golden-test the exact literal payload and ref.

## A6 — Language-neutral sense rows

Stop treating each English gloss string as its own `sense` row.

One persisted `sense` row represents one retained raw Wiktextract
`senses[]` distinction.

The English meaning strings that belong to that distinction become
`sense_meaning` rows.

Retain the ADR-0001/ADR-0004 maximum-three English learner-meaning policy by
traversing retained raw source senses in source order and their nonblank
`glosses` in source order, deduplicating identical text, and persisting at most
the first three English `sense_meaning` rows total for one lemma.

Create a `sense` row only when at least one English meaning for that raw
distinction survives that Stage-01 cap.

For retained senses:

- `sense.ord` is sequential `0..` in retained source-sense order;
- `source='wiktionary'`;
- `license='CC BY-SA'`;
- `source_namespace='wiktextract:enwiktionary'`;
- stable refs as A4/A5.

## A7 — D36 `sense_meaning`

Add PART-A table:

CREATE TABLE sense_meaning (
  id        INTEGER PRIMARY KEY,
  sense_id  INTEGER NOT NULL REFERENCES sense(id) ON DELETE CASCADE,
  language  TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK (kind IN ('definition', 'synonym', 'translation')),
  ord       INTEGER NOT NULL DEFAULT 0,
  text      TEXT NOT NULL,
  source    TEXT NOT NULL,
  license   TEXT NOT NULL,
  UNIQUE(sense_id, language, kind, ord)
);

CREATE INDEX ix_sense_meaning
ON sense_meaning(sense_id, language, ord);

Do NOT add a closed-language CHECK/FK.

Stage-01 English gloss rows are:

- `language='en'`
- `kind='translation'`
- deterministic `ord` within their source sense;
- `text=<existing accepted English gloss text>`
- `source='wiktionary'`
- `license='CC BY-SA'`

`sense.gloss_en` is removed completely as the normative meaning carrier.

German-edition glosses are NOT silently converted into Stage-01 learner meanings
by heuristic cross-edition sense matching. Later multilingual enrichment owns
that mapping/generation.

## A8 — D45 `sense_meaning_derivation`

Add exactly the normalized PART-A relation:

CREATE TABLE sense_meaning_derivation (
    generated_meaning_id INTEGER NOT NULL
        REFERENCES sense_meaning(id) ON DELETE CASCADE,
    source_meaning_id INTEGER NOT NULL
        REFERENCES sense_meaning(id) ON DELETE RESTRICT,
    PRIMARY KEY (generated_meaning_id, source_meaning_id),
    CHECK (generated_meaning_id <> source_meaning_id)
) WITHOUT ROWID;

Stage 01 normally emits zero rows here.

Implement a deterministic build-time validation function used before atomic
publish and reusable by later build stages.

A generated marker matches exactly:

`^llm_generated_v[1-9][0-9]*$`

For every derivation edge validate:

1. generated side exists;
2. generated side source matches the versioned generated marker;
3. source side exists;
4. source side source does NOT match the generated marker;
5. source side has nonblank source/license;
6. both meanings have identical `sense_id`;
7. generated→generated is forbidden;
8. self-edge is forbidden.

Tests must construct synthetic valid and invalid rows to prove all four D45
rules named by ADR-0004:

- generated marker on generated side;
- source-backed non-generated source side;
- same `sense_id`;
- no generated→generated edges.

Zero derivation edges is valid.

## A9 — Tri-state noun plural

Add to `lemma`:

`plural_none INTEGER NOT NULL DEFAULT 0 CHECK (plural_none IN (0,1))`

and a table CHECK enforcing:

`plural_none = 0 OR plural IS NULL`

Meaning:

- known plural: `plural=<text>`, `plural_none=0`;
- explicitly no normal plural: `plural=NULL`, `plural_none=1`;
- unknown: `plural=NULL`, `plural_none=0`.

Never infer `plural_none=1` merely because no plural form is present.

For Stage 01, the only supported explicit no-plural evidence is the literal
entry-level Wiktextract tag `no-plural`.

If `no-plural` is present and a plural form is simultaneously extracted, fail
closed as contradictory participating source evidence.

Add fixture coverage proving all three states.

## A10 — PART-A numeric IDs are local only

Document in:

- `reference/schema.sql`;
- Stage-01 schema comments/code where useful;
- relevant Python dataclass comments.

`lemma.id`, `sense.id`, and `sense_meaning.id` are deterministic/local SQLite
keys inside one built asset. They are NOT cross-version semantic identity.

No stable reference may contain, hash, serialize, or otherwise depend on those
numeric IDs.

## A11 — D46 resolver-visible component information

PART A and the read-only dictionary seam must expose enough information for the
accepted D46 deterministic component binding:

lemma:

- local `id`
- `semantic_ref`
- `lemma`
- `freq_rank`
- `pos`
- `gender`

sense:

- local `id`
- `semantic_ref`
- `lemma_id`
- `ord`
- `source_namespace`
- `source_ref`

Extend the pure resolver seam minimally.

`LemmaRecord` gains:

- `semantic_ref: str | None`
- `freq_rank: int | None`

Introduce a lightweight resolver-facing source-sense record carrying:

- local sense id
- stable `semantic_ref`
- `lemma_id`
- `ord`

and extend `LookupProtocol` with the minimal read-only source-sense lookup
required for D46.

Introduce an immutable ordered D46 component-binding representation carrying at
least:

- component lemma text
- `pos`
- `gender`
- `freq_rank`
- stable `lemma_ref`
- stable `sense_ref`
- `sense_ord`
- optional local lemma/sense IDs as current-asset caches only.

The derived-compound `Ref` must carry the ordered stable component-binding vector
left-to-right, grammatical head last.

The existing bare component strings may remain as a convenience/backwards-
compatibility field, but they are NOT the semantic binding.

## A12 — D46 deterministic selection

For every PRECEDING component candidate set, order exactly:

1. `freq_rank` ascending, `NULL` last;
2. `pos` ascending;
3. `gender` ascending, `NULL` last;
4. `lemma.semantic_ref` lexical ascending.

Do not use numeric SQLite ID as a semantic tie-breaker.

For the head, retain the existing resolver-selected head behaviour, but ensure
the underlying candidate ordering is deterministic using stable PART-A
information rather than asset-local ID ordering.

For each selected component lemma, select exactly one source sense:

1. lowest `sense.ord`;
2. lexical `sense.semantic_ref`.

A `derived_compound` result may expose a durable component vector only when all
components have:

- nonblank stable lemma refs; and
- an unambiguous selected source sense with nonblank stable sense ref.

If a candidate split cannot produce a complete stable binding, do not invent a
binding from numeric IDs or text-only identity; continue any already-defined
deterministic resolution path and ultimately fail closed to the resolver stub if
no fully bound derived result exists.

Do NOT implement D46 multilingual rendering/availability here.

## A13 — `app.dictionary` PART-A read seam

Update the read-only dictionary seam to the new PART-A schema.

`LemmaEntry` exposes `semantic_ref`.

`SenseEntry` no longer exposes `gloss_en` as sense identity; it exposes:

- id
- lemma_id
- semantic_ref
- source_namespace
- source_ref
- ord
- register
- source
- license

Add a localized-meaning entry/read method sufficient to retrieve
`sense_meaning` rows deterministically.

Meaning retrieval order is deterministic by:

- `language`
- `kind`
- `ord`
- local id only as a final within-asset deterministic fallback if necessary.

Lemma candidate lookup used by D46 must order by the accepted tuple, not numeric
ID.

Sense lookup orders by `ord`, then stable `semantic_ref`.

Do not add PART-B access to `app.dictionary`.

## A14 — `reference/schema.sql` PART-A repair only

Repair PART A to reflect A2–A9:

- `lemma.semantic_ref`
- `lemma.plural_none`
- `sense.semantic_ref`
- `sense.source_namespace`
- `sense.source_ref`
- remove normative `sense.gloss_en`
- add `sense_meaning`
- add `sense_meaning_derivation`
- document numeric IDs as per-asset local keys.

Keep:

- `surface_form`;
- `example`;
- `example_lemma`;
- their existing stage ownership.

Do NOT implement or repair PART-B ADR-0004 tables/columns here.

It is acceptable and intentional that PART B remains marked/known as the later
slice-7 owner.

## A15 — Regression and deterministic tests

Tests must prove at minimum:

1. original Stage-01 CLI remains unchanged;
2. original fail-closed/no-overwrite/atomic-output behaviours remain;
3. original POS/gender/IPA/forms behaviour remains;
4. `rief an` / `ruft an` still work;
5. exact lemma serialization + golden hashes;
6. exact sense serialization + golden hash;
7. NFC-equivalent lemma identity produces the same semantic ref;
8. source `senseid` path;
9. fallback source-ref path;
10. fallback is insensitive to whitespace-only differences;
11. fallback is insensitive to punctuation-only differences;
12. fallback changes for a real lexical sense change;
13. duplicate stable semantic refs fail closed;
14. one raw source sense with multiple glosses produces one `sense` and multiple
    `sense_meaning` rows rather than multiple semantic senses;
15. maximum three English meaning rows per lemma remains enforced;
16. every localized meaning row has nonblank source/license;
17. no `sense.gloss_en` column exists in Stage-01 output;
18. language column has no DE/EN/FA closed-list database CHECK;
19. valid D45 derivation edge passes;
20. generated marker violation fails;
21. generated source-side violation fails;
22. cross-sense derivation fails;
23. generated→generated derivation fails;
24. known plural state;
25. explicit `no-plural` state;
26. absent plural evidence remains UNKNOWN, not `plural_none=1`;
27. contradictory plural + `no-plural` fails closed;
28. resolver D46 component selection uses freq-rank/POS/gender/stable-ref tuple;
29. source-sense selection uses `ord`, then stable sense ref;
30. derived compound result contains ordered stable component bindings;
31. numeric ID differences do not alter stable semantic refs;
32. `app.dictionary.Dictionary` opens the aligned asset read-only;
33. all pre-existing resolver/Gate-1 cases still pass;
34. no PART-B tables are emitted by Stage 01.

## A16 — Report preservation

Do NOT replace or rewrite the accepted Attempt-1 narrative in
`tasks/slice-3.report.md`.

Preserve it verbatim.

Add near the top:

`Review: PENDING (T3, full diff)`

because this alignment is `Risk: migration`.

Then append:

`## ADR-0004 Stage-01 alignment amendment`

Record:

- accepted Attempt-1 SHA remains the historical baseline;
- this amendment is owner-driven and is not a WORKFLOW §5 retry;
- exact alignment commit SHA;
- exact targeted test counts;
- full `make gate` counts;
- stable-ref canonicalization/golden results;
- source-ref fallback stability evidence;
- D36/D45 schema/validation results;
- plural tri-state evidence;
- D46 stable component-binding evidence;
- changed-file list;
- Stop-and-ask conditions;
- work deliberately left for PART-B/slice-7 and smoke/slice-8.

## Stop-and-ask

STOP rather than redesign if:

- accepted `slice/3` is not exactly
  `7ceea14e39a7c831edfc803632d3c868ea0f3091` at start;
- current `main` does not contain accepted/frozen ADR-0004;
- implementation requires modifying ADR-0004;
- implementation requires PART-B/user DB/API/rendering/activation work;
- a real participating Wiktextract sense cannot be represented by the declared
  stable-id/fingerprint policy without choosing an unbriefed identity rule;
- source attribution cannot be represented by the D36/D45 tables;
- a required D46 binding would require guessing a semantic sense;
- a new dependency is required;
- any file outside the allowlist must change;
- Gate 1 resolver behaviour would need architectural redesign rather than the
  additive PART-A/binding extension;
- any command would overwrite an existing dictionary output;
- any stable-ref collision/ambiguity cannot fail closed.

## Verification

Before close, run:

- targeted Stage-01 alignment tests;
- `tests/test_dictionary.py`;
- `tests/test_resolve.py`;
- Gate-1 real-model resolver tests;
- `git diff --check`;
- full `make gate`.

Verify changed paths since the accepted slice-3 tip plus untracked files are
strictly inside the Allowlist.

Commit alignment work on top of the existing accepted `slice/3` history.

Do NOT merge/rebase/reset/rewrite the branch.

Push `slice/3`.

Print:

- accepted baseline SHA;
- new aligned slice/3 HEAD;
- targeted test counts;
- full gate counts;
- changed files;
- report path;
- `Review: PENDING (T3, full diff)`.

Stop. The implementation worker does NOT self-accept.
