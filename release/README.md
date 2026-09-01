# Flashcard Dictionary Release Manifest (v1)

This directory contains the standalone release metadata for the
read-only dictionary asset. The actual ``*.sqlite`` file is **not**
checked in: the dictionary is a distributable asset downloaded (or
manually placed) at install time.

| File                      | Purpose                                            |
| ------------------------- | -------------------------------------------------- |
| ``dictionary-manifest-v1.json`` | Machine-readable manifest: filename, exact SHA-256, byte size, classification, attribution reference, optional download URL. |
| ``ATTRIBUTION.md``        | Human-readable summary of upstream sources and licences (German / English Wiktionary, Tatoeba). |
| ``LICENSE/``              | (Empty placeholder; CC BY-SA / CC BY 2.0 FR licence texts are bundled with the published dictionary artefact, not with the manifest.) |

The manifest is consumed by ``app/dict_install.py`` and the
``flashcard`` launcher (``--install-dictionary``). The manifest's
``download_url`` field is intentionally nullable in this branch: the
release has not been published yet, and no URL should be assumed until
the orchestrator publishes a release.
