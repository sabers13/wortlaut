# Flashcard Dictionary Release Metadata

This directory contains the standalone release metadata for the
read-only dictionary asset. The actual `*.sqlite` file is **not**
checked in: the dictionary is a distributable asset downloaded (or
manually placed) at install time.

| File | Purpose |
| --- | --- |
| `dictionary-manifest-v1.json` | Historical Stage-02 manifest. |
| `ATTRIBUTION.md` | Historical Stage-02 attribution. |
| `dictionary-manifest-v2.json` | Active technical-candidate manifest for the recovered Stage-04 asset. |
| `ATTRIBUTION-v2.md` | Attribution and rights status for the v2 candidate. |
| `dictionary-online-manifest-v2.json` | Schema-shaped fixture for the Slice 11 Online corpus manifest (NOT a production asset manifest). |
| `LICENSE/`                | (Empty placeholder; CC BY-SA / CC BY 2.0 FR licence texts are bundled with the published dictionary artefact, not with the manifest.) |

The manifest's `filename` field is `dictionary.sqlite`. The standalone
launcher installs the dictionary to exactly that name under
`$XDG_DATA_HOME/flashcard/dictionary/dictionary.sqlite` (default), so the
next normal launch finds it without needing `--dict-path`. The same
filename is used for every manifest version (`v1`, `v2`, …); the
manifest's `sha256` is the durable identity, not the filename.

## Release identities and publication status

**V1 is historical.** It describes the source-backed Stage-02 asset with SHA-256
`75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`. That exact
asset is no longer locally recovered; its manifest and attribution are immutable
historical provenance.

**V2 is the active public release.** It represents the exact recovered Stage-04
asset:

| Field | Value |
| --- | --- |
| SHA-256 | `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c` |
| Bytes | `945418240` |
| Classification | `source-backed-stage02-plus-stage04-canary` |
| Canonical local filename | `dictionary.sqlite` |

The v2 `download_url` identifies the public release asset. The owner has
confirmed redistribution rights for the contributed rows documented in
`ATTRIBUTION-v2.md`; that rights prerequisite is satisfied. The remote asset is
named `dictionary-v2.sqlite`, while the installer atomically activates it under
the canonical local name `dictionary.sqlite`.

## Online corpus (Slice 11 / Slice 13)

`dictionary-online-manifest-v2.json` carries the committed schema contract:
256 lookup shards, 256 entry shards, 64 example shards, and one membership
filter (577 assets total). It is parsed unchanged by the Slice-11 + Slice-12
acceptance suite and by the production-bound verifier.

The Slice-13 production corpus has been built against the verified v2
source (945 418 240 bytes; SHA-256
`1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`) and
structurally validated end-to-end:

| Field | Value |
|-------|-------|
| dataset_token | `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c` |
| topology | lookup=256, entry=256, example=64, membership_filter=1 |
| total corpus bytes | 2 450 244 752 |
| every asset byte_size + sha256 matches manifest | YES |
| every SQLite shard `PRAGMA integrity_check=ok` | YES (576/576) |
| membership filter parses via `BloomFilter.from_bytes` | YES |
| builder peak RSS | ~946 MiB (bounded-memory disk-backed rebuild) |
| aggregate SHA (577 concatenated asset SHAs) | `0577cdb429c6feff25144b173005edc3d07f554c8eccfe228206b224a528092a` |

As of the Slice-13 CF2-repair-integrated pre-publication continuation,
`release/dictionary-online-manifest-v2.json` is the exact validated
production manifest (byte-identical to the staging copy at
`/home/saber/.cache/flashcard/builds/20260904T213935Z/dictionary-online-manifest-v2.json`).
The Slice-12 CF2 surface-only parity repair has been integrated into
main (`86786ad fix(dictionary): restore online surface-form parity`,
`d7efb48 docs(slice-12-report): record final make gate result for
repair`) and carried into `slice/13` via a no-content-delta merge.
The repaired Slice-12 `OnlineDictionaryProvider.lookup_surface_form`
now returns the surface-table matches on the deterministic
`surface_form` case (where a form is BOTH a `lemma` row AND a
`surface_form` row of another lemma), restoring CF2 surface-only
parity against `LocalDictionaryProvider`.

The Slice-13 publication stage is in the **prepared, awaiting
final independent full-diff review** state:

- the Slice-12 CF2 surface-only parity repair has been merged into
  `main` and carried into `slice/13`. The merged tree is byte-equal
  to the accepted repair tree (proved by `git rev-parse
  REPAIRED_MAIN_HEAD^{tree}` vs the repair HEAD tree);
- the production-bound differential verifier
  (`tools/verify_online_dictionary_release.py`) is in place and
  type-clean (one bug fix applied: `load_manifest(path)` vs
  `parse_manifest(text)` were swapped at the two pre-existing read sites);
- the production corpus builder has been rewritten
  (`tools/build_online_dictionary.py`) to use a private SQLite staging
  database and emit one shard at a time, capping peak RSS at ~946 MiB
  on the contested 4 GiB host where the in-memory builder repeatedly
  OOM-killed. Output is byte-identical to the Slice-11 in-memory
  implementation on the same verified input (proven by an out-of-repo
  A/B build);
- the production corpus against the verified v2 dictionary has been
  built, structurally validated, and locally verifier-tested — the
  Slice-13 verifier now reports **1179/1179 differential cases PASS**
  on the existing production corpus (no rebuild required after the
  provider fix);
- owner publication authorisation for `dictionary-online-v2` is
  recorded on 2026-09-04 and remains ACTIVE;
- publication of the new release therefore requires only:
  1. one independent full-diff review against `origin/main` of the
     complete pre-publication candidate (the only remaining gate);
  2. upload and publication of the resulting `dictionary-online-v2`
     release, anonymous verification of the same, and a final real-user
     Online + Offline smoke test.

The earlier (eaa8d4c / e2045a / e10c5d6) full-diff review was recorded
against a candidate with `PRODUCTION_CORPUS_BUILT=no`; it is
documented as PRELIMINARY / PREFLIGHT evidence only. A final
independent full-diff review of this exact production-built,
1179/1179 PASS, CF2-repair-integrated candidate is PENDING.

Until that final full-diff review completes and `dictionary-online-v2`
is actually published, the existing v2 full-dictionary release remains
the offline install path and continues to satisfy all offline flows.
The Online flow is offline-pending publication of `dictionary-online-v2`
on this exact 1179/1179 PASS candidate. The rest of the Slice-13
infrastructure (bounded-memory builder, production corpus, production
verifier with the bug fix, the Slice-12 CF2 parity repair integrated
into `main` and carried into `slice/13`) is in place.

The lookup shards additionally carry a `sense_route(sense_ref, lemma_ref)`
table bucket-closed on `bucket256_v1(sense_ref)` for the
`sense_ref -> lemma_ref` lookup the runtime performs before opening any
entry shard. Entry shards do not carry the authoritative `example`
payload; example rows live in the 64-shard example family keyed by
`example.id % 64`. The membership filter is sized dynamically from the
actual closure-key set and uses a self-describing serialization
(`WFBL` magic + version + size_bits + hash_count + bit payload); the
producer never assumes a 512-bit production size. The Product HTTP
transport (`app/online_transport.py`) is the trusted GitHub Release
boundary and is the only path that downloads Online shards in product
use.

## Verified invariants for `dictionary-v2`

The `dictionary-v2` release is unchanged through every slice commit:

| Field | Value |
|-------|-------|
| release id   | `381651690` |
| asset id     | `541973166` |
| asset        | `dictionary-v2.sqlite` |
| bytes        | `945418240` |
| SHA-256      | `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c` |

It continues to be the offline install path; no modification was
attempted at any point in Slice 13.

## Slice 13 publication state (2026-09-05)

The independent final full-diff review of the
`aafbd58142dc5c4710010eb650fe7179178233b3` candidate returned
**PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS**.

- `dictionary-online-v2` **published and anonymously verified**
- final Online smoke **PASS** (real served-product over the new public
  GitHub corpus, exercised lookup, highlight, note, card, and Anki
  export)
- final Offline smoke **PASS** (real served-product over the verified v2
  source, same exercised paths)
- `dictionary-v2` **unchanged** (release id 381651690, asset id
  541973166, 945418240 bytes,
  `sha256:1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`)

The new `dictionary-online-v2` release contains exactly 579 approved
assets (577 corpus + 1 manifest + 1 attribution). The full publication
receipt is in `tasks/slice-13.report.md`; the anonymous public
verifier JSON is in
`release/dictionary-online-public-verifier-report-v2.json`. No product
code changed, no corpus was rebuilt, and `main` was not modified by
the publication worker.
