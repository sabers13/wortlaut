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
- `MODULES.toml` only if required to register the new owned modules
- `tasks/slice-11.report.md`

Required reading: `docs/adr/0009-session-scoped-online-dictionary.md`,
`docs/adr/0001-flashcards-core.md`, `docs/adr/0004-multilingual-learner-meanings.md`,
`AGENTS.md`, `MODULES.toml`, `app/dictionary.py`, `app/deck.py`, relevant
dictionary/deck tests, and `tasks/slice-11.md`.

Acceptance:

1. `LocalDictionaryProvider` and `OnlineDictionaryProvider` share an explicit
   provider contract and are different transports for v2 token
   `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.
   Provider switching makes no D47 relink; stable refs remain authoritative.
2. A deterministic builder creates the fixed 256 lookup / 256 entry / 64
   example / 1 membership-filter families from a verified full asset, preserves
   semantic/provenance values, and emits an exact, strictly validated manifest.
   Tiny fixture assets are committed only for CI; production assets are not.
3. Lookup shards route both lookup keys and `sense_ref → lemma_ref`; entry and
   example routes use stable identities. The Bloom filter has no false negatives
   for the fixture's authoritative set; tests treat FPR as statistical only.
4. Product retrieval accepts only the committed manifest, HTTPS and the pinned
   GitHub-release redirect policy. No caller/browser URL or custom manifest can
   configure Online. Maximum family identity is 256 and a top-level operation
   makes at most 32 new lookup-shard downloads, otherwise returns exactly
   `online_dictionary_budget_exceeded` with no PART-B mutation.
5. Cache acquisition proves byte count, SHA-256 and SQLite/logical validity;
   uses temp + fsync + atomic install, immutable validated leases, single-flight,
   corrupt-cache refetch, and clear-cache safety with concurrent leases.
6. Differential tests prove Online and Local providers produce equivalent
   results for fixture lookups, sense routing, examples, misses and failure
   states. Transport, integrity, and budget failures never become `needs_gloss`
   or `not-found` and make no PART-B mutation.
7. Focused validation plus final `make gate` pass. The report records exact
   commands, fixture corpus evidence, and required full-diff T3 review results.

Stop-and-ask: any need for a new runtime dependency, a PART-B schema migration,
production Release publication, first-run/Settings UI, a change to the logical
dataset token, a path outside the allowlist, or any contract conflict.

Risk: public-api, auth-security.

Model: gpt-5.6-terra / T3 / high

Why: WORKFLOW §4's novelty, public network trust boundary, and provider seam
establish a cross-cutting pattern that later dictionary work will rely on.

Fallback: opus-5 / T3 / high.
