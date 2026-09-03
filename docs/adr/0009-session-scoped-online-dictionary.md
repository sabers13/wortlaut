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
   preference.
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

### Settings and user data

Settings offers **Use Online for this session**, **Use Offline**, **Download
for Offline use**, **Remove Offline dictionary**, and **Clear Online cache**.
Offline → Online retains the Offline asset. Online → Offline activates only a
verified full asset or offers download; incomplete data is never activated.
Removal and cache clearing are independent explicit actions and never affect
cards, reviews, meanings, or audio.

### Provider and online-data contract

`LocalDictionaryProvider` and `OnlineDictionaryProvider` expose one provider
contract. They represent the same v2 logical dataset token:

`1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.

Switching providers within that dataset performs no D47 relink and never uses
numeric SQLite IDs as durable identity. The online corpus is static GitHub
Release distribution, not remote SQLite VFS or a query API. Its committed,
trusted manifest describes 256 lookup shards, 256 entry shards, 64 example
shards, and one membership filter (577 assets total):

* lookup shards route lookup keys and `sense_ref → lemma_ref`;
* entry shards route by stable lemma semantic ref; example shards route by
  stable example identity;
* the verified Bloom filter has zero false negatives for the authoritative
  lookup-key set. Its false-positive rate is statistical only; it makes no
  deterministic FPR promise;
* a lookup family has at most 256 identities. One top-level operation may
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
separate Offline-only CLI trust domain.

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
   first-run or Settings UI.
2. **Slice 12:** session-only launcher selection, chooser, Settings switching,
   offline installation progress, cache/offline removal, CLI matrix, and E2E.
   It must prove that no backend mode-preference file exists.
3. **Slice 13:** only after Slices 11 and 12 are accepted, build and validate
   the production corpus, check storage, create the separate
   `dictionary-online-v2` release, upload and anonymously verify assets, and
   perform end-user testing. It never changes `dictionary-v2`.

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

Pending cold review #1. The reviewer must test whether this is genuinely
materially simpler, verify no persisted mode remains, exercise startup and
custom-manifest precedence, confirm zero network before an explicit first-run
choice, existing-user Offline startup, provider/cache integrity, and the
three-phase execution split.
