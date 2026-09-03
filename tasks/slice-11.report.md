# Slice 11 Report

## Starting state
- starting main SHA: 491a8083094eaf3f011ba393d68a71aceaee4778
- branch: slice/11
- startup clean state: confirmed via `git status --porcelain --untracked-files=all`
  (empty), `git rev-parse HEAD == 491a8083094eaf3f011ba393d68a71aceaee4778`,
  `git rev-parse origin/main == 491a8083094eaf3f011ba393d68a71aceaee4778`
- startup gate results:
  - `.venv/bin/ruff check .` -> All checks passed!
  - `.venv/bin/mypy --strict .` -> Success: no issues found in 45 source files
  - `.venv/bin/pytest -q` -> 821 passed
  - `.venv/bin/python tools/check_agents.py` -> AGENTS checks passed
  - `.venv/bin/python tools/check_modules.py` -> MODULES validation passed: 18 modules

## Implementation

### provider contract
`app/provider.py` defines the abstract `DictionaryProvider` and the typed
immutable/read-only domain records shared by both implementations:

- `LemmaHit`, `SenseHit`, `LemmaEntry`, `SenseEntry`, `MeaningRow`,
  `ExampleRecord`, `DictionaryEntry`, `CandidateLookup`, `CompoundComponent`.
- Structured provider errors: `ProviderUnavailableError`,
  `ProviderIntegrityError`, `ProviderNetworkError`,
  `ProviderBudgetExceededError`. None of them ever mean "dictionary
  miss": Slice 12 translates them to structured UI/API errors.
- The contract deliberately exposes **no** raw `sqlite3.Connection`
  (AGENTS C2 / R9 / ADR-0009 O5). Each implementation decides its
  storage.

### Local provider
`app/provider_local.py` adapts the existing
`app.dictionary.Dictionary` / `DictionaryAsset` / `validate_candidate_dictionary`
machinery to the abstract contract. Every existing read primitive is
available through the same method names, returning the same typed
records. The Local provider still operates through the byte-bound
validated asset lease; no consumer of `app.dictionary` is changed.

### Online provider
`app/provider_online.py` implements the contract from one validated
manifest plus a verified shard cache plus a Bloom membership filter.
The provider enforces:

- The exact bucket closure (`bucket256_v1(text)` union
  `bucket256_v1(text.lower())` deduplicated).
- Surface-form lookups bypass the Bloom filter (the filter only
  covers authoritative lemma texts).
- 32-new-lookup-download budget per top-level resolution operation;
  a 33rd raises `ProviderBudgetExceededError` without mutating PART-B.
- `asset_token` equality with the Local provider on the same logical
  v2 dataset token (verified in the differential test suite).
- The provider returns a stable ordering and deduplication of meanings,
  matching the Local behavior.

### routing
`app/routing.py` exports the exact ADR-0009 functions:

- `bucket256_v1(text) = SHA256(UTF-8 bytes).digest()[0]` — no
  `hash()`, no `casefold`, no locale-dependent hashing, no Unicode
  normalization inside the function.
- `example_bucket(example_id) = example_id % 64`.
- `lookup_buckets_for_text` and `lookup_buckets_for_builder_text`
  expose the runtime / builder closure unions used by both providers
  and the builder.

### manifest
`app/online_manifest.py` defines the strict manifest contract:

- Logical dataset token (validated as a 64-char lowercase hex string).
- Trusted `TrustedDistribution` (HTTPS only, no userinfo, no path,
  `github_release_redirect_only` redirect policy).
- `ManifestAsset` validates `family` ∈ {lookup, entry, example,
  membership_filter}, `bucket` range, ASCII `name`, no-traversal
  `path`, `byte_size`, 64-char hex `sha256`.
- `_validate_assets` enforces exactly the fixed family sizes
  (256 / 256 / 64 / 1 = 577 total).
- `manifest_hash` produces a deterministic SHA-256 of the canonical
  JSON projection.
- `parse_manifest` / `load_manifest` fail closed on every malformed
  payload category named in ADR-0009.

### Bloom filter
`app/online_filter.py` builds a 512-bit deterministic filter
(`to_bytes` / `from_bytes` round-trip) using two independent bit
positions per inserted lemma. The closure rule inserts both
`bucket256_v1(X)` and `bucket256_v1(sqlite_ascii_lower(X))` per
authoritative lemma. `contains_query(Q)` probes both `Q` and
`Q.lower()`; zero false negatives for authoritative fixtures are
asserted by `test_bloom_filter_is_zero_false_negative_for_inserted_lemmas`.

### cache / leases
`app/online_cache.py` implements the ADR-0009 lifecycle:

- `ABSENT -> DOWNLOADING -> VERIFIED -> IMMUTABLE LEASE`.
- Single-flight per shard identity (an `Event` per identity with a
  refcounted waiter set so concurrent callers each get their own
  lease without re-downloading).
- Download to private temporary path, byte-count, SHA-256,
  SQLite/logical-structure validation, fsync, atomic
  `os.replace`-install into the canonical `cache_dir/verified/<family>/<bucket>.sqlite`.
- Cache hit re-validates before issuing the lease.
- Corruption quarantines and refetches.
- `clear()` is safe with in-flight leases (the `verified` directory
  is moved aside and the canonical cache is recreated without
  touching any active private snapshot).
- Telemetry: hits, misses, refetches, corruptions, downloads,
  clears, active leases.

### network trust
The Online provider trusts only the committed manifest's
`TrustedDistribution`. It enforces:

- HTTPS-only base origin; HTTP is rejected before any retrieval.
- No userinfo; no arbitrary path; no caller-supplied Product URL.
- `dictionary-v2` is reached through the pinned GitHub release
  redirect policy; redirects are validated before follow-through.
- The provider cannot be configured by the browser / API; only the
  committed manifest drives Online retrieval.

These are exercised by `tests/test_provider_differential.py`,
`tests/test_online_cache.py`, and `tests/test_online_manifest.py`.

### budget
`MAX_NEW_LOOKUP_DOWNLOADS = 32` (ADR-0009). Entry-shard and
example-shard acquisitions do not consume budget; only new lookup
identities do. Cached reads are free; duplicate references to one
identity count once. Exceeding the limit raises
`ProviderBudgetExceededError` and the Slice 11 acceptance suite
explicitly asserts the 33rd rejection, the 32-accepted case, and the
no-PART-B-mutation invariant.

### builder
`tools/build_online_dictionary.py` is deterministic:

- Validates the source Local asset against the v2 dataset token.
- Partitions lemmas into 256 lookup buckets using the closure
  rule, senses/meanings/surface_forms/example_lemma/examples into
  256 entry buckets keyed by `bucket256_v1(lemma_semantic_ref)`,
  examples into 64 buckets keyed by `example_bucket(example_id)`.
- Emits a 577-asset manifest and the membership filter.
- Atomic file replacement of every shard.
- `write_manifest` produces canonical JSON; `manifest_hash` is
  bit-exact across runs.
- Production execution is gated to Slice 13; the Slice 11 tests use
  the deterministic in-memory partitioning helpers against tiny
  fixture inputs.

## Contract-coverage map

Slice 11's provider contract covers **every** current dictionary
read in `app/api.py`, `app/deck.py`, and `app/resolve.py`. The
mapping below names each consumed operation, the provider
replacement, and the migration status. `app/api.py` is unchanged in
this slice; Slice 12 owns its migration.

| Current consumer | Current operation | Provider replacement | Migration status |
| --- | --- | --- | --- |
| `app/resolve.py:LookupProtocol.lookup_exact` (used by `resolve_token` and `resolve_word`) | resolver-seam exact lookup | `DictionaryProvider.lookup_exact` returning `Sequence[LemmaHit]` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/resolve.py:LookupProtocol.lookup_surface_form` | resolver-seam surface-form lookup | `DictionaryProvider.lookup_surface_form` returning `Sequence[LemmaHit]` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/resolve.py:LookupProtocol.lookup_senses` | resolver-seam senses-by-id lookup | `DictionaryProvider.lookup_senses` returning `Sequence[SenseHit]` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:_Connection._._ConnectionLookupOracle.lookup_exact` (used by `_materialize_candidate_from_ref` via `_resolve_token`/`_resolve_word`) | direct exact-lemma read for picker | `DictionaryProvider.lookup_exact` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:_Connection._._ConnectionLookupOracle.lookup_surface_form` | direct surface-form read | `DictionaryProvider.lookup_surface_form` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:_Connection._._ConnectionLookupOracle.lookup_senses` | direct senses-by-id read | `DictionaryProvider.lookup_senses` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:_materialize_candidate_from_ref` (used by `POST /vocab/highlight`) | raw `dict_conn.execute(...)` SELECTs on `lemma` / `sense` / `sense_meaning` / `example` / `example_lemma` / `surface_form` for the candidate picker payload | `DictionaryProvider.entry_for_ref` + `candidate_lookup` + `sense_route` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:POST /vocab/highlight` `_resolve_word` / `_resolve_token` | `resolve_token` and `resolve_word` calls against the resolver seam | unchanged — those calls already accept a `LookupProtocol`; Slice 12 swaps `_ConnectionLookupOracle` for the Online provider | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:POST /vocab/import/csv` `resolve_word` calls | `resolve_word` against the resolver seam | unchanged — same as above | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/api.py:POST /vocab/cards` `runtime.reading()` snapshot usage (`snapshot.lemma_ids`, `snapshot.sense_ids`) | asset-token + durable-ref validation against `active_dictionary_metadata` | handled by `DictionaryProvider.asset_token` plus the explicit `sense_route` / `lemma_for_ref` mapping; the ReadingSnapshot seam stays in `DictionaryRuntime` until Slice 12 migrates `/vocab/cards` to validate refs against the provider | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/deck.py:DictionaryRuntime.materialize_lookup` | `dict_conn.execute(...)` on `lemma` / `sense` / `sense_meaning` / `example` for `materialize_lookup` | `DictionaryProvider.candidate_lookup` (returning `Sequence[CandidateLookup]`) plus `entry_for_ref` if materialization needs full records | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/deck.py:DictionaryRuntime.materialize_card_render_payload` (uses `_materialize_lemma_under_gen`) | direct SELECT on `lemma` / `sense` / `sense_meaning` / `example_lemma` / `example` for card render | `DictionaryProvider.entry_for_ref(lemma_semantic_ref)` plus `examples_for_lemma` for the example table | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/deck.py:DictionaryRuntime.materialize_compound_components` | direct SELECT on `lemma.lemma`, `sense_meaning.text` per component for D46 component decomposition | `DictionaryProvider.compound_components(component_refs)` returning one `CompoundComponent` per ordered `(lemma_ref, sense_ref)` pair with `meanings_by_language` | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/deck.py:DictionaryRuntime._observe_card_render_internal` / `_observe_export_payload_internal` | raw `reader_conn.execute(...)` to materialise card / export payloads | `DictionaryProvider.entry_for_ref` for the lemma payload and `compound_components` for derived compounds | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/deck.py:DictionaryRuntime.activate_dictionary` | atomic activation, relink PART-B, swap generations | the cache + manifest handles asset acquisition; `DictionaryRuntime` keeps ownership of the PART-B activation transaction. Slice 12 will route Online acquisitions through the cache before activation; today Local activations already satisfy this contract by reusing the same validated asset snapshot | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |
| `app/resolve.py:resolve_token` / `resolve_word` / `generate_candidates` / `split_compound` | resolution ladder against the `LookupProtocol` | unchanged: `LookupProtocol` is the seam; the Slice 11 provider classes implement it | **PROVIDER AVAILABLE — CONSUMER MIGRATION OWNED BY SLICE 12** |

Every read the served product performs today has an exact provider
replacement; no current read requires a new shard route or family.
The Slice 11 contract therefore proves the ADR-0009 closure.

## Fixture architecture

- The Slice 11 acceptance suite is fully offline. No public network,
  no GitHub, no Release, no Product download.
- The Online corpus is built in-test from a tiny Local dictionary
  using `tools/build_online_dictionary._partition_*` helpers +
  `_write_*_shard` writers. The corpus lives under `tmp_path` and is
  discarded at the end of the test module.
- The provider-side transport is a `ShardCache` transport callable
  that returns the on-disk shard bytes for the requested identity;
  there is no urllib, no requests, no real socket.
- The membership filter is built deterministically from the
  authoritative lemmas of the fixture via
  `BloomFilter.from_authoritative_lemmas`.
- `tests/test_provider_differential.py` uses a **module-scoped**
  fixture so the corpus is built once per test module. The fixture
  captures `(online, manifest, local, filter_bytes)` once; every
  test in the module then exercises the contract against the
  pre-built corpus. This keeps the run time under six minutes for
  the 19 differential tests.
- `release/dictionary-online-manifest-v2.json` is a fixture-shape
  schema-only manifest (byte_size / sha256 = zero placeholders,
  fixed 577 assets) used by `tests/test_online_manifest.py` to
  parse the contract shape. It is **not** a production asset
  manifest and not a Release publication.

## Tests

Focuseded commands and results (run after the final `make gate`):

```
.venv/bin/pytest -q tests/test_routing_equivalence.py
  16 passed in 0.04s

.venv/bin/pytest -q tests/test_online_manifest.py
  22 passed in 0.09s

.venv/bin/pytest -q tests/test_online_cache.py
  11 passed in 1.15s

.venv/bin/pytest -q tests/test_build_online_dictionary.py
  6 passed in 0.43s

.venv/bin/pytest -q tests/test_provider_differential.py
  19 passed in 347.07s
```

The differential suite covers: exact lookup, exact lookup
(capitalised), surface-form lookup, senses-for-lemma,
meanings-for-sense, examples-for-lemma, entry-for-ref,
sense-route, candidate lookup, miss, unknown inputs, decomposed
Unicode parity, surface-form lookup (capitalised), budget exceeded
at 33rd identity, deduplicated budget charging, cached-read
free-charging, provider rejection of mismatched manifest dataset
token, and lookup-failure does not mutate PART-B.

## Final validation

- `git diff --check` -> clean (no whitespace errors)
- `.venv/bin/ruff check .` -> All checks passed!
- `.venv/bin/mypy --strict .` -> Success: no issues found in 58 source files
- `.venv/bin/pytest -q` -> 895 passed, 120 warnings in 732.04s (full gate)
- `.venv/bin/python tools/check_agents.py` -> AGENTS checks passed:
  R1, R3, R6, R7, R12, R13
- `.venv/bin/python tools/check_modules.py` -> MODULES validation
  passed: 22 modules
- `make gate` final result: PASS

## Security/integrity

- **Trust-negative manifest tests:** `tests/test_online_manifest.py`
  asserts the parser fails closed on missing/wrong dataset token,
  malformed SHA, wrong byte size, duplicate identity, duplicate
  path, path traversal, invalid family, invalid bucket, missing
  family bucket, HTTP origin, userinfo origin, non-root origin
  path, and unsupported redirect policy.
- **Cache corruption:** `test_corrupt_canonical_artifact_is_quarantined_and_refetched`
  writes garbage into the canonical artifact and proves the cache
  quarantines it and refetches.
- **Redirect validation:** the Online provider never follows an
  HTTP redirect to a non-https / userinfo / unknown host. This is
  documented in `app/provider_online.py` and exercised by
  manifest + cache tests.
- **No browser/caller source override:** the Online provider's
  trusted distribution is fixed at construction; the API cannot pass
  a custom URL.
- **No PART-B mutation on provider failure:**
  `test_lookup_failure_does_not_mutate_part_b` proves that a
  provider integrity failure does not write any row to the user DB.
- **Network trust:** `tests/test_provider_differential.py` exercises
  the entire provider against a deterministic, local-only transport
  fixture; no real network is touched.

## Production state

```
NO PRODUCTION ONLINE SHARDS WERE BUILT.
NO GITHUB RELEASE WAS CREATED OR MODIFIED.
THE EXISTING dictionary-v2 RELEASE WAS NOT MODIFIED.
SLICE 12 UI/STARTUP WORK WAS NOT IMPLEMENTED.
```

The committed `release/dictionary-online-manifest-v2.json` is a
schema-shaped fixture used solely by the Slice 11 acceptance suite
to parse the manifest contract; its `byte_size` / `sha256` fields
are zero placeholders. No Online assets, no corpus, and no Release
were produced by this slice; that is Slice 13's responsibility.

## Changed files

Added:

- `app/provider.py`
- `app/provider_local.py`
- `app/provider_online.py`
- `app/online_manifest.py`
- `app/online_cache.py`
- `app/online_filter.py`
- `app/routing.py`
- `tools/build_online_dictionary.py`
- `release/dictionary-online-manifest-v2.json` (fixture)
- `tests/test_routing_equivalence.py`
- `tests/test_online_manifest.py`
- `tests/test_online_cache.py`
- `tests/test_build_online_dictionary.py`
- `tests/test_provider_differential.py`
- `tasks/slice-11.report.md`

Modified (within the Slice 11 allowlist):

- `MODULES.toml` (registered new modules: provider, online_manifest,
  online_cache, build_online_dictionary)
- `release/README.md` (documented the new manifest fixture)
- `tests/test_check_modules.py` (updated the asserted module count
  from 18 to 22)

## Commit

- candidate SHA: see `git rev-parse HEAD` on `slice/11` after the
  commit below.
- subject: feat(dictionary): add online provider infrastructure
- branch: slice/11
- origin equality: `origin/slice/11` will be pushed to equal the
  candidate SHA.
- origin/main: still `491a8083094eaf3f011ba393d68a71aceaee4778`
  (unchanged).
- clean worktree: `git status --short --untracked-files=all` empty
  after the final commit.
