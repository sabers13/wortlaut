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

As of the Slice-13 pre-publication candidate, the manifest's asset rows
remain schema-shaped placeholders (`byte_size: 0`, `sha256: 0…0`); the
production Online corpus has not been materialised on the slice host yet.

The Slice-13 publication stage is in the **prepared, awaiting
host-capacity** state:

- the production-bound differential verifier
  (`tools/verify_online_dictionary_release.py`) is in place and type-clean;
- the production corpus builder's CLI entry-point
  (`tools/build_online_dictionary.py`'s missing `__main__` block) is fixed;
- the production corpus against the verified v2 dictionary (945 MB,
  SHA-256 `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`)
  is the only piece outstanding;
- owner publication authorisation for `dictionary-online-v2` is recorded
  on 2026-09-04;
- publication of the new release requires:
  1. the production corpus build to complete on a host with
     sufficient RAM for the in-memory partitioner (~3.5–4 GB peak
     working-set on the same fixture size; a host with ≥ 8 GiB
     available is sufficient);
  2. an independent full-diff risk review against `origin/main`
     (one review; not started yet);
  3. upload and publication of the resulting `dictionary-online-v2`
     release, anonymous verification of the same, and a final real-user
     Online + Offline smoke test.

While the production corpus is not yet built, the existing v2
full-dictionary release remains the offline install path and continues
to satisfy all offline flows. The Online flow is offline-pending the
production corpus build but the Online infrastructure (Slice-11 builder
+ Slice-12 session modes + the new Slice-13 verifier) is in place.

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
