# Slice 11 — Core online dictionary infrastructure

**BLOCKED until ADR-0009 passes cold review #1 and is frozen.**

Task: Build and prove the provider-level Online dictionary infrastructure from
the ADR-0009 contract, with no startup chooser or Settings product work.

Depends: ADR-0009 approved and frozen.

Allowlist:
- `app/provider.py` (new), `app/provider_local.py` (new),
  `app/provider_online.py` (new), `app/online_manifest.py` (new),
  `app/online_cache.py` (new), `app/online_filter.py` (new), and
  `app/routing.py` (new)
- `app/dictionary.py`, `app/deck.py`
- `tools/build_online_dictionary.py` (new)
- `release/dictionary-online-manifest-v2.json` (fixture/schema-shaped metadata
  only; no production assets), `release/README.md`
- `tests/test_provider_differential.py` (new),
  `tests/test_routing_equivalence.py` (new), `tests/test_online_cache.py` (new),
  `tests/test_online_manifest.py` (new),
  `tests/test_build_online_dictionary.py` (new), `tests/test_dictionary.py`,
  `tests/test_deck.py`, `tests/conftest.py`
- One additional new focused test file directly required for Slice 11's own
  provider-contract acceptance (e.g. a contract-coverage test exercising the
  inventoried `app/api.py` / `app/deck.py` / `app/resolve.py` read shapes
  against both providers) may be added if genuinely necessary; anything
  further is Stop-and-ask, not silent scope growth.
- `MODULES.toml` only if required to register the new owned modules
- `tasks/slice-11.report.md`

Required reading: `docs/adr/0009-session-scoped-online-dictionary.md`,
`docs/adr/0001-flashcards-core.md`, `docs/adr/0004-multilingual-learner-meanings.md`,
`AGENTS.md`, `MODULES.toml`, `app/dictionary.py`, `app/deck.py`, `app/resolve.py`,
`app/api.py` (read-only, for the dictionary-read inventory — this brief does
not authorize editing it), relevant dictionary/deck tests, and
`tasks/slice-11.md`.

Acceptance:

1. `LocalDictionaryProvider` and `OnlineDictionaryProvider` share an explicit
   provider contract and are different transports for v2 token
   `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.
   Provider switching makes no D47 relink; stable refs remain authoritative.
   No generic raw SQLite connection is exposed as the provider abstraction.
2. **Contract-coverage map (new).** Inventory every real dictionary read
   performed by `app/api.py`, `app/deck.py`, and `app/resolve.py` today —
   resolver exact lookup, resolver surface-form lookup, sense lookup,
   `sense_ref → lemma_ref` point routing, lemma/candidate materialization by
   stable semantic ref, meanings needed by candidate/card materialization,
   examples needed by candidate/card materialization, and any other current
   served-product dictionary read discovered during the inventory. The
   provider contract's operations must cover all of them. The report records
   an explicit table: `current consumer/call site -> provider operation`,
   naming at minimum `app/api.py`'s `_ConnectionLookupOracle.lookup_exact`,
   `.lookup_surface_form`, `.lookup_senses`, and `_materialize_candidate_from_ref`
   (used by `POST /vocab/highlight` and `POST /vocab/import/csv`), plus
   `app/deck.py`'s `DictionaryRuntime` reader-connection consumers. If any
   current read cannot be covered without a new shard route/family, STOP —
   that is an architecture boundary, not an implementation choice for this
   slice to resolve alone. Slice 11 itself still does not modify `app/api.py`.
3. A deterministic builder creates the fixed 256 lookup / 256 entry / 64
   example / 1 membership-filter families from a verified full asset, preserves
   semantic/provenance values, and emits an exact, strictly validated manifest.
   Tiny fixture assets are committed only for CI; production assets are not.
4. **Exact routing functions (new).** Implement `bucket256_v1(text) =
   SHA256(UTF-8 bytes of text).digest()[0]` (integer 0..255; no Python
   `hash()`, no locale-dependent hashing, no casefolding or Unicode
   normalization inside the function) unless an already-binding repository
   helper provides an equivalent function. Entry bucket =
   `bucket256_v1(lemma_semantic_ref)`; sense route bucket =
   `bucket256_v1(sense_ref)` for `sense_ref → lemma_ref` routing. Example
   shard routing is exactly `example_bucket(example_id) = example_id % 64`
   against the authoritative `example.id`; the builder preserves authoritative
   example IDs exactly. Tests must prove the route is exact and
   machine-checkable, must never call `example.id` a stable semantic
   identity, and the production builder validation must prove every emitted
   example is in exactly its expected bucket. Record the finite family bound
   (64 example shards, ~92.6 MB total per the prior verified-v2 probe) as an
   operational fact, not a new per-query correctness budget.
5. **Lookup/normalization closure (new).** Preserve the exact current
   observable predicate `X == Q OR sqlite_ascii_lower(X) == python_lower(Q)`
   (`sqlite_ascii_lower` = SQLite's built-in ASCII-oriented `lower()`;
   `python_lower` = Python `str.lower()`) — never `casefold()`, Unicode-wide
   SQLite lowering, or NFC/NFKC normalization. For each authoritative
   lookup-index row `X` (applied independently to the lemma and
   surface-form lookup indexes), the builder places/indexes that row in the
   union of `bucket256_v1(X)` and `bucket256_v1(sqlite_ascii_lower(X))`
   (deduplicated when equal). At runtime, for query `Q`, the Online provider
   fetches the union of `bucket256_v1(Q)` and `bucket256_v1(python_lower(Q))`
   (deduplicated when equal), then applies the exact predicate above to the
   fetched candidates. Routing may over-approximate; it must never
   under-approximate. No query string is assumed to be NFC: the Online
   provider must match whatever `LocalDictionaryProvider` does for the exact
   input, including a decomposed/non-NFC query returning no result if that is
   what Local returns. The Bloom membership set used for lemma-oracle pruning
   is built with keys for both `X` and `sqlite_ascii_lower(X)` per
   authoritative lemma text, guaranteeing zero false negatives for runtime
   checks with `Q` and `python_lower(Q)`; FPR remains statistical only.
6. **Required differential fixture (new).** Local-vs-Online parity tests must
   explicitly cover: normal ASCII capitalization; uppercase/lowercase; German
   umlauts; ß; NFC text; deliberately decomposed/non-NFC input; surface
   forms; exact lemmas; and unknown values. Each assertion is parity with
   `LocalDictionaryProvider`'s actual result, not a preconceived linguistic
   answer. A separate builder closure test proves every full-fixture match is
   present within the exact runtime-selected bucket set.
7. Entry and example routes use stable identities per items 4-5 above (entry
   by `lemma_semantic_ref`; example by numeric `example.id % 64` as an
   internal routing key only). The Bloom filter has no false negatives for
   the fixture's authoritative set; tests treat FPR as statistical only.
8. Product retrieval accepts only the committed manifest, HTTPS and the pinned
   GitHub-release redirect policy. No caller/browser URL or custom manifest
   can configure Online. Maximum family identity is 256 and a top-level
   operation makes at most 32 new lookup-shard downloads, otherwise returns
   exactly `online_dictionary_budget_exceeded` with no PART-B mutation.
   **Product network trust tests (new)** must prove, automatedly: arbitrary
   hosts rejected; plain HTTP rejected for Product traffic; userinfo
   rejected; invalid redirect rejected; approved release redirect accepted;
   and that the browser/API cannot configure a source.
9. Cache acquisition proves byte count, SHA-256 and SQLite/logical validity;
   uses temp + fsync + atomic install, immutable validated leases, single-flight,
   corrupt-cache refetch, and clear-cache safety with concurrent leases.
10. Differential tests prove Online and Local providers produce equivalent
    results for fixture lookups, sense routing, examples, misses and failure
    states. Transport, integrity, and budget failures never become `needs_gloss`
    or `not-found` and make no PART-B mutation.
11. No production assets, no production Release, and no network dependency in
    the normal gate. Focused validation plus final `make gate` pass. The
    report records exact commands, fixture corpus evidence, the
    contract-coverage map, and required full-diff T3 review results.

Stop-and-ask: any need for a new runtime dependency, a PART-B schema migration,
production Release publication, first-run/Settings UI, a change to the logical
dataset token, a path outside the allowlist, a current product dictionary read
the contract cannot cover without a new shard route/family, or any other
contract conflict.

Risk: public-api, auth-security.

Model: gpt-5.6-terra / T3 / high

Why: WORKFLOW §4's novelty, public network trust boundary, and provider seam
establish a cross-cutting pattern that later dictionary work will rely on.

Fallback: opus-5 / T3 / high.
