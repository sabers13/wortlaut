# Flashcard Dictionary Attribution (v2 candidate)

This document covers the exact recovered Stage-04 dictionary identified by
SHA-256 `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`.
It is a technical release candidate, not a publicly released asset.

## Upstream sources

### German Wiktionary (`de.wiktionary.org`)

Used for lemma records, sense inventories, German glosses, grammatical metadata,
and IPA transcriptions. License: **CC BY-SA**.

### English Wiktionary (`en.wiktionary.org`)

Used for localized English meanings cross-referenced to the German sense
inventory. License: **CC BY-SA**.

### Tatoeba (`tatoeba.org`)

Used for example sentence pairs and DE/EN translations. License: **CC BY 2.0
FR** (or the recorded license of the originating sentence).

Every relevant dictionary row carries its own `source` and `license` fields; the
SQLite asset remains the authoritative per-row provenance record.

## Stage-04 additions

The recovered asset contains 48 `sense_meaning` rows with
`source='llm_generated_v1'`, `language='de'`, and `license='CC BY-SA'`. It also
contains 58 `sense_meaning_derivation` edges linking those generated rows to
non-generated source meanings. These edges preserve traversal to the source
material used as derivation input.

## Contributed manual adjudications — publication blocker

The recovered database also contains two `sense_meaning` rows with
`source='contributed'`, an asserted `license='CC BY-SA'`, and an empty-string
`language` field:

| `sense_meaning.id` | Associated manual adjudication |
| --- | --- |
| 577162 | Marmarameer |
| 577190 | Mod |

Repository/build evidence records these as owner-authored or owner-corrected
manual adjudications. This recovery session has not independently established a
contributor redistribution grant. In particular, the database's asserted license
field is not itself evidence of the contributor's authorization.

**Public redistribution of this exact Stage-04 asset is blocked until the
repository owner explicitly confirms authorship/rights and grants redistribution
under CC BY-SA for IDs 577162 and 577190.**
