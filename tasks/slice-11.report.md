# Slice 11 Report

## Starting state
- starting main SHA: 491a8083094eaf3f011ba393d68a71aceaee4778
- branch: slice/11
- startup clean state: confirmed via `git status --porcelain --untracked-files=all`
  (empty), `git rev-parse HEAD == 5c37768b7865ab2e8a7c42ba59facd9a1f206b78`,
  `git rev-parse origin/main == 491a8083094eaf3f011ba393d68a71aceaee4778`
- startup gate results (before this repair):
  - `.venv/bin/ruff check .` -> All checks passed!
  - `.venv/bin/mypy --strict .` -> Success: no issues found in 58 source files
  - `.venv/bin/pytest -q` -> 895 passed
  - `.venv/bin/python tools/check_agents.py` -> AGENTS checks passed
  - `.venv/bin/python tools/check_modules.py` -> MODULES validation passed: 22 modules

## Orchestrator pre-review repair

The primary orchestrator's pre-review identified seven concrete
implementation defects in the Slice 11 candidate. This report records
the bounded repair that closes them. ADR-0009 is **ACCEPTED / FROZEN**
and was not reopened. No production shards or releases were created.

- **Starting candidate:** `5c37768b7865ab2e8a7c42ba59facd9a1f206b78`

### R1 — entry-family scans are forbidden

The previous candidate's `sense_route`, `_lemma_ref_for_numeric_id`,
and `_sense_ref_for_numeric_id` methods scanned all 256 entry shards.
The repair introduces an independent `sense_route(sense_ref, lemma_ref)`
table **inside** the lookup shard family, bucket-closed on
`bucket256_v1(sense_ref)` (per ADR-0009). The runtime
`OnlineDictionaryProvider.sense_route(sense_ref)` opens exactly one
lookup shard and queries `sense_route(sense_ref) -> lemma_ref`.
Numeric IDs are session-local cache identities only: the provider
populates `_lemma_id_to_ref`, `_sense_id_to_ref`,
`_sense_id_to_lemma_ref` from rows it legitimately observes through
lookup hits, senses-for-ref reads, and entry-shard materialization. A
cold unknown numeric ID yields documented cache-miss semantics
(`None` / `()`) without any 256-bucket remote scan. Builder
validation in `_validate_sense_route_partitions` proves every
authoritative `sense_ref` lands in exactly one sense-route bucket and
points to its real parent `lemma_ref`. The inflight-dict bookkeeping
bug in `ShardCache.lease` (which overwrote the dict on every
identity) is also fixed as part of the cache refactor.

Regression tests (added to `tests/test_provider_differential.py`):
- `test_sense_route_resolves_via_lookup_shard_only`
- `test_sense_route_does_not_scan_all_entry_shards`
- `test_cold_numeric_lemma_id_returns_documented_cache_miss`

### R2 — compound sense lookup uses wrong entry bucket

The previous `_select_component_text(sense_ref)` opened an entry shard
on `bucket256_v1(sense_ref)`. The repair routes it through
`sense_route(sense_ref) -> lemma_ref` first (R1's lookup-shard index)
and only then opens the entry shard on `bucket256_v1(lemma_ref)`. The
differential test
`test_compound_components_routes_sense_via_lookup_then_entry` asserts
the compound path never requests `("entry", bucket256_v1(sense_ref))`
and does request `("lookup", bucket256_v1(sense_ref))`.

### R3 — example shards must be the actual example source

The previous candidate duplicated the full example payload into the
entry shard. The repair removes the entry shard's `example` table and
the entry shard writer's example-payload inserts. Entry shards carry
only `lemma / sense / sense_meaning / surface_form / example_lemma`;
example rows live exclusively in the 64-shard example family keyed by
`example.id % 64`. `OnlineDictionaryProvider.examples_for_lemma` now:
1. fetches the `example_lemma` join from the entry shard;
2. groups example IDs by `example_bucket(example_id) = id % 64`;
3. acquires only the required example shards;
4. reads the authoritative example records from the example family;
5. materializes `ExampleRecord` from those rows.

Regression tests (added to `tests/test_provider_differential.py`):
- `test_entry_shard_does_not_carry_example_payload`
- `test_example_shards_carry_full_example_payload`
- `test_example_bucket_assignment_is_example_id_modulo_64`
- `test_example_id_refs_point_to_existing_example_records`

### R4 — Bloom filter is not production-scalable

The previous Bloom filter hardcoded `size_bits = 512` and only had two
SHA-256-derived bit positions per inserted text. The repair replaces
this with a fully scalable filter using the standard Bloom formulas
sized from the actual deduplicated closure-key count:

    m = ceil(-n * ln(p) / (ln(2)^2))  rounded up to whole bytes
    k = max(1, round((m / n) * ln(2)))

with target `p = 0.01`. Hash positions use deterministic SHA-256
double-hashing `(h1 + i * h2) % m` for `i = 0..k-1` (no `hash()`). The
serialized payload carries a self-describing header
(`WFBL` magic + version + hash_count + size_bits) followed by the
bit payload; the loader reads the actual parameters and never assumes
a 512-bit production size. For the production-scale closure-key count
`n = 1_477_819` the test
`test_bloom_size_bits_for_production_corpus_evidence` asserts the
filter sizes into the ADR-0009 evidence band (~1.69 MiB, `k ≈ 7`).
Malformed, truncated, wrong-magic, and zero-hash-count payloads are
rejected fail-closed. FPR remains statistical only (no deterministic
percentage claim).

Regression tests (added to `tests/test_routing_equivalence.py`):
- `test_bloom_size_bits_matches_standard_formula`
- `test_bloom_size_bits_byte_aligned`
- `test_bloom_size_bits_grows_with_item_count`
- `test_bloom_hash_count_uses_optimal_k_formula`
- `test_bloom_hash_count_at_least_one`
- `test_bloom_size_bits_for_production_corpus_evidence`
- `test_bloom_filter_size_grows_with_inserted_keys`
- `test_bloom_filter_self_describing_payload`
- `test_bloom_filter_loaded_reads_recorded_size`
- `test_bloom_filter_rejects_truncated_payload`
- `test_bloom_filter_rejects_wrong_magic`
- `test_bloom_filter_rejects_zero_hash_count`
- `test_bloom_filter_large_synthetic_does_not_saturate`
- `test_bloom_filter_fpr_is_statistical_no_deterministic_claim`

### R5 — Product HTTP transport is missing

The previous ShardCache accepted `transport: Callable[[ShardRequest], bytes]`
but no production Product transport existed. The repair adds
`app/online_transport.py` with the trusted GitHub Release transport:

- URL is built internally from `TrustedDistribution.base_origin`
  (`https://github.com`), the `release_tag`, and the committed
  Wortlaut repo `sabers13/wortlaut`; the caller never supplies a URL,
  host, manifest URL, or redirect target.
- HTTPS-only; userinfo rejected; unexpected ports rejected; arbitrary
  hosts rejected; plain HTTP rejected.
- Every redirect is validated before follow-through against a small
  explicit allowlist (`github.com`, `objects.githubusercontent.com`,
  `githubusercontent.com`); redirect loop / excessive redirects are
  rejected.
- Network / DNS / SSL failures raise `ProviderNetworkError` and never
  become a dictionary miss.
- An injectable low-level opener seam drives every redirect case so
  tests never reach the public GitHub network.
- Constructor seams: `create_product_shard_cache` and
  `create_product_online_provider` install the trusted Product
  transport automatically. Slice 12 does not have to know about
  redirect policy or construct a transport callable.

Regression tests (added to `tests/test_online_transport.py`, 15 tests):
- `test_initial_url_is_exact_github_release_form`
- `test_approved_release_redirect_is_accepted`
- `test_arbitrary_host_redirect_is_rejected`
- `test_plain_http_redirect_is_rejected`
- `test_userinfo_redirect_is_rejected`
- `test_unexpected_port_redirect_is_rejected`
- `test_redirect_loop_is_rejected`
- `test_non_2xx_response_is_rejected`
- `test_connection_failure_is_a_network_error`
- `test_ssl_failure_is_a_network_error`
- `test_url_error_is_a_network_error`
- `test_successful_payload_is_returned`
- `test_caller_cannot_supply_arbitrary_product_source`
- `test_create_product_shard_cache_uses_trusted_transport`
- `test_create_product_online_provider_uses_trusted_transport`

### R6 — budget must count real new remote lookup downloads

The previous `_lease_with_budget` charged the budget iff the
canonical pathname did not exist before the call, so a corrupt cached
artifact that required a remote refetch was not charged. The repair
moves the charge decision to the cache layer: `ShardLease` now carries
a `was_downloaded` boolean set by the cache, and
`OnlineDictionaryProvider._lease_with_budget` charges the budget iff
`lease.was_downloaded is True`. Entry / example shards remain free of
charge. Verified cached reads, single-flight waiters, and clear-cache
rebuilds are all accounted for correctly. Duplicate identities inside
one operation count once.

Regression tests (added to `tests/test_provider_differential.py`):
- `test_budget_does_not_charge_for_verified_cached_reads`
- `test_budget_charges_for_each_new_download_identity`
- `test_budget_rejects_on_33rd_real_download`
- `test_lease_was_downloaded_flag_tracks_real_downloads`
- `test_corrupt_refetch_counts_as_new_download`

### R7 — top-level operation budget continuity

The previous candidate's `lookup_exact`, `lookup_surface_form`, and
`candidate_lookup` each created a fresh `_Budget` per call, so a
compound / resolver sequence could bypass the 32 limit by accidentally
resetting the budget at every nested call. The repair adds
`OnlineDictionaryProvider.operation()` — a context manager that binds
one `_Budget` to a `contextvars.ContextVar`. Nested reads consult the
active operation budget; reads outside any `operation()` block fall
back to a fresh throwaway budget (preserving back-compat). The
ContextVar is task-local, not process-global.

Regression tests (added to `tests/test_provider_differential.py`):
- `test_operation_context_shares_one_budget_across_nested_calls`
- `test_operation_does_not_reset_budget_on_nested_method`
- `test_top_level_compound_like_sequence_cumulative_budget`
- `test_operation_budget_is_not_process_global`

## Final validation

- `git diff --check` -> clean (no whitespace errors)
- `.venv/bin/ruff check .` -> All checks passed!
- `.venv/bin/mypy --strict .` -> Success: no issues found in 60 source files
- `.venv/bin/pytest -q` -> 941 passed, 120 warnings in 380.84s
  - added 1 new focused test module (`tests/test_online_transport.py`,
    15 tests) and additional regression tests in
    `tests/test_routing_equivalence.py` and
    `tests/test_provider_differential.py`
- `.venv/bin/python tools/check_agents.py` -> AGENTS checks passed:
  R1, R3, R6, R7, R12, R13
- `.venv/bin/python tools/check_modules.py` -> MODULES validation
  passed: 22 modules
- `make gate` final result: PASS

### Focused-test counts after repair
- `tests/test_routing_equivalence.py` -> 30 passed (was 16; added
  R4 regression coverage).
- `tests/test_online_manifest.py` -> 22 passed (unchanged).
- `tests/test_online_cache.py` -> 11 passed (unchanged).
- `tests/test_build_online_dictionary.py` -> 6 passed (unchanged;
  one signature update).
- `tests/test_online_transport.py` -> 15 passed (new).
- `tests/test_provider_differential.py` -> 36 passed (was 19; added
  R1/R2/R3/R6/R7 regression coverage; three tests were updated to
  follow the documented `lookup_exact -> numeric-ID` flow).

## Security/integrity

- **Trust-negative manifest tests:** `tests/test_online_manifest.py`
  asserts the parser fails closed on missing/wrong dataset token,
  malformed SHA, wrong byte size, duplicate identity, duplicate
  path, path traversal, invalid family, invalid bucket, missing
  family bucket, HTTP origin, userinfo origin, non-root origin
  path, and unsupported redirect policy.
- **Trust-negative Product transport tests:**
  `tests/test_online_transport.py` asserts the policy fails closed
  on HTTP redirect, userinfo redirect, unexpected port redirect,
  arbitrary-host redirect, redirect loop, non-2xx response,
  connection failure, SSL failure, and URL error — and asserts the
  initial request URL is exactly the committed GitHub Release form.
- **Cache corruption:** `test_corrupt_canonical_artifact_is_quarantined_and_refetched`
  writes garbage into the canonical artifact and proves the cache
  quarantines it and refetches. `test_corrupt_refetch_counts_as_new_download`
  proves the corruption refetch is charged as a new download.
- **No browser/caller source override:** the Product transport's
  trusted distribution is fixed at construction; the API cannot pass
  a custom URL. `test_caller_cannot_supply_arbitrary_product_source`
  asserts the transport does not expose any host/URL/manifest
  parameter.
- **No PART-B mutation on provider failure:**
  `test_lookup_failure_does_not_mutate_part_b` proves that a
  provider integrity failure does not write any row to the user DB.
- **Network trust:** the focused differential tests exercise the
  entire provider against a deterministic, local-only transport
  fixture; the Product transport tests inject a low-level opener
  seam that drives every redirect case; no real network is touched.

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

## Scope

### Changed paths

Modified (within the Slice 11 allowlist):

- `app/online_cache.py` — `ShardLease.was_downloaded`, inflight
  bookkeeping fix, dedicated download path.
- `app/online_filter.py` — scalable Bloom sizing, double-hashing,
  self-describing serialization (`WFBL` magic + version +
  size_bits + hash_count).
- `app/provider_online.py` — lookup-shard sense_route, compound
  routing via sense_route, example payload from example family,
  session-local numeric ID cache maps, `operation()` context
  manager, `_lease_with_budget` driven by `lease.was_downloaded`.
- `app/online_transport.py` (new) — trusted Product HTTP transport
  with redirect validation, network-error mapping, and the
  Slice-12-ready `create_product_shard_cache` /
  `create_product_online_provider` constructors.
- `tools/build_online_dictionary.py` — `sense_route` partitioning
  and writer integration, builder validation
  (`_validate_sense_route_partitions`), removal of example payload
  from the entry shard writer, dynamic Bloom closure-key sizing.
- `MODULES.toml` — `app/online_transport.py` and the new
  `tests/test_online_transport.py` are owned by the existing
  `online_cache` module (no new module added).
- `tests/test_provider_differential.py` — fixture now uses the
  new partitioner signatures; R1/R2/R3/R6/R7 regression tests
  added; three parity tests updated to the documented
  `lookup_exact -> numeric-ID` flow.
- `tests/test_routing_equivalence.py` — R4 scalable-Bloom
  regression tests added; one signature update for the new
  `from_bytes(payload)` (no `size_bits` argument).
- `tests/test_build_online_dictionary.py` — one signature update
  for the new `_partition_lookup_shards` return value.
- `tests/test_online_transport.py` (new) — 15 R5 transport trust
  tests.
- `release/README.md` — added a short paragraph noting the
  sense_route table, the example-family separation, the dynamic
  Bloom filter, and the trusted Product transport.
- `tasks/slice-11.report.md` — this update.

Not modified:

- `app/provider.py`, `app/provider_local.py`, `app/routing.py`,
  `app/online_manifest.py`, `app/dictionary.py`, `app/deck.py`,
  `app/api.py` (unchanged).
- `release/dictionary-online-manifest-v2.json` (fixture schema
  unchanged).
- The committed corpus files (`release/*.sqlite`) — none exist
  for the Online corpus.

### `tests/test_check_modules.py` authorization

The previous candidate changed `tests/test_check_modules.py` from
the hard-coded expected module count `18 -> 22` because Slice 11
legitimately registered new modules in `MODULES.toml`. The primary
orchestrator explicitly authorized this exact mechanical co-change
during pre-review repair dispatch:

> The original brief did not list this test path. The PRIMARY
> ORCHESTRATOR NOW EXPLICITLY AUTHORIZES that exact mechanical
> co-change. It is not a blocker and does not require another
> governance session.

This authorization is recorded here for traceability. No further
broadening of `tests/test_check_modules.py` was made.

## Commit

- starting candidate: `5c37768b7865ab2e8a7c42ba59facd9a1f206b78`
- repaired SHA: see `git rev-parse HEAD` on `slice/11` after the
  commit below.
- subject: `fix(dictionary): close online provider routing gaps`
- branch: `slice/11`
- origin/slice/11: pushed to equal the repaired SHA.
- origin/main: still `491a8083094eaf3f011ba393d68a71aceaee4778`
  (unchanged).
- clean worktree: `git status --short --untracked-files=all` empty
  after the final commit.
