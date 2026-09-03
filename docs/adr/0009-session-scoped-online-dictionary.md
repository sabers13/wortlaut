# ADR-0009 — Session-scoped online dictionary

**Status:** NEEDS COLD REVIEW.

**Lineage:** ADR-0008 is terminally **NON-CONVERGENT / BLOCKED** after its
third cold review. ADR-0009 is a materially simpler successor that supersedes
ADR-0008 for the Online/Offline dictionary product scope; ADR-0008 and
`tasks/slice-10.md` remain immutable historical evidence. This is **not**
ADR-0008 review #4. It starts a new lineage at cold review #1 because it
removes persisted dictionary-mode state and splits the work into independently
accepted infrastructure, session/UI, and publication phases.

## Decision

Wortlaut supports a local full dictionary and a trusted online dictionary, but
does **not** store a user dictionary-mode preference in this feature version.
There is no `preferences.json` for dictionary mode, and `online`, `offline`,
and `unconfigured` are never persisted backend/application states. A provider
is selected for the current process from explicit invocation and current local
facts only. A future persistent preference requires a separate decision after
this feature has proved stable.

### Startup selection

The launcher applies this order before provider construction, network access,
or PART-B mutation:

1. `--manifest CUSTOM` is an explicit Offline Developer/Recovery operation.
   Without `--install-dictionary`, it verifies the canonical Offline asset
   against that manifest then launches Offline. With installation, it uses the
   established Developer/Recovery install flow. It never configures the online
   provider or persists a choice. `--dictionary-mode online --manifest CUSTOM`
   is exit-2 usage error before network, provider, or PART-B mutation. Existing
   `--dict-path` precedence remains unchanged: without installation it selects
   that explicit Offline asset and makes a simultaneous manifest inert; with
   installation the manifest drives installation and constrains subsequent
   explicit-path activation.
2. An explicit `--dict-path` selects Offline for this process. Any explicit
   Online combination is rejected before mutation.
3. `--dictionary-mode offline` selects Offline for this process. A missing or
   invalid required asset produces a structured actionable error unless this
   invocation explicitly installs it; it never falls back to Online.
4. `--dictionary-mode online` selects the trusted `OnlineDictionaryProvider`
   for this process. It accepts no custom online manifest and writes no
   preference. Combining `--dictionary-mode online` with
   `--install-dictionary` is a deterministic exit-2 usage error, rejected
   before network access, provider activation, dictionary install, or
   PART-B mutation: downloading the full Offline dictionary while
   explicitly requesting Online for the session is contradictory in this
   version. A user can instead run normal installation or use the UI's
   explicit **Download for Offline use** action.
5. With no explicit selection, a valid canonical full Offline dictionary
   selects Offline automatically. Existing users therefore keep their fully
   local experience, with no chooser and no dictionary network request.
6. With no explicit selection and no valid full Offline dictionary, Wortlaut
   starts in an unconfigured *runtime* UI state. It makes zero dictionary
   network requests before user action and shows:

   ```text
   Choose how to use the dictionary
   [ Use Online ]                 Start now without downloading the full dictionary.
   [ Download for Offline use ]   Download ~945 MB and work without internet afterward.
   ```

   Choosing Online activates the trusted provider for the running process only.
   Choosing Offline performs the existing hardened full-dictionary installation
   and activates Offline only after verification.

At the next launch, a valid full Offline asset again selects Offline; otherwise
the chooser appears again. The UI must say that Online applies to the current
session.

This unconfigured chooser intentionally **supersedes** the prior fully-local
product's `missing dictionary -> launcher exits` behavior; that old behavior
is replaced, not preserved, by this ADR, and the existing launcher tests that
assert it must be updated to the new behavior rather than kept unchanged.
Installed/valid-Offline startup and custom-manifest integrity remain
backward-compatible and unaffected.

### Settings and user data

Settings offers **Use Online for this session**, **Use Offline**, **Download
for Offline use**, **Remove Offline dictionary**, and **Clear Online cache**.
Offline → Online retains the Offline asset. Online → Offline activates only a
verified full asset or offers download; incomplete data is never activated.
Removal and cache clearing are independent explicit actions and never affect
cards, reviews, meanings, or audio. Downloading the ~945 MB full Offline
asset performs a conservative free-space preflight, accounting for the
installer's temporary file and the existing activation/private-snapshot
behavior, so a download that is predictably unable to complete never begins;
an insufficient-space failure is actionable, replaces no valid Offline
asset, and mutates no user data.

`active_dictionary_metadata` (PART-B) keeps its existing, narrower meaning:
the metadata of the last successfully activated **full Offline** dictionary.
It is **not** dictionary-mode state and is never deleted merely because the
disposable canonical Offline asset is removed; this ADR introduces no new
preference/state table. **Remove Offline dictionary** while
`LocalDictionaryProvider` is the active session provider is rejected with a
structured, actionable conflict (conceptually `offline_dictionary_in_use`)
telling the user to switch to Online for this session first; no file is
deleted and no PART-B row is modified. While `OnlineDictionaryProvider` is
active and the canonical full Offline asset exists, removal verifies the
target is exactly the managed canonical asset, removes only that asset,
leaves `active_dictionary_metadata` unchanged, touches no cards, reviews,
meanings, audio, media, online cache, or semantic refs, and triggers no D47
relink — the Online provider continues using its own immutable shard leases
throughout. At the next launch, provider/startup selection checks whether
the canonical full Offline asset actually exists and validates **before**
constructing `LocalDictionaryProvider` or invoking its recovery path; a
stale historical `active_dictionary_metadata` row must never by itself
trigger `DictionaryRuntime`'s missing-file recovery error when no Local
provider is being activated — that combination (no explicit mode, canonical
asset absent) is simply the unconfigured chooser. Reinstalling the exact
same v2 canonical dictionary later reuses the normal metadata-match
activation path with no artificial D47 relink merely because the file was
once removed; activating a genuinely different dictionary identity still
follows the normal D47 activation/relink rules.

### Provider and online-data contract

`LocalDictionaryProvider` and `OnlineDictionaryProvider` expose one provider
contract. They represent the same v2 logical dataset token:

`1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.

Switching providers within that dataset performs no D47 relink and never uses
numeric SQLite IDs as durable identity. The online corpus is static GitHub
Release distribution, not remote SQLite VFS or a query API. Its committed,
trusted manifest describes 256 lookup shards, 256 entry shards, 64 example
shards, and one membership filter (577 assets total):

* Lookup and entry shards route by `bucket256_v1`, a deterministic,
  locale-independent function: `bucket256_v1(text) = SHA256(UTF-8 bytes of
  text).digest()[0]`, an integer in `0..255`. No Python `hash()`, no
  locale-dependent hashing, and no casefolding or Unicode normalization
  inside the hash function itself. Entry bucket =
  `bucket256_v1(lemma_semantic_ref)`; `sense_ref → lemma_ref` routing uses
  sense route bucket = `bucket256_v1(sense_ref)`.
* Example shards route by `example_bucket(example_id) = example_id % 64`
  across the fixed 64-shard family. `example.id` is deliberately an
  **active-dictionary-internal routing/index identity only** — it may be
  used to locate rows inside one immutable logical dictionary dataset; it
  must never be persisted into PART-B as durable identity; no existing
  PART-B table stores example IDs; and stable lemma/sense semantic refs
  remain the durable identity boundary, so this does not weaken AGENTS R13.
  The builder preserves authoritative example IDs exactly, and entry shards
  may carry those active-asset example IDs for subsequent example-shard
  retrieval. This 64-shard example family measures approximately 92.6 MB
  total in the prior verified-v2 probe — an operational transparency note,
  not a per-query correctness budget, and no lookup downloads that amount.
* ADR-0009 preserves the exact current observable lookup predicate —
  `X == Q OR sqlite_ascii_lower(X) == python_lower(Q)`, where
  `sqlite_ascii_lower` is SQLite's built-in ASCII-oriented `lower()` and
  `python_lower` is Python `str.lower()` — and does not replace it with
  `casefold()`, Unicode-wide SQLite lowering, or NFC/NFKC normalization.
  For each authoritative lookup-index row with text `X` (applied
  independently to the lemma and surface-form lookup indexes), the builder
  places/indexes that row in the union of `bucket256_v1(X)` and
  `bucket256_v1(sqlite_ascii_lower(X))` (deduplicated when equal). For a
  runtime query `Q`, the Online provider fetches the union of
  `bucket256_v1(Q)` and `bucket256_v1(python_lower(Q))` (deduplicated when
  equal), then applies the exact predicate above to the fetched candidates.
  This proves closure: the exact-match clause is covered because `X == Q`
  implies `bucket(X) == bucket(Q)`, and the folded clause is covered because
  `sqlite_ascii_lower(X) == python_lower(Q)` implies
  `bucket(sqlite_ascii_lower(X)) == bucket(python_lower(Q))`. Routing may
  over-approximate (fetching extra candidates the predicate then filters)
  but must never under-approximate. No query string is assumed to be NFC:
  the Online provider must match whatever the Local provider does for the
  exact input, including returning no result for a decomposed/non-NFC query
  if that is what Local returns.
* The Bloom membership set used for lemma-oracle pruning is built compatibly
  with the same predicate: for each authoritative lemma text `X` it includes
  keys covering both `X` and `sqlite_ascii_lower(X)` with zero false
  negatives for the runtime checks, queried with both `Q` and
  `python_lower(Q)` (deduplicated as appropriate). Its false-positive rate
  remains statistical only; it makes no deterministic FPR promise.
* A lookup family has at most 256 identities. One top-level operation may
  download at most 32 **new** remote lookup-shard identities. Exceeding this
  limit returns `online_dictionary_budget_exceeded`, never `needs_gloss` or
  `not-found`, and causes no PART-B mutation.

Every remote shard is leased only after byte-count, SHA-256, and SQLite/logical
validation; cache installation is temporary-file + fsync + atomic replace.
Validated leases are immutable and single-flight. Corrupt cache entries are
rejected/refetched; clear-cache is safe with in-flight leases. Product network
access accepts only committed Wortlaut manifests, HTTPS, the pinned GitHub
Release distribution contract, and validated redirects. Browser/API input
cannot supply a URL or manifest. Custom Developer/Recovery manifests remain a
separate Offline-only CLI trust domain. Product network trust is proven by
automated tests: arbitrary hosts rejected, plain HTTP rejected, userinfo
rejected, invalid redirects rejected, the approved release redirect
accepted, and no browser/API caller able to configure a source.

The deterministic builder consumes a verified full asset, preserves exact
semantic and attribution fields, and emits a manifest plus deterministic shard
families. Provider equivalence is proven by differential tests against the
local provider with tiny CI fixtures; production sampling is a later publication
gate. No production assets or releases are created by infrastructure work.

### Privacy

After installation, Offline makes no dictionary network access. Online static
distribution receives an IP address and opaque shard-access pattern; the search
word is not directly present in an asset URL. Wortlaut adds no telemetry or
analytics and uploads no cards, reviews, meanings, or audio. This is not a
claim of cryptographic query privacy.

## Consequences and implementation order

Removing stored mode removes the persisted-online startup path, preference
atomicity/corruption/migration logic, and the precedence conflict that produced
ADR-0008 F1. The accepted work is deliberately split:

1. **Slice 11:** provider seam, deterministic shards/manifest, trusted online
   retrieval, verified cache leases, and provider differential evidence. No
   first-run or Settings UI. Its provider contract must be designed and
   tested against a complete inventory of every dictionary read that
   `app/api.py`, `app/deck.py`, and `app/resolve.py` currently perform —
   resolver exact/surface-form lookup, sense lookup, `sense_ref → lemma_ref`
   routing, lemma/candidate materialization by stable semantic ref, and the
   meanings/examples needed for candidate/card materialization — proven with
   an explicit contract-coverage map from call site to provider operation.
   No generic raw SQLite connection is exposed as the provider abstraction.
   If the contract cannot cover a current product read without a new shard
   route/family, that is a Stop-and-ask architecture boundary. Slice 11
   still does not touch `app/api.py`.
2. **Slice 12:** session-only launcher selection, chooser, Settings switching,
   offline installation progress, cache/offline removal, CLI matrix, and E2E.
   It must prove that no backend mode-preference file exists. Slice 12 owns
   `app/api.py` and migrates every served-product dictionary read onto the
   accepted Slice 11 provider contract, explicitly naming and removing/
   bypassing the current direct `runtime._current_generation.asset.connection`
   reads used by `POST /vocab/highlight` and `POST /vocab/import/csv`, and
   the raw dictionary SQL in `_materialize_candidate_from_ref`. Low-level
   SQLite access remains allowed only inside `LocalDictionaryProvider`/
   dictionary implementation, never reintroduced as a bypass elsewhere in
   `app/api.py`. Against the deterministic fixture Online provider, Slice 12
   proves `POST /vocab/highlight`, `POST /vocab/import/csv`, candidate
   materialization, and a representative card-creation path all work
   without a full local dictionary, with transport/integrity/budget errors
   remaining structured provider failures rather than dictionary misses or
   PART-B writes.
3. **Slice 13:** only after Slices 11 and 12 are accepted, build and validate
   the production corpus, check storage, create the separate
   `dictionary-online-v2` release, upload and anonymously verify assets, and
   perform end-user testing. It never changes `dictionary-v2`. By the time
   Slice 13 begins, every served product read path already works through
   `OnlineDictionaryProvider`; Slice 13 must not discover basic API/provider
   migration work, and if its end-user test exposes a code/provider bypass
   it must stop publication rather than repair product code inside the
   publication slice.

Each slice must preserve AGENTS R1–R13, including no runtime LLM, one resolver,
separate dictionary/user data, D47 stable semantic identity, and guarded
browser-facing writes.

## Rejected alternatives

Persisting `online`, `offline`, or `unconfigured` recreates ADR-0008's terminal
precedence/state-machine problem and is rejected for this version. Silently
falling back from explicit Offline to Online breaks operator intent and is
rejected. A custom manifest as an Online source or browser-provided fetch URL
breaks the trust boundary and is rejected. Remote SQLite VFS, a hosted query
API, and any runtime LLM are out of scope.

## Cold review

**Cold review #1 (complete).** The reviewer confirmed ADR-0009 is genuinely
materially simpler than blocked ADR-0008; that no persisted dictionary-mode
state remains; that ADR-0008 F1 has exactly one answer under this ADR; that
the logical v2 dataset token is coherent; that `sense_ref → lemma_ref`
routing is bucket-closed; that the 577-asset corpus remains within GitHub
Release limits; and that Slice 11 may establish the provider seam without
`app/api.py` itself. Those points are not re-litigated below. It raised five
objections, O1–O5, recorded here with their resolutions.

### O1 — Example shard routing lacked a defined stable identity

The ADR said examples route by a "stable example identity", but the
authoritative `example` table (`reference/schema.sql`) has no
`semantic_ref`, and `source`/`source_ref` are nullable — so no such identity
exists to route on as originally worded.

**Resolution — O1.** Example shard routing is
`example_bucket(example_id) = example_id % 64` against the table's numeric
primary key, an active-dictionary-internal routing/index identity only —
never persisted into PART-B, never a durable user identity, and not a
weakening of AGENTS R13 since stable lemma/sense semantic refs remain the
durable identity boundary. See "Provider and online-data contract" above and
the updated `tasks/slice-11.md` for the machine-checkable route, fixture
proof, and production builder validation that every emitted example lands
in its exact expected bucket, plus the finite family bound (64 shards,
~92.6 MB measured) recorded as an operational transparency note.

### O2 — Lookup routing, normalization, and closure were undefined

The ADR said providers "route lookup keys" without defining the routing
function or preserving the current asymmetric SQLite/Python lower-casing
lookup semantics (`X == Q OR sqlite_ascii_lower(X) == python_lower(Q)`,
confirmed in `app/dictionary.py` and `app/api.py`'s `_ConnectionLookupOracle`),
risking silent Local/Online divergence for capitalization, umlauts, ß, and
NFC/non-NFC input.

**Resolution — O2.** The ADR now defines `bucket256_v1(text) = SHA256(UTF-8
bytes).digest()[0]` and a bucket-closure rule: the builder indexes each
authoritative row in the union of `bucket256_v1(X)` and
`bucket256_v1(sqlite_ascii_lower(X))`; the runtime fetches the union of
`bucket256_v1(Q)` and `bucket256_v1(python_lower(Q))`; the exact existing
predicate is applied afterward, unchanged. This proves closure for both the
exact-match and folded-match clauses; routing may over-approximate but never
under-approximate; no query is assumed to be NFC. The Bloom membership set
is built compatibly. See "Provider and online-data contract" above and the
updated `tasks/slice-11.md` for the required Local-vs-Online differential
fixture (ASCII case, umlauts, ß, NFC, deliberately non-NFC input, surface
forms, exact lemmas, unknown values — asserted as parity with
`LocalDictionaryProvider`, not a preconceived answer) and the builder
closure test.

### O3 — Offline removal was incompatible with `active_dictionary_metadata` recovery

`active_dictionary_metadata` records the last active local dictionary, and
the existing `DictionaryRuntime._init_active_generation` (`app/deck.py`)
hard-fails recovery if that recorded file is gone. ADR-0009's Offline
removal was not defined in a way compatible with "next startup → chooser"
without weakening D47 recovery/relink protections.

**Resolution — O3.** `active_dictionary_metadata` keeps its existing
meaning, is not dictionary-mode state, and is never deleted merely because
the disposable canonical asset is removed; no new preference/state table is
introduced. Removal is rejected with a structured conflict while Offline is
the active session provider; removal is allowed while Online is active,
deletes only the verified canonical asset, leaves the metadata row and all
user data untouched, and triggers no D47 relink. Provider/startup selection
checks canonical-asset existence *before* constructing `DictionaryRuntime`
or invoking local recovery, so a stale metadata row alone can never trigger
the missing-file recovery error when no Local provider is being activated —
that case is simply the unconfigured chooser. Reinstalling the identical v2
asset reuses the normal metadata-match path with no artificial relink. See
"Settings and user data" above and the updated `tasks/slice-12.md`
acceptance/Stop-and-ask for the required test groups (Offline-active
rejection, Online-active removal, restart-after-removal, reinstall, and
cleanup-cannot-touch-user-data).

### O4 — The E2E harness could not exercise a true no-dictionary state

The Playwright harness (`frontend/tests/e2e/serve.py`,
`frontend/playwright.config.ts`) always seeds and activates a dictionary
before the app starts, so Slice 12 could not create a real
unconfigured-chooser environment inside its original allowlist, and normal
tests must not depend on public GitHub network availability.

**Resolution — O4.** `tasks/slice-12.md`'s allowlist is expanded to include
`frontend/tests/e2e/serve.py`, `frontend/tests/e2e/run-server.sh`,
`frontend/playwright.config.ts`, `frontend/src/api/client.test.ts`,
`frontend/src/api/index.ts`, and `frontend/src/styles/tokens.css`, modified
only as necessary for the dictionary-mode feature. The E2E harness must
support at least two deterministic served-product states — an
Offline-installed fixture, and a no-full-dictionary/fixture-Online
environment with the chooser visible and a local deterministic static
online-shard fixture reachable through the Product trust/test seam under
backend/harness control, never an arbitrary browser-supplied endpoint. See
the updated Slice 12 acceptance for the full scenario list and the frontend
focused-test requirement including the co-owned `client.test.ts`.

### O5 — `app/api.py` bypasses the provider on real product paths

`POST /vocab/highlight` and `POST /vocab/import/csv` read
`runtime._current_generation.asset.connection` directly (`app/api.py`,
`_ConnectionLookupOracle` construction sites), and
`_materialize_candidate_from_ref` issues raw dictionary SQL against that
same connection — none of which can work against
`OnlineDictionaryProvider`. Without an explicit inventory and migration
commitment, the three-slice split risked leaving basic product/provider
migration work undiscovered until publication.

**Resolution — O5.** Slice 11's provider contract must be designed and
tested to cover every real dictionary read used by the current product —
inventoried from `app/api.py`, `app/deck.py`, and `app/resolve.py` — with an
explicit contract-coverage map from call site to provider operation, and no
generic raw SQLite connection exposed as the provider abstraction; Slice 11
still does not touch `app/api.py`. Slice 12 owns `app/api.py` and must
migrate every product dictionary read onto that contract, explicitly naming
and removing/bypassing the current direct-connection reads in
`/vocab/highlight` and `/vocab/import/csv` and the raw SQL in
`_materialize_candidate_from_ref`, proving those two endpoints plus a
representative candidate/card-materialization path work against the
deterministic fixture Online provider. Slice 13 is publication-only: by the
time it begins, every product read path already works with
`OnlineDictionaryProvider`, and if its end-user test finds a code/provider
bypass it must stop publication rather than repair product code inside the
publication slice. See "Consequences and implementation order" above and
the updated Slice 11/12/13 briefs.

Cold review #2 — focused remedy verification — is the next required review
before this ADR may be approved and frozen.
