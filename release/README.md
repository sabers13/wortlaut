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
| `LICENSE/`                | (Empty placeholder; CC BY-SA / CC BY 2.0 FR licence texts are bundled with the published dictionary artefact, not with the manifest.) |

The manifest's `filename` field is `dictionary.sqlite`. The standalone
launcher installs the dictionary to exactly that name under
`$XDG_DATA_HOME/flashcard/dictionary/dictionary.sqlite` (default), so
the next normal launch finds it without needing `--dict-path`. The
same filename is used for every manifest version (`v1`, `v2`, …); the
manifest's `sha256` is the durable identity, not the filename.

## Release identities and publication status

**V1 is historical.** It describes the source-backed Stage-02 asset with SHA-256
`75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`. That exact
asset is no longer locally recovered; its manifest and attribution are immutable
historical provenance.

**V2 is the active technical candidate.** It represents the exact recovered
Stage-04 asset:

| Field | Value |
| --- | --- |
| SHA-256 | `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c` |
| Bytes | `945418240` |
| Classification | `source-backed-stage02-plus-stage04-canary` |
| Canonical local filename | `dictionary.sqlite` |

The v2 `download_url` is intentionally `null`; it is not publicly released.
Publication of the exact Stage-04 asset remains blocked pending owner confirmation
of redistribution rights for the contributed rows documented in `ATTRIBUTION-v2.md`.
Once authorized and published, a remote asset may be named `dictionary-v2.sqlite`,
while the installer will atomically activate it under the canonical local name
`dictionary.sqlite`.
