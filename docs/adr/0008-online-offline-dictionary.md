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
| **D86** | **Static sharded dataset with three shard families plus one membership filter**, each family bucket-**closed** for the queries it serves (§5). Families and counts: `lookup` × 256, `entry` × 256, `example` × 64, `filter` × 1 — **577 assets**, 57.7% of GitHub's 1000-asset limit. | Measured (§5.6) to keep the common lookup at ~1.3 MB + ~1.5 MB while leaving 423 assets of headroom. |
| **D87** | **Routing keys over-approximate; matching stays exact.** The routing function is `bucket(k) = int.from_bytes(sha256(python_lower(k))[:4]) % N`. It is used **only** to select a shard. Every match/order/dedup decision is made by executing the *current* predicate against the fetched rows. Python `casefold()`, Unicode normalization changes, and stripping are forbidden as behaviour changes. | §6. The current predicate mixes SQLite's ASCII-only `lower()` with Python's Unicode `lower()`; 2,716 lemma texts depend on that asymmetry. |
| **D88** | **Negative-membership accelerator.** A single verified Bloom filter over the lemma lookup key set (exact texts ∪ ASCII-lowered texts) is downloaded once when Online mode is activated. No false negatives; target false-positive rate ≤ 1%; deterministic build parameters; implemented in-repo over `hashlib`, with no third-party runtime dependency. | Turns the 96-key / 87-bucket unknown-compound probe into ~12 fetches. Measured size: 1,477,819 keys → **1.69 MB** at 1% FPR (k=7). |
| **D89** | **`release/dictionary-online-manifest-v2.json`** is committed as normal text metadata, is the *only* source of shard URLs, and is validated strictly and fail-closed before any request. It pins the canonical full-dataset SHA, the routing parameters, the filter parameters, and the exact filename, byte count and SHA-256 of every shard. | An unpinned or partially validated manifest is an arbitrary-fetch primitive with extra steps. |
| **D90** | **Logical dataset identity is mode-independent.** For v2, `asset_token` is `1698b997…67d4c` in both modes. Per-shard SHA-256 values prove transport and cache integrity only; they never become the dataset identity. Switching Online ↔ Offline within one version performs **no** D47 relink and does not change any stable semantic ref. | Prevents a mode switch from masquerading as a dictionary version change, invalidating picker tokens, or forking review state. |
| **D91** | **Mode is a local application preference** persisted in a small validated, atomically written `preferences.json` under the existing data directory. States: `unconfigured` \| `online` \| `offline`. No PART-B schema migration is added for it. | Mode is machine-local configuration, not dictionary data and not user study data (AGENTS R9). |
| **D92** | **Startup never contacts the network before an explicit user choice.** The startup state machine is §8.2. In `unconfigured` state the app starts with no active provider and every dictionary-dependent operation fails with a structured `dictionary_unavailable` state, never a crash. | Requirement I; also keeps `./wortlaut` honest for a user who never opts into online mode. |
| **D93** | **Settings/Dictionary UI contract** (§9.2) exposes mode, online cache size and shard count with an explicit "Clear online cache", and offline install state with explicit "Download for offline use" / "Remove offline copy". Destructive actions are separate explicit user actions and never touch user data. | Requirement J. |
| **D94** | **UI-initiated offline install reuses `app/dict_install.py` unchanged in substance**; a progress-reporting seam is added, not a second downloader/verifier. `./wortlaut --install-dictionary` remains supported. | Two download/verify implementations means two integrity contracts and one of them will rot. |
| **D95** | **Online shard cache** lives at `<data-dir>/cache/dictionary-online/<version>/<family>/`, is disposable, contains no user data, verifies exact manifest bytes + SHA-256 before a shard becomes active, is written temp-then-fsync-then-atomic-rename, opens read-only/immutable, is single-flight per shard key, and never mixes versions. Automatic LRU eviction is out of scope for v1; explicit "Clear online cache" is required. | Requirement L. Matches the existing atomic-install discipline in `dict_install.py`. |
| **D96** | **Outbound HTTPS only to manifest-pinned dictionary distribution assets.** No generic fetch API, no browser-supplied URL reaching a server-side fetch. Scheme, host, path/filename, byte count and SHA are all validated. Loopback bind, Host/Origin checks, CORS exactness and `X-Flashcards-Request` are untouched. | Requirement M; AGENTS R8/R12 unweakened. |
| **D97** | **Honest privacy contract** (§11). Offline: no dictionary network access after installation. Online: GitHub sees the user's IP and an opaque shard access pattern; the searched word never appears in a URL; no telemetry, analytics, account, or upload of user data. Shard access is **not** claimed to be cryptographically private. | A public routing algorithm permits inference. Saying otherwise would be false. |
| **D98** | **Online failure is explicit and never fabricated.** Unavailable / timeout / wrong size / wrong SHA / invalid SQLite / malformed / wrong dataset version ⇒ the shard is never used, no stub or partial dictionary result is synthesized, an actionable `online_dictionary_unavailable` error is returned, user data is untouched, and the persisted mode is not silently changed. A clearly surfaced temporary local fallback is permitted only when a complete verified offline dictionary exists; it is optional and it is never silent. | Requirement O. A "successful" lookup produced by a failed fetch would write wrong bindings into PART B. |
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

Contents for bucket *b*:

- the resolver-facing `lemma` projection (`id`, `semantic_ref`, `lemma`, `pos`,
  `gender`, `freq_rank`) for every lemma with `bucket(python_lower(lemma)) == b`;
- every `surface_form` row whose `bucket(python_lower(form)) == b`, carrying the
  target lemma's `id` and its `entry` bucket;
- inline deduplicated lemma projections for the lemmas referenced by
  high-fan-out forms in this bucket (§5.7).

`resolve_word` probes `lookup_exact(cleaned)` and then
`lookup_surface_form(cleaned)` with **the same key**, so ladder steps 1 and 2
are served by **one** shard fetch.

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

Content bytes plus a fixed per-row overhead allowance, computed over the real
v2 asset. These are **budget targets**, not built artifacts; D101 requires the
builder to report measured file sizes and the implementation slice to reconcile
them against these budgets.

| Family | Shards | min | median | p95 | max | family total |
|---|---|---|---|---|---|---|
| `lookup` | 256 | 1.26 MB | **1.30 MB** | 1.36 MB | 3.39 MB | 338.9 MB |
| `entry` | 256 | 1.38 MB | **1.47 MB** | 1.75 MB | 2.36 MB | 383.9 MB |
| `example` | 64 | — | — | — | — | 92.6 MB (mean 1.45 MB) |
| `filter` | 1 | — | 1.69 MB | — | — | 1.7 MB |
| **total** | **577** | | | | | **≈ 817 MB** |

Budget: **no shard may exceed 4 MB**; the median lookup and entry shard must
stay at or below 2 MB. Asset count 577 of 1000 leaves 423 assets (42.3%) of
headroom for a future family or a higher shard count.

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
  65,310 lemmas span the whole family, i.e. up to 338.9 MB of `lookup` shards.

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

Surface-form lookups are deliberately **not** filtered: `resolve_word` performs
at most one surface probe per word, so a filter would save at most one fetch
while costing roughly 10 MB of first-run download for ~8.5M keys.

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
3. `asset_base_url` must be `https://`, must be on the expected release host,
   and must not embed credentials (`@`, `token=`, `api_key=`, `apikey=`) — the
   existing `dict_install` predicate, reused rather than reimplemented.
4. Every shard entry must carry a positive byte count within a per-family
   ceiling and a 64-character lowercase hex SHA-256.
5. Shard counts must match the `routing` block exactly; a missing or duplicate
   shard index is a rejection.
6. URLs are **derived** from `asset_base_url` + `filename`. No URL is ever
   accepted from the browser, from a shard, or from an HTTP response body.

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

| Invocation | Behaviour |
|---|---|
| `./wortlaut` | Unchanged for existing users (D105). Applies §8.2. |
| `./flashcard …` | Unchanged compatibility alias; execs `./wortlaut`. |
| `./wortlaut --install-dictionary` | Unchanged: installs and verifies the full asset via `dict_install`. On success, persists mode `offline` if no preference exists; never downgrades an existing explicit `online` preference. |
| `./wortlaut --dictionary-mode online` | **Session-only.** Runs this launch in Online mode. Does not write `preferences.json`. |
| `./wortlaut --dictionary-mode offline` | **Session-only.** Requires an already-valid local asset; does not trigger a download. Exits non-zero with an actionable message if absent. |
| `--dictionary-mode` + `--dict-path` | `--dict-path` implies an explicit local asset, so it is compatible with `offline` only. Combining it with `online` is a usage error (exit 2). |
| `--dictionary-mode online` + `--install-dictionary` | Permitted and unambiguous: the install runs first and completes, then the session runs in Online mode; the persisted preference is untouched. |

`--dictionary-mode` being session-only is the whole point: headless and
scripted invocations must not silently reconfigure a human's installation.

---

## 10. Network security boundary

- Online mode performs outbound HTTPS **only** to manifest-derived shard URLs
  (D96). There is no generic fetch endpoint, and no browser input selects a
  server-side fetch URL.
- Validated per request: scheme, host (and any redirect host), derived path /
  single-segment filename, declared byte count, and SHA-256 of the received
  bytes before the shard becomes readable.
- Credential redaction and the fail-closed URL predicates from
  `app/dict_install.py` are reused, not reimplemented.
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
- Full shard corpus: ≈ 0.82 GB.
- Peak temporary disk with incremental emission and upload: **≈ 1.0 GB** beyond
  the source, if shards are uploaded and released per family rather than staged
  as one complete tree.
- Absolute worst case if a full staging copy is also kept: ≈ 1.9 GB beyond the
  source.
- The builder must check free space against a declared budget before writing and
  must fail closed with the required figure rather than filling the disk. The
  current machine reports ~13 GB free, which is sufficient for the incremental
  path with margin.
- Per-user online cache: bounded in practice by usage; the theoretical maximum
  is the 0.82 GB corpus, versus 0.95 GB for the offline asset. Users are not
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
   are exactly the rows the corresponding full-asset query could match.
3. **Membership filter has no false negatives.** Every key in the build set is
   reported present; measured FPR is within the manifest-declared bound.
4. **Compound bound.** Resolving an unknown long word touches at most
   (filter hits + measured FPR allowance) shards, not the 87 buckets the raw
   probe produces.
5. **Integrity failure.** Truncated, byte-flipped, wrong-SHA, non-SQLite, and
   wrong-dataset-version shards are rejected, never cached as active, and
   surface `online_dictionary_unavailable` with zero PART-B writes.
6. **Atomicity.** Concurrent requests for the same uncached shard produce one
   active cache entry and no corruption; a mode switch under concurrent load
   never mixes providers within one logical operation.
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
  `--port`, `--no-browser`, `--manifest`, `--install-dictionary` all keep their
  current behaviour.
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

1. **AGENTS R14 (new, `[executable]`) — pinned-asset-only outbound network.**
   Outbound HTTPS from `app/` is permitted only to manifest-derived dictionary
   distribution assets; no generic fetch helper; no browser-supplied URL may
   reach a server-side fetch. Gate check: scan `app/` for network entry points
   and assert each one is reached only through the validated manifest path.
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
product whose identity is offline-first. The online corpus (~0.82 GB, 577
assets) is a second artifact set to build, publish, and keep consistent with the
full asset. Eleven pathological surface forms retain a large worst-case fetch
(§5.7).

**Neutral.** Total bytes a heavy online user eventually downloads (~0.82 GB) is
comparable to the offline asset (0.95 GB); the win is *when* and *whether* those
bytes are needed, not their sum.

---

## 20. Cold review

No cold review is performed in this drafting session. A fresh cold orchestrator
session must review this ADR under WORKFLOW §7 / AGENTS G7. This is a new
lineage; its first review is **cold review #1 — the broad architecture
challenge**.

Cold-review lineage count: **0 completed / #1 next.**
