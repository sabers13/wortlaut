# ADR-0008 — Online and offline dictionary modes

**Status:** NEEDS COLD REVIEW.

**Lineage:** This is a genuinely new architectural decision made after ADR-0007
was accepted and frozen. It begins a new cold-review lineage under WORKFLOW §7 /
AGENTS G7 and starts at cold review #1. It does not reopen, reset, or consume
reviews in the ADR-0001, ADR-0002, ADR-0004, ADR-0006 or ADR-0007 lineages.

**Extends:**
- ADR-0001: D4 (dictionary is a static SQLite asset distributed via GitHub
  releases), §12 (dictionary distribution, checksums, disposability);
- ADR-0002: D20 (fully standalone service), D25 / AGENTS C1 (app factory);
- ADR-0004: D47 (stable semantic references, atomic activation/relink).

**Preserves unchanged:**
- ADR-0001 D1 (no LLM at runtime), D3 (one resolver), D5–D10, D14, D18;
- ADR-0002 D21–D27 in full, including the two-stage stateless capture contract
  and the §4.1 browser trust boundary;
- ADR-0003 in full (confidence ratings, FSRS mapping, append-only `review_log`);
- ADR-0004 D33, D34, D36, D39, D40, D43–D47;
- ADR-0005 in full (pronunciation audio precedence and lifecycle);
- ADR-0006 D65–D69;
- ADR-0007 in full (DE/EN active meaning languages; Persian deferred);
- AGENTS R1–R13 and G1–G12 as currently written. This ADR requires **no**
  amendment to any executable AGENTS rule at draft time; §16 lists the exact
  later governance amendments the implementation slice must carry.

**Decision IDs:** D82–D106.

---

## 1. Context

### 1.1 The problem the owner is solving

Wortlaut currently requires the complete verified dictionary asset before the
application will start at all. `app/standalone.py:build_standalone_app` raises
`StandaloneError` when `dictionary.sqlite` is absent, and the `./wortlaut`
launcher exits non-zero before `ensure_user_db` runs. The published v2 asset is
**945,418,240 bytes** with SHA-256
`1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.

That is a hard ~945 MB download standing between a new user and the first
screen of the product. The owner has decided that Wortlaut must additionally
support an **online** mode that starts immediately and fetches only the small
immutable pieces of the dictionary a lookup actually needs, while the existing
**offline** mode — full local asset, no dictionary network access, exact
manifest identity — remains available and remains the behaviour existing users
already have.

This is a product decision already taken by the owner/orchestrator. This ADR
records how it is built, not whether it is built.

### 1.2 Evidence gathered for this ADR

All figures below were obtained by **read-only** probes against the
authoritative recovered v2 asset at
`~/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite`, verified
before use as exactly 945,418,240 bytes with SHA-256
`1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`. The file
was opened `mode=ro&immutable=1` and never mutated. No shard corpus was built.

**Row counts (PART A, v2):**

| Table | Rows |
|---|---|
| `lemma` | 1,118,636 |
| `surface_form` | 4,793,054 |
| `sense` | 480,221 |
| `sense_meaning` | 577,191 |
| `sense_meaning_derivation` | 58 |
| `example` | 777,295 |
| `example_lemma` | 6,504,849 |

**Distribution facts that drive the design:**

- 356,273 lemmas have at least one sense; 99,537 lemmas have at least one
  example link. Most lemmas are index-only surface material.
- 1,047,239 distinct `lemma` texts; 1,031,478 distinct SQLite-`lower()` lemma
  texts; 4,281,941 distinct `surface_form.form` values.
- Examples per lemma: p50 = 3, p90 = 33, p99 = 663, max = **230,795** (`der`).
  652 lemmas exceed 1,000 links; 8 exceed 100,000.
- Surface-form fan-out: 247,491 forms map to more than one lemma; 517 forms map
  to more than 10; 40 map to more than 100; the maximum is **65,310**
  (`'de-ndecl'`). The largest fan-out values are Wiktionary template tags that
  leaked into `surface_form` (`de-ndecl`, `no-table-tags`, `strong`, `de-adecl`,
  `de-conj`, `weak`, `neuter strong`, `masculine strong`, `neuter`) plus the
  paradigm heads `haben` (15,168) and `sein` (2,975).
- **Zero** `lemma.lemma` and **zero** `surface_form.form` values are non-NFC or
  carry leading/trailing whitespace. Normalization state of the shipped data is
  clean.
- **2,716** distinct lemma texts have `sqlite_ascii_lower(text) != python_lower(text)`
  (examples: `AAÜG`, `AGÖF`, `ARBÖ`, `Altes Ägypten`). This is the exact
  population a naive port to Python `casefold()`/`lower()` would silently change.

**Per-table byte contribution** (`dbstat`, sums to the file size exactly):

| Object | Bytes |
|---|---|
| `lemma` | 201,768,960 |
| `surface_form` | 151,326,720 |
| `sense` | 109,326,336 |
| `sqlite_autoindex_lemma_1` | 105,029,632 |
| `example` | 89,935,872 |
| `example_lemma` | 87,547,904 |
| `sense_meaning` | 51,048,448 |
| remaining indexes | 149,434,368 |
| **total** | **945,418,240** |

Roughly 27% of the published asset is SQLite index overhead that a sharded
representation does not have to reproduce in the same form.

**Compound-resolution probe.** `app/resolve.py:split_compound` was executed
against the real asset through an instrumented oracle that recorded every
distinct lookup key and its 256-way routing bucket:

| Input | Oracle calls | Distinct lookup keys | Keys that matched | Distinct buckets touched | Result |
|---|---|---|---|---|---|
| `Haus` | 1 | 1 | 1 | 1 | resolved |
| `Bundeskanzlerin` | 1 | 1 | 1 | 1 | resolved |
| `Hausaufgabe` | 1 | 1 | 1 | 1 | resolved |
| `Zwetschgenkuchen` | 1 | 1 | 1 | 1 | resolved |
| `Hausaufgabenbetreuung` | 1 | 1 | 1 | 1 | resolved |
| `Zzzqqqxxvvbbnnmm` (16 chars, unknown) | **633** | **96** | **11** | **87 of 256** | needs_gloss |

This is the single most important measurement in this ADR. A known word costs
one lookup. One unknown 16-character word probes 96 distinct keys spread over 87
of 256 buckets. Without a local negative-membership accelerator, one such word
would pull roughly a third of the entire lookup shard family over the network.
With one, only the 11 genuinely matching keys (plus the filter's false-positive
rate) require a fetch.

The same probe also recorded that this single unknown word took ~285 s of
cold-cache wall clock **against the local 945 MB SQLite file**. That is a
pre-existing property of the current recursive splitter, not something online
mode introduces; §14.4 records it as follow-up work owned elsewhere.

**GitHub Release limits**, verified 2026-09-03 from
<https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>:

> "Up to 1000 release assets may be associated with a single release."
> "Each file included in a release must be under 2 GiB."

### 1.3 The current dictionary contract being extended

- `app/dictionary.py` owns PART-A reading and `validate_candidate_dictionary`,
  which produces a `DictionaryAsset` holding **complete** `lemma_ids` and
  `sense_ids` maps built by scanning every `lemma` and `sense` row.
- `app/deck.py:DictionaryRuntime` owns activation, read pins (`reading()`),
  D47 relinking, and the `asset_token` (the asset's SHA-256).
- `app/api.py` does **not** go through `app/dictionary.py:Dictionary` at
  runtime. It holds a raw `sqlite3.Connection`
  (`runtime._current_generation.asset.connection`) and issues its own SQL
  through `_ConnectionLookupOracle` and `_materialize_candidate_from_ref`. The
  `Dictionary` class is used by `tools/gate2_coverage.py` and tests.
- `app/dict_install.py` owns manifest parsing, two-tier verification, and
  atomic install. It already streams from an arbitrary manifest-declared
  `download_url`, already rejects credential-bearing URLs, and already refuses
  to overwrite a valid dictionary.

There is therefore **no dictionary provider seam today**. Creating one is the
main structural cost of this ADR, and it is why the implementation is T3.

---

## 2. Owner-approved product requirements

These are recorded as given. They are not alternatives this ADR may reopen.

1. Wortlaut supports two dictionary modes, **ONLINE** and **OFFLINE**, and the
   user chooses and switches between them from the Wortlaut UI.
2. ONLINE requires no ~945 MB upfront download, fetches only small immutable
   shards, verifies each shard before use, caches verified shards locally, and
   requires internet only when an uncached shard is needed.
3. OFFLINE keeps the existing complete canonical `dictionary.sqlite`, its exact
   manifest SHA/byte validation, and works with no network after installation.
4. Both modes represent the same logical dictionary dataset for v2.
5. Opening the published 945 MB SQLite file directly over HTTP Range requests is
   rejected as the production architecture.
6. A Wortlaut-hosted dictionary query API/server is rejected for this version.
7. Online distribution uses static GitHub-hosted release artifacts only.
8. No user cards, reviews, meanings, or audio may be deleted by any mode switch
   or cache operation.

---

## 3. Decisions

| ID | Decision | Why |
|---|---|---|
| **D82** | **Two dictionary modes over one logical dataset.** Wortlaut supports `ONLINE` and `OFFLINE`. For a given dictionary version both modes expose the *same* logical dataset and the same observable dictionary semantics; they differ only in where the bytes come from and when they are fetched. | The 945 MB precondition is a product barrier; the offline guarantee is a product promise. Both are real requirements and neither may be traded for the other. |
| **D83** | **Reject HTTP-Range SQLite over the published asset.** No HTTP-backed SQLite VFS is implemented. | §12.1. |
| **D84** | **Reject a Wortlaut-hosted query API.** Online mode reads static release artifacts only. | §12.2. |
| **D85** | **`DictionaryProvider` seam.** All dictionary reads pass through one provider abstraction with exactly two implementations: `LocalDictionaryProvider` (wrapping the existing trusted local runtime) and `OnlineDictionaryProvider`. No `if mode == "online"` branching outside the provider construction site. | Without a seam the mode flag metastasizes into `api.py`, `deck.py` and `render.py` and every future change has to be made twice. |
| **D86** | **Static sharded dataset with three shard families plus one membership filter**, each family bucket-**closed** for the queries it serves (§5). The 256 physical `lookup` shards contain two independent logical indexes: lookup-key rows and `sense_ref → parent lemma_ref` routes. Families and counts: `lookup` × 256, `entry` × 256, `example` × 64, `filter` × 1 — **577 assets**, 57.7% of GitHub's 1000-asset limit. | The measured routing-index projection (§5.6) keeps the enlarged lookup family under the 4 MB per-shard ceiling and leaves 423 assets of headroom. |
| **D87** | **Routing keys over-approximate; matching stays exact.** The routing function is `bucket(k) = int.from_bytes(sha256(python_lower(k))[:4]) % N`. It is used **only** to select a shard. Every match/order/dedup decision is made by executing the *current* predicate against the fetched rows. Python `casefold()`, Unicode normalization changes, and stripping are forbidden as behaviour changes. | §6. The current predicate mixes SQLite's ASCII-only `lower()` with Python's Unicode `lower()`; 2,716 lemma texts depend on that asymmetry. |
| **D88** | **Negative-membership accelerator and bounded remote expansion.** A single verified Bloom filter over the lemma lookup key set (exact texts ∪ ASCII-lowered texts) is downloaded once when Online mode is activated. It has no false negatives; target false-positive rate ≤ 1%; deterministic build parameters; and is implemented in-repo over `hashlib`, with no third-party runtime dependency. A top-level logical operation may acquire at most **32 new remote lookup-shard identities**; on a 33rd it cancels remaining expansion and returns `online_dictionary_budget_exceeded` without PART-B mutation. | The Bloom FPR is statistical, not a correctness bound. The 256-family maximum remains the hard identity bound (§5.8); 32 is a separate network-safety budget justified by the measured 12-shard probe and the revised 3.72 MB worst-case lookup projection. |
| **D89** | **`release/dictionary-online-manifest-v2.json`** is committed as normal text metadata, is the *only* source of shard URLs, and is validated strictly and fail-closed before any request. It pins the canonical full-dataset SHA, the routing parameters, the filter parameters, and the exact filename, byte count and SHA-256 of every shard. | An unpinned or partially validated manifest is an arbitrary-fetch primitive with extra steps. |
| **D90** | **Logical dataset identity is mode-independent.** For v2, `asset_token` is `1698b997…67d4c` in both modes. Per-shard SHA-256 values prove transport and cache integrity only; they never become the dataset identity. Switching Online ↔ Offline within one version performs **no** D47 relink and does not change any stable semantic ref. | Prevents a mode switch from masquerading as a dictionary version change, invalidating picker tokens, or forking review state. |
| **D91** | **Mode is a local application preference** persisted in a small validated, atomically written `preferences.json` under the existing data directory. States: `unconfigured` \| `online` \| `offline`. No PART-B schema migration is added for it. | Mode is machine-local configuration, not dictionary data and not user study data (AGENTS R9). |
| **D92** | **Startup never contacts the network before an explicit user choice.** The startup state machine is §8.2. In `unconfigured` state the app starts with no active provider and every dictionary-dependent operation fails with a structured `dictionary_unavailable` state, never a crash. | Requirement I; also keeps `./wortlaut` honest for a user who never opts into online mode. |
| **D93** | **Settings/Dictionary UI contract** (§9.2) exposes mode, online cache size and shard count with an explicit "Clear online cache", and offline install state with explicit "Download for offline use" / "Remove offline copy". Destructive actions are separate explicit user actions and never touch user data. | Requirement J. |
| **D94** | **UI-initiated offline install reuses `app/dict_install.py` unchanged in substance**; a progress-reporting seam is added, not a second downloader/verifier. The default `./wortlaut --install-dictionary` uses the committed production manifest. An explicit local `--manifest PATH` retains the present developer/recovery override only for offline installation; its declared source may be `file://` or `http(s)://`, but it never configures Online mode or browser/UI fetches. | Two download/verify implementations means two integrity contracts and one of them will rot; retaining an explicit operator override does not make it a product network source. |
| **D95** | **Online shard cache with verified immutable leases** lives at `<data-dir>/cache/dictionary-online/<version>/<family>/`, is disposable, contains no user data, and never mixes versions. A shard is usable only through a verified immutable lease: a miss is single-flight, temp-written, exact-byte/SHA/schema-validated, fsynced and atomically installed before a private immutable snapshot is leased; a new cache-hit lease revalidates canonical bytes before snapshot creation. Clear-cache serializes mutation, bars new canonical acquisitions, and defers files held by active leases. | Requirement L. This matches and extends the full-dictionary anti-TOCTOU discipline without relying on platform-specific unlinking of an open SQLite pathname. |
| **D96** | **Two outbound trust domains.** Product/runtime/UI distribution (Online provider, first-run/Settings Online selection, UI offline download, and default `--install-dictionary`) uses only the committed Wortlaut production manifests and pinned GitHub Release asset paths over HTTPS. The fetcher validates every redirect against the closed GitHub distribution host policy in §10. An explicit CLI `--manifest PATH` remains a segregated developer/recovery offline-install override, with credential redaction, but cannot configure Online mode or any browser/API fetch. | R14 can be enforced honestly for automatic product traffic while preserving the existing explicit operator recovery path. |
| **D97** | **Honest privacy contract** (§11). Offline: no dictionary network access after installation. Online: GitHub sees the user's IP and an opaque shard access pattern; the searched word never appears in a URL; no telemetry, analytics, account, or upload of user data. Shard access is **not** claimed to be cryptographically private. | A public routing algorithm permits inference. Saying otherwise would be false. |
| **D98** | **Online failure is explicit and never fabricated.** Unavailable / timeout / wrong size / wrong SHA / invalid SQLite / malformed / wrong dataset version / corrupt cache recovery failure ⇒ the shard is never used, no stub or partial dictionary result is synthesized, an actionable `online_dictionary_unavailable` error is returned, user data is untouched, and the persisted mode is not silently changed. Exceeding D88's remote-download budget instead returns `online_dictionary_budget_exceeded`; it is neither `needs_gloss` nor a dictionary miss and likewise performs no PART-B mutation. A clearly surfaced temporary local fallback is permitted only when a complete verified offline dictionary exists; it is optional and it is never silent. | A "successful" lookup produced by a failed or incomplete fetch would write wrong bindings into PART B. |
| **D99** | **Provider activation is serialized and atomic.** At any request boundary exactly one coherent provider/dataset identity is active. In-flight requests complete against the provider they pinned; no single logical operation joins data from both providers. | Requirement P; mirrors the existing `DictionaryRuntime` generation/pin discipline. |
| **D100** | **`ReadingSnapshot`'s eager reference maps become lazy, bounded resolvers.** `lemma_ids` / `sense_ids` keep their `Mapping`-shaped `in` / `[]` contract but resolve refs on demand through the provider with per-snapshot memoization. D47 relink resolves only the refs actually persisted in `note_dictionary_binding`. | Online mode cannot hold 1.1M lemma refs and 480k sense refs eagerly. All current call sites (`app/api.py` lines 1053–1134, 1642–1737 and `_relink_part_b`) are point lookups and are unchanged by this. |
| **D101** | **Deterministic builder `tools/build_online_dictionary.py`**, input one verified full `dictionary.sqlite`, output outside Git (§13). Verifies the input SHA before any production build, streams/partitions rather than loading the asset into memory, emits rows in deterministic order, preserves exact values including `source`/`license`/`semantic_ref`, never mutates the source, and reports row counts, total bytes, per-family size distribution and a re-verified digest for every emitted asset. | Requirement Q. A non-deterministic builder makes every future rebuild an unreviewable diff. |
| **D102** | **Differential verification against the local provider is a release gate.** CI runs it over a tiny deterministic fixture; the production v2 build runs it over a large deterministic sample with explicit row/count validation. `make gate` never downloads production shards. | Requirement R. "Looks plausible" is not a dictionary correctness standard. |
| **D103** | **CLI contract.** `./wortlaut` and the `./flashcard` alias are unchanged. `--install-dictionary` is unchanged. A new `--dictionary-mode online\|offline` is **session-only**, does not write `preferences.json`, and its interactions with `--dict-path` and `--install-dictionary` are specified exhaustively in §9.3. | Requirement U forbids leaving these interactions ambiguous. |
| **D104** | **Online shards publish to a separate GitHub Release `dictionary-online-v2`.** The existing `dictionary-v2` release stays intact and untouched. Publication follows the fixed sequence in §13.3. | 577 assets do not belong in the full-asset release; and the full asset must not be disturbed by online-mode iteration. |
| **D105** | **Existing users are never forced through the chooser.** A user with a valid `~/.local/share/flashcard/dictionary/dictionary.sqlite` and no persisted preference launches straight into Offline. Persistent user paths are not renamed. | Requirement T. The product rename to Wortlaut is not a reason to move anyone's data. |
| **D106** | **The build/publication path must not require multiple simultaneous multi-GB duplicate trees.** Shards are emitted and uploaded incrementally against a checked free-space budget on a caller-supplied working directory. Realistic temporary-disk requirements are recorded in §13.4. | The owner has had local storage pressure; the current machine has ~13 GB free. |

---

## 4. Provider contract

### 4.1 Inventory of what the runtime actually needs

The contract is derived from real call sites, not invented:

| Capability | Current call site | Shape |
|---|---|---|
| `lookup_exact(text, pos?, gender?)` | `app/api.py:_ConnectionLookupOracle`, `app/dictionary.py:Dictionary` | ordered `LemmaRecord` sequence |
| `lookup_surface_form(form)` | same | ordered, deduplicated by lemma id |
| `lookup_senses(lemma_id)` | same, and `app/resolve.py:_bind_component` | ordered `SenseRecord` sequence |
| full lemma row by lookup text | `app/api.py:_materialize_candidate_from_ref` | one `lemma` row, ordered candidate set |
| lemma row by `semantic_ref` | `app/deck.py:_materialize_lemma_under_gen`, `_materialize_components_under_gen` | one row or `None` |
| senses / meanings / examples for a lemma id | `app/deck.py:_materialize_lemma_under_gen`, `app/api.py:_materialize_candidate_from_ref` | ordered row sets |
| first meaning for a `sense.semantic_ref` and language | `app/deck.py:_materialize_components_under_gen` | one text or absent |
| `ref -> id` existence/identity resolution | `ReadingSnapshot.lemma_ids` / `sense_ids`, `_relink_part_b` | point lookup (D100) |
| `asset_token` | `DictionaryRuntime.asset_token`, every picker token check | the v2 dataset SHA (D90) |

### 4.2 Rules

1. `LocalDictionaryProvider` **wraps** the existing validated
   `DictionaryAsset` / `DictionaryRuntime` path. It does not reimplement
   validation, activation, pinning or relinking. Offline behaviour after this
   ADR must be byte-identical to offline behaviour before it.
2. `OnlineDictionaryProvider` must return results **observably equal** to the
   local provider for the same dataset version: same rows, same field values,
   same ordering, same deduplication, same absence.
3. Both providers expose the same `asset_token` for v2 (D90).
4. Ordering and dedup are never delegated to the shard layout. They are
   recomputed from fetched rows using the current predicates, so a routing
   change can never silently reorder results.
5. The provider is the only component that knows about modes. `app/render.py`,
   `app/examples.py`, `app/export.py` and the frontend see one dictionary.

---

## 5. Shard model

### 5.1 Format

Shards are **small SQLite database files** carrying a subset of the PART-A
schema, stored and served **uncompressed**. The manifest's byte count and
SHA-256 are over the exact asset bytes as served; no transfer encoding is
trusted. Application-level compression is deliberately out of scope for v1: it
adds a decompression surface and a second integrity boundary for a saving that
does not change the architecture. It is recorded in `docs/backlog.md` as a
future optimization, not as unfinished work here.

Using SQLite for shards is a correctness decision, not a convenience one: the
provider can execute the *same predicate text* against a bucket-closed shard
that the local provider executes against the full asset, including SQLite's own
`lower()` semantics, `NULLS LAST` ordering and collation behaviour.

### 5.2 The closure invariant

> **For every query the provider serves, the shard(s) selected by the routing
> function must contain every row that the equivalent query against the full v2
> asset could match.**

Closure is what makes "same SQL, same answer" true. Routing may
over-approximate (fetch a shard that turns out to contain no match); it may
never under-approximate.

### 5.3 Family `lookup` — 256 shards, routed by `bucket(python_lower(key))`

Each physical lookup file has two independently routed SQLite tables. Contents
for bucket *b* are:

- **Lookup-key index.** The resolver-facing `lemma` projection (`id`,
  `semantic_ref`, `lemma`, `pos`, `gender`, `freq_rank`) for every lemma with
  `bucket(python_lower(lemma)) == b`; every `surface_form` row whose
  `bucket(python_lower(form)) == b`, carrying the target lemma's `id` and its
  `entry` bucket; and inline deduplicated lemma projections for the lemmas
  referenced by high-fan-out forms in this bucket (§5.7).
- **Sense-route index.** Exactly one `sense_route(sense_ref PRIMARY KEY,
  lemma_ref NOT NULL)` row for every authoritative `sense.semantic_ref` where
  `bucket(sense_ref, 256) == b`. `sense_ref` here is routed as its literal,
  canonical semantic reference: `bucket()` applies its normal `python_lower`
  step, which leaves `sense:v1:<lower-hex>` unchanged. The builder rejects a
  duplicate, missing, or mismatched mapping.

`resolve_word` probes `lookup_exact(cleaned)` and then
`lookup_surface_form(cleaned)` with **the same key**, so ladder steps 1 and 2
are served by **one** shard fetch.

`ReadingSnapshot.sense_ids[sense_ref]` and D47 relinking first fetch only the
lookup shard `bucket(sense_ref, 256)`, read its exact `sense_route` row, then
fetch only `entry[bucket(lemma_ref, 256)]` and resolve the exact sense row
there. Neither path may scan entry shards or infer absence from a lookup-key
table. Thus a sense point read is bucket-closed while retaining the current
`Mapping` contract (`sense_ref → (sense_id, lemma_id)`).

### 5.4 Family `entry` — 256 shards, routed by `int(lemma_ref_digest[:8], 16) % 256`

Routed from the digest already embedded in `lemma:v1:<sha256>`, so both the
lookup path (which has the lemma's `semantic_ref`) and the `deck.py` relink path
(which has only a ref) route directly with no extra map. Contents per lemma:
the full `lemma` row, its `sense` rows, its `sense_meaning` rows, the
`sense_meaning_derivation` edges reachable from them, and its `example_lemma`
links in `example.id ASC` order. Each entry shard is internally indexed by both
`lemma.id` and `lemma.semantic_ref`.

### 5.5 Family `example` — 64 shards, routed by `example.id % 64`

`example` rows only, so one sentence's text is stored once no matter how many
lemmas link to it. The entire family is ~92.6 MB, which is the **hard upper
bound on all example traffic for a user, ever** — including the 230,795-link
`der` case (§14.3).

### 5.6 Measured sizing

The original lookup/entry projection was content bytes plus a fixed per-row
overhead allowance over the real v2 asset. O1 changes lookup contents, so this
revision separately measured the exact added index shape against the verified
source: 480,221 ordered `(sense_ref, lemma_ref)` rows were routed across 256
temporary SQLite files, each `sense_route(sense_ref TEXT PRIMARY KEY, lemma_ref
TEXT NOT NULL) WITHOUT ROWID`, page size 4096, then committed and vacuumed.
The probe output was deleted after measurement; it did not build a production
corpus. The added family total is **78,663,680 bytes** (min 290,816; median
307,200; p95 319,488; max 331,776). Both refs are exact 73-byte canonical
texts, so the probe includes the real key/value payload rather than an
estimated row count.

Revised values below are conservative projections: total is the old projection
plus the measured index total; median and max add the respective measured
index percentiles/maximum to the prior budgets. D101 must replace these with
the final builder's actual file measurements before publication.

| Family | Shards | min | median | p95 | max | family total |
|---|---|---|---|---|---|---|
| `lookup` (lookup-key + sense-route indexes) | 256 | 1.55 MB | **≤ 1.61 MB** | ≤ 1.68 MB | **≤ 3.72 MB** | **417.6 MB** |
| `entry` | 256 | 1.38 MB | **1.47 MB** | 1.75 MB | 2.36 MB | 383.9 MB |
| `example` | 64 | — | — | — | — | 92.6 MB (mean 1.45 MB) |
| `filter` | 1 | — | 1.69 MB | — | — | 1.7 MB |
| **total** | **577** | | | | | **≈ 895.7 MB** |

Budget: **no shard may exceed 4 MB**; the median lookup and entry shard must
stay at or below 2 MB. The 3.72 MB conservative lookup maximum remains below
that ceiling; the 1.61 MB conservative median remains below 2 MB. Asset count
577 of 1000 leaves 423 assets (42.3%) of headroom for a future family or a
higher shard count.

Cold-cache cost of a first lookup of a known word: one `lookup` shard + one
`entry` shard ≈ **2.8 MB**, plus at most one `example` shard per distinct
example bucket touched (p50 is 3 examples). Every subsequent lookup landing in
a cached bucket costs zero bytes.

### 5.7 High-fan-out surface forms

Measured: 517 forms map to more than 10 lemmas, 40 to more than 100, and 11 to
more than 1,024 — dominated by leaked Wiktionary template tags. Rule:

- fan-out ≤ 8: the form's lemma projections are fetched from their own `lookup`
  shards (normally one extra shard, because a form averages 1.1 lemmas);
- 8 < fan-out ≤ 1024: the lemma projections are **inlined** into the form's own
  shard, so the lookup costs exactly one fetch. Measured cost of inlining: 753
  forms, +2.2 MB across the whole family;
- fan-out > 1024 (11 forms): normalized path. Worst case is `'de-ndecl'`, whose
  65,310 lemmas span the whole family, i.e. up to 417.6 MB of `lookup` shards.

That worst case is accepted, deliberately and with its numbers stated. All 11
strings are corpus artifacts (`de-ndecl`, `no-table-tags`, `strong`, `de-adecl`,
`de-conj`, `weak`, `neuter strong`, `masculine strong`, `neuter`) or paradigm
heads (`haben`, `sein`) that the surface path never reaches, because
`resolve_word` tries `lookup_exact` first and both are lemmas. Fixing
`surface_form` data quality would change the dataset SHA and is therefore out
of scope for this ADR; it is filed to `docs/backlog.md`. The implementation must
surface a bounded, cancellable progress state rather than appearing to hang if
one of these forms is ever queried.

### 5.8 Membership filter

One asset. A Bloom filter over the union of `{lemma}` ∪ `{ascii_lower(lemma)}` —
measured at **1,477,819 keys**. At a 1% false-positive rate: m ≈ 14.2 Mbit =
**1.69 MB**, k = 7. At 0.1%: 2.53 MB, k = 10. The manifest pins `m`, `k`, the
hash construction, the key count and the SHA-256, so the filter is reproducible
and verifiable.

Query rule: a lookup key `Q` may skip its shard fetch **only if** neither `Q`
nor `python_lower(Q)` is present in the filter. This has no false negatives
because the build set contains both key families, and it is exactly the
predicate `lookup_exact` evaluates.

The configured FPR is a build/statistical characteristic, **not** a
deterministic per-query download bound. False positives may occur in any
pattern. The tested unknown 16-character word's approximately 12 fetched
lookup shards is therefore a non-normative performance observation only.

There are exactly **N = 256** lookup bucket identities for one dataset version,
so 256 is the absolute finite distinct-family maximum for a logical lookup;
probing a bucket already acquired by that operation does not create another
identity. Separately, D88 sets a network-safety budget of **32 new remote
lookup-shard downloads** per top-level logical operation. Count only a shard
whose verified lease was acquired by a network fetch during that operation;
already-cached validated leases, the filter, entry shards and example shards do
not consume this lookup budget. A 33rd required remote lookup identity cancels
the remaining expansion, releases all request leases, preserves verified cache
entries, and returns `online_dictionary_budget_exceeded` with no partial
dictionary result or PART-B mutation. With the revised 3.72 MB maximum lookup
projection, the budget caps new lookup transfer at **≤ 119.1 MB** (decimal),
while allowing 2.7× the measured ~12-shard case. It is intentionally below the
256-identity family maximum.

Surface-form lookups are deliberately **not** filtered: `resolve_word` performs
at most one surface probe per word, so a filter would save at most one fetch
while costing roughly 10 MB of first-run download for ~8.5M keys.

### 5.9 Verified shard lease lifecycle (D95, D98–D99)

Each `(dataset version, family, shard index)` has a cache-mutation lock and a
conceptual lifecycle:

```
ABSENT → DOWNLOADING → VERIFIED → LEASED immutable snapshot
```

For a miss, one single-flight owner downloads to a cache-local temporary file,
streams and counts bytes, verifies exact manifest byte count and SHA-256,
validates the required SQLite schema and family logical closure, fsyncs the
file and parent directory, atomically installs the canonical cache file, then
copies/opens only validated bytes as a private immutable snapshot lease. Waiters
join that flight and acquire their own lease only after its verification
succeeds. No partial canonical file or pathname-based SQLite handle becomes
active.

For a cache hit, a filename alone conveys no trust. Before a **new** lease after
process start, or when no already-validated in-process lease represents that
canonical file, the provider rechecks exact bytes and SHA-256 and derives the
SQLite handle from the validated immutable snapshot, not from a pathname that
could change after hashing. Repeated reads through an existing immutable lease
do not rehash it. Failed cache validation never opens the bytes: it serializes
safe eviction/quarantine, then redownloads through the same single-flight path
if Product network is permitted; recovery failure is
`online_dictionary_unavailable`, never a dictionary miss.

“Clear online cache” takes the same cache-mutation lock before provider-switch
state is considered, so the order is cache lock then provider-generation lock
everywhere. It applies only to
`<data-dir>/cache/dictionary-online/<version>/`: it immediately blocks new
canonical acquisitions in that version, removes unleased canonical files, and
marks leased ones deferred. Existing private immutable snapshot leases and
their logical requests may finish. Deferred canonical files/state are removed
only after the final relevant lease releases; implementation must not depend on
unlinking an SQLite pathname that another platform keeps open. Clear never
touches `flashcards.sqlite`, `media/`, the canonical offline dictionary, or
preferences except optional cache metadata. Switching providers acquires a
generation pin before releasing any shard lease, so an in-flight request stays
on one coherent provider while cache cleanup remains independent. A mode switch
that needs to coordinate with online cache state takes the cache-mutation lock
first and the provider-generation lock second, the same order as clear-cache;
it never holds the generation lock while waiting for a cache lock.

---

## 6. Routing keys and lookup normalization

### 6.1 The current semantics, stated exactly

`lookup_exact(Q)` executes, in both `app/dictionary.py` and `app/api.py`:

```sql
WHERE (lemma = ? OR lower(lemma) = ?)   -- params: (Q, Q.lower())
```

SQLite's `lower()` is **ASCII-only**; Python's `str.lower()` is **Unicode**. So
a row `R` matches `Q` iff:

```
R.lemma == Q   OR   ascii_lower(R.lemma) == python_lower(Q)
```

Consequences that are current, intended-or-not, and preserved:

- `Straße` matches `STRAßE` (all differing characters are ASCII) but not
  `STRASSE`;
- `Äpfel` does **not** match `äpfel`, because `ascii_lower("Äpfel") == "Äpfel"`
  while `python_lower("ÄPFEL") == "äpfel"`;
- 2,716 distinct lemma texts sit exactly on this asymmetry;
- `resolve_word` strips the input once (`word.strip()`); the SQL itself does
  not strip. `split_compound` lowercases with Python `.lower()` before probing.

`lookup_surface_form` uses the identical construction over `surface_form.form`.

### 6.2 The routing-key rule (D87)

```
routing_key(k)  = python_lower(k)                # no NFC, no casefold, no strip
bucket(k, N)    = int.from_bytes(sha256(routing_key(k).encode("utf-8"))[:4], "big") % N
```

**Correctness obligation.** For every `(Q, R)` pair that matches under §6.1,
`bucket(Q) == bucket(R.lemma)`. Proof sketch, to be encoded as a test:

- clause 1, `R.lemma == Q`: identical strings, identical bucket;
- clause 2, `ascii_lower(R.lemma) == python_lower(Q)`: applying
  `python_lower` to both sides gives `python_lower(ascii_lower(R.lemma)) ==
  python_lower(Q)`, and `python_lower(ascii_lower(x)) == python_lower(x)`
  because `ascii_lower` only maps `A–Z`, which `python_lower` maps identically.
  Hence `routing_key(R.lemma) == routing_key(Q)`.

Because routing is an over-approximation and matching is exact, a query that
*today* returns nothing still returns nothing: it either lands in a bucket with
no matching row, or in a different bucket entirely. NFD input, `STRASSE`, and
`äpfel` all behave exactly as they do now.

### 6.3 What is forbidden

`casefold()`, Unicode normalization on lookup keys, trimming that the current
code does not perform, and any collation change. If a future owner decision
wants ASCII-lower semantics fixed for umlauts, that is a **separate**
owner-approved behaviour change with its own ADR and its own dataset
implications — never a side effect of adding online mode.

The shipped v2 data is fully NFC and whitespace-clean (§1.2), so routing
introduces no normalization risk on the build side.

---

## 7. Manifest schema and identity rules

`release/dictionary-online-manifest-v2.json`, committed as text, is the only
source of shard URLs. Required fields:

```
schema_version        online shard format version (integer, pinned)
dictionary_version    "v2"
full_dataset_sha256   "1698b997...67d4c"    (D90 logical identity)
full_dataset_bytes    945418240
attribution           "ATTRIBUTION-v2.md"
release_tag           "dictionary-online-v2"
asset_base_url        immutable https:// base sufficient to derive exact asset URLs
routing               { hash: "sha256", key_normalization: "python_lower",
                        lookup_shards: 256, entry_shards: 256, example_shards: 64,
                        entry_route: "lemma_semantic_ref_digest",
                        sense_route: "sense_ref_to_parent_lemma_ref_in_lookup",
                        surface_inline_min: 8, surface_inline_max: 1024 }
membership_filter     { kind: "bloom", m_bits, k, key_count, hash_construction,
                        filename, bytes, sha256 }
families[]            per family: name, shard_count, and for every shard:
                      { index, filename, bytes, sha256 }
```

Validation rules, all fail-closed before any request is made:

1. `full_dataset_sha256` must equal the v2 identity constant compiled into the
   application. A manifest describing a different dataset is rejected, not
   adopted.
2. Filenames are single-segment, `[A-Za-z0-9._-]+`, no separators, no `..` —
   the same rule `dict_install.parse_manifest_payload` already enforces.
3. The committed production `asset_base_url` must be the exact HTTPS GitHub
   release prefix
   `https://github.com/sabers13/wortlaut/releases/download/dictionary-online-v2/`.
   It must not embed credentials (`@`, `token=`, `api_key=`, `apikey=`). It is
   not a general URL field.
4. Every shard entry must carry a positive byte count within a per-family
   ceiling and a 64-character lowercase hex SHA-256.
5. Shard counts must match the `routing` block exactly; a missing or duplicate
   shard index is a rejection.
6. URLs are **derived** from `asset_base_url` + `filename`. No URL is ever
   accepted from the browser, from a shard, or from an HTTP response body.
7. The builder validates logical closure of the lookup-key index **and** that
   every authoritative sense ref appears exactly once in its routed
   `sense_route` index and names the parent lemma's exact semantic ref.

---

## 8. Mode and startup state machines

### 8.1 Mode state machine

```
                +-----------------+
                |  unconfigured   |  no provider active; zero network
                +--------+--------+
                    |           |
       user picks Online   user picks Offline
                    |           |
                    v           v
            +---------------+  +----------------+
            |    ONLINE     |  |    OFFLINE     |
            +-------+-------+  +--------+-------+
                    |                   |
   switch to Offline: install/validate  |  switch to Online: activate provider,
   the full asset first; never activate |  do NOT delete the full asset
   an invalid/partial dictionary        |
                    +---------<---------+
```

- ONLINE → OFFLINE: if a complete asset already exists and validates, activate
  it; otherwise offer the download with visible progress. The switch commits
  only after the asset validates. A failed or cancelled download leaves the mode
  unchanged and leaves no partial file (`dict_install` already guarantees this).
- OFFLINE → ONLINE: swap the provider. The full asset is **not** deleted.
- Deleting the offline asset and clearing the online cache are separate,
  explicit, individually confirmed user actions (D93).
- No mode transition ever writes to, deletes from, or migrates PART B.

### 8.2 Startup state machine

```
read preferences.json
  |
  +-- valid preference present ---------------------> honor it
  |        (online -> online provider; offline -> offline provider)
  |
  +-- absent AND a valid canonical offline dictionary exists ---> OFFLINE (D105)
  |        and persist "offline" so the user is never asked again
  |
  +-- absent AND no offline dictionary -------------> unconfigured (first-run UI)
  |
  +-- present but corrupt/invalid ------------------> fail safe:
           treat as unconfigured, surface the problem, do NOT enable network,
           do NOT overwrite the file until the user makes a choice
```

The first network request of a Wortlaut installation happens only after an
explicit user selection of Online, or an explicit offline download action.

`unconfigured` is a fully startable state: the app factory constructs, the HTTP
service binds loopback, the frontend loads, decks and existing cards are
readable to the extent they do not need the dictionary, and any
dictionary-dependent operation returns a structured `dictionary_unavailable`
payload carrying the state, the reason, and the actions that would resolve it.
It never raises `StandaloneError` at construction time the way today's
`build_standalone_app` does.

---

## 9. UI and CLI contract

### 9.1 First run

Shown only when there is no preference and no valid offline dictionary. No
dictionary network request precedes the choice.

```
Choose how Wortlaut uses the dictionary

Online
Start now without downloading ~945 MB.
Wortlaut downloads small verified dictionary chunks as needed.
Internet is required for uncached entries.

Offline
Download the complete dictionary (~945 MB).
Works without internet after installation.
```

### 9.2 Settings → Dictionary

```
Dictionary mode:   ( ) Online   ( ) Offline

Online cache:      <size>  ·  <n> cached shards
                   [ Clear online cache ]

Offline dictionary: Installed / Not installed  ·  ~945 MB
                   [ Download for offline use ]
                   [ Remove offline copy ]      # only when present
```

Cache size must be displayed so storage use is visible. The frontend currently
has no settings view (`frontend/src/app.ts` renders `decks | deck | study`), so
the implementation adds `setup` and `settings` views to that shell.

### 9.3 CLI

`./flashcard …` remains a compatibility alias that execs `./wortlaut`. Every
row below has the same data-root rule: omitted `--data-dir` uses the existing
XDG `flashcard` root; `--data-dir PATH` changes, for that invocation, the
preferences file to `PATH/preferences.json`, online cache to
`PATH/cache/dictionary-online/`, canonical offline dictionary to
`PATH/dictionary/dictionary.sqlite`, and default PART-B/media paths to
`PATH/flashcards.sqlite` and `PATH/media/`. `--dict-path PATH` changes only the
offline dictionary selected for the launch; it does not move those other
per-user paths. `--user-db` retains its established independent override.

`--manifest PATH` remains an explicit local developer/recovery manifest file
(not a browser/API value). Its existing `download_url` may be `file://` or
explicit `http(s)://`, subject to existing credential redaction. It is accepted
only together with `--install-dictionary`, is never persisted, and never
configures `OnlineDictionaryProvider`. “Production manifest” below means the
committed `release/dictionary-manifest-v2.json` for offline installation;
“online manifest” means the separate committed trusted online configuration in
§7. A usage error is deterministic exit 2 before network or user-state
mutation. Installation retains its current lifecycle: install/verify first,
then the normal runtime launch; it is not an install-and-exit command.

| Mode flag | `--manifest` | `--dict-path` | `--install-dictionary` | Result, manifest/trust domain, and exit |
|---|---|---|---|---|
| none | none | none | no | Apply §8.2 persisted preference/startup state; normal launch. No network unless persisted Online later needs an uncached shard. |
| none | none | none | yes | Install canonical offline asset from production manifest through Product domain; then normal §8.2 launch. If no preference exists, persist `offline`; never overwrite an explicit preference. |
| none | none | PATH | no | Normal Offline launch against explicit path; no canonical manifest check or install; normal launch, error if path is absent/invalid. |
| none | none | PATH | yes | Install canonical offline asset from production manifest through Product domain, then normal Offline launch against the explicit path; normal launch. This preserves the existing independent override/install behavior. |
| none | PATH | none | no | **Usage error.** A custom manifest has no runtime-startup role. |
| none | PATH | none | yes | Install canonical offline asset using the explicit developer/recovery manifest and its declared source; then normal §8.2 launch. This is Developer/Recovery domain. |
| none | PATH | PATH | no | **Usage error.** A custom manifest has no runtime-startup role. |
| none | PATH | PATH | yes | Install canonical offline asset through Developer/Recovery domain, then normal Offline launch against explicit path; normal launch. |
| `offline` | none | none | no | Session-only Offline; requires a valid canonical asset; normal launch or actionable nonzero absence/validation error. Preference unchanged; no dictionary network. |
| `offline` | none | none | yes | Install canonical offline asset through Product domain, then session-only Offline normal launch; preference unchanged. |
| `offline` | none | PATH | no | Session-only Offline against explicit path; normal launch or actionable nonzero path error; preference unchanged. |
| `offline` | none | PATH | yes | Install canonical asset through Product domain, then session-only Offline launch against explicit path; preference unchanged. |
| `offline` | PATH | none | no | **Usage error.** Custom manifests apply only to explicit install. |
| `offline` | PATH | none | yes | Install canonical asset through Developer/Recovery domain, then session-only Offline normal launch; preference unchanged. |
| `offline` | PATH | PATH | no | **Usage error.** Custom manifests apply only to explicit install. |
| `offline` | PATH | PATH | yes | Install canonical asset through Developer/Recovery domain, then session-only Offline launch against explicit path; preference unchanged. |
| `online` | none | none | no | Session-only Online using only the committed trusted online manifest and Product domain; normal launch. Preference unchanged; uncached shards may use Product network. |
| `online` | none | none | yes | **Usage error.** Offline installation and Online session selection are contradictory; neither install nor network begins. |
| `online` | none | PATH | no | **Usage error.** Explicit offline dictionary paths cannot select Online; no mutation/network. |
| `online` | none | PATH | yes | **Usage error.** Both contradictions apply; no mutation/network. |
| `online` | PATH | none | no | **Usage error.** A custom manifest cannot redirect Online; no mutation/network. |
| `online` | PATH | none | yes | **Usage error.** A custom manifest cannot redirect Online and install is contradictory; no mutation/network. |
| `online` | PATH | PATH | no | **Usage error.** A custom manifest and explicit offline path cannot select Online; no mutation/network. |
| `online` | PATH | PATH | yes | **Usage error.** All contradictions apply; no mutation/network. |

Thus `--dictionary-mode` is session-only in every valid row and never mutates
`preferences.json`; a custom manifest never affects Online; and `--data-dir`
scopes every default per-user path, including cache and PART-B state, in every
row.

---

## 10. Network security boundary

### 10.1 Product/runtime/UI distribution path (R14 scope)

OnlineDictionaryProvider, first-run Online selection, Settings Online mode, UI
“Download for offline use”, and default `./wortlaut --install-dictionary` are
the **Product** path. They use only committed Wortlaut manifests/configuration;
the UI and browser never submit a URL. Each initial product asset request must
be HTTPS to exactly:

```
github.com/sabers13/wortlaut/releases/download/dictionary-online-v2/<validated filename>
```

for online shards, or exactly
`github.com/sabers13/wortlaut/releases/download/dictionary-v2/dictionary-v2.sqlite`
for the default offline installer. No credentials, userinfo,
non-default port, arbitrary host, `file://`, or plain HTTP is permitted.

GitHub documents release-asset URLs on `github.com` and currently redirects
their downloads to signed asset hosts. The fetcher follows at most three HTTPS
redirects and validates **every** hop: initial host `github.com`, then only
`release-assets.githubusercontent.com` or `objects.githubusercontent.com`.
The initial path must be the exact owner/repository/release/validated-filename
path above; a redirect URL may carry GitHub's signed query parameters but must
have no userinfo or non-default port. Any redirect to another scheme, host, or
an invalid initial path fails closed before bytes are read. The response is
still accepted only after exact manifest byte count, SHA-256, and required
SQLite/logical validation. This deliberately allows the observable GitHub
release host families, not a temporary signed CDN hostname or a generic
`*.githubusercontent.com` wildcard.

### 10.2 Explicit developer/recovery offline-install path

The operator-only `--manifest PATH --install-dictionary` route is outside R14's
automatic Product allowlist. It preserves existing `dict_install` compatibility
for a local custom manifest whose explicit `download_url` is `file://` or
`http(s)://`; credentials remain rejected/redacted. It may only install an
offline asset, is never persisted as a preference or online source, and cannot
be reached from UI/browser/API input. It is not a generic runtime fetch proxy.

### 10.3 Unchanged local browser boundary

- Unchanged and not weakened: loopback-only bind (AGENTS R8), loopback `Host`
  validation and exact-origin CORS (AGENTS R12), `X-Flashcards-Request: 1` on
  every non-GET browser-callable route, dictionary/user database separation
  (AGENTS R9), no LLM SDK anywhere in the runtime graph (AGENTS R1), per-row
  provenance (AGENTS R11), and stable semantic refs (AGENTS R13).
- The mode-switch and cache-clear endpoints are non-GET `/vocab` routes and are
  therefore covered by the existing R12 guard set and its executable check.

---

## 11. Privacy contract

**OFFLINE mode:** no dictionary network access after installation. The existing
README claim holds unchanged for this mode.

**ONLINE mode, stated honestly:**

- the backend contacts GitHub / GitHub's static asset infrastructure to fetch
  shards;
- no telemetry, no analytics, no account, no error reporting;
- no card, review, user-meaning, or audio data is uploaded, ever;
- the word the user searched **never appears** in a requested URL — shard
  filenames are bucket indices;
- GitHub nevertheless observes the user's IP address and the sequence of shard
  indices requested;
- because the routing algorithm is public and committed, shard access **may
  permit inference** about what was looked up. Wortlaut does not claim shard
  access is cryptographically private, and must not be documented as if it were.

README's "nothing leaves your network" line is accurate only for Offline mode
and must be scoped when the feature ships (§16).

---

## 12. Rejected alternatives

### 12.1 Remote SQLite over HTTP Range requests (D83)

Opening the published 945 MB SQLite file directly over HTTP Range requests is
rejected as the production architecture, because:

- SQLite's B-tree access pattern assumes low-latency random access; each
  `lookup_exact` walks index and table pages that are only discovered
  sequentially, so a single lookup becomes a dependent chain of network
  round-trips;
- lookup latency and total bytes become a function of page layout rather than of
  anything the product controls, and the 87-bucket compound probe (§1.2) shows
  how quickly that degrades;
- GitHub Release assets are an artifact distribution channel, not a database
  service; Range support and redirect behaviour there are neither contractual
  nor version-stable for this purpose;
- a custom VFS owns page caching, locking, retry, partial-read and error
  semantics — a large amount of hard, security-relevant code whose failure modes
  surface as *wrong data*, not as errors;
- observability and failure isolation are poor: a truncated or misordered range
  response is a corrupt page, not a clean exception.

Not implemented, not partially implemented, not kept as a fallback.

### 12.2 A Wortlaut-hosted dictionary query API (D84)

Rejected for this version: it introduces always-on infrastructure, hosting and
operations cost, a service-availability dependency for a local-first product,
server security responsibility, and telemetry/privacy questions — all for a
static, read-only, immutable dataset that a CDN-backed artifact store already
serves. It also contradicts ADR-0001's "live Wiktionary API at runtime"
rejection for the same underlying reason.

### 12.3 Mandatory full download (status quo)

Rejected by the owner: a 945 MB precondition before the first screen is a
product barrier, and it is unnecessary for a dataset whose typical lookup
touches a few megabytes.

### 12.4 One release asset per lemma

Rejected: 1,118,636 assets against a 1,000-asset ceiling is impossible by three
orders of magnitude, and it would leak the searched lemma into the URL,
destroying the §11 privacy property that bucket routing provides.

### 12.5 Compressed shards in v1

Deferred, not rejected on merit: it adds a decompression surface and a second
integrity boundary (compressed vs. decompressed digest) without changing the
architecture. Filed to `docs/backlog.md`.

### 12.6 Per-lemma prefetch of the whole example set for hot lemmas

Rejected: the `der` case is 230,795 links. Lazy example-shard fetching bounded
by the 92.6 MB family total (§5.5, §14.3) is strictly better.

---

## 13. Builder and publication

### 13.1 `tools/build_online_dictionary.py`

Input: exactly one verified full `dictionary.sqlite`. The builder **verifies
the input's SHA-256 against the pinned v2 identity before building a production
shard set** and refuses otherwise. It opens the source `mode=ro&immutable=1` and
never mutates it.

Output, written to a caller-supplied directory **outside** the Git tree:
membership filter, `lookup` shards, `entry` shards, `example` shards, and the
online manifest.

Requirements: stream/partition rather than loading the asset into memory;
deterministic row order within every shard; exact preservation of row values
including `source`, `license`, and all `semantic_ref` values; verification of
the logical closure each family promises (§5.2); recomputation and verification
of every emitted digest; and a build report containing row counts, total output
bytes, and the largest/smallest/median shard per family.

Production shard files **must not** be committed to Git. The implementation
slice adds the `.gitignore` protections and, ideally, an executable check.

### 13.2 Determinism

Byte-for-byte reproducibility across runs on the same input is the target and
the builder must report whether it achieved it. Where SQLite file-format
non-determinism (page freelists, `sqlite_sequence`) makes byte equality
impractical, the builder must instead prove **content** determinism (identical
ordered row sets per shard) and record that distinction explicitly rather than
quietly weakening the claim.

### 13.3 Publication sequence (D104)

1. implement builder / provider / UI on a branch;
2. build and validate the production v2 shard set;
3. prepare a **draft** GitHub Release `dictionary-online-v2`;
4. upload shard assets to the draft;
5. independently review code + manifest + generated asset evidence;
6. publish the already-prepared release;
7. verify anonymous shard access from a clean environment;
8. merge the accepted code candidate.

The existing `dictionary-v2` release is not modified at any step. **This
ADR-only mission creates and publishes nothing.**

### 13.4 Storage and operational cost (D106)

- Source asset: 0.95 GB (already present).
- Full shard corpus: **≈ 0.90 GB** (the §5.6 895.7 MB projection, including
  sense-route indexes).
- Peak temporary disk with incremental emission and upload: **≈ 1.1 GB** beyond
  the source, if shards are uploaded and released per family rather than staged
  as one complete tree.
- Absolute worst case if a full staging copy is also kept: ≈ 1.9 GB beyond the
  source.
- The builder must check free space against a declared budget before writing and
  must fail closed with the required figure rather than filling the disk. The
  current machine reports ~13 GB free, which is sufficient for the incremental
  path with margin.
- Per-user online cache: bounded in practice by usage; the theoretical maximum
  is the ≈0.90 GB corpus, versus 0.95 GB for the offline asset. Users are not
  worse off, and "Clear online cache" is always available.

---

## 14. Testing and differential verification

### 14.1 The gate (D102)

`make gate` runs the differential harness against a **tiny deterministic
fixture** dictionary built by the builder itself from a synthetic PART-A asset.
`make gate` never downloads production shards and never touches the network.

The harness constructs a `LocalDictionaryProvider` over the fixture asset and an
`OnlineDictionaryProvider` over the fixture's shard set served from a local
directory, then asserts observable equality across a deterministic sample
covering:

exact lemmas · capitalization variants · umlauts · `ß` · nouns with gender ·
verbs (including separable) · surface forms · lemmas with multiple senses ·
DE and EN learner meanings · examples · derived compounds · unknown words ·
semantic-ref relinking.

Equality means: identical ordered row sequences, identical field values,
identical `None`/absence, identical dedup behaviour, and identical
`asset_token`.

### 14.2 Required dedicated tests

1. **Routing equivalence (§6.2).** For a large deterministic sample of real
   lemma texts and adversarial queries, assert
   `bucket(Q) == bucket(R.lemma)` for every pair that matches under the current
   predicate. Must include the 2,716 ASCII/Unicode-lower divergence population,
   NFD inputs, `STRASSE`, and `äpfel`.
2. **Closure.** For every family, assert that the rows routed into bucket *b*
   are exactly the rows the corresponding full-asset query could match. For
   lookup shards, additionally prove every authoritative `sense_ref` appears
   exactly once in `sense_route`, routes to its parent `lemma_ref`, and a
   `sense_ids[sense_ref]` read plus D47 relink fetches only that lookup bucket
   then that parent entry bucket—never an entry-shard scan.
3. **Membership filter semantics.** Every key in the build set is reported
   present (zero false negatives); false positives are permitted and measured
   FPR is reported against the manifest-declared statistical target.
4. **Family maximum and remote budget.** A harness proves the absolute maximum
   distinct lookup identities is N=256, then enforces D88's 32-new-remote-shard
   budget. A forced 33rd new remote lookup acquisition cancels cleanly, releases
   request leases, preserves verified cache integrity, returns
   `online_dictionary_budget_exceeded`, and performs zero PART-B writes. The
   approximate 12-shard production probe remains a non-normative observation,
   not this test's correctness bound.
5. **Integrity and cache lifecycle.** Truncated, byte-flipped, wrong-SHA, non-SQLite, and
   wrong-dataset-version shards are rejected, never cached as active, and
   surface `online_dictionary_unavailable` with zero PART-B writes. A later
   byte-corrupted canonical cache entry is revalidated, never opened, safely
   evicted/quarantined and refetched or fails closed. Concurrent same-shard
   misses produce one verified installation; clear during an active lease keeps
   its reader valid, defers its canonical cleanup, blocks new acquisition, and
   touches no PART-B/offline asset/media file.
6. **Atomicity.** Concurrent same-shard misses produce one verified installation
   and a provider switch under active leases never mixes providers within one
   logical operation.
7. **Mode persistence.** All four §8.2 startup branches, including the corrupt
   preference file failing safe without enabling network access.
8. **Offline regression.** The full existing suite passes unchanged with the
   local provider, proving D82's "offline behaviour is unchanged" claim.

### 14.3 Production-v2 validation

Before publication (§13.3 step 2), a much larger deterministic sample plus
explicit row/count validation must be run against the real shard set, and it
must include at least one lemma from each measured tail: a >100,000-link lemma
(`der`), a >1,024-fan-out surface form, and a lemma whose entry shard is at the
family maximum. The measured worst-case byte cost of each must be recorded in
the slice report.

---

## 15. Backward compatibility

- A user with a valid `~/.local/share/flashcard/dictionary/dictionary.sqlite`
  and no persisted preference launches into Offline and is never shown the
  chooser (D105).
- Persistent user paths are unchanged: `~/.local/share/flashcard/` with
  `flashcards.sqlite`, `media/`, `cache/`, `dictionary/dictionary.sqlite`.
- `release/dictionary-manifest-v2.json`, `ATTRIBUTION-v2.md`, and the
  `dictionary-v2` release are unchanged.
- `./wortlaut`, `./flashcard`, `--dict-path`, `--data-dir`, `--user-db`,
  `--port`, and `--no-browser` keep their current behaviour. `--manifest` and
  `--install-dictionary` retain the existing offline developer/recovery and
  install lifecycle, with the §9.3 restriction that a custom manifest cannot
  become a runtime/Online source.
- PART-B schema is unchanged; no migration is introduced by this ADR.
- `asset_token` for v2 is unchanged in both modes, so existing picker tokens,
  bindings, and review state are unaffected by adopting online mode.

---

## 16. Interaction with accepted ADRs and AGENTS rules

### 16.1 ADR interactions

| Accepted decision | Interaction |
|---|---|
| **ADR-0001 D4** — dictionary is a static SQLite asset distributed via GitHub releases | **Extended, not superseded.** Online mode uses the same static-artifact channel at finer granularity. The dataset is still built offline, still versioned, still checksummed. |
| **ADR-0001 D1 / AGENTS R1** — no LLM at runtime | Untouched. No LLM SDK enters the graph. R1's *defect statement* ("an offline app silently grows a network failure path") is addressed head-on by D92, D97 and D98: the path is opt-in, user-visible, documented, and fail-closed. |
| **ADR-0001 §12** — dictionary is disposable and refetchable | Reinforced. The online shard cache is also disposable and refetchable, and is stored under the existing cache area. |
| **ADR-0001 rejected: "live Wiktionary API at runtime"** | Not resurrected. Online mode serves the same pre-built rows from immutable artifacts; it does not query a third-party API or re-parse wiki markup at runtime. |
| **ADR-0002 D20** — fully standalone service | Preserved. Offline mode remains fully standalone; Online is a user-chosen mode, never a precondition. |
| **ADR-0002 D25 / AGENTS C1** — app factory | The provider is injected through the factory. No module-level state and no import-time env reads are added. |
| **ADR-0002 D26** — opportunistic remote TTS with bounded timeout and silent fallback | Deliberately *not* the model here: dictionary correctness may never be silently degraded, so D98 requires an explicit error instead of a silent fallback. |
| **ADR-0002 §4.1 / AGENTS R12** — browser trust boundary | Unchanged. New non-GET routes inherit the full guard set. |
| **ADR-0004 D47 / AGENTS R13** — stable semantic refs, atomic activation/relink | Preserved and strengthened. D90 keeps the logical identity mode-independent so a mode switch performs no relink; D100 keeps ref resolution bounded without changing any call site's semantics. |
| **ADR-0004 D46** — all-components-or-none derived compounds | Preserved. Component binding is a provider read like any other; D98 guarantees a failed fetch produces an error, never a partial component set. |
| **ADR-0007** — DE/EN only | Untouched. |

No accepted ADR body is rewritten by this ADR, and no historical decision is
retroactively edited. Nothing in ADR-0001/0002/0004 is *superseded* here: this
ADR only extends D4's distribution model and adds a seam in front of an
existing runtime, so no supersession record is required. Should cold review
determine that D4 is genuinely superseded rather than extended, the remedy is a
supersession record in this ADR's own §16, not an edit to ADR-0001.

### 16.2 Governance amendments deferred to implementation

This ADR intentionally changes **no** executable AGENTS rule, because the code
those rules would govern does not exist yet. The implementation slice must carry
exactly these governance changes, and no others:

1. **AGENTS R14 (new, `[executable]`) — Product-path pinned distribution
   network.** Product/runtime/UI outbound traffic from `app/` is permitted only
   through committed Wortlaut manifests and §10's HTTPS initial/redirect host
   policy; no generic Product fetch helper and no browser-supplied URL may reach
   a server-side fetch. The explicit operator-only developer/recovery
   `--manifest PATH --install-dictionary` offline-install path is segregated
   from R14's automatic Product domain, remains credential-redacted, and cannot
   persist/configure Online mode. Gate check: scan product network entry points
   and assert they are reached only through the validated committed-manifest
   policy; test the explicit CLI segregation separately.
2. **AGENTS R9 clarification.** The online shard cache is dictionary material,
   is disposable, and lives under the cache area — never in the user database or
   its volume. R9's separation invariant is restated, not weakened.
3. **`MODULES.toml`.** New modules for the provider seam, the online provider,
   the shard cache, the preferences store, and `tools/build_online_dictionary.py`,
   with their `owned_paths`, `dependencies`, `focused_tests` and `adrs = ["0008"]`.
4. **README.** Scope "nothing leaves your network" to Offline mode and add the
   §11 privacy text for Online mode.
5. **`release/README.md`.** Document
   `release/dictionary-online-manifest-v2.json` and the `dictionary-online-v2`
   release identity.

Nothing in that list is applied by this ADR-only mission.

---

## 17. Implementation sequence

1. **S1 — Provider seam, offline only.** Introduce `DictionaryProvider` and
   `LocalDictionaryProvider`, route `app/api.py` and `app/deck.py` reads through
   it, and convert `ReadingSnapshot`'s reference maps to lazy resolvers (D100).
   Acceptance: the entire existing suite passes unchanged; no behaviour change;
   no online code yet. This step is independently valuable and independently
   revertible.
2. **S2 — Preferences, startup state machine, `dictionary_unavailable`.** Make
   the app startable with no dictionary. Acceptance: §14.2 test 7; existing
   users still boot straight into Offline.
3. **S3 — Builder + fixture shard set + differential harness.** No network.
   Acceptance: §14.2 tests 1–4 against the fixture.
4. **S4 — Online provider + shard cache + manifest validation + failure
   semantics.** Acceptance: §14.2 tests 5, 6, and the full differential harness.
5. **S5 — UI: first-run chooser, settings view, cache display, UI-initiated
   offline install with progress.** Acceptance: Playwright coverage of both
   modes and both switch directions against the real served product.
6. **S6 — Production v2 shard build + validation + draft release + independent
   review + publish + anonymous access verification + merge** (§13.3).

Steps 1 and 2 land value with zero network surface, which is the right order if
the later steps stall.

---

## 18. Rollback and failure recovery

| Failure | Recovery |
|---|---|
| A published shard is later found corrupt | Every shard is content-addressed in a committed manifest. Republish the corrected shard and the manifest; clients reject the old bytes on SHA mismatch and refetch. No user data is involved. |
| The whole online format proves defective | Set mode to Offline. The full `dictionary-v2` release and installer are untouched, so recovery is a download, not a migration. |
| Online mode ships and must be withdrawn | Revert the frontend chooser and default startup to Offline. The preferences file is machine-local, is not user data, and an unknown/withdrawn mode value fails safe to unconfigured (§8.2). |
| A user's cache is corrupted or full | "Clear online cache" removes it. It is disposable by construction and contains no user data. |
| `dictionary-online-v2` is deleted or unreachable | Online mode reports `online_dictionary_unavailable`. Offline mode and all local user data are unaffected. |
| Implementation lands and later needs reverting | Steps S1/S2 (seam + startability) are separable from S4/S5 (network + UI); reverting the latter leaves a strictly better-factored offline product. |

At no point does any rollback path delete or migrate cards, reviews, user
meanings, or audio.

---

## 19. Consequences

**Positive.** New users start in seconds instead of after ~945 MB. Existing
users are unaffected. The dictionary finally gets a real seam, which also
removes `app/api.py`'s raw-connection coupling. The eager 1.1M-entry map copy
per `reading()` call becomes a bounded lazy resolution. Privacy is documented
honestly instead of aspirationally.

**Negative.** A second read path exists and must be proven equivalent forever —
hence D102's gate. Online mode introduces a real network failure surface into a
product whose identity is offline-first. The online corpus (~0.90 GB, 577
assets) is a second artifact set to build, publish, and keep consistent with the
full asset. Eleven pathological surface forms retain a large worst-case fetch
(§5.7).

**Neutral.** Total bytes a heavy online user eventually downloads (~0.90 GB) is
comparable to the offline asset (0.95 GB); the win is *when* and *whether* those
bytes are needed, not their sum.

---

## 20. Cold review

Cold review #1 — broad architecture challenge — is complete. Its blockers are
preserved below. This ADR remains **NEEDS COLD REVIEW** until a fresh cold
review #2 approves it; this revision does not approve itself.

Cold-review lineage count: **1 completed / #2 next — focused remedy
verification.**

### O1 — Sense-reference point reads are not bucket-closed.

**Defect:** entry shards route only from a lemma semantic-ref digest, but D100
retains `sense_ids[sense_ref]` point reads and D47 relinking receives sense
refs. A `sense:v1:<digest>` does not reveal its parent lemma's entry bucket; no
sense-ref index family is defined.

**Why it blocks:** Online mode must otherwise scan entry shards or return an
incorrect absence, violating D86/D100, R13, and equivalent semantics.

**Affected:** §§4–5, D86, D100, §14.

**Required remedy:** add a bucket-closed sense-ref index/routing path and
account for its assets/bytes, or redesign every caller to supply a parent lemma
ref.

#### Resolution — O1

D86, §5.3, §5.6, §7 and §14.2 now place a logically independent
`sense_route(sense_ref → lemma_ref)` index in the existing 256 physical lookup
shards. A sense point read/D47 relink routes sense ref → lookup shard → parent
lemma ref → entry shard, with no entry scan. The builder must emit every
authoritative sense ref exactly once and the revised differential/closure tests
exercise arbitrary `sense_ids` reads and D47 relinking. The verified-v2 probe
measured 480,221 mappings and 78,663,680 added lookup-family bytes; §5.6
revises the projection to 417.6 MB, ≤1.61 MB median and ≤3.72 MB max while
retaining 577 assets. Slice-10 acceptance now requires this routing and
no-scan proof. The missing bucket-closed path is therefore specified and sized.

### O2 — The outbound-network contract contradicts retained installer behavior.

**Defect:** D96/R14 permit only pinned HTTPS distribution assets, but the
existing `dict_install` accepts arbitrary `http(s)` and `file://` manifest
URLs; `wortlaut --manifest` preserves that path. D94 says to retain it unchanged
in substance.

**Why it blocks:** R14 cannot be truthfully enforced, and the proposed network
boundary is not executable.

**Affected:** D94, D96, D103, §15, §16.2.

**Required remedy:** define a strict production/UI installer source and
redirect-host policy, then either constrain or explicitly segregate the generic
developer manifest path outside the runtime network contract.

#### Resolution — O2

D94/D96, §§9.3 and 10, §15 and §16.2 now define Product and
Developer/Recovery trust domains. Product/runtime/UI traffic uses only committed
Wortlaut manifests, exact HTTPS GitHub Release initial paths, and a closed
redirect policy (`github.com` initial, then only
`release-assets.githubusercontent.com` or `objects.githubusercontent.com`, at
most three HTTPS redirects, no userinfo/non-default port). The explicit
operator-only `--manifest PATH --install-dictionary` offline-install override
retains current local-manifest `file://`/`http(s)` source compatibility with
credential redaction, but cannot persist, configure Online, or be reached from
browser/API input. R14 is explicitly scoped to Product traffic and Slice-10
now allowlists its gate/test work and tests this segregation. The network
contract is consequently enforceable without falsely denying the explicit
developer path.

### O3 — The CLI matrix is not exhaustive as claimed.

**Defect:** §9.3 omits `--dictionary-mode` interactions with `--manifest` and
does not fully specify precedence/network behavior for `--data-dir`,
`--dict-path`, and `--install-dictionary` combinations.

**Why it blocks:** acceptance cannot mechanically prove D103's “specified
exhaustively” claim; online mode could ambiguously use a custom offline manifest
or the committed online manifest.

**Affected:** D103, §9.3, §15, Slice-10 acceptance 11.

**Required remedy:** add a complete combination table with preference/cache
locations, manifest applicability, network permission, and exit behavior.

#### Resolution — O3

D103, §9.3 and §15 now supply the 24-row Cartesian CLI matrix over mode,
custom-manifest, explicit-dictionary-path and install, plus the data-root/path
rules that apply to every row. It specifies provider, session-only persistence,
preferences/cache/canonical-offline/PART-B-media paths, Product versus
Developer/Recovery network permission, custom-manifest exclusion from Online,
installation-before-normal-launch behaviour, precedence and every usage error.
In particular Online plus `--dict-path`, `--install-dictionary`, or custom
`--manifest` rejects before mutation. Slice-10 acceptance now requires exact
enumeration of the table. The former ambiguity is removed.

### O4 — Cache corruption and clear-cache concurrency lack an executable lifecycle contract.

**Defect:** D95 verifies newly downloaded shards, but does not require
validation/recovery on later cache reads or define lease behavior when “Clear
online cache” races an in-flight/pinned shard.

**Why it blocks:** a later-corrupted cached shard can be read without
re-verification, and deletion behavior is platform-dependent while SQLite
handles remain active.

**Affected:** D95, D98–D99, §14.2(5–6), §18.

**Required remedy:** specify per-shard leases, cache-hit integrity
validation/eviction/refetch, and clear-cache behavior that never invalidates an
active reader or touches user data.

#### Resolution — O4

D95/D98–D99 and §5.9 define `ABSENT → DOWNLOADING → VERIFIED → LEASED`
immutable snapshots, per-shard single flight, exact cache-hit byte/SHA
revalidation before a new lease, safe corrupt-entry quarantine/eviction and
refetch/fail-closed recovery. Clear-cache uses compatible cache-then-generation
lock order, blocks new canonical leases, removes unleased files, defers leased
canonical cleanup until final release, and never relies on unlinking an open
SQLite path. It names the only allowed cache subtree and expressly excludes
PART-B, media and offline dictionary files. §14.2 and Slice-10 acceptance now
cover corrupt cache, clear during a lease, same-shard single flight,
provider-switch leases and no-user-data-touch proof. The lifecycle is now
executable.

### O5 — The Bloom-filter download bound is stated as a guarantee that Bloom filters cannot provide.

**Defect:** “at most filter hits + measured FPR allowance” is not a
deterministic bound; an adversarial query can encounter arbitrarily many false
positives up to the finite shard-family maximum.

**Why it blocks:** §14.2(4) is not a universally executable acceptance test,
and §5.8 overstates the guarantee.

**Affected:** D88, §5.8, §14.2(4).

**Required remedy:** state and test the hard family-based maximum with
cancellation/error semantics; retain the ~12-shard result as an empirical
expectation, not a correctness bound.

#### Resolution — O5

D88, §5.8 and §14.2 distinguish the zero-false-negative/statistical-FPR Bloom
property from two deterministic limits: the absolute 256 distinct lookup-family
identity maximum, and a 32-new-remote-lookup-shard per-operation safety budget.
The latter is measured against the revised ≤3.72 MB shard projection (≤119.1
MB transfer) and permits 2.7× the observed approximately 12-shard probe. A
33rd new remote identity cancels, releases request leases, preserves cache,
returns `online_dictionary_budget_exceeded`, and makes no PART-B mutation; it
is never `needs_gloss` or not-found. Slice-10 acceptance mechanically tests
zero false negatives, permitted false positives, family maximum, budget
enforcement and fail-closed error. The ~12 result is explicitly non-normative.
