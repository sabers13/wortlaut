# Flashcard Dictionary Release Manifest (v1)

This directory contains the standalone release metadata for the
read-only dictionary asset. The actual `*.sqlite` file is **not**
checked in: the dictionary is a distributable asset downloaded (or
manually placed) at install time.

| File                      | Purpose                                            |
| ------------------------- | -------------------------------------------------- |
| `dictionary-manifest-v1.json` | Machine-readable manifest: filename, exact SHA-256, byte size, classification, attribution reference, optional download URL. |
| `ATTRIBUTION.md`          | Human-readable summary of upstream sources and licences (German / English Wiktionary, Tatoeba). |
| `LICENSE/`                | (Empty placeholder; CC BY-SA / CC BY 2.0 FR licence texts are bundled with the published dictionary artefact, not with the manifest.) |

The manifest's `filename` field is `dictionary.sqlite`. The standalone
launcher installs the dictionary to exactly that name under
`$XDG_DATA_HOME/flashcard/dictionary/dictionary.sqlite` (default), so
the next normal launch finds it without needing `--dict-path`. The
same filename is used for every manifest version (`v1`, `v2`, …); the
manifest's `sha256` is the durable identity, not the filename.

## Release publication status

**Release code: ready.**

**Dictionary publication: pending.** This branch is the standalone
release candidate: the code, manifest shape, installer, and end-user
install/launch commands are ready to ship, but the dictionary artefact
itself is not yet published. The manifest's `download_url` is
intentionally `null`, and `--install-dictionary` will fail closed
until a later orchestrator-authorized publication worker fills in the
real URL. End users can still obtain the dictionary manually by
placing a verified `dictionary.sqlite` at the default slot — the
filename and SHA-256 documented in the manifest are the contract.

When the production dictionary is published, the only change required
in this directory is the `download_url` field. The `filename`,
`sha256`, `bytes`, and `classification` are pinned for v1 and are not
edited by this repair.
