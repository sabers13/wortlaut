# Slice-6 Report — ADR-0007 Design Reset

## ADR-0007 Design-reset Attempt 1 — Phase A

**Status:** Phase A implementation and local verification; stopped before the paid
generation boundary. No provider credential was read and no provider request was made.

### Accepted input and real Stage-03 execution

- Accepted Stage-02 SHA-256: `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`
- Accepted Stage-02 bytes: `945410048`
- Stage-03 output was constructed from that asset read-only; no input mutation was detected.
- Queue records: `480221`
- `de`: `480221`; `en`: `0`
- `de_learner_meaning`: `480221`; `en_meaning`: `0`
- With localized derivation text: `0`; without: `480221`
- Queue SHA-256: `e542f2f96b3966690fe2fcebb145440deba7a8ec9aa7dd2d0c93ba3540ef7aa1`
- Queue bytes: `316541240`
- Queue scan found no credentials, secret markers, or private absolute paths.

The zero EN count reflects the accepted asset's existing source-backed English
meanings. The zero derivation-text count reflects its absence of source-backed
German learner wording for the queued senses; a job with no consumed localized
text correctly creates no derivation edge.

### Active DE/EN build contract

- Stage 03 accepts only `de_learner_meaning` and `en_meaning`, uses stable lemma
  and sense semantic references for durable identity, and emits bytewise ordered
  `batch:<item_id>` custom IDs.
- Stage 04 accepts only those jobs; its checkpoint is
  `flashcard-stage04-checkpoint-v2`, with compatibility over queue identity,
  generation marker, output classification, DE/EN bulk model occupants, QA model,
  bulk/QA pipeline versions, and response-schema version.
- The fake/local transport coverage verifies prepared manifest correlation
  (`batchcorr:v1:<manifest-sha>`), exact custom-ID joining, valid completion,
  durable rejection, ambiguous in-flight retention, and fail-closed incompatible
  checkpoint reuse. The historical five-item Persian checkpoint remains inert:
  active code neither clears, migrates, nor resubmits it.
- Generated fixture rows use `source='llm_generated_v1'`, an explicit fixture
  classification, and same-sense source-backed derivation validation. Rollback
  remains the marker-based `DELETE FROM sense_meaning` contract.

### Fixture packaging and Piper prerequisite

- Stage 05 fixture tests verify input immutability, SQLite validation, attribution,
  output checksum/size metadata, and overwrite refusal. No real enriched asset was
  packaged or published.
- The local Podman-backed Docker build completed for image
  `flashcard-slice6-piper:phase-a` (`d58382bad977d28996036e69b920c8ecab0446a5091c9336c8f685a4ec557fc3`).
  It verified `piper-tts==1.6.0`, `de_DE-thorsten-high`, revision
  `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8`, model SHA-256
  `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1`,
  the bounded synthesis smoke, no runtime LLM SDK, and the GPL-3.0-or-later / MIT /
  CC0 notice material.

### Verification and remaining authority

- Focused Stage-03/04/05 tests: `13 passed`.
- Targeted Ruff and strict mypy: PASS.
- Full `make gate` was launched after the focused checks; Ruff and strict mypy
  completed PASS and the full pytest run completed before this report update.
- `git diff --check`: PASS.
- Paid provider calls: `0`; paid spend this attempt: `USD 0`.
- Stop-and-ask conditions hit: none.

Work intentionally left undone: any paid DE/EN canary or production Batch
submission, live semantic QA, packaging of a real enriched dictionary, and release
publication. Those require the Slice-6 orchestrator's explicit Phase-A acceptance
decision and a separate paid-run authorization.

**Branch:** `slice/6` @ pending commit
**Base main:** `39bf247bffb6332af750b45b1b59609c66c1e374`
**Archive preserved:** `archive/slice-6-pre-adr0006-1782cd7` @ `1782cd71343d86946757dce8f36784f9582e28f4` — not deleted/rewritten
**Model:** `gpt-5.6-terra / T3 / high`
**Disposition:** `PRE_CANARY_READY` — implementation complete, verified, committed; **paid 50-item canary NOT authorized and NOT executed**

## Historical pre-ADR-0007 evidence — preserved audit record

The following sections are historical pre-ADR-0007 audit evidence, preserved verbatim without modification. A cold reader must not interpret the preceding pending-commit metadata as current. Current authoritative evidence is in the ADR-0007 Design-reset Attempt 2 section below.

## Stage-02 Input Verification (A14.1, read-only)

- **Role:** accepted real cache-MISS output (Stage02 parent is Stage01 SHA `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`)
- **SHA-256:** `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97` — PASS (reverified at handoff adoption, before Stage03 work, and again at pre-canary close)
- **Bytes:** `945410048` — PASS
- **PRAGMA quick_check:** `ok` — PASS
- **Counts:** examples `777295` (with EN `494687`, without EN `282608`), `example_lemma` `6504849`, distinct indexed lemmas `99537`, token_count sum `7292286`, incomplete attribution `0`, orphan associations `0` — PASS
- **Required PART-A + Stage02 tables:** present — PASS
- **Input unchanged:** SHA before == SHA after every local stage execution — PASS
- **No mutation:** Stage03/04/05 never mutate input asset in place — PASS

## Persian Source Investigations — CLOSED

### Primary source: English Wiktionary FA — REJECTED

An exact persisted source-sense → FA translation relation could not be proven without
forbidden free-text/gloss matching. Mechanical proof is mandatory (AGENTS R11, ADR-0006);
gloss matching is not acceptable evidence of a translation relation. Investigation closed;
not reopened.

### Secondary source: German Wiktionary FA bridge — REJECTED

An exact EN canonical sense → exactly-one DE Wiktionary source-sense bridge could not be
mechanically proven. Fail-closed per ADR-0006 D57–D71. Investigation closed; not reopened.

### Owner disposition: bounded Persian LLM fallback prepared under D64

After both source rejections, the owner explicitly invoked ADR-0006 D64 to prepare a
bounded Persian LLM fallback. Authorization history:

1. Both free Persian source options mechanically rejected (above).
2. Owner decision stop recorded at base HEAD `1382c30bf6d613a27f18d1bbea8777a7005f8224`.
3. Owner authorized v2 fallback preparation only: identity, manifest, canary selection,
   checkpoint namespace, validation, tests, measurement. **No paid call was or is authorized.**

## v1 Preparation — RETIRED BEFORE LIVE USE

- Historical job class `fa_translation` and item version `fa-generation-job:v1` are retired.
  `tools/build_dict.py` rejects `fa_translation` outright (queue validation and candidate
  building raise fail-closed errors). No v1 identifier survives into v2 identity.
- The v1 preparation manifest and v1 canary selection are retired artifacts; never used live.
- The five historical Persian-era legacy `bulk.in_flight` IDs remain **LEGACY UNRESOLVED** —
  not cleared, not migrated, not reinterpreted, not resubmitted (read-only preservation
  verified by test).

## FA v2 Identity and Output Contract

| Constant | Value |
| --- | --- |
| Job class | `fa_generated_meaning` |
| Item version | `fa-generation-job:v2` |
| Item ID payload | canonical JSON `[lemma_semantic_ref, sense_semantic_ref, "fa", "fa_generated_meaning"]` → `fa-generation-job:v2:<sha256>` |
| Input version | `fa-input-v2` |
| Bulk version | `fa-bulk-v2` |
| Response version | `fa-response-v2` |
| Canary strata classifier | `fa-canary-strata-v1` |
| Generated marker | `llm_generated_v1` |
| Classification | `AI_GENERATED_FROM_WIKTIONARY_ATTRIBUTED_v1` |
| Max scalars | `160` Unicode scalars |
| Max tokens | `24` whitespace-delimited tokens |

- No numeric dictionary ID (`lemma_id`, `sense_id`) participates in durable v2 identity;
  stable semantic refs only (AGENTS R13). Verified: manifest and canary records carry no
  numeric-ID keys.
- Strict output object contains exactly `{"persian": "<string>"}`; no `persian_alt`;
  `additionalProperties=false`.
- Result validation: nonblank after trim; ≤160 scalars; ≤24 tokens; must contain
  Arabic/Persian script; ZWNJ `U+200C` allowed; forbidden bidi/control policy binding
  (`U+061C`, `U+200E`, `U+200F`, `U+202A–202E`, `U+2066–2069`, `Cc` all, `Cf` except ZWNJ);
  no markdown; no commentary; no romanization; echo-of-lemma rejected.
- Instructional goal: prefer the shortest natural Persian equivalent faithful to the exact
  sense. For morphology/inflection senses a concise Persian grammatical description is
  allowed and may exceed four words within the 160/24 bounds.

## FA v2 Candidate Manifest (verified against actual bytes this session)

- **TOTAL_FA_V2_CANDIDATES:** `480221` (= all canonical senses; each has ≥1 non-blank
  source-backed EN meaning, so missing-EN exclusions = `0`)
- **FA_V2_MANIFEST_SHA256:** `b9f1d32481d4495abc006ac691895bc8d34245d4623b6ba50d4f282f7c25a81b`
- **FA_V2_MANIFEST_BYTES:** `257643091`
- Deterministic build from accepted Stage02 via `_build_fa_v2_candidates`; ordering
  bytewise by `item_id`; duplicate item IDs fail closed.
- Every record carries `job_class=fa_generated_meaning` and `custom_id=batch:<item_id>`.

## Canary Selection (50 items; verified this session by independent recomputation)

- **CANARY_COUNT:** `50`
- **CANARY_MORPHOLOGY_COUNT:** `25`
- **CANARY_LEXICAL_COUNT:** `25`
- Classifier `fa-canary-strata-v1`: deterministic morphology keyword match on the exact
  source-backed EN meaning; strata totals `349222` morphology / `130999` lexical.
- Selection ranking: `SHA256(item_id)` ascending within each stratum (25 lowest each).
- **Final stored and future execution order:** bytewise ascending `item_id` (selection
  ranking is used only to pick members; it does not define execution order).
- **CANARY_SELECTION_SHA256:** `396e3e03f16bb4f1bd769173abba31d9b8d80dc26fd9ed376bcd785ade25dc16`
- **CANARY_SELECTION_BYTES:** `26789` (canonical compact JSON; actual-byte hash verified,
  writer also self-verifies written bytes against expected digest atomically)
- This session independently recomputed strata membership, member selection, canonical
  bytes, and digest from the candidate manifest — exact match.

Exact 50 canary IDs in execution order (`M` = morphology, `L` = lexical):

| # | item_id | stratum | lemma |
| --- | --- | --- | --- |
| 1 | `fa-generation-job:v2:0034d9c74131e41bb568d30f526eaaeae77251fd9d51288aeefbfef7190d39a7` | M | freigeistige |
| 2 | `fa-generation-job:v2:0091bf69f230f32acf15f72ea0c5710b48ec773c7a2f077a1cd917aa9cb64c7c` | L | Papua-Neuguinea |
| 3 | `fa-generation-job:v2:017e6969fabf8fe0c17ecc2ebf2a26784e35c73b94d6c5b4f29b9f4635f42882` | L | einweihen |
| 4 | `fa-generation-job:v2:090a4de75143a9eb2965e3aae65749fa8873dc2d64f162f3af552167250adcc3` | M | fettiger |
| 5 | `fa-generation-job:v2:09d0ce2ff8d45a8b41f03d748b93ea00f538719dd2d351df70ffcec1d5de7b42` | M | Halbinseln |
| 6 | `fa-generation-job:v2:0a4d51a1fe3f8554e7d6bbd64621fc3894893e2d2537f16fb9f5854a7374e880` | M | unwiederholbare |
| 7 | `fa-generation-job:v2:1330c3189b9a2410166b33523ef6f4f5e5b00639cc09c78dba304e195cb7e536` | L | altnorwegisch |
| 8 | `fa-generation-job:v2:2b9c675248c0b4fe926ebfe09f07b5fe1a01dbdcc74f2ba84259cb19c39c8700` | L | Comedian |
| 9 | `fa-generation-job:v2:35b0feab77523f08b1e126b79a29aa4127cbe0af1dca04c566593e4f176c0426` | M | Kurzstreckenläuferinnen |
| 10 | `fa-generation-job:v2:4106427bd119e87dcb2a54f59120f14b0912e8d5587bfc9f7268cc90c99db7c9` | L | Typsystem |
| 11 | `fa-generation-job:v2:42432f2dcb1afcd4a0ba30bb1e3e3471d3ee5ab3db51a9a6fb4f1fbc7e6d9487` | L | europamüde |
| 12 | `fa-generation-job:v2:42864c96fc6a146871a573062b3ad4a0da9012b36c416792851b6a7a7a501e16` | L | Anschiss |
| 13 | `fa-generation-job:v2:431ae54ad9b03aacc79ca97bf23c8f0c5fce6b978b01877c1ee95d52c1a20561` | L | Haubenammer |
| 14 | `fa-generation-job:v2:46f178d4a95595a512dc056aef15917cd25d4ae62e54301d49949d6e1a7413b1` | M | ungenießbarerer |
| 15 | `fa-generation-job:v2:48a659636a3a3d17db85fe4ffe1a80a2bc57bbf415f0f7a95277f0b4e16562e1` | M | erledigend |
| 16 | `fa-generation-job:v2:4db340209529d7caf720b6446b3e4b1de56c8b4ae4eeed8305b5c6a1f98825d8` | L | Mops |
| 17 | `fa-generation-job:v2:565d0e3e8444d1f8895b53d8d4f09296e88e5031d443111af74afd85e0be5540` | M | Unterstände |
| 18 | `fa-generation-job:v2:68327f006f537c8fd2d844f790fbb0e25d79d4211e6978cb6123e1b0346b9c34` | L | Radrennfahrer |
| 19 | `fa-generation-job:v2:6ad32527e2bcb1079d67f0138aef535e8acf0aade4dd654d9645d493327d582b` | M | süsst |
| 20 | `fa-generation-job:v2:730e75c32184ff62c099739f6f66f1ce81d76bb8922ad33fc89298350f0e665a` | L | Alanin |
| 21 | `fa-generation-job:v2:7645f27566a8850f1e47b7396802458f48d46f16674b89af70790d51e40280e9` | M | synonymen |
| 22 | `fa-generation-job:v2:79374cfc5946a1f1b417e90fb3fe9da3c26dd0b500207c1a79c25514c6946028` | M | verlieret |
| 23 | `fa-generation-job:v2:79d8dead9e94389117f49fe8637e1b0bac72ea38d29530b2a6f0f3152a08d580` | M | Dogmen |
| 24 | `fa-generation-job:v2:7c649b6d6e40fb1a764b9ca75079a6e2f68336a641366e73b8fb9e78f9c4de2f` | L | Winkelmesser |
| 25 | `fa-generation-job:v2:7e2497064e5bf34f5bbd93c2514ba91b4c8b4bf781b02480908a8841e45a676a` | L | Rübe |
| 26 | `fa-generation-job:v2:7fc7685cc002da368de9102ab79f1c4e82096ca6512a293b687920e93f10e9b6` | M | abgefahrene |
| 27 | `fa-generation-job:v2:877dc7b684de2785a820b1d17da949d64c58dac502a988516ca1c7da4f652e6e` | M | Zuspruches |
| 28 | `fa-generation-job:v2:8fe5b0c1684adf74c6001c3ad7165530e43278c09749b1afe9c7772401d23997` | M | Zeitplanes |
| 29 | `fa-generation-job:v2:9243882dbba2f442bc22db34f08951cfbf5e6a39221b063fa70c4b6c72c236d6` | L | quetschen |
| 30 | `fa-generation-job:v2:95ce0e9308c179fd12b78e60f812b841a855e8342c4c1e4556f562c988ec2490` | L | zurückerinnern |
| 31 | `fa-generation-job:v2:9a0eb02cd314e0ce5d6b3016b1f3711e87436de2fcac1cba7a4607200e8978da` | L | mAK |
| 32 | `fa-generation-job:v2:9b43de87dead2000ef006c375018cbd93d921b15db98ace3c26848341f3109ed` | M | potenzsteigernderer |
| 33 | `fa-generation-job:v2:9f5ba77080df79fb427c30dc4fc8fa11fc8efa94771ca7f024d47f3fce8ceeea` | M | Folterknechtes |
| 34 | `fa-generation-job:v2:a81f6d8ab838be61b28f3def831f8ddca847c0a79491896a1562b78752fdecd4` | M | ruhmsüchtigerer |
| 35 | `fa-generation-job:v2:ab86fae4892c31f84c25547a15bbbc4736812d6124b56e1e625ff2c037ad63f4` | L | Auftragsstornierung |
| 36 | `fa-generation-job:v2:c9cb6fe982e3a431590d7b924a8152ddd55bb2f632b1ea43fbcff2fce62851e3` | M | schröpfe |
| 37 | `fa-generation-job:v2:cf3234914e14c50456958e8594f360b5a2ff9e4b21af54fc89499b02670279e8` | M | Halogenkohlenwasserstoffen |
| 38 | `fa-generation-job:v2:d0e6bed9f6a1afc8a786fa42f3c6c2d8c23e214507e6addb0d8ceabdb5d1db7f` | L | Weissdornhecke |
| 39 | `fa-generation-job:v2:e2f12a417f20ea472c4d2c3e70600b9d74728b6036192e6ac6dc4d3fa9adb5a6` | M | begegnest |
| 40 | `fa-generation-job:v2:e4621d0a9c09523f873551bd188fbb925d426b618b42892d6b6a920509ed902e` | L | Quittung |
| 41 | `fa-generation-job:v2:e4bf148279f08e59f6af63195f7c79444c25c73136af46bb479b672d548855ab` | L | deutsche Sprache, schwere Sprache |
| 42 | `fa-generation-job:v2:f047582aecdf9c7b4ac3a89d3fbaed3b1e3527b197d728a878ebed5f1075fefd` | L | Roland |
| 43 | `fa-generation-job:v2:f2f0782defe7515fb58601ad836bc36428253cbd4e065cff1efce4cfa2b14cdf` | M | duftigerer |
| 44 | `fa-generation-job:v2:f391b4624701720a98e87e444b5c2b4bf092e1aa088aea70f7e779b03add3e85` | L | stutzen |
| 45 | `fa-generation-job:v2:f505255a3bdc792b8a69a5fbc98f07cda3de218b5f480485ccc7dc503aa24b34` | M | erwünschtere |
| 46 | `fa-generation-job:v2:f5e7ca95e50ab60b51af277daba61cd0c43d0f04fed8971fcbf9542e2414110a` | L | Olympia |
| 47 | `fa-generation-job:v2:f626a39e674610b6100365427b9c06afb2be3bd26119968afeb89b4897794afb` | L | Verdunklung |
| 48 | `fa-generation-job:v2:f91d6c21bbeb1414f9edbb15b45a4489bf042752844c474462be15b46df54672` | M | obgenanntem |
| 49 | `fa-generation-job:v2:f984ff1f0e2d7afc044b44aaeff908fb6ab7f247bddd84652466659a82370e2b` | L | lebensmüde |
| 50 | `fa-generation-job:v2:ff2aa058fda84de04ce330b749967b38e422f9319dbe5a9cfd6b5854c5fc9923` | M | ledigere |

## Derivation Contract — EXACTLY ONE EN edge

Every successfully persisted generated FA meaning carries **exactly one**
`sense_meaning_derivation` edge from its exact source-backed English meaning:

- same sense for generated row and source row;
- source side is non-generated (`llm_generated_v1` pattern match on source fails closed);
- no duplicate edges (composite PK);
- generated→generated edges forbidden and rejected;
- candidates without the required source-backed EN meaning are excluded upstream, so an
  eligible item always has exactly one derivation source available;
- rollback by deleting `source='llm_generated_v1'` rows removes generated rows plus their
  derivation edges and never touches source-backed rows (verified by test).

Verified in implementation (`build_stage04` insertion path validates each edge: existence,
non-generated source, same-sense) and by dedicated v2 tests.

## bulk_fa Checkpoint Namespace

- `bulk_fa` is a separate checkpoint phase (`completed` / `rejected` / `in_flight`),
  independent of the legacy DE/EN `bulk` and `qa` namespaces; validated on load; optional
  key for backward compatibility, strictly schema-checked when present.
- Compatibility identity includes: queue SHA, generation marker `llm_generated_v1`,
  classification license `AI_GENERATED_FROM_WIKTIONARY_ATTRIBUTED_v1`, model occupants,
  pipeline versions, response schema version, plus FA fields (`bulk_fa_model`,
  `fa_input_version=fa-input-v2`, `fa_bulk_version=fa-bulk-v2`,
  `fa_response_version=fa-response-v2`). Any mismatch ⇒ incompatible, fail closed.
- Accepted durability rules preserved: completed/rejected/in_flight; no automatic ambiguous
  resend; exact-ID `retry_rejected` only; no wildcard retry; QA independently durable;
  corrupt checkpoint state fails closed.

## Token / Cost Measurement

Method honesty note: the previous worker session measured with a `len(text)/4`
approximation because tiktoken was not installed, reporting mean `98.9`, P50 `98`,
P95 `108`, max `259`, estimated total input ≈`47.4M` tokens. Those figures are
approximations over a request-body-shaped basis and are superseded here.

This session measured exactly: tiktoken `0.14.0` encoding `o200k_base` over the canonical
JSON request body per item (`model` + `input` prompt + strict `json_schema` output spec),
all `480221` candidates:

- mean input tokens: `102.2`
- P50: `101` · P95: `111` · max: `224`
- estimated total input: ≈`49.06M` tokens

`o200k_base` is the nearest available proxy; the public tokenizer for `gpt-5.6-luna` is
not confirmed. tiktoken was installed locally as a one-off build-time measurement aid only;
it is **not** a project dependency (R1 runtime boundary untouched, `pyproject.toml`
unchanged).

Estimated full-run Batch input cost at `$0.10/M` ≈ `$4.91` — planning figure only, **not
authorization**. Estimated 50-item canary cost ≈ `$0.0005` input + trivial output — far
below the hard cap; `_estimate_fa_cost(50) < 0.10` enforced by test with conservative
default mean `146.5`.

**Future canary hard spend cap: USD 0.10** (`_check_canary_spend_cap` fails closed above it).

## Model Occupants — operational, no execution

| Role | Model |
| --- | --- |
| `bulk_fa` | `gpt-5.6-luna` |
| QA | `gpt-5.6-terra` |

Future canary transport: standard synchronous Responses API, 50 generation calls + 50 QA
calls — **NOT Batch**. No Batch upload occurred. These occupants are operational choices,
not architecture changes.

## Paid Boundary

- **Paid provider calls:** `0`
- **Paid credits spent:** `0`
- **Live Batch submissions:** `0`
- **API key use:** none
- **Persian paid generation:** none
- **DE/EN production generation:** none

## Tests & Gate (final, actual counts)

- **Targeted Stage03:** 19 passed (13 existing + 6 new v2)
- **Targeted Stage04:** 26 passed (17 existing + 9 new v2)
- **Targeted Stage05:** 7 passed
- **Stage01 regressions:** 46 passed
- **Stage02 regressions:** 54 passed
- **Full gate:** `make gate` — ruff PASS, mypy --strict PASS (18 files), pytest
  275 passed (0 skipped; real-asset v2 tests ran via `FLASHCARD_TEST_STAGE02`),
  check_agents R1/R3/R7 PASS — PASS
- **git diff --check:** PASS
- **Allowlist:** PASS — only `tools/build_dict.py`,
  `tests/test_build_dict_stage03.py`, `tests/test_build_dict_stage04.py`,
  `pyproject.toml` (unchanged), `Dockerfile` (unchanged), `.dockerignore` (unchanged),
  `tasks/slice-6.report.md`; `tests/test_build_dict_stage05.py` unchanged
- **Report private-path scan:** PASS — no private absolute paths, no credentials
- **Stage02 unchanged at close:** PASS

Real-asset FA v2 tests resolve the accepted local Stage-02 asset through the
`FLASHCARD_TEST_STAGE02` environment variable and skip cleanly when it is absent, so the
committed suite stays machine-portable while running fully on the maintainer machine.

## Work Left Undone / Next Authority

- **Paid 50-item canary is NOT authorized and NOT executed.** It requires a separate
  explicit owner/orchestrator authorization naming transport (standard synchronous
  Responses), the 50 selected IDs, models, prompts, the `USD 0.10` hard spend cap,
  classification, QA plan, and checkpoint handling.
- After a successful canary review: materialize the full FA queue execution plan, then
  Stage05 packaging. No work may infer authorization from passing tests or from this report.

---
*No private absolute paths, no API keys, no credentials recorded. Generated-output
classification `AI_GENERATED_FROM_WIKTIONARY_ATTRIBUTED_v1` applies to future generated
rows marked `llm_generated_v1`; no such row exists yet. TEST_SYNTHETIC_LICENSE_v1 remains
synthetic test-only.*

---

# ATTEMPT 2 ADDENDUM (fa-input-v3 prompt-contract repair)

## ATTEMPT 1: FAILURE 1

- **Failure trigger:** live authorized 50-item Persian canary (cap USD 0.50), Luna generation
  item 4 of 50 (`fa-generation-job:v2:090a4de75143a9eb2965e3aae65749fa8873dc2d64f162f3af552167250adcc3`,
  lemma `fettiger`, morphology stratum) returned but failed deterministic validation
  `too_long` (>160 Unicode scalars). Contract-mandated STOP before item 5.
- **Known paid spend:** USD **0.0008764** (cumulative project spend; not reset).
  Provider usage: Luna input 200 tok, output 697 tok.
- **Generation:** 3 completed · 1 rejected · 0 ambiguous/in_flight.
- **QA:** 0 sent (contract forbids QA on partial generation sets).
- **Root cause:** the binding brevity/exact-output instruction existed only in design
  evidence; the actually transmitted request body contained just
  `lemma / POS / English meaning`. Passing outputs additionally demonstrated
  German/Latin grammatical-label leakage ("(Nominativ/Akkusativ)", "einweihen (فعل)")
  and sense broadening on a polysemous lexical item.
- **Operational notes (unbilled):** first runner launch crashed pre-transmission;
  second launch hit HTTP 401 because `.env` stores the credential wrapped in double
  quotes and the untracked loader sent them verbatim; parser fixed locally, evidence
  preserved (`checkpoint.401-evidence.json`). Credential-format sanity check is now a
  committed helper (`credential_format_ok`) for all future runs.
- **Disposition:** WORKFLOW §5 Failure-1 → same-tier T3 retry as **Attempt 2**.
  Attempt-1 paid states are historical evidence under their old compatibility identity,
  preserved in maintainer-local storage, never migrated or reused.

## Repair shipped in Attempt 2

- `FA_INPUT_VERSION` → `fa-input-v3`; `FA_BULK_VERSION` → `fa-bulk-v3`;
  `FA_RESPONSE_VERSION` unchanged at `fa-response-v2` (schema semantics unchanged);
  semantic item identity unchanged (`fa-generation-job:v2`, same canonical payload).
- New committed single-source request builders `fa_v3_request_input()` /
  `fa_v3_request_body()`: the transmitted instruction now explicitly requires
  shortest-natural faithful meaning for exactly one canonical sense, standard written
  Persian (فارسی معیار), meaning text only, no lemma repetition as explanation, no
  German/English dictionary commentary, no Latin-script grammatical labels
  (Nominativ/Akkusativ/Dativ/Genitiv/Singular/Plural), no etymology/examples/
  parenthetical commentary/alternative senses, no merging of meanings, concise lexical
  equivalent for lexical senses, concise Persian grammatical description only for
  morphology senses, and preference for brevity well below the mechanical maximum.
- Deterministic validation strengthened, never weakened: new exact-substring
  `lemma_repetition` rejection catches embedded German lemma commentary
  (Attempt-1 defect class); no overbroad ASCII ban (legitimate acronyms pass).
  `too_long` bound unchanged at ≤160 scalars / ≤24 tokens.
- Checkpoint compatibility now rejects fa-input-v2/fa-bulk-v2 state when v3 is requested
  (tested, including explicit "Attempt-1 completed state not reusable" test).
- Canary selection reverified byte-exact unchanged from Attempt 1:
  SHA `396e3e03f16bb4f1bd769173abba31d9b8d80dc26fd9ed376bcd785ade25dc16`,
  bytes 26789, 25 morphology + 25 lexical, bytewise execution order, 480221 candidates,
  identical semantic item IDs.
- 16 new executable tests prove the repair against the actual serialized logical body
  (brevity/exact-one-sense/no-merging/standard-Persian/morphology/commentary/Latin-label
  prohibitions, sync≡Batch logical body, v2→v3 checkpoint rejection, semantic-ID and
  selection stability, validation bounds, lemma_repetition, acronym safety,
  credential_format_ok).

## v3 token/cost re-measurement (planning evidence only; no provider call)

- tiktoken o200k_base over exact committed v3 request bodies for the frozen 50 canary items:
  mean **326.1**, P50 **326**, P95 **334**, max **344** (sum 16,306).
- Conservative future whole-canary bound at current standard short-context prices
  (luna $0.20/$1.20, terra $2.00/$12.00 per MTok):
  gen-in (2×measured sum) $0.0065 + gen-out (≤500 tok/req) $0.0300 +
  QA-in (≤(P95+120)×2/req) $0.0908 + QA-out (≤600 tok/req) $0.3600
  = **$0.4873 ≤ $0.50 cap** — provable with completion-safe margins.

---

## ADR-0007 Design-reset Attempt 2 — Phase-A Acceptance Evidence

**Status:** Phase-A acceptance-evidence retry complete. No architecture change. No provider credential read, no network call, no paid spend. Stopped before paid boundary. Awaiting Slice-6 orchestrator Phase-A acceptance decision.

**Failure-1 class:** acceptance-evidence/reporting — Attempt 1 reached Phase-A boundary and passed local verification but committed report/evidence did not satisfy the complete A13/A14/A16 acceptance record. No design deficiency. This retry closes evidence gaps with narrowest missing tests and report repair, preserving historical Persian audit records.

**No architecture change:** ADR-0007 remains ACCEPTED / FROZEN. DE/EN-only build/runtime contracts unchanged. Only test/report completeness was repaired.

### 1. Stage-02 accepted input (mechanical verification, read-only)

- SHA-256: `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97` — PASS (preflight, `sha256sum` + `stat`)
- Bytes: `945410048` — PASS
- `PRAGMA quick_check`: `ok` — PASS
- Counts: examples `777295` (with EN `494687`, without EN `282608`), `example_lemma` `6504849`, distinct indexed lemmas `99537`, token_count sum `7292286`, incomplete attribution `0`, orphan `0` — PASS
- Required PART-A + Stage-02 tables (`lemma`, `surface_form`, `sense`, `sense_meaning`, `sense_meaning_derivation`, `example`, `example_lemma`) present — PASS
- Input SHA before == SHA after all stage executions — PASS (no mutation)

### 2. Stage-03 real queue (Attempt-1 measurement preserved, input unchanged)

- **Mechanically confirmed:** accepted Stage-02 SHA/bytes/quick_check/counts unchanged; no live Stage-03 rebuild executed (OOM-killed on 15 GiB host if attempted; task authorizes preserving accepted 316 MB output evidence when input unchanged and mechanically verifiable). Measurements below are the accepted Attempt-1 real Stage-03 values that remain valid:
- `total` queue = `480221`
- `de` = `480221`; `en` = `0`
- `de_learner_meaning` = `480221`; `en_meaning` = `0`
- `with localized derivation text` = `0`; `without` = `480221`
- Queue SHA-256: `e542f2f96b3966690fe2fcebb145440deba7a8ec9aa7dd2d0c93ba3540ef7aa1`
- Queue bytes: `316541240`
- Zero secret/private-path leakage (scan for `api_key`, `authorization`, `bearer`, `password`, `/home/` — PASS)
- Stage-03 made zero network calls (code path has no transport; verified by `grep` + test `test_stage03_no_network_and_input_immutable`)
- Input remained unchanged: SHA before == SHA after — PASS
- **Explanation:** EN queue is zero because all 480221 accepted canonical senses already have source-backed EN `sense_meaning` rows; DE queue covers all senses because suitable source-backed localized DE learner wording is absent for those queued senses (D65 positive predicate fails for `siehe`/`vgl.`/bounds etc.); no localized meaning text was consumed, therefore zero derivation-text jobs is valid.

### 3. Targeted test evidence (separate per-suite, fake/local transport only, no network)

- `pytest -q tests/test_build_dict_stage03.py`: **9 passed** (deterministic queue IDs/order, input-order independence, missing-EN classification, source-first DE retention, DE fallback provenance, positive DE predicate, overwrite/retired-packet refusal, stable semantic refs, no-network/input-immutable)
- `pytest -q tests/test_build_dict_stage04.py`: **18 passed** (fake bulk/QA, generated marker, license, source-backed unchanged, derivation exact/zero-edge, generated→generated rejection, validation, 5-item 4-valid+1-invalid durable rejected, restart no-resubmit, unknown outcome in_flight, checkpoint compatibility, retry manifest, Batch manifest/custom-ID, interruption/resume bulk & QA, legacy preservation, provenance/rollback, QA routing, corrupt checkpoint, no-secret leakage)
- `pytest -q tests/test_build_dict_stage05.py`: **4 passed** (fixture copy/metadata, overwrite/bad-attribution refusal, duplicate/blank ref & malformed provenance rejection, input unchanged & metadata consistency)
- **Stage-01 regressions:** `pytest -q tests/test_build_dict_stage01.py` — **46 passed**
- **Stage-02 regressions:** `pytest -q tests/test_build_dict_stage02.py` — **54 passed** (via `.venv/bin/pytest`; requires `de_core_news_md` model)
- **No provider credentials/network used by any test** — verified (fake transport only)

### 4. Interruption / resume evidence (A13/A16 — executable, with exact IDs)

**Bulk (fake/local transport):**

- Deterministic bounded unit size: `batch_size=1` (each `queue:v1:` item is one independent logical request)
- Completed unit: `queue:v1:3fea0b08cf699c71e988b8790c9df32b` — persisted as `bulk.completed`
- Deliberate interruption point: second bulk unit `queue:v1:6599e00d197ef7283452294a71fb8788` transport raises `RuntimeError("deliberate bulk failure after one completed unit")`; checkpoint retains `bulk.in_flight = ["queue:v1:6599e00d197ef7283452294a71fb8788"]`
- Exact item IDs submitted before interruption: `["queue:v1:3fea0b08cf699c71e988b8790c9df32b"]`
- Exact completed IDs persisted before interruption: `["queue:v1:3fea0b08cf699c71e988b8790c9df32b"]`
- Restart from checkpoint: verified `ambiguous` fails closed while `in_flight` present; after exact-one owner reconciliation (`in_flight` cleared), restart
- Exact completed IDs skipped on restart: `["queue:v1:3fea0b08cf699c71e988b8790c9df32b"]` — **not** in `good.bulk_submitted`
- Exact remaining IDs submitted after restart: `["queue:v1:6599e00d197ef7283452294a71fb8788", "queue:v1:ad9ddc565a25bac478c7d47b20571c67", "queue:v1:bf178577ec7f139b0c88e308b88c0024"]`
- Zero automatic resubmission of completed IDs — PASS
- Resumed logical generated result set equals uninterrupted equivalent — PASS (`resumed_state["bulk"]["completed"] == uninterrupted_state["bulk"]["completed"]`)
- Full synthetic BULK set for this test (sorted): `["queue:v1:3fea0b08cf699c71e988b8790c9df32b", "queue:v1:6599e00d197ef7283452294a71fb8788", "queue:v1:ad9ddc565a25bac478c7d47b20571c67", "queue:v1:bf178577ec7f139b0c88e308b88c0024"]` (prefix `bulk-interrupt`, `n=4`)

**Selective QA (fake/local transport):**

- At least one QA unit completes: `qa-valid` for `queue:v1:09a0e55ec66348c4f34180d1b8e94d10` (first required QA id)
- Deliberate interruption point: second QA unit transport raises `RuntimeError("deliberate QA failure after one completed unit")`; checkpoint retains `qa.in_flight` for one required id
- Exact QA IDs submitted before interruption: first required QA id (deterministic `required` set via flagged + audit sample)
- Exact completed QA IDs persisted: same one id in `qa.completed`
- Checkpoint `qa.required` (sorted) derived from `len(text)>50` flagged + deterministic audit sample (`_deterministic_audit_sample` with seed `queue_sha`): e.g. for `qa-interrupt` case `required` subset includes flagged + 2-sample; test asserts `qa_completed` not resubmitted
- Restart from checkpoint: verified `ambiguous` fails closed; after clearing `qa.in_flight`, restart
- Exact completed QA IDs skipped: first completed QA id not in `good.qa_submitted`
- Exact remaining QA IDs submitted after restart: remaining `required \ completed`
- Zero completed QA resubmission — PASS
- Resumed corrected logical result equals uninterrupted equivalent — PASS (`resumed_state["qa"]["completed"] == uninterrupted_state["qa"]["completed"]`)
- Full synthetic QA set for this test: `["queue:v1:09a0e55ec66348c4f34180d1b8e94d10", "queue:v1:a89a597194979604c7d5b9173ccecc1f", "queue:v1:cf01385619d683f2f39aab5893a0de3c", "queue:v1:e1657af8d9db01dc5a60d2a98971e927"]` (prefix `qa-interrupt`, `n=4`)

**Evidence source:** `tests/test_build_dict_stage04.py::test_bulk_interruption_resume_with_exact_ids` and `::test_qa_interruption_resume_with_exact_ids` — deterministic synthetic IDs, fake transport with `FailingBulkAfterOneTransport` / `FailingQAAfterOneTransport`.

### 5. Rejected / ambiguous / retry evidence (DE/EN, executable)

**Complete returned bounded response (five-item fixture, batch_size=5):**

- Synthetic queue `five-item` with sorted IDs `["queue:v1:0c7b3487a34993e3b64150a6f7fba66f", "queue:v1:54d5ea60790677709d2a82197dbe9899", "queue:v1:ab9ad8ca7c9dd213555b602fa21ee372", "queue:v1:c8c9d130b6bdf97b3740a488554e5452", "queue:v1:e4c8f5256ee44e473b17fde14aba79be"]`
- Invalid fixture: `queue:v1:ab9ad8ca7c9dd213555b602fa21ee372` text = its lemma `Lemma0002` → `echo_lemma` rejection
- Durable completed: 4 (`queue:v1:0c7b3487a34993e3b64150a6f7fba66f`, `54d5...`, `c8c9...`, `e4c8...`)
- Durable rejected: 1 (`queue:v1:ab9ad8ca7c9dd213555b602fa21ee372`, `error_code="echo_lemma"`, `phase="bulk"`, `attempt_count=1`, evidence `{text: "Lemma0002"}`)
- `in_flight` cleared: `[]` — PASS
- STOP before another paid bounded unit: `BuildDictError("Bulk unit had 1 rejected")` raised before next unit — PASS
- Test: `test_five_item_four_valid_one_invalid_durable_state` — PASS

**Restart:**

- Completed IDs not resubmitted — PASS (`retry-test` case: bad `queue:v1:54d5ea...` not in `again.bulk_submitted`)
- Rejected IDs not automatically resubmitted — PASS

**Explicit rejected retry:**

- Exact rejected ID authorization only — PASS (`retry_rejected(checkpoint, queue, [bad_id], ...)`)
- Paid-attempt counter increments: `attempt_count` 1→2 on retry (verified via `rejected[bad_id]["attempt_count"]`)
- Prior rejected evidence retained — PASS
- Wildcard retry forbidden — PASS (`retry_rejected(..., sorted_ids)` raises `BuildDictError`)
- `in_flight`/ambiguous ID cannot be retried through rejected-retry — PASS (`retry_rejected(..., [in_flight_id])` raises `BuildDictError: in-flight`)

**Ambiguous transport:**

- Unknown provider outcome remains `in_flight` — PASS (failing bulk leaves `bulk.in_flight` with one id)
- No automatic resubmission — PASS
- Exact-one compatible recovery succeeds — PASS (clear `in_flight` after owner reconciliation, next `build_stage04` succeeds and submits only remaining ids)
- Zero/multiple/contradictory recovery candidates fail closed — PASS (incompatible queue SHA or multiple manifests raise `BuildDictError: incompatible`)

### 6. Checkpoint compatibility evidence

- Schema/version: `flashcard-stage04-checkpoint-v2`
- Material identity components implemented (from `tools/build_dict.py:3087` `_checkpoint_identity`):
  - `queue_sha256` (queue identity/content, derived from `hashlib.sha256(queue_bytes)`)
  - `generation_marker` (`llm_generated_v1`)
  - `generated_license` (`generated-output classification`)
  - `bulk_de_model` (`gpt-5.6-luna` — DE bulk occupant)
  - `bulk_en_model` (`gpt-5.6-luna` — EN bulk occupant)
  - `qa_model` (`gpt-5.6-terra` — QA occupant)
  - `bulk_pipeline_version` (`stage04-bulk-v1`)
  - `qa_pipeline_version` (`stage04-qa-v1`)
  - `response_schema_version` (`openai-responses-json-schema-v1`)
- Mechanically verified incompatible identity fails closed — PASS (tests `test_checkpoint_compatibility_components_and_fail_closed`: changing `generated_license`, `bulk_pipeline_version`, `qa_pipeline_version`, or `bulk_de_model` each raises `BuildDictError: incompatible`)
- Configured fake/current role occupants from implementation: DE=`gpt-5.6-luna`, EN=`gpt-5.6-luna`, QA=`gpt-5.6-terra` (defaults in `tools/build_dict.py:2068`; overridden per-run via identity)

### 7. Batch / custom-ID evidence (fake/local, deterministic)

- Deterministic manifest partitioning: bytewise-sorted `item_ids`, partitioned by `max_requests` and `max_bytes` — PASS (`_build_manifests` with `max_requests=2` → 3 manifests for 5 ids)
- Request-count bound: `max_requests` enforced — PASS
- Exact serialized JSONL-byte bound: `byte_len` == `len(payload_bytes)+1` per record including newlines, and `manifest byte_len` == `len(b"\n".join(...)+b"\n")` — PASS
- Manifest-first durability: `manifests` persisted to checkpoint before any `send_bulk`/`send_qa` — PASS (`state["manifests"]` non-empty before submission)
- Input-file identity/SHA: `input_file_sha256 == manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()` — PASS
- Stable custom IDs: `custom_id == f"batch:{item_id}"` for every queue item — PASS
- One semantic item == one logical request == one Batch record — PASS (`sum(len(m["item_ids"])) == len(items)`)
- Output order ignored: `ReorderingTransport` returns reversed dict but join via `custom_id` still succeeds — PASS
- Exact custom-ID join, missing/duplicate/unknown fail closed — PASS (`MissingTransport` → `Missing custom_id`, `UnknownTransport` → `Unknown custom_id`)
- Prepared state: `state == "PREPARED"` — PASS
- Uploaded/submitted states where modeled: manifest `state` transitions are represented as `PREPARED` for fake transport; real Batch states `UPLOADED`, `SUBMISSION_AMBIGUOUS`, `SUBMITTED`, `PROCESSING`, `COMPLETED`, `FAILED`, `EXPIRED/CANCELLED` are accepted as schema values (validated as allowed strings) — PASS
- Ambiguous submission state: `in_flight` retained, no automatic resubmit — PASS
- Terminal states: checkpoint `bulk.completed` / `bulk.rejected` / `qa.completed` are terminal and durable — PASS
- Completed manifest no-resubmit: already-completed manifest `item_ids` never resubmitted on restart — PASS
- Exact-one ambiguous recovery: only clearing exact `in_flight` set allows forward progress — PASS
- No live Batch endpoint contacted — PASS

### 8. Legacy Persian preservation

- Historical five Persian first-canary `bulk.in_flight` IDs remain **LEGACY UNRESOLVED** — PASS
- Verified: file `tests/test_build_dict_stage04.py::test_legacy_persian_checkpoint_preserved` creates legacy checkpoint with `["enrichment-job:v1:ad94a...", "enrichment-job:v1:b9d5cf...", "enrichment-job:v1:bb1978...", "enrichment-job:v1:db6832...", "enrichment-job:v1:f457af..."]`, runs new DE/EN build against separate checkpoint path, asserts legacy file unchanged, and asserts `_load_checkpoint(legacy_path, current_identity)` raises `incompatible` rather than clearing/migrating/resubmitting.
- Current code did not clear, migrate, reinterpret as DE/EN, resubmit, or retry them — PASS
- Historical Persian paid evidence (USD 0.0008764, 3 completed / 1 rejected / 0 ambiguous) remains historical only — not executed.

### 9. Generated row / provenance / rollback evidence

- Generated DE/EN rows use `source='llm_generated_v1'` — PASS (`test_generated_row_provenance_rollback`: 2 rows with `llm_generated_v1` and `TEST_CLASSIFICATION_v1`)
- Explicit generated-output classification/license present: `license='TEST_CLASSIFICATION_v1'` — PASS
- Source-backed rows remain unchanged (`wiktionary` / `CC BY-SA`) — PASS
- Consumed localized source text creates exact same-sense derivation: each `queue:v1:` item with `derivation_source_ids=[1001..]` yields one `sense_meaning_derivation` edge (`generated_meaning_id` → `source_meaning_id`, same `sense_id`) — PASS (2 edges for 2 items)
- Zero-edge valid case: item with `derivation_source_ids=[]` yields zero edges — PASS
- Generated→generated derivation fails closed — PASS (`INSERT ...` then `validate_sense_meaning_derivations` raises `generated->generated forbidden`)
- Rollback deletes generated rows and outgoing derivation edges — PASS (`DELETE FROM sense_meaning WHERE source='llm_generated_v1'` + cascade/manual cleanup → 0 generated, 0 derivation)
- Source-backed meanings survive rollback — PASS (`wiktionary` rows still present)

### 10. Validation / selective QA evidence

- Deterministic validation rules implemented (`tools/build_dict.py:3053` `_validate_generated_candidate`):
  `empty`, `invalid_language`, `invalid_kind`, `too_long (>280 scalars)`, `duplicate` (within unit), `echo_lemma`, `forbidden_bidi` (`U+061C`, `U+200E`, `U+200F`, `U+202A–202E`, `U+2066–2069`), `forbidden_Cc`, `forbidden_Cf` (only `U+200C` ZWNJ allowed), `implausible_german` (no Latin/German letter), `has_no_text` etc.
- German plausibility for DE: regex `[A-Za-zÄÖÜäöüß]` required — PASS
- Forbidden/control content checked via `unicodedata.category` — PASS
- Provenance consistency checked in `validate_sense_meaning_derivations` — PASS
- Flagged set is deterministic: `len(text)>50` or `"flag" in lower` — PASS
- Deterministic QA sample: `_deterministic_audit_sample(sorted_ids, queue_sha, 2)` via `SHA256(seed:item_id)` — PASS
- QA is `all flagged + deterministic sample`, not every row — PASS (`required = flagged ∪ sample`, `len(required) < len(ids)` in test `test_validation_rules_and_qa_routing`)

### 11. Stage-05 current fixture evidence

- Source input unchanged: SHA before == SHA after — PASS (`test_stage05_input_unchanged_and_metadata_consistency`)
- No overwrite: second `build_stage05` to same path raises `BuildDictError: already exists` — PASS
- `PRAGMA quick_check = ok` — PASS
- Required tables validated (`lemma`, `surface_form`, `sense`, `sense_meaning`, `sense_meaning_derivation`, `example`, `example_lemma`) — PASS
- Stable semantic refs uniqueness/nonblank — PASS (blank `semantic_ref` raises `blank`)
- Attribution: every `sense_meaning` has non-empty `source`/`license` — PASS (blank `license` raises `attribution`)
- Derivation integrity via `validate_sense_meaning_derivations` — PASS
- Orphan checks for `example_lemma`, `sense_meaning`, `sense_meaning_derivation` — PASS
- Output checksum/SHA-256 and byte size recorded in metadata — PASS
- Deterministic release metadata (`version`, `filename`, `sha256`, `bytes`, `generated_marker`) — PASS
- **Explicitly:** real Stage-04 enrichment NOT executed; real Stage-05 dictionary NOT produced; no release published — PASS

### 12. Docker / Piper evidence (mechanical reverification, no rebuild for ceremony)

- Image identity/digest: `flashcard-slice6-piper:phase-a` (`d58382bad977d28996036e69b920c8ecab0446a5091c9336c8f685a4ec557fc3`, digest `sha256:2bd3fdd088ebf28e8e38b5ac8ed1b2726e364681a8e342385429681fa2050a6d`) — PASS (Podman inspect)
- `piper-tts==1.6.0` pinned in runtime image (`pip freeze` shows `piper-tts==1.6.0`) — PASS
- Voice `de_DE-thorsten-high` pinned to source revision `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8` (`PIPER_VOICE_REV` ARG) — PASS
- Model SHA `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1` verified (`sha256sum --check` at build) — PASS (`sha256sum /opt/piper/de_DE-thorsten-high.onnx` matches)
- Bounded synthesis smoke: `printf 'Guten Tag.' | piper --model /opt/piper/de_DE-thorsten-high.onnx --output_file /tmp/piper-smoke.wav && test -s /tmp/piper-smoke.wav` — PASS (reverified via `podman run` → `/tmp/test.wav` 24K)
- No runtime LLM SDK: `pip freeze | grep -E '^(anthropic|openai|google-genai)=='` empty — PASS
- GPL-3.0-or-later engine classification: `PIPER-ENGINE-LICENSE` contains `GPL-3.0-or-later` (from `importlib.metadata` at build) — PASS
- MIT voice-repository metadata: `PIPER-VOICE-REPOSITORY-METADATA.json` has `cardData.license == "mit"` and `sha == "8aaa3c9839d2b669cb57a94e1ec92ae0928897e8"` — PASS
- Thorsten model-card dataset CC0 classification/notices: `/usr/share/doc/flashcard/THORSTEN-MODEL-CARD` contains `License: CC0` and `PIPER-NOTICES` records `Thorsten-Voice dataset/model card: CC0` — PASS
- Do not rebuild solely for ceremony: exact current local image and evidence mechanically reverified via `podman image inspect` / `podman run` — PASS
- No bulk pronunciation media baked in — PASS

### 13. Final authoritative gate (WORKFLOW §15)

After retry changes and targeted tests, executed exactly one final `make gate` with longest blocking timeout:

```
.venv/bin/ruff check . — All checks passed!
.venv/bin/mypy --strict . — Success: no issues found in 18 source files
.venv/bin/pytest -q — 254 passed in 107.76s (0:01:47)
.venv/bin/python tools/check_agents.py — AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling)
```

- Ruff: PASS
- mypy strict: PASS (18 source files)
- pytest: **254 PASSED**, 0 failed, 0 skipped
- check_agents: **R1/R3/R7 PASS**
- `git diff --check`: PASS (no whitespace errors)
- Provider calls: **0** — verified (no credential read, no transport that contacts provider)
- Paid spend this retry: **USD 0**

### 14. Changed-path evidence (Attempt-2)

Before commit, verified `git diff --stat` shows every changed tracked path within allowlist:

- `tests/test_build_dict_stage03.py`
- `tests/test_build_dict_stage04.py`
- `tests/test_build_dict_stage05.py`
- `tasks/slice-6.report.md`

No other tracked path was modified in Attempt 2. In particular `tools/build_dict.py`, `pyproject.toml`, `Dockerfile`, `.dockerignore` were unchanged in this retry (implementation already correct).

Exact Attempt-2 changed paths: `tests/test_build_dict_stage03.py, tests/test_build_dict_stage04.py, tests/test_build_dict_stage05.py, tasks/slice-6.report.md`

### 15. Work left undone / STOP

- Any paid DE/EN canary or production Batch submission — NOT executed (requires explicit orchestrator authorization per D79)
- Live semantic QA on real DE/EN queue — NOT executed
- Packaging of real enriched dictionary via Stage-05 — NOT executed
- Release publication — NOT executed
- Real Stage-03 queue not re-materialized as 316 MB artifact this retry (input unchanged; measurement preserved)

**Disposition:** `STOPPED BEFORE PAID BOUNDARY` — Phase-A implementation and acceptance-evidence complete; no paid provider work authorized or executed. Next authority required is the Slice-6 orchestrator Phase-A acceptance decision.

### 16. Branch / push status

- Base `main`: `2f2486a5021465842ada8e5cc3d43e9a030e6955` — unchanged
- Base `slice/6` before retry: `e45912e39eff49ba046984133206c01132b786a3` — verified `git rev-parse HEAD` and `origin/slice/6` before changes
- Final `HEAD` after retry commit: to be recorded after `git push` (see return receipt)
- Remote push: `git push origin slice/6` then `git fetch origin`; verified `origin/slice/6 == local HEAD` and `origin/main == 2f2486a...` — PASS
- Working tree after push: `clean` (`git status --porcelain` empty)

---

*No API keys, credential fragments, or private absolute paths recorded. Generated-output classification `TEST_SYNTHETIC_LICENSE_v1` is synthetic test-only; live generated rows will use `llm_generated_v1` with explicit license supplied at execution time. Stage-03 queue byte hash and Stage-04 checkpoint identities are deterministic and reproducible from recorded inputs.*

---

## ADR-0007 Post-ceiling Semantic-context Repair — Attempt 1

**Status:** Post-ceiling narrowed repair complete. No provider credential read, no network call, no paid spend. Old queue:v1 artifacts invalidated. Stopped before paid DE canary boundary.

**Attempt lineage:**
- Prior T3 task reached WORKFLOW §5 Failure 2 and was returned to orchestrator for design reset.
- Prior Phase-A acceptance was withdrawn after zero-spend canary preparation exposed the semantic request defect (queue:v1 omitted source-backed EN text, requests carried no German instruction and no strict structured-output schema, human canary report drifted from machine artifact).
- T3 ceiling returned to read-only design reset; design reset concluded `ADR_REQUIRED=NO` (RESULT: STAGE04_SEMANTIC_CONTEXT_DESIGN_RESET_COMPLETE).
- This is a newly narrowed post-ceiling task Attempt 1, not Attempt 3 of the failed task.

**Defect recorded:**
- `queue:v1` (SHA `e542f2f96b3966690fe2fcebb145440deba7a8ec9aa7dd2d0c93ba3540ef7aa1`, 316541240 bytes) omitted all 577141 source-backed EN meaning rows.
- Requests had no actual German instruction; no transmitted strict `text.format` json_schema.
- Prior DE canary artifacts (queue:v1 selection, request hash, Batch manifest hash) are INVALIDATED and were never transmitted (provider calls 0).
- Human canary report drifted from machine artifact (no single-source receipt).

**Repair shipped:**
- Queue format `flashcard-stage03-queue-v2`, item prefix `queue:v2:` (no `queue:v1:` emitted).
- For every canonical sense producing `de_learner_meaning`, all same-sense source-backed `sense_meaning` rows with `language='en'` and `source NOT GLOB 'llm_generated_v*'`, ordered `ORDER BY ord ASC, id ASC`, are carried as semantic context. Each EN row contributes `language, kind, ord, text, source, license` to deterministic identity; numeric `meaning_id` rides only as convenience.
- Durable item ID depends on `lemma.semantic_ref`, `sense.semantic_ref`, target language, job class and actual EN semantic content; numeric IDs, mtimes, paths do not affect identity. Identity changes iff EN source text changes.
- Bounded-memory streaming queue build: ordered SQLite iteration, temp-sort spill DB, incremental SHA-256, atomic temp-file then rename; no requirement to hold full 480221 items or 577141 texts in RAM.
- Real Stage03 v2 executed against accepted Stage-02 asset (`75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`, 945410048 bytes, `PRAGMA quick_check=ok`, counts verified, no mutation):
  - `STAGE03_V2_TOTAL=480221`, `STAGE03_V2_DE=480221`, `STAGE03_V2_EN=0`
  - `STAGE03_V2_DERIVATION_INPUTS_TOTAL=577141`
  - `STAGE03_V2_ONE_SOURCE=383303`, `STAGE03_V2_TWO_SOURCE=96916`, `STAGE03_V2_THREE_SOURCE=2`, `STAGE03_V2_ZERO_SOURCE=0`
  - `STAGE03_V2_QUEUE_SHA256=114dd20f1e071708ca43ff433284ce1be0e9662763db5a589930a8f5a045cf2a`
  - `STAGE03_V2_QUEUE_BYTES=334605426` (new, differs from queue:v1 as expected)
  - `items_sha256` (canonical items array) `dc32611224e20ab3bdaeb5ac8dd77d01e8a81ffe5a4922c55175edf458787198`
  - Verified: queue format v2, every `item_id` prefix `queue:v2:`, unique IDs, deterministic bytewise order, no credentials, no private absolute paths, Stage-02 SHA unchanged, zero network calls.
- Derivation contract: every persisted generated German meaning gets N edges where N = number of EN texts supplied; expected distribution 383303×1, 96916×2, 2×3, 0×0 = 577141 total; edges satisfy same-sense, source-backed non-generated, nonblank source/license, no generated→generated, no duplicates, atomic with generated row, rollback by `DELETE WHERE source='llm_generated_v1'` preserves source rows.
- German prompt contract: single-source `de_learner_meaning_request_body(item, model) -> dict` carries German lemma, POS, gender when present, every EN meaning in canonical order, opaque refs labelled as identifiers carrying no meaning; instructions enforce the 14 required clauses (single sense only, EN defines sense, refs opaque, German only, synonym-first, short A2-B1 explanation otherwise, no broadening/drift, no lemma echo, no `siehe`/`vgl.` etc., no etymology/examples/English, morphology handling, strict schema only, brevity).
- Strict response schema via `text.format` `type=json_schema`, `strict=true`, `additionalProperties=false`; DE requires `meaning`+`kind` (`synonym`|`definition`), EN requires `meaning` only (`kind=translation` locally fixed), provider language field never trusted, missing/extra/wrong type fails closed.
- Sync/Batch logical equivalence: one committed body-builder per job class (`_request_body_for_item` → `de_learner_meaning_request_body` / `en_meaning_request_body`); Batch record `body` is exact same dict; test proves `canonical_json(sync_body)==canonical_json(batch_record["body"])`.
- Pipeline/checkpoint version reset: `stage04-bulk-v2`, `stage04-qa-v2`, `openai-responses-json-schema-v2`, `flashcard-stage04-checkpoint-v3`; checkpoint identity includes queue SHA, generation marker `llm_generated_v1`, generated-output classification `TEST_SYNTHETIC_LICENSE_v1` (synthetic), bulk DE/EN models, QA model, bulk/QA pipeline versions, response-schema version; pre-repair DE checkpoint fails closed.
- QA semantic context: selective QA receives same EN texts, German candidate, lemma/POS/gender, opaque refs; QA is flagged ∪ audit sample (deterministic SHA), not every row; QA pipeline bumped to v2.
- Generated-output classification remains REQUIRED execution input; synthetic test value `TEST_SYNTHETIC_LICENSE_v1` used in checkpoint/tests, not a live default; missing classification fails closed before generated row creation; source rows retain `wiktionary/CC BY-SA`, generated rows use `llm_generated_v1` and never masquerade.
- Canary artifact single source: ` _write_canary_selection_manifest` is the sole writer (deterministic bytewise order, self-hashes exact bytes, refuses overwrite, returns SHA+bytes); human receipt `_render_canary_receipt` re-reads canonical artifact, verifies SHA, parses/validates, rejects extra/missing/mutated/SHA mismatch; every displayed field comes from same artifact record.
- Marker remains `llm_generated_v1` (not bumped, no live generated row yet).
- Live generated-output classification/license remains `NOT YET AUTHORIZED`; missing live value stays fail-closed.

**Executable evidence:**

- Stage-03 targeted: `pytest -q tests/test_build_dict_stage03.py` — **16 passed** (deterministic queue, DE fallback provenance with EN context, predicate, overwrite/retired, stable refs, no-network, and 9 new v2 semantic-context tests: 1-/2-/3-source, generated-source exclusion, other-sense exclusion, ord,id ordering, identity ignores numeric IDs, queue:v1 ban, format v2, prompt EN text)
- Stage-04 targeted: `pytest -q tests/test_build_dict_stage04.py` — **30 passed** (fake bulk/QA, marker/license, derivation, validation, checkpoint, Batch manifest, legacy preservation plus 12 new v2 tests: strict DE/EN schema, provider language override, synonym/definition persistence, missing kind rejection, sync≈Batch equivalence, QA semantic context, N=2/3 derivations, induced edge rollback, old checkpoint rejection, missing classification, canary single-source)
- Stage-01 regressions: `pytest -q tests/test_build_dict_stage01.py` — **46 passed**
- Stage-02 regressions: `pytest -q tests/test_build_dict_stage02.py` (via `.venv`) — **54 passed**
- Full gate: `make gate` — Ruff PASS, mypy --strict PASS (18 source files), pytest **273 passed** in 103.17s, check_agents R1/R3/R7 PASS
- `git diff --check`: PASS
- Allowlist: PASS — only `tools/build_dict.py`, `tests/test_build_dict_stage03.py`, `tests/test_build_dict_stage04.py`, `tasks/slice-6.report.md`
- Stage-02 unchanged after build: SHA before == SHA after `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`
- No private absolute paths in queue or checkpoint; zero network calls
- Legacy Persian `bulk.in_flight` 5 IDs remain preserved/not resubmitted (incompatible checkpoint fails closed)
- Old queue:v1 canary invalidated/not transmitted

**Changed paths (this repair):**
`tools/build_dict.py`, `tests/test_build_dict_stage03.py`, `tests/test_build_dict_stage04.py`, `tasks/slice-6.report.md`

**Branch/push:**
- Base `main`: `2f2486a5021465842ada8e5cc3d43e9a030e6955` — unchanged
- Base `slice/6` before repair: `57e783cf7ce4984e5df22008863826c50a96d353`
- Final `HEAD` after repair commit: to be recorded after `git push` (see return receipt)
- Remote push: `git push origin slice/6` then `git fetch origin`; verified `origin/slice/6 == local HEAD` and `origin/main == 2f2486a...` — PASS
- Working tree after push: `clean`

**Provider calls:** `0` — no credential read, no German canary, no Batch upload, no Persian execution

**Paid spend:** `USD 0`

**Work left undone / Next authority:**
- Paid 50-item DE canary and selective QA not authorized/executed (requires separate owner/orchestrator authorization naming canonical artifact SHA, transport, models, prompts, USD cap, classification, QA plan, checkpoint handling)
- Full DE/EN Batch production long run not authorized (requires D79 gates: ADR-0007 frozen, measured queue, accepted canary/QA, verified Batch limits/correlation, prepared partition plan/manifests, cost estimate, explicit authorization)
- Real Stage-05 enriched dictionary packaging and release publication not executed

**Disposition:** `POST_CEILING_SEMANTIC_REPAIR_COMPLETE` — implementation repair verified and pushed; awaiting Slice-6 orchestrator acceptance of the post-ceiling semantic repair, followed by a new zero-spend German canary preparation against `queue:v2`.

*No private absolute paths, no API keys, no credentials recorded. Old queue:v1 SHA `e542f2f96b3966690fe2fcebb145440deba7a8ec9aa7dd2d0c93ba3540ef7aa1` is pre-repair and invalid for live generation. New queue:v2 SHA `114dd20f1e071708ca43ff433284ce1be0e9662763db5a589930a8f5a045cf2a` (334605426 bytes) carries 577141 EN derivation inputs.*

---

## ADR-0007 Canary paid-request boundedness repair — Attempt 1

**Status:** Narrow zero-spend logical-request-contract repair complete. No provider
credential read, no network call, no live provider request of any kind. Stopped
before the paid boundary. The already-frozen canary-v2 selection was NOT reselected.

**Defect recorded:** Zero-spend German canary-v2 preparation produced request and
Batch artifacts whose bodies carried no `max_output_tokens` and no explicit
`reasoning.effort`. Under the current OpenAI Responses API, `max_output_tokens`
bounds VISIBLE OUTPUT + REASONING TOKENS together; absent bounds leave model
execution non-deterministic and unbudgeted.

### Frozen / unchanged inputs

- Canary-v2 selection remains ACCEPTED/FROZEN — `CANARY_SELECTION_SHA256`
  `1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475`, 40385 bytes,
  50 items. Not reselected; no selection identity input changed.
- Queue remains `flashcard-stage03-queue-v2`,
  SHA `114dd20f1e071708ca43ff433284ce1be0e9662763db5a589930a8f5a045cf2a`, 480221 items.
- Generation marker remains `llm_generated_v1`.
- Checkpoint file format remains `flashcard-stage04-checkpoint-v3` (not bumped
  cosmetically; the new strict identity components alone invalidate old state).
- Response schema version remains `openai-responses-json-schema-v2`.

### Invalidated prepared artifacts

- Old canary requests (`0035db54b824d3fcf0886a13120d049c0b08e9affe0526615fdb4d1880d10a1f`)
  and old Batch manifest (`220f9ef45a697edebff512ac79b8365b71b3b5d3b443796ef16bf3f4bdd4ff19`)
  are INVALIDATED FOR LIVE TRANSMISSION. Neither was ever transmitted. They lack the
  repaired body fields and cannot be regenerated under the new pipeline identity.
  Regeneration against the frozen selection requires a fresh zero-spend preparation run.

### Repair shipped

- Single-source logical body builders remain authoritative; no transport-only
  alternative body exists:
  - every Luna bulk DE/EN logical body now contains exactly
    `"reasoning": {"effort": "none"}` and `"max_output_tokens": 512`;
  - every Terra QA logical body now contains exactly
    `"reasoning": {"effort": "low"}` and `"max_output_tokens": 512`;
  - all pre-existing fields unchanged: model, exact semantic input, strict
    `text.format` json_schema (`strict=true`, `additionalProperties=false`),
    exact same-sense EN meaning context, opaque identity refs, German learner
    instructions.
- Sync/Batch equivalence preserved: the exact same body object is embedded in
  Batch records (`custom_id`/`method=POST`/`url=/v1/responses`/`body`); bytewise
  canonical equality of sync vs embedded body is proven by test, including through
  the manifest payload serialization path.
- Pipeline identities bumped: `stage04-bulk-v2` → `stage04-bulk-v3`,
  `stage04-qa-v2` → `stage04-qa-v3`.

### Checkpoint compatibility additions

Identity now additionally carries six explicit components (values):
`bulk_de_reasoning_effort=none`, `bulk_de_max_output_tokens=512`,
`bulk_en_reasoning_effort=none`, `bulk_en_max_output_tokens=512`,
`qa_reasoning_effort=low`, `qa_max_output_tokens=512`. Changing any reasoning-effort
or max-output-token component invalidates checkpoint reuse (tested). Any
pre-repair DE checkpoint (v2 pipelines, missing the six components) fails closed
as incompatible (tested). Historical Persian checkpoint remains untouched:
not cleared, not migrated, not resubmitted.

### Incomplete-response handling

Returned provider responses are completion-checked before candidate extraction:
`response_status != "completed"` → durable rejection `provider_status_<status>`;
`incomplete_details.reason = "max_output_tokens"` → durable rejection
`incomplete_max_output_tokens`; malformed envelope metadata fails closed
(`invalid_response_envelope`). Partial JSON is never silently extracted or
persisted; the existing deterministic returned-response rejected handling applies
(durable rejected state with attempt count, `in_flight` cleared) and execution
STOPs before any further paid bounded unit (A6). Proven for bulk and QA phases.

### Pre-transmission spend guard (synthetic-price tests only)

Deterministic pure functions, prices supplied as operational execution input
(never code constants; must be reverified before live work):

- `stage04_worst_case_request_cost_usd(input_token_estimate, max_output_tokens,
  input_price_per_mtok, output_price_per_mtok, input_safety_multiplier=2.0)` —
  all output tokens (visible + reasoning) charged at the output rate against the
  request's own `max_output_tokens` ceiling; input estimate inflated by the
  accepted safety multiplier; negative/degenerate inputs fail closed.
- `stage04_pretransmission_guard_blocks(recorded_spend_usd, authorized_hard_cap_usd,
  next_request_worst_case_usd)` — True ⇒ the live synchronous worker MUST NOT
  transmit (`recorded_spend + worst_case_next > authorized_hard_cap`);
  boundary arithmetic tested (exactly-at-cap permitted, beyond-cap blocked).

### Hard-cap acceptance arithmetic (evidence only; zero-spend readiness rerun remains authoritative)

At verified rates Luna $0.20/$1.20 per MTok, Terra $2.00/$12.00 per MTok, and
`max_output_tokens=512` on every request, with conservative inputs (measured v3
canary body maximum ≈344 input tokens; QA assumed ≤600 raw; committed ×2 safety
multiplier): worst case per Luna request $0.0001376 in + $0.0006144 out =
$0.000752; per Terra request $0.0024 in + $0.006144 out = $0.008544. Canary of
50 Luna + up to 50 Terra QA: 50×$0.000752 + 50×$0.008544 = **$0.4648 ≤ USD 0.50**
with margin. All output/reasoning tokens are charged at ceiling on every request.

### Executable evidence

- New Stage-04 repair tests (13): DE reasoning none/max 512; EN reasoning none/max
  512; QA reasoning low/max 512; sync≡Batch bytewise canonical equivalence incl.
  bounds; strict schema + exact semantic context unchanged with bounds present;
  reasoning-effort change invalidates checkpoint; max-token change invalidates
  checkpoint; pre-repair checkpoint fails closed; incomplete max_output_tokens
  response never persisted + STOP before further paid unit; non-completed status
  fails closed; incomplete QA response never persisted; spend guard blocks
  over-cap; spend guard permits within-cap (+ fail-closed argument checks).
- Targeted: `pytest -q tests/test_build_dict_stage04.py` — **43 passed**
  (30 prior + 13 new); `pytest -q tests/test_build_dict_stage03.py` — **16 passed**
  (unchanged; prompt-context regression green).
- Full gate: `make gate` — Ruff PASS, mypy --strict PASS (18 source files),
  pytest **286 passed**, check_agents R1/R3/R7 PASS — PASS (single final run).
- `git diff --check`: PASS.
- Allowlist: PASS — only `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
  `tasks/slice-6.report.md`.
- No network: all coverage uses fake/local deterministic transports; new code paths
  perform no I/O. No credential read: no credential path touched by implementation
  or tests.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`

**Branch/push:** Base `slice/6` before repair:
`44dbfdb0dfd0449eab88c0fe53431da73a14aec7`; base `main`
`2f2486a5021465842ada8e5cc3d43e9a030e6955` unchanged. Final HEAD recorded in the
return receipt after push.

**Provider calls:** `0`. **Paid spend:** `USD 0`.

**Work left undone / Next authority:** Slice-6 orchestrator acceptance of this
repair, then zero-spend regeneration of request/Batch artifacts for the frozen
50-item selection under `stage04-bulk-v3`/`stage04-qa-v3` identities, then owner
paid authorization with a fresh readiness/cost rerun. The invalidated request and
Batch hashes above must never be transmitted.

**Disposition:** `CANARY_PAID_REQUEST_BOUNDS_REPAIR_COMPLETE`

*No private absolute paths, no API keys, no credentials recorded.*

---

## ADR-0007 Live Responses transport activation — Attempt 1

**Status:** ZERO-SPEND implementation of the missing live Stage-04 OpenAI
Responses transport. The owner had already authorized the exact German Canary
v3, but execution remained SUSPENDED because the accepted code had no real
provider transport: the stage04 CLI invoked `build_stage04` without a transport
argument, `transport` defaulted to `None`, pending work with `transport=None`
failed closed ("No local deterministic Stage 04 transport configured"), and the
only existing transports were fake/local test seams. This attempt repairs that
defect without performing any provider call.

**Provider calls:** `0`. **Paid spend this attempt:** `USD 0`.
No credential was read, validated against a provider, or transmitted; no
canary ran; execution authorization remains suspended pending the mandated T3
full-diff review.

### Explicit opt-in activation

- New stage04 CLI flag `--live-openai-responses` plus required explicit
  operational authorization arguments (selection artifact+SHA, accepted queue
  SHA+bytes, authorized request SHA, authorized Batch-equivalence SHA,
  cost-plan artifact+SHA, hard spend cap USD, bulk/QA input/output prices per
  MTok, input safety multiplier, approved bulk/QA models, finite HTTP timeout).
- Default behavior is unchanged and zero-network/zero-credential: without the
  flag the CLI never reads `OPENAI_API_KEY`, never constructs a live transport,
  and never contacts any host. Live authorization arguments supplied without
  the flag fail closed.
- Credential read boundary: every authorization artifact is SHA-verified by
  `prepare_stage04_live` BEFORE `_read_openai_api_key()` runs (the only place
  the project touches `OPENAI_API_KEY`). Missing/blank key stops before any
  provider transmission. The key is never printed, logged, persisted, embedded
  in exception text, included in checkpoints/reports/request artifacts, or
  exposed via `repr`.

### Provider endpoint / network security

- Fixed endpoint constant `https://api.openai.com/v1/responses`; POST with
  `Authorization: Bearer …` + `Content-Type: application/json`; verified-TLS
  defaults; environment proxies explicitly emptied so the credential
  destination is not configurable; no CLI/API-base override exists anywhere.
- Redirects are never followed (declining redirect handler ⇒ HTTPError);
  redirect responses are treated as ambiguous outcomes.
- Exactly ONE transmission attempt per paid request: no retry wrappers, no
  backoff, no automatic resends of 429/5xx/timeouts/EOF. Connection failure,
  timeout, TLS failure, EOF, or any non-2xx outcome preserves `in_flight`,
  keeps the conservative worst-case reservation, and STOPs.

### Authorization fences (all BEFORE key read)

- Frozen-selection fence: canonical selection re-read via the accepted
  SHA-verifying reader (`_render_canary_receipt`), count == 50, 50 unique IDs,
  each selected item resolved record-by-record against the byte-exact accepted
  queue:v2 asset (streaming, bounded memory); missing/divergent records stop.
- Working-set fence: live pending work is limited to exactly the 50 authorized
  IDs by materializing a derived 50-item subset queue; the full 480221-item
  queue can never become eligible for transmission.
- Request-SHA fence: the 50 synchronous request bodies are regenerated through
  the committed single-source builders and serialized in the readiness
  artifact format; SHA must equal the authorized value or STOP.
- Batch-equivalence fence: Batch-envelope bytes are re-materialized and their
  SHA must equal the authorized value or STOP.
- Cost-plan fence: maintainer-local cost plan must be SHA-exact, bound to the
  same selection+request SHAs, cover exactly the 50 IDs, carry nonnegative
  integer estimates, and match the frozen German-canary aggregates
  (bulk `23996`, QA-bound `24546`).

### Durable spend ledger and pre-transmission cap

- Checkpoint-embedded ledger (`flashcard-stage04-spend-ledger-v1`) records, per
  paid request: phase, item ID, provider response ID when known, reported
  input/output/reasoning tokens, computed charge, cumulative chain, ACTUAL vs
  WORST_CASE_RESERVED accounting, plus the full authorization mirror
  (selection SHA, request SHA, cap, prices, multiplier). Corrupt ledgers fail
  closed on load; restarts preserve cumulative spend; bulk and QA share the
  single USD cap. Historical Persian spend remains separate and untouched.
- Before EACH transmission the guard computes
  `worst_case = safety × estimate × input_price + 512 × output_price` in exact
  Decimal arithmetic and blocks (`recorded_or_reserved + worst_case > cap`)
  BEFORE the unit's `in_flight` state is written — a blocked request leaves
  zero checkpoint side effects. An admitted request persists its worst-case
  reservation together with `in_flight` atomically before transmission.
- Complete response + valid usage ⇒ reservation converts to ACTUAL charge at
  authorized rates (output tokens include reasoning) atomically with the item
  result. Complete response + missing/malformed usage ⇒ WORST_CASE_RESERVED
  stands, durable rejection `provider_usage_unavailable`, STOP.

### Response parsing (fail-closed)

- Safe metadata recorded: response id, status, incomplete_details, usage
  tokens (+ reasoning tokens when supplied).
- Non-completed status and max_output_tokens exhaustion flow into the existing
  durable rejected/incomplete state machine; partial JSON is never extracted.
- Completed responses may carry provider reasoning items alongside the final
  assistant message; exactly one usable assistant output_text payload is
  required, parsed as JSON, required to be an object, then passed through the
  existing strict deterministic candidate validation. Missing / multiple /
  malformed / non-object payloads produce deterministic durable rejections
  (`missing_output_text`, `multiple_output_text`, `malformed_output_json`,
  `output_not_object`, `invalid_response_envelope`). Raw reasoning content is
  neither persisted nor exposed.

### QA boundary

Live QA remains exactly all deterministically flagged candidates UNION the
deterministic audit sample; Terra bodies (`gpt-5.6-terra`, reasoning low,
max_output_tokens 512) come from the committed single-source QA builder; the
same ledger, cap, reservation, in-flight and parsing rules apply; QA requests
are sent only after all prerequisite bulk state is durably checkpointed.

### Unchanged frozen logical requests (zero-spend re-verification)

The committed live preflight was executed end-to-end against the real accepted
queue (`114dd20f…`, 334605426 bytes) and real frozen selection
(`1ffa5e76c7…`, 50 items), with tiktoken-measured cost-plan aggregates
matching the frozen contract (23996 / 24546):

- Regenerated synchronous request artifact SHA:
  `5e2f6f92a72e83c3a14e61d78380fbcf5e76233e9133381440de4724ca731f7b` — EXACT MATCH
- Regenerated Batch-equivalence bytes SHA:
  `ad9cb8c10a479155015b1fa97a552bf129a129268231ecd8e1e73c39d203d6d6` — EXACT MATCH
- Preflight printed `LIVE_PREFLIGHT_OK`, then stopped at the credential
  boundary ("OPENAI_API_KEY is missing or blank"); no checkpoint file was
  created and nothing was transmitted. REQUEST_SHA UNCHANGED / BATCH_SHA
  UNCHANGED: PASS.

### Executable evidence

- Stage-04 targeted: `pytest -q tests/test_build_dict_stage04.py` — **87 passed**
  (43 prior + 44 new live-transport tests covering the mandatory matrix:
  default zero-network; flag-gated key access; selection/count/uniqueness/
  divergence fences pre-key-read; request/Batch/cost-plan SHA fences;
  outside-authorization items cannot transmit; fixed endpoint and no
  configurable credential destination; redirect not followed; header built but
  never logged/persisted; exact authorized body transmitted unchanged;
  structured completion parsing; reasoning coexistence without exposure;
  missing/multiple/malformed output failures; incomplete status; usage ACTUAL
  accounting; missing-usage worst-case reservation; timeout/network/HTTP-error
  ambiguity preserving in_flight; zero automatic retries on every error path;
  over-cap guard blocking before HTTP; restart-preserving cumulative spend;
  shared bulk+QA cap; classification/cap/price/multiplier checkpoint
  invalidation; legacy Persian preservation; pinned serialization format; no
  credential leakage; no real provider calls).
- Stage-03 targeted: `pytest -q tests/test_build_dict_stage03.py` — **16 passed**
- Full gate: `make gate` — Ruff PASS; mypy --strict PASS (18 source files);
  pytest **330 passed**; check_agents R1/R3/R7 PASS — PASS (single final run)
- `git diff --check`: PASS

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`

**Branch/push:** Base `slice/6`
`033085ccf59cc52110d9a9a139fc16ad945b077a`; base `main`
`2f2486a5021465842ada8e5cc3d43e9a030e6955` unchanged. Final HEAD recorded in
the return receipt after push.

**Work left undone / next authority:** Independent fresh T3 auth-security
full-diff review of the slice range. No paid call is permitted before review
acceptance; the owner's existing Canary v3 authorization may then be used only
if the frozen logical request bodies remain byte-identical (re-provable by the
committed preflight).

**Disposition:** `LIVE_RESPONSES_TRANSPORT_IMPLEMENTATION_COMPLETE`

*No API keys, credential fragments, or private absolute paths recorded.*

## ADR-0007 Live Responses transport activation — Attempt 2

**Status:** ZERO-SPEND repair of the single blocking defect found by the mandatory
independent T3 auth-security full-diff review of Attempt 1. Attempt-1 historical
evidence above is preserved unchanged; the restart-persistence claims made in that
section are **superseded by the Attempt-2 evidence below**.

**Provider calls:** `0`. **Paid spend this attempt:** `USD 0`.
No credential was read, validated, or transmitted; no canary ran. The owner's
German Canary v3 authorization remains RECORDED but SUSPENDED pending fresh
independent auth-security re-review.

### Review outcome that triggered this attempt

The independent reviewer (opus-5 / T3 / high) returned
`AUTH_SECURITY_FULL_DIFF_REVIEW_BLOCKED` over range
`033085cc..dbee7bc0` with two blockers:

- **B1 — stale spend-ledger object.** `execute_stage04_live` loaded the checkpoint
  and handed spend-ledger object *A* to `OpenAILiveResponsesTransport`.
  `build_stage04` then reloaded the same checkpoint, producing an independent
  ledger object *B*. The pre-existing re-alias `state["spend"] = spend_state` ran
  only when no `spend` key existed, so on any **restarted** run the transport
  mutated *A* while every `_write_checkpoint` serialized *B*. Paid requests were
  transmitted whose worst-case reservations and ACTUAL charges never reached
  durable state, breaking durable-reservation-before-transmission, restart
  cumulative-spend preservation, and hard-cap enforcement across restarts.
  The reviewer reproduced it with a fake provider: run 1 persisted 2 entries /
  USD 0.000136; after restart, 50 transmissions occurred and 49 bulk items
  completed while the persisted ledger still showed 2 entries / USD 0.000136.
- **B2 — report claim invalidated.** The Attempt-1 section asserted "restarts
  preserve cumulative spend" and that an admitted request "persists its worst-case
  reservation together with `in_flight` atomically before transmission". Both were
  false for any run resuming an existing checkpoint.

### Exact remedy (B1 — RESOLVED)

Single narrow change in `build_stage04`, at the checkpoint-load site:

- when a persisted ledger exists, its validated contents are moved **into the
  caller-supplied ledger dict** (`spend_state.clear()` + `spend_state.update(...)`,
  guarded by an identity check) instead of rebinding a local name;
- `state["spend"] = spend_state` now executes on **both** branches.

Result: exactly **one authoritative mutable spend-ledger object** exists per live
Stage-04 execution — the same dict the live transport mutates, the same dict
`build_stage04`'s `state` references, and the same dict `_write_checkpoint`
serializes, on fresh runs and restarts alike. The transport was not redesigned;
no other behavior changed.

### Durability invariant now holds after restart

For every live paid request, including after restart: authoritative ledger loaded →
worst-case reservation appended → `in_flight` + updated ledger durably checkpointed
→ only then HTTP transmission → completed response with valid usage converts the
reservation to ACTUAL → missing/malformed usage retains `WORST_CASE_RESERVED` →
ambiguous outcome retains `in_flight` and the reservation → restart reloads the
cumulative ledger and continues from that exact value. No restart resets, forks, or
stops persistence of cumulative spend.

### End-to-end restart regression (the boundary Attempt 1 missed)

`test_execute_stage04_live_restart_persists_new_spend_end_to_end` drives **three
consecutive real `execute_stage04_live` invocations against one checkpoint**,
discarding every in-memory object between them (fake opener, injected test
credential, zero network). It crosses the exact
`execute_stage04_live → build_stage04` boundary that caused B1:

- **Run 1** — 2 paid transmissions; item 0 completes with usage, item 1 returns
  `incomplete` → STOP. Persisted: **2 entries, both ACTUAL, USD 0.000136**,
  `in_flight == []`.
- **Run 2 (restart)** — 1 further paid transmission to
  `https://api.openai.com/v1/responses`, response carries no `usage` →
  `WORST_CASE_RESERVED` stands, durable rejection `provider_usage_unavailable`.
  Checkpoint re-read from disk: **3 entries, USD 0.0009424** — the prior two
  entries preserved verbatim, the new entry carrying the run-2 reservation
  (`charge_usd == 0.0008064`) with a valid cumulative chain. Persisted ledger
  equals the accounting the second run actually used.
- **Run 3 (restart)** — the next request's worst case plus the cumulative spend
  from **both** prior runs exceeds the cap: `Stage04PretransmissionBlocked`
  raised with **zero HTTP calls**, `in_flight == []`, ledger unchanged.
- The test also asserts the counterfactual that makes it meaningful: the *same*
  cap would have **admitted** that run-3 request had the ledger reset to zero
  (`stage04_pretransmission_guard_blocks_decimal(0, cap, w) is False` while
  `(total_after_two_runs, cap, w) is True`).

`test_live_spend_ledger_object_is_shared_with_checkpoint_state` additionally
asserts object identity directly on both a fresh run and a restart: the
transport's `_spend_state` **is** the dict passed to `_write_checkpoint`.

Both new tests were confirmed to **fail against the Attempt-1 code**
("restart spend must persist (Attempt-1 B1)" / "transport ledger and serialized
checkpoint ledger diverged") and pass after the remedy.

### Preserved Attempt-1 security properties (unchanged)

Explicit live opt-in; credential read only after the full authorization preflight;
fixed `https://api.openai.com/v1/responses`; redirects declined; env proxies
emptied; zero automatic retries; finite timeout; frozen 50-item selection fence;
request-SHA fence; Batch-SHA fence; cost-plan fence; Decimal cap arithmetic;
combined bulk+QA USD 0.45 cap; ambiguous `in_flight` STOP; response parsing;
reasoning content never persisted; usage accounting; missing-usage worst-case
reservation; legacy Persian checkpoint untouched. No request-body semantics,
governance, ADR, Stage-03, Stage-05, dependency, or Docker file was touched.

### Frozen request invariance (re-verified, zero spend)

The committed preflight was re-executed end-to-end against the **real** accepted
queue (`114dd20f…`, 334605426 bytes, 480221 items) and the **real** frozen
50-item selection (`1ffa5e76c7…`), via `prepare_stage04_live` only, in a process
with `OPENAI_API_KEY` removed from the environment:

- `LIVE_PREFLIGHT_OK selection=1ffa5e76c731 request_sha=5e2f6f92a72e
  batch_equiv_ok cost_plan_ok`
- Regenerated synchronous request artifact SHA:
  `5e2f6f92a72e83c3a14e61d78380fbcf5e76233e9133381440de4724ca731f7b` — **EXACT MATCH**
- Regenerated Batch-equivalence bytes SHA:
  `ad9cb8c10a479155015b1fa97a552bf129a129268231ecd8e1e73c39d203d6d6` — **EXACT MATCH**
- 50 selected items, 50 unique; no checkpoint file created; nothing transmitted.

REQUEST_SHA UNCHANGED / BATCH_SHA UNCHANGED: **PASS**.

### Executable evidence

- Stage-04 targeted: `pytest -q tests/test_build_dict_stage04.py` — **89 passed**
  (87 from Attempt 1 + 2 new restart-persistence regressions)
- Stage-03 targeted: `pytest -q tests/test_build_dict_stage03.py` — **16 passed**
- Full gate: `make gate` — Ruff PASS; mypy --strict PASS (18 source files);
  pytest **332 passed**; check_agents R1/R3/R7 PASS — PASS (single final run)
- `git diff --check`: PASS

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`

**Branch/push:** Base `slice/6`
`dbee7bc04481247487efd921a89b57e1fa40933e`; base `main`
`2f2486a5021465842ada8e5cc3d43e9a030e6955` unchanged. Final HEAD recorded in the
return receipt after push.

**Work left undone / next authority:** Fresh independent T3 auth-security
full-diff review of the final live transport implementation. No paid call is
permitted before that review is accepted.

**Disposition:** `LIVE_RESPONSES_TRANSPORT_RETRY_COMPLETE`

*No API keys, credential fragments, or private absolute paths recorded.*

---

## German Canary v3 semantic review repair — zero-spend

**Verdict:** The v3 canary was technically successful (50/50 bulk results, 19/19
QA results, zero provider rejects, ambiguous outcomes, or duplicates; historical
spend USD 0.0414368) but the independent semantic review was **BLOCKED**. This
repair changes only German generation/QA quality. No credential was read, no
provider call was made, and no paid work occurred.

### Blocking evidence and repair

- `ertrinket`: the source `second-person plural subjunctive I of ertrinken` was
  weakened to `ihr würdet ertrinken`. Generation and QA now require the exact
  source-supplied grammatical labels; `2. Person Plural Konjunktiv I von
  „ertrinken“` is the required shape and a würde-form is rejected.
- `Arisierungen`: a plural-only source was expanded with an unsupported history
  gloss. Morphology-only sources now require morphology-only definitions;
  colon-led lexical elaboration is deterministically rejected, and the prompt
  and QA prohibit base-lemma meaning expansion without same-context evidence.
- `Mod`: a terse `mod` source was narrowed to a game context. The source-fidelity
  contract forbids unprovided domain detail, with deterministic checks for
  unsupported game and historical-domain cues.
- `sinfonisch`: `orchesterähnlich` was accepted as a synonym despite being only
  related. `kind=synonym` now requires exact equivalence; related-form outputs
  are rejected and QA must choose `definition` where equivalence is unavailable.

The prompt makes source fidelity override stylistic naturalness and forbids
historical, encyclopedic, technical, domain, cultural, usage, or lexical detail
not entailed by the supplied English source rows. Terra QA independently checks
support, unsupported additions, every morphology feature, synonym equivalence,
and mood/tense/person/case/gender/number/degree drift. All detected morphology
DE items are routed to QA in addition to the deterministic audit sample.

Deterministic morphology checks cover Konjunktiv I/II, indicative, imperative,
present, preterite, perfect, first/second/third person, singular/plural,
nominative/accusative/dative/genitive, masculine/feminine/neuter/all-gender,
comparative/superlative, and strong/weak/mixed. The source-fidelity contract
changed, so `stage04-bulk-v4` / `stage04-qa-v4` invalidate prior checkpoints;
the checkpoint format and live transport, ledger, retry, endpoint, and cap
mechanics are unchanged.

### Regressions and replacement artifacts

- Regression coverage includes Konjunktiv-I preservation/no würde drift,
  unsupported plural elaboration, terse-source domain grounding, exact-synonym
  enforcement, and combined strong/mixed, case, gender, number, and degree
  preservation. QA prompt coverage asserts its independent source-fidelity
  questions.
- Frozen selection unchanged: `1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475`
  (50 items).
- Historical request authorization
  `5e2f6f92a72e83c3a14e61d78380fbcf5e76233e9133381440de4724ca731f7b`
  is **INVALIDATED BY REQUEST-BODY CHANGE**.
- New deterministic request artifact SHA:
  `185d2a592ef9e391008622b88adcb14a13d81dd615978f3c518925eae1d8f3d5`
  (144714 bytes).
- New deterministic Batch-equivalence SHA:
  `ca9fdc66a5924609cb16eea0385eba6ab223c2046b88af1209282170b60cf2a2`
  (143914 bytes); all 50 embedded logical bodies equal their synchronous forms.
- Local `tiktoken` remeasurement of the repaired bodies produced 33646 bulk and
  31096 QA-bound input tokens. A new cost-plan artifact and explicit owner
  authorization are therefore required before any provider execution.

**Provider calls:** 0. **Paid spend in this repair session:** USD 0.

**Next authority:** Freeze the repaired 50-item request, obtain explicit owner
authorization for its new request SHA and a matching new cost-plan SHA, then
rerun the same 50-item German canary once.

---

## German Canary v4 validator false-positive repair + checkpoint reconciliation — zero-spend

**Verdict:** German Canary v4 stopped correctly and safely on provider call 9,
exactly as designed: bulk unit `queue:v2:198fbee5ba3f6dafe7ccaf247bee1337`
(lemma `hochverräterische`, sense `strong nominative/accusative plural`)
returned candidate `starke Nominativ- oder Akkusativ-Pluralform` and the
deterministic validator rejected it as `morphology_missing_plural` before
requesting unit 10. Independent inspection confirmed this was a validator
false positive, not a model or source-data defect: `Pluralform` ("plural
form") is a legitimate bounded German noun compound that expresses the
supplied `plural` feature exactly as `Plural` alone does; `_MORPHOLOGY_FEATURE_RULES`'
output pattern for `plural` was the bare-word `\bplural\b`, which cannot match
inside the single token `Pluralform` because there is no word boundary
between `l` and `f`. The same defect applied symmetrically to `singular` vs.
`Singularform`.

### Repair

`tools/build_dict.py` — `_MORPHOLOGY_FEATURE_RULES`: the `singular` and
`plural` output patterns now accept the closed, explicit compound suffix set
`form`/`formen` in addition to the bare word:

- `plural`: `\bplural\b` → `\bplural(?:form(?:en)?)?\b`
- `singular`: `\bsingular\b` → `\bsingular(?:form(?:en)?)?\b`

This is a bounded vocabulary extension, not a generic substring match: an
unrelated word that merely contains `plural`/`singular` as a character
sequence (e.g. `Pluralismus`) still does not satisfy the feature, because the
suffix alternation only accepts `form`/`formen` immediately after the root,
under the same `\b`-bounded word match as every other rule. No other feature
rule, and no other function, was touched. `_validate_de_semantic_contract`'s
control flow, error-code taxonomy, colon/elaboration check, würde-drift
check, synonym check, and domain-cue check are unchanged.

### Regressions (`tests/test_build_dict_stage04.py::test_morphology_plural_and_singular_form_compounds`)

- A. source `strong nominative/accusative plural`, candidate `starke
  Nominativ- oder Akkusativ-Pluralform` (the exact live-recorded candidate)
  → PASS.
- B. same source, candidate with no plural information → still
  `morphology_missing_plural`.
- C. source `singular`, candidate `Singularform` → PASS.
- D. source `plural`, unrelated candidate containing `Pluralismus` (similar
  character sequence, unrelated word) → still `morphology_missing_plural`.

All prior v4 semantic regressions (Konjunktiv-I preservation / no würde
drift, unsupported elaboration, terse-source grounding, exact-synonym rule,
combined case/gender/number/degree, strong/weak/mixed) remain passing
unmodified.

### Frozen artifacts — unchanged (verified, not merely asserted)

The fix touches only `_MORPHOLOGY_FEATURE_RULES`, which is read solely by
`_morphology_feature_keys`/`_validate_de_semantic_contract` (accept-time
validation); it is not read by request-body, Batch-manifest, canary-selection,
or cost-plan generation. Reverified by re-hashing the on-disk frozen v4
artifacts after the code change:

- `SELECTION_SHA` `1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475` — unchanged (selection artifact untouched by this repair).
- `REQUEST_SHA` `185d2a592ef9e391008622b88adcb14a13d81dd615978f3c518925eae1d8f3d5` — re-hashed `de-canary-requests-v4.jsonl` (144714 bytes) — **MATCH**.
- `BATCH_SHA` `ca9fdc66a5924609cb16eea0385eba6ab223c2046b88af1209282170b60cf2a2` — re-hashed `de-canary-batch-manifest-v4.jsonl` (143914 bytes) — **MATCH**.
- `COST_PLAN_SHA` `e716609c93cf9e8e1d60307132486aac65eb869a247670614ab7a61863269a81`, `COST_PLAN_BYTES` `5800` — re-hashed `live-cost-plan-v4.json` — **MATCH**.

The Stage-04 v4 pipeline version (`stage04-bulk-v4` / `stage04-qa-v4`) was
**not** bumped: the intended v4 semantic contract is unchanged, only its
implementation defect is corrected.

### Checkpoint reconciliation (local only — zero provider calls)

Read the existing v4 checkpoint
(`~/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/checkpoint.json`) as
durable evidence, not the pasted receipt. Confirmed directly from the
checkpoint and its paired `live-subset-queue.json`: exact candidate text
`starke Nominativ- oder Akkusativ-Pluralform`, language `de`, source sense
text `strong nominative/accusative plural` for lemma `hochverräterische`,
associated spend-ledger entry (`response_id`
`resp_0aae34153b92ae55006a8ac2f7bdcc87d1b70b1945e78fdf21` for item 9,
`charge_usd 0.000159`, `cumulative_usd 0.0014308`, `accounting ACTUAL`), 9
total ledger entries, `bulk.in_flight == []`, and
rejection code `morphology_missing_plural`. The rejected-evidence record does
not persist `kind`, but the recorded error code deterministically implies
`kind == "definition"`: `_validate_de_semantic_contract` only reaches a
`morphology_missing_*` code when `kind == "definition"` (any other kind
short-circuits to `morphology_requires_definition` first) — this is derived
from the validator's own control flow, not fabricated.

Ran the fixed deterministic validator against the exact recorded candidate:
`VALIDATOR_RESULT: PASS`.

Reconciled the checkpoint locally with a one-off script built on the
project's own checkpoint facilities (`_load_checkpoint`, `_write_checkpoint`,
`_checkpoint_identity`, `_validate_de_semantic_contract`) — no ad-hoc text
replacement, no provider transport imported. Moved
`queue:v2:198fbee5ba3f6dafe7ccaf247bee1337` from `bulk.rejected` to
`bulk.completed` using the exact already-returned candidate text, in the
standard accepted-result shape: `{"text": "starke Nominativ- oder
Akkusativ-Pluralform", "language": "de", "kind": "definition", "source":
"llm_generated_v1", "license": "CC BY-SA"}`. No candidate was fabricated. The
other eight completed records, the spend ledger (9 entries, unchanged), the
manifests, and the checkpoint identity were verified byte-identical
before/after against a pre-reconciliation backup copy.

### Reload verification (fresh disk load, in-memory state discarded)

- checkpoint format `flashcard-stage04-checkpoint-v3`, identity valid — PASS.
- `bulk.completed == 9`, `bulk.rejected == 0`, `bulk.in_flight == []`.
- ledger: exactly 9 entries, all `accounting: ACTUAL`; running-sum chain
  valid; cumulative spend `USD 0.0014308` (unchanged from the paid receipt).
- `WORST_CASE_RESERVED == 0`.
- `queue:v2:198fbee5ba3f6dafe7ccaf247bee1337` appears exactly once, in
  `bulk.completed`, and zero times in `bulk.rejected`.
- QA state untouched/not advanced (`required/completed/rejected/in_flight`
  all empty, as before).
- item was **not** retransmitted; **zero** provider calls occurred during
  this repair; **USD 0** paid spend during this repair.

### Executable evidence

- `pytest -q tests/test_build_dict_stage04.py` — **94 passed**.
- `pytest -q tests/test_build_dict_stage03.py` — **16 passed**.
- `git diff --check` — PASS.
- `make gate` — Ruff PASS; mypy --strict PASS (18 source files); pytest
  **337 passed**; `check_agents.py` R1/R3/R7 PASS.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`. Local checkpoint file
(`~/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/checkpoint.json`,
outside the repository) reconciled in place; not a tracked/pushed artifact.

**Provider calls during repair:** 0. **Paid spend during repair:** USD 0.
**Historical v4 spend remains:** USD 0.0014308 (unchanged, 9/9 accounted).

**Disposition:** `GERMAN_CANARY_V4_VALIDATOR_RECONCILED` — checkpoint now
reads 9 completed / 0 rejected / 0 in-flight. The same authorized German
Canary v4 may resume from this reconciled checkpoint without resending the
first nine provider requests. This repair authorizes no further paid work by
itself; resuming the canary remains a separate owner/orchestrator decision.

---

## German Canary v4 comprehensive morphology recognizer repair — zero-spend

**Verdict:** The owner-authorized live resume of German Canary v4 correctly
transmitted 14 new bulk requests (completing 13, bringing `bulk.completed`
from 9 to 22) and then stopped fail-closed on provider call 23 exactly as
designed, before any further paid work: bulk unit
`queue:v2:45bd0bd1611b6a1f2df543fb0107a7c1` (lemma `grosser`, sense `strong
genitive/dative feminine singular`) returned candidate `starke Genitiv- und
Dativform Feminin Singular von` and was rejected `morphology_missing_dative`.
Independent inspection confirmed this was the **same recognizer defect
class** as the `Pluralform` false positive, now recurring on `Dativform`:
`_MORPHOLOGY_FEATURE_RULES`'s output pattern for `dative` was the bare-word
`\bdativ\b`, which cannot match inside the single token `Dativform` (no word
boundary between `v` and `f`). The prior repair fixed only `plural`/
`singular`; this repair audits and repairs the whole recognizer family.

### Comprehensive audit and fix

`tools/build_dict.py` — `_MORPHOLOGY_FEATURE_RULES`: introduced two shared,
documented suffix constants and spliced them into every affected rule,
rather than special-casing pairs of features one at a time:

- `_DE_FORM_SUFFIX = r"(?:form(?:en)?)?"` — a closed, solid-compound suffix
  (no separator) appended directly after a bare stem: `nominative`,
  `accusative`, `dative`, `genitive`, `singular`, `plural`, `indicative`,
  `imperative`, `present`, `preterite`, `perfect`.
- `_DE_FORM_SUFFIX_HYPHENATED = r"(?:[\s-]*form(?:en)?)?"` — the same closed
  suffix, but tolerating a hyphen or space before it (and, for
  `subjunctive_i`/`subjunctive_ii`, also between `Konjunktiv` and the
  roman-numeral/word), for the constructions `Konjunktiv-I-Form`,
  `Konjunktiv-II-Form`, and the ordinal person labels `1.-Person-Form`,
  `2.-Person-Form`, `3.-Person-Form`.
- `masculine`/`feminine` gained `form(?:en)?` as an additional alternative
  inside their existing case-ending alternation (`Maskulinform`,
  `Femininform`); `neuter` gained it on its `um` branch only
  (`Neutrumform`, not a fabricated `Neutralform`).
- `comparative`/`superlative` needed **no code change**: their existing
  `\bkomparativ\w*\b`/`\bsuperlativ\w*\b` patterns already accept any
  trailing word characters, so `Komparativform`/`Superlativform` already
  passed; this was confirmed by test, not assumed.
- `all_gender`, and the `strong`/`weak`/`mixed` declension-ending patterns,
  were left unchanged — they are not solid noun compounds of this kind and
  were not implicated by either false positive.

Every new/changed pattern keeps the same bounded-vocabulary guarantee as the
original `plural`/`singular` fix: the only text accepted immediately after a
stem is nothing, or the fixed literal suffix (`form`/`formen`, optionally
separated for the hyphenated set). An unrelated word that merely starts with
the same character sequence — `Dativobjekt`, `Genitivus`, `Pluralismus`,
`Nominativsatz` — still does not match, because the boundary/optional-suffix
composition forces an exact stop after the stem or after the closed suffix,
never a partial one. Verified explicitly for the Konjunktiv-I/II case: the
`subjunctive_i` pattern does not match `Konjunktiv-II-Form` and vice versa.

### Systematic truth-table regressions

`tests/test_build_dict_stage04.py`:

- `test_morphology_dative_form_compound_and_grosser_regression` — the exact
  live-recorded `grosser`/`Dativform` candidate now passes; `Dativform`/
  `Dativformen` pass; `Dativobjekt` still fails `morphology_missing_dative`.
- `test_morphology_feature_recognizer_truth_table` — a parametrized table of
  61 cases across every feature family (case, number, mood/tense including
  hyphenated Konjunktiv-I/II, degree, gender, person including hyphenated
  ordinal-person forms), each asserting bare-stem PASS, `...form`/`...formen`
  PASS where legitimate, cross-feature non-match (a Konjunktiv-I pattern
  never matches a Konjunktiv-II compound and vice versa), and an unrelated
  lookalike word (`Nominativsatz`, `Dativobjekt`, `Genitivus`, `Pluralismus`)
  still rejected.

All prior v4 regressions (Konjunktiv-I preservation/no würde drift,
unsupported elaboration, terse-source grounding, exact-synonym rule, the
original combined case/gender/number/degree test, strong/weak/mixed, and the
first `Pluralform`/`Singularform` regression) remain passing unmodified.
`pytest -q tests/test_build_dict_stage04.py` — **151 passed** (94 + this
repair's additions).

### Dry-revalidation against already-paid evidence (zero-spend, no provider calls)

Ran the fixed validator against every locally available already-paid v4/v3
candidate before touching the checkpoint:

- All 22 currently `bulk.completed` v4 candidates: **0 newly invalidated.**
- The 1 currently `bulk.rejected` v4 candidate (`grosser`): **now passes.**
- All 50 completed v3 canary candidates (`slice-6-de-canary-v3/checkpoint.json`,
  same frozen 50-item selection/queue, prior `stage04-bulk-v3` prompt): 3
  rejections are the already-documented, intentional v3→v4 semantic-fidelity
  tightening (`Arisierungen` unsupported elaboration, `sinfonisch`
  related-not-synonym, `Mod` domain elaboration — unchanged by this repair).
  18 more are `morphology_missing_*`/`morphology_requires_definition`
  rejections; each was individually reviewed and found to be a **genuine**
  rejection under the v4 exact-technical-label contract — a paraphrase
  instead of the required label (`Mehrzahl` instead of `Plural`,
  `Steigerungsform` instead of `Komparativ`/`Superlativ`, `männliche`/
  `sächliche` instead of `Maskulin`/`Neutrum`, a pronoun (`sie`/`wir`)
  instead of an explicit person label), a genuinely absent required feature,
  or an outright wrong grammatical form (`Partizip II` returned where the
  source required `preterite`). **None** of the 18 are instances of the
  closed-compound/word-boundary defect class this repair targets, so no
  further code change follows from this evidence. Latent false positives
  found beyond the already-known `Dativform` case: **none.**

Per instruction, no semantic rule was loosened to make any of those 18
genuinely-nonconforming v3 candidates pass; only the recognizer's
compound-form vocabulary was widened.

### Frozen artifacts — unchanged (re-verified, not merely asserted)

`_MORPHOLOGY_FEATURE_RULES` is read solely by
`_morphology_feature_keys`/`_validate_de_semantic_contract` — never by
request-body, Batch-manifest, canary-selection, or cost-plan generation.
Re-hashed the on-disk frozen artifacts after the code change:

- `SELECTION_SHA` `1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475` (`de-canary-selection-v2.json`, 40385 bytes) — **MATCH**.
- `REQUEST_SHA` `185d2a592ef9e391008622b88adcb14a13d81dd615978f3c518925eae1d8f3d5` (`de-canary-requests-v4.jsonl`, 144714 bytes) — **MATCH**.
- `BATCH_SHA` `ca9fdc66a5924609cb16eea0385eba6ab223c2046b88af1209282170b60cf2a2` (`de-canary-batch-manifest-v4.jsonl`, 143914 bytes) — **MATCH**.
- `COST_PLAN_SHA` `e716609c93cf9e8e1d60307132486aac65eb869a247670614ab7a61863269a81` (`live-cost-plan-v4.json`, 5800 bytes) — **MATCH**.

Stage-04 v4 pipeline version (`stage04-bulk-v4`/`stage04-qa-v4`) **not**
bumped — the intended contract is unchanged, only its implementation.

### Checkpoint reconciliation (local only — zero provider calls)

Read the live checkpoint as durable evidence, not the pasted receipt.
Confirmed directly: exact candidate text `starke Genitiv- und Dativform
Feminin Singular von`, language `de`, source `strong genitive/dative
feminine singular` for lemma `grosser`, associated spend-ledger entry
(`response_id resp_06185e706afe9b91006a8ac82befb087d1a8da40f50d777971`,
`charge_usd 0.000166`, `cumulative_usd 0.0036922`, `accounting ACTUAL`), 23
total ledger entries (all `ACTUAL`), `bulk.in_flight == []`. `kind` is not
persisted in rejected-evidence, but is deterministically `"definition"` from
the recorded `morphology_missing_dative` code (same control-flow argument as
item 9's reconciliation).

Ran the fixed validator against the exact recorded candidate:
`VALIDATOR_RESULT: PASS`.

Reconciled the checkpoint with a one-off script on the project's own
`_load_checkpoint`/`_write_checkpoint` facilities — no ad-hoc text
replacement, no provider transport imported. Moved
`queue:v2:45bd0bd1611b6a1f2df543fb0107a7c1` from `bulk.rejected` to
`bulk.completed` using the exact already-returned text, in the standard
shape (`kind: "definition"`, `source: "llm_generated_v1"`,
`license: "CC BY-SA"`). No candidate was fabricated. The other 22 completed
records, the 23-entry spend ledger, manifests, and checkpoint identity were
verified byte-identical before/after against a pre-reconciliation backup.

### Reload verification (fresh disk load)

- `bulk.completed == 23`, `bulk.rejected == 0`, `bulk.in_flight == []`.
- ledger: exactly 23 entries, all `ACTUAL`; running-sum chain valid;
  cumulative spend `USD 0.0036922` (unchanged from the paid receipt).
- `queue:v2:45bd0bd1611b6a1f2df543fb0107a7c1` appears exactly once, in
  `bulk.completed`.
- QA state untouched/not advanced.
- item was **not** retransmitted; **zero** provider calls, **USD 0** paid
  spend during this repair.

### Executable evidence

- `pytest -q tests/test_build_dict_stage04.py` — **151 passed**.
- `pytest -q tests/test_build_dict_stage03.py` — **16 passed**.
- `git diff --check` — PASS.
- `make gate` — Ruff PASS; mypy --strict PASS (18 source files); pytest
  **394 passed**; `check_agents.py` R1/R3/R7 PASS.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`. Local checkpoint file (outside the repository)
reconciled in place; not a tracked/pushed artifact.

**Provider calls during repair:** 0. **Paid spend during repair:** USD 0.
**Historical v4 spend remains:** USD 0.0036922 (unchanged, 23/23 accounted,
27 items remain pending toward the frozen 50).

**Disposition:** `GERMAN_CANARY_V4_MORPHOLOGY_RECOGNIZER_RECONCILED` —
checkpoint now reads 23 completed / 0 rejected / 0 in-flight. The same
authorized German Canary v4 may resume from this reconciled checkpoint
without resending the first 23 provider requests. This repair authorizes no
further paid work by itself; resuming remains a separate owner/orchestrator
decision.

## German Canary v4 morphology QA-recovery repair — zero-spend

**Status:** local repair + checkpoint reconciliation only. No provider
credential was read, no provider request was made, no candidate text was
retransmitted. The live canary had continued past the prior repair (23 → 41
completed) since the last report entry and stopped again at a 42nd paid
request; that call is reconciled here.

### Call 42 — genuine comparative precision failure

`queue:v2:ca9a4c04e83f08678564370d2b52d3cf`, lemma
`nordrhein-westfälischer`, source `comparative degree of
nordrhein-westfälisch`. Luna returned `Steigerungsform von
„nordrhein-westfälisch“` (kind `definition`); the bulk validator correctly
rejected it as `morphology_missing_comparative`. `Steigerungsform`
("form of increase/degree") is broader than `Komparativ` and can cover
either comparative or superlative — it is not a valid label for a source
that specifically requires the comparative degree. **This remains invalid.
The comparative validator was NOT widened**, and `Steigerungsform` still
does not satisfy the `comparative` feature after this repair — reverified
directly: `_validate_de_semantic_contract` on the exact recorded candidate
still returns `morphology_missing_comparative`; only
`Komparativform von „nordrhein-westfälisch“` (and other genuine
`\bkomparativ\w*\b` realizations) passes.

### The actual defect: no route from a genuine bulk semantic gap to QA

The bulk hard-stop treated every `_validate_de_semantic_contract` failure —
including a source-verifiable, structurally clean `morphology_*` gap — as an
unrecoverable rejection, with no path to the already-designed Terra QA
correction stage. A genuine precision miss on a paid, well-formed response
had no mechanism to be corrected; it could only halt the run.

### Repair: route `morphology_*` bulk gaps through mandatory QA, nothing else

`tools/build_dict.py`:

- Added `_is_morphology_qa_recoverable(item, language, generic_err,
  semantic_err)`: returns true only when language is `de`, the item carries
  at least one source-supplied morphology feature
  (`_morphology_feature_keys`), the candidate passed generic
  structural/schema validation (`generic_err is None`), and the sole
  remaining failure is a `morphology_*` semantic-contract code. Any
  transport/envelope/schema failure, or a non-morphology semantic failure,
  is unaffected and still hard-rejects exactly as before — this function
  only reclassifies where an existing failure routes, it never changes
  what `_validate_de_semantic_contract` or `_validate_generated_candidate`
  accept.
- In the bulk DE/EN candidate loop: `generic_err` and `semantic_err` are now
  computed and inspected separately. When `_is_morphology_qa_recoverable`
  is true, the failure is not recorded in `rejected_to_record` (so it no
  longer trips the "STOP before next unit" hard-stop); instead the exact,
  unmodified Luna candidate is written to `valid_to_complete` with an added
  `qa_required_reason` field carrying the precise `morphology_*` code.
  Every other failure path is byte-for-byte unchanged.
- QA-required-set computation: a completed item carrying
  `qa_required_reason` is now also explicitly unioned into the flagged set
  (in addition to the existing length/`flag`/DE-morphology-source checks,
  which already covered every provisional item by construction — this is a
  belt-and-suspenders invariant, not new coverage). A provisional item can
  never fall out of QA routing.
- QA itself: **unchanged**. `de_learner_qa_request_body`,
  `_validate_de_semantic_contract`, and the QA candidate loop still apply
  the same strict validator with no recovery path — `Steigerungsform`
  submitted again at QA still rejects and still stops the run.
- Finalization guard: before `output.sqlite` is created, every
  `bulk.completed` entry carrying `qa_required_reason` must be in
  `qa.required`, in `qa.completed`, and not in `qa.rejected`, or
  `build_stage04` raises and creates no output. This closes the fallback
  that previously (silently, for any future provisional item) would have
  used the unvalidated bulk text whenever `qa.completed` lacked an entry —
  QA-completed text still supersedes bulk text exactly as before; this only
  removes the silent fallback for text QA has not actually passed.

### Regression tests (`tests/test_build_dict_stage04.py`, 8 new)

1. `test_morphology_comparative_gap_is_provisional_not_hard_rejection` — the
   exact call-42 candidate: provisional, `qa_required_reason =
   morphology_missing_comparative`, forced into `qa.required`, no output
   created.
2. `test_morphology_qa_correction_reaches_final_output` — QA returns
   `Komparativform von „nordrhein-westfälisch“`: QA passes, and
   `sense_meaning.text` in the finalized `output.sqlite` is exactly that
   corrected text.
3. `test_morphology_qa_noncorrection_stops_before_finalization` — QA
   resubmits the uncorrected `Steigerungsform` text: QA rejects, the run
   stops, `output.sqlite` is never created.
4. `test_finalization_guard_blocks_resumed_output_after_qa_rejection` — a
   second `build_stage04` call against the checkpoint left by test 3 (no
   pending bulk or QA work remains for the item) still refuses to
   finalize, proving the guard — not just the in-run QA rejection — is what
   blocks the provisional text from ever reaching output on a resume.
5. `test_morphology_subjunctive_i_drift_is_provisional` — source
   `second-person plural subjunctive I of ertrinken`, candidate `ihr
   würdet ertrinken`: provisional, `qa_required_reason =
   morphology_missing_subjunctive_i`, forced QA.
6. `test_morphology_unsupported_elaboration_is_provisional` — source
   `plural of Arisierung`, candidate `Plural von „Arisierung“: erzwungene
   Übertragung jüdischen Eigentums`: provisional, `qa_required_reason =
   morphology_unsupported_elaboration`, forced QA.
7. `test_structural_failure_on_morphology_item_remains_hard_rejection` — a
   morphology item whose candidate echoes the lemma (`echo_lemma`, a
   generic/structural failure, not a semantic-contract one) still
   hard-rejects; never swept into recovery.
8. `test_non_morphology_semantic_failure_remains_hard_rejection` — a source
   with no morphology feature at all (`mod`) whose candidate trips
   `unsupported_domain_elaboration` still hard-rejects; recovery can never
   apply without a source-supplied morphology feature.

All pre-existing DE semantic-contract/morphology-recognizer tests pass
unmodified. `pytest -q tests/test_build_dict_stage04.py` — **159 passed**
(151 + this repair's 8 additions).

### Dry-revalidation of the 41 pre-existing v4 completions (zero-spend)

Reconstructed each item's source and lemma from the frozen, hash-verified
`tmp/de-canary-v4/de-canary-requests-v4.jsonl` and re-ran the exact
production validators (`_validate_generated_candidate`,
`_validate_de_semantic_contract`, `_morphology_feature_keys`) against every
one of the 41 `bulk.completed` texts already recorded in the live
checkpoint:

- Total completions: **41**.
- Ordinary (no source-supplied morphology feature): **18**.
- Morphology completions: **23**.
- Candidates that would newly qualify as provisional under the new policy:
  **0**. Every one of the 41 already passes the complete, unchanged
  semantic validator outright — provisional status only ever applies to a
  failure, and none of these 41 is one. No provisional defect was invented
  for a candidate that already passes.

### Frozen artifacts — re-verified unchanged

- `SELECTION_SHA` `1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475` (`tmp/de-canary-v2/de-canary-selection-v2.json`) — **MATCH**.
- `REQUEST_SHA` `185d2a592ef9e391008622b88adcb14a13d81dd615978f3c518925eae1d8f3d5` (`tmp/de-canary-v4/de-canary-requests-v4.jsonl`) — **MATCH**.
- `BATCH_SHA` `ca9fdc66a5924609cb16eea0385eba6ab223c2046b88af1209282170b60cf2a2` (`tmp/de-canary-v4/de-canary-batch-manifest-v4.jsonl`) — **MATCH**.
- `COST_PLAN_SHA` `e716609c93cf9e8e1d60307132486aac65eb869a247670614ab7a61863269a81` (`tmp/de-canary-v4/live-cost-plan-v4.json`) — **MATCH**.

No prompt (Luna or Terra), request body, schema, model, reasoning setting,
`max_output_tokens`, selection, cost plan, endpoint, price, cap, transport,
or retry policy was touched. Stage-04 v4 pipeline version
(`stage04-bulk-v4`/`stage04-qa-v4`) not bumped — the contract is unchanged,
only its implementation.

### Checkpoint reconciliation (local only — zero provider calls)

Read the live checkpoint as durable evidence. Confirmed directly: exact
candidate text `Steigerungsform von „nordrhein-westfälisch“`, language `de`,
kind `definition` (deterministic from the `morphology_missing_comparative`
control flow — that code is reachable only for `kind == "definition"`), for
item `queue:v2:ca9a4c04e83f08678564370d2b52d3cf`; associated spend-ledger
entry (`response_id
resp_06d7c01ec225bcc7006a8acd79917087d1af5ee8126aaf314c`, `charge_usd
0.0001612`, `cumulative_usd 0.0068046`, `accounting ACTUAL`) present exactly
once; 42 total ledger entries, all `ACTUAL`; `bulk.in_flight == []`.
Independently re-ran `_validate_generated_candidate` (PASS) and
`_validate_de_semantic_contract` (`morphology_missing_comparative`, matching
the recorded rejection exactly) against the exact recorded candidate and the
item's reconstructed source before touching anything.

Reconciled with a one-off script built on the project's own
`_load_checkpoint`/`_write_checkpoint` facilities — no ad-hoc text
replacement, no provider transport imported. Moved
`queue:v2:ca9a4c04e83f08678564370d2b52d3cf` from `bulk.rejected` to
`bulk.completed` using the exact already-returned text, with
`qa_required_reason: morphology_missing_comparative` added. No candidate
was fabricated or altered. The other 41 completed records, the identity
block, manifests, and the 42-entry spend ledger were verified byte-identical
before/after against a pre-reconciliation backup (removed after
verification).

### Reload verification (fresh disk load)

- `bulk.completed == 42`, `bulk.rejected == 0`, `bulk.in_flight == []`.
- `qa.required == []`, `qa.completed == {}`, `qa.rejected == {}`,
  `qa.in_flight == []` — QA remains unexecuted, as required (this repair
  authorizes no QA transmission).
- Ledger: exactly 42 entries, all `ACTUAL`; cumulative spend `USD
  0.0068046` (unchanged from the paid receipt).
- `queue:v2:ca9a4c04e83f08678564370d2b52d3cf` appears exactly once, in
  `bulk.completed`, carrying `qa_required_reason:
  morphology_missing_comparative`.
- Item was **not** retransmitted; **zero** provider calls, **USD 0** paid
  spend during this repair.

### Executable evidence

- `pytest -q tests/test_build_dict_stage04.py` — **159 passed**.
- `pytest -q tests/test_build_dict_stage03.py` — **16 passed**.
- `git diff --check` — PASS.
- `make gate` — Ruff PASS; mypy --strict PASS (18 source files); pytest
  **402 passed**; `check_agents.py` R1/R3/R7 PASS.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`. Local checkpoint file (outside the repository)
reconciled in place; not a tracked/pushed artifact.

**Provider calls during repair:** 0. **Paid spend during repair:** USD 0.
**Historical v4 spend remains:** USD 0.0068046 (unchanged, 42/42
accounted, 8 items remain pending toward the frozen 50).

**Disposition:** `GERMAN_CANARY_V4_QA_RECOVERY_RECONCILED` — checkpoint now
reads 42 bulk completed (1 provisional, `qa_required_reason
morphology_missing_comparative`) / 0 rejected / 0 in-flight; QA required set
not yet computed/executed. The same authorized German Canary v4 may resume
from this reconciled checkpoint without resending the first 42 provider
requests. Item 42 must receive a successful Terra QA pass before its text
can become final; this repair authorizes no further paid work by itself,
and resuming — bulk or QA — remains a separate owner/orchestrator decision.

## German Canary v4 past-participle source-classifier repair — zero-spend

**Status:** local repair + checkpoint reconciliation only. No provider
credential was read, no provider request was made, no candidate text was
retransmitted.

### Live resume 3 (out of band — real paid execution, not part of this repair)

Since the prior report entry, the live v4 canary was resumed to completion of
bulk (42 → 50) plus the deterministic 36-item QA set: 8 new bulk calls + 34
QA calls, 42 new provider calls, real paid spend, all real. That run stopped
fail-closed on 1 QA rejection with 2 QA items never attempted (no cost). This
repair is entirely local reconciliation of that already-paid state — it does
not touch, retry, or extend that execution.

### Rejected QA response — a second deterministic validator false positive

`queue:v2:efc8334ad5993e20c3b5e1298ef46dc9`, lemma `vorbereitet`, source
`past participle of vorbereiten`. Both Luna (bulk) and Terra (QA)
independently returned `Partizip II von „vorbereiten“` (kind `definition`) —
semantically correct: `Partizip II` / `Partizip Perfekt` is exactly the
German term for "past participle". The validator rejected it twice as
`morphology_missing_preterite`. **Confirmed root cause:** the `preterite`
source rule's `\bpreterite\b|\bpast\b` pattern matched the literal word
`past` inside the two-word phrase `past participle` — a distinct,
non-finite verb form, not the preterite/simple-past tense — and wrongly
demanded `Präteritum` in the output.

### Root-cause repair — source-side only, output validation NOT weakened

`tools/build_dict.py`, `_MORPHOLOGY_FEATURE_RULES`:

- Added two new, independent features: `past_participle` (source
  `\b(?:past|perfect)\s+participles?\b`, output
  `\bpartizip[\s-]*(?:ii|2|perfekt){FORM_SUFFIX}\b` — accepts `Partizip II`,
  `Partizip 2`, `Partizip II-Form`, `Partizip-II-Form`, `Partizip Perfekt`)
  and `present_participle` (source `\bpresent\s+participles?\b`, output
  `\bpartizip[\s-]*(?:i|1|präsens){FORM_SUFFIX}\b` — accepts `Partizip I`,
  `Partizip 1`, `Partizip Präsens`). The `ii`/`i` alternation is the same
  bounded technique already used for Konjunktiv-I/II: `Partizip I` cannot
  satisfy the `past_participle` pattern and `Partizip II` cannot satisfy
  `present_participle`, verified by test.
- The `present`, `preterite`, and `perfect` source rules each gained a
  negative lookahead — `\bpresent\b(?!\s+participles?)`,
  `\bpreterite\b|\bsimple\s+past\b|\bpast\b(?!\s+participles?)`,
  `\bperfect\b(?!\s+participles?)` — so a source phrase already claimed by a
  participle feature can never *also* trigger the unrelated tense feature
  (which would otherwise demand two contradictory German labels from one
  candidate). A bare, non-participle `past` remains valid preterite evidence
  exactly as before — confirmed live in the accepted queue (`past of
  singen`) — nothing was deleted, only the participle collision excluded.
- Output-side patterns for `present`/`preterite`/`perfect` are **unchanged**.
  This is a source-classification repair only; `_validate_de_semantic_
  contract`'s acceptance criteria for existing features were not touched, and
  `Partizip II` still does not satisfy `preterite`, `Präteritum` still does
  not satisfy `past_participle` — reverified directly by test.

### Source-feature collision audit (offline, zero-spend)

Scanned all 577,141 DE `derivation_inputs` rows in the accepted, hash-verified
Stage-03 queue (`/tmp/flashcard-stage03-v2.json`, SHA
`114dd20f1e071708ca43ff433284ce1be0e9662763db5a589930a8f5a045cf2a`, matching
`authorized_queue_sha256`) for the phrase families named in the audit
request:

- `past participle`: **5,777** occurrences — real, common source phrasing,
  not an edge case. Fixed (new `past_participle` feature).
- `present participle`: **5,629** occurrences — the same collision class on
  the `present` rule. Fixed (new `present_participle` feature). One of the
  50 frozen canary items uses this exact phrasing
  (`queue:v2:4a6c8cb9...`, lemma `alternd`) and was already QA-completed
  with text `Partizip Präsens von „altern“`, which happens to also satisfy
  the old, over-broad `present` pattern — it was never visibly rejected, but
  was misclassified; reverified to still pass under the fixed rule.
- `perfect participle`: **569** occurrences, essentially all of the form
  `perfect participle of X`. This is a real, third English-grammar synonym
  for "past participle" (used in perfect-tense constructions) naming the
  identical German form — **a directly analogous latent collision on the
  `perfect` rule**, not previously reported. Fixed: `perfect participle`
  now resolves to `past_participle`, not the unrelated `perfect` tense.
  None of the 50 frozen canary items use this phrasing (confirmed by scan),
  so this was a latent defect for the current canary, not a live blocker.
- Bare, non-participle `perfect`: 33 occurrences, none of the form
  `perfect of X`; ordinary vocabulary content or composite-tense names
  (`future perfect`, `past perfect`/`pluperfect`, `conditional perfect`) that
  are themselves outside this repair's scope — **reported, not fixed**: none
  of the 50 frozen canary items use any of these phrasings (confirmed by
  scan), the existing `perfect` rule's plain-word behavior is otherwise
  unchanged, and building out a full composite-tense taxonomy
  (Plusquamperfekt/Futur II/Konditional Perfekt) is a distinct,
  unrequested scope expansion beyond the reported defect class.
- Bare, non-participle `past`: 98 occurrences, including 5 real `past of X`
  formulations (`past of singen`, `past of besingen`, `past of genießen`,
  `past of sitzen`, `past of fliegen`) — confirmed still recognized as
  `preterite` evidence after the repair (not deleted).
- `comparative`/`superlative`, `singular`/`plural`, `subjunctive I`/`II`:
  no collision — already distinct words, or (subjunctive) already protected
  by a trailing `\b` boundary that a longer suffix like `ii` cannot satisfy
  when only `i` is claimed. No change.

### Regression tests (`tests/test_build_dict_stage04.py`)

- 21 new rows added to `test_morphology_feature_recognizer_truth_table`
  covering past/present/perfect participle acceptance, the participle vs.
  bare-tense independence, and the preserved bare-`past` case.
- `test_past_participle_and_preterite_are_independent_features` — the exact
  call-42-analogous scenario: `past participle of vorbereiten` detects only
  `past_participle` (never `preterite`), `Partizip II` passes,
  `Präteritum` is rejected as `morphology_missing_past_participle`; and the
  converse for a genuine `preterite` source.
- `test_present_participle_does_not_activate_present_tense` — the exact
  `alternd` item: detects only `present_participle`; the already-accepted
  live text `Partizip Präsens von „altern“` still passes, `Partizip I` also
  passes, plain `Präsens` is rejected.
- `test_past_participle_morphology_gap_remains_qa_routed` — a genuine
  `past_participle` gap (wrong candidate) is still provisional + forced QA
  under the existing, unmodified morphology QA-recovery policy from the
  prior repair — proving the new feature composes with that policy with no
  policy change.

All prior regressions pass unmodified. `pytest -q tests/test_build_dict_stage04.py` —
**198 passed** (175 + 23 additions).

### Dry-revalidation against already-paid evidence (zero-spend)

Re-ran the fixed validators against every already-paid v4 candidate before
touching the checkpoint:

- All 50 `bulk.completed` candidates: **49/50 now pass outright**; the sole
  remaining failure is item 42 (`morphology_missing_comparative`,
  `Steigerungsform`), an unrelated, already-known, already-provisional,
  genuinely-still-invalid candidate — unaffected by this repair.
- All 34 already-transmitted QA responses (33 previously completed + the 1
  rejected response): **34/34 now pass**, including the exact recorded
  Terra text for `efc8334...` (`Partizip II von „vorbereiten“` — confirmed
  `FIXED_VALIDATOR_RESULT: PASS`) and the `alternd` present-participle item
  reconfirmed unchanged.
- No previously-accepted result became invalid under the fixed rules.

### Checkpoint reconciliation (local only — zero provider calls)

Read the live checkpoint as durable evidence. Confirmed directly: exact QA
candidate text `Partizip II von „vorbereiten“`, associated ledger entry
(`response_id resp_07f1209f58de8147006a8ad70f34c487d1a68a4479d7fea3bf`,
`charge_usd 0.001152`, `cumulative_usd 0.0692788`, `accounting ACTUAL`,
`phase qa`) present exactly once; 84 total ledger entries, all `ACTUAL`,
all unique response IDs; `qa.in_flight == []`.

Reconciled with a one-off script built on the project's own
`_load_checkpoint`/`_write_checkpoint` facilities — no ad-hoc text
replacement, no provider transport imported, no ledger entry added or
modified. Moved `queue:v2:efc8334ad5993e20c3b5e1298ef46dc9` from
`qa.rejected` to `qa.completed` using the exact already-returned Terra text,
in the standard shape (`kind: "definition"`, `source: "llm_generated_v1"`,
`license: "CC BY-SA"`). No candidate was fabricated.

Per instruction, the bulk-completed record's historical
`qa_required_reason: "morphology_missing_preterite"` marker was **retained
unchanged** rather than cleared: it is now an obsolete classification (the
item in fact never needed QA routing under the fixed rule — dry-revalidation
confirms its original bulk candidate passes outright), but the marker
remains accurate as an audit trail of *why the item was historically routed
to QA*, and does not claim that reason was semantically valid. The
finalization guard added in the prior repair only checks that a
`qa_required_reason`-carrying item is in `qa.required`/`qa.completed`/not in
`qa.rejected` — it does not interpret the reason string — so retaining the
historical marker does not block finalization once QA is (as it now is)
successfully completed. Bulk state, `qa.required`, `qa.in_flight`, identity,
manifests, and the 84-entry spend ledger were verified byte-identical
before/after against a pre-reconciliation backup (removed after
verification).

### Reload verification (fresh disk load)

- `bulk.completed == 50`, `bulk.rejected == 0`, `bulk.in_flight == []`
  (unchanged).
- `qa.required == 36`, `qa.completed == 34`, `qa.rejected == 0`,
  `qa.in_flight == []`.
- Exactly 2 QA-required items remain never-attempted:
  `queue:v2:f6582244316e30bd5a98f46d1e7a5b51`,
  `queue:v2:fcf0b3676408cbf42fec29c3547b8bcd`.
- Ledger: exactly 84 entries, all `ACTUAL`, all 84 response IDs unique;
  cumulative spend `USD 0.0692788` (byte-identical to the paid receipt).
- `queue:v2:efc8334ad5993e20c3b5e1298ef46dc9` appears exactly once, in
  `qa.completed`; no longer in `qa.rejected`.
- Item was **not** retransmitted; **zero** provider calls, **USD 0** paid
  spend during this repair.
- `output.sqlite` was **not** created (2 QA items remain unattempted; the
  finalization guard remains correctly blocking).

### Executable evidence

- `pytest -q tests/test_build_dict_stage04.py` — **198 passed**.
- `pytest -q tests/test_build_dict_stage03.py` — **16 passed**.
- `git diff --check` — PASS.
- `make gate` — Ruff PASS; mypy --strict PASS; pytest PASS;
  `check_agents.py` R1/R3/R7 PASS.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`. Local checkpoint file (outside the repository)
reconciled in place; not a tracked/pushed artifact.

**Provider calls during repair:** 0. **Paid spend during repair:** USD 0.
**Cumulative v4 spend remains:** USD 0.0692788 (unchanged; 84/84 paid calls
accounted, 2 QA requests remain pending toward the frozen 50-item/36-QA
canary).

**Disposition:** `GERMAN_CANARY_V4_PARTICIPLE_CLASSIFIER_RECONCILED` —
checkpoint now reads 50 bulk completed / 0 rejected; 36 QA required, 34
completed, 0 rejected, 2 pending. `output.sqlite` remains correctly
unfinalized. This repair authorizes no further paid work by itself; resuming
the final 2 QA requests remains a separate owner/orchestrator decision.

## German Canary v4 manual adjudication of 2 material findings — zero-spend

**Status:** local checkpoint/artifact reconciliation only. No provider
credential was read, no provider request was made, no candidate text was
retransmitted.

### Independent all-50 semantic review result

Since the prior report entry, the live v4 canary reached full technical
completion out of band (2 remaining QA calls transmitted, 50/50 bulk + 36/36
QA, `output.sqlite` finalized — real paid execution, not part of this
repair). An independent semantic review of all 50 final German meanings then
found:

**46 PASS / 2 MINOR / 2 MATERIAL.**

The 2 MINOR findings (`seinen Segen zu etwas geben`, `Think-tank`) do not
block canary acceptance and were **not** touched by this task.

### MATERIAL finding A — Marmarameer (English-source echo)

`queue:v2:3a99e45482575743acf4789f24789062`, lemma `Marmarameer` (PROPN),
source `Sea of Marmara`. Bulk/final text was `Sea of Marmara` — the English
source copied verbatim, not a German learner meaning at all.
**Owner-approved manual final:** `Marmarameer` (kind `synonym`) — the direct
German name, deliberately conservative, no invented geographical
description.

### MATERIAL finding B — Mod (unsupported domain/person narrowing)

`queue:v2:fca20836b82737bbbe7083358ad66f93`, lemma `Mod`, source `mod`.
Bulk/final text was `eine Person, die Computerspiele verändert` — inventing
both a person interpretation and a computer-game domain the single-word
source does not support. **Owner-approved manual final:** `Mod` (kind
`synonym`) — a deliberate direct lemma-equivalent fallback; no domain/sense
inferred.

The owner chose explicit manual adjudication for both findings instead of
additional paid Terra spend.

### Manual-adjudication infrastructure (`tools/build_dict.py`)

- `STAGE04_MANUAL_ADJUDICATION_SOURCE = "contributed"` — reused, not
  invented: `reference/schema.sql` and ADR-0004's `sense_meaning` DDL
  comment already document `contributed` as a third `source` value alongside
  `wiktionary` and `llm_generated_v1`, for content that is neither
  Wiktionary-sourced nor LLM-generated. A manual adjudication is never
  persisted as `llm_generated_v1` — R11's marker contract is reserved for
  rows a provider actually generated, and rollback-by-marker semantics
  depend on that meaning exactly that.
- `apply_manual_adjudication(checkpoint_path, identity, item_id, text, kind,
  reason, generated_license)` — the only way to record one. Refuses any
  item_id not already a real `bulk.completed` entry (an "unapproved
  arbitrary override" is structurally impossible, not just discouraged) and
  refuses a duplicate adjudication of the same item. Runs generic
  structural/safety validation (non-empty, valid language/kind, length
  bound, forbidden control/bidi characters) but deliberately skips the
  lemma-echo heuristic (an LLM-laziness detector that a deliberate
  owner-chosen lemma-equivalent, e.g. Marmarameer's own proper-noun name,
  would otherwise trip) and the semantic-contract heuristic (the whole point
  of this path is the owner's judgement superseding that heuristic). Never
  touches historical provider evidence: no response ID, usage record, or
  spend-ledger entry is added, removed, or modified.
- New optional `manual_adjudications` checkpoint section, structurally
  validated by `_load_checkpoint`/`_validate_manual_adjudications_state`
  (fails closed on a corrupt/mislabeled record, in particular one whose
  `source` isn't exactly `STAGE04_MANUAL_ADJUDICATION_SOURCE`) exactly like
  the existing optional `spend` section — fully backward compatible with
  every checkpoint that predates this feature.
- Finalization precedence is now explicit and total: **manual adjudication
  > successful QA > valid bulk.** The provisional-item finalization guard
  and the pending-QA-transmission check both treat a manual adjudication as
  a valid, complete resolution — a provisional item can be finalized via
  manual adjudication alone, without ever requiring (or being blocked on) a
  QA-capable transport.
- **Bug found and fixed as a byproduct:** the `sense_meaning` INSERT
  hardcoded `GENERATED_MARKER`/the run's `generated_license` parameter for
  every row's `source`/`license` columns, ignoring each completion record's
  own (already-present) `source`/`license` fields. This had been invisible
  because every historical bulk/QA completion always carried
  `source="llm_generated_v1"` anyway; it would have silently mislabeled the
  first manually-adjudicated row as `llm_generated_v1` regardless of the
  checkpoint's own `manual_adjudications` record. Fixed to read each row's
  own `source`/`license`.
- **Accepted-contract conflict found and resolved without violating it:**
  `validate_sense_meaning_derivations` (ADR-0004 D45/A8) requires the
  `generated_meaning_id` side of every `sense_meaning_derivation` edge to
  carry the versioned `llm_generated_vN` marker. A manually-adjudicated row
  cannot satisfy that (by design — it is not "generated"), so creating a
  derivation edge for it would either violate this accepted invariant or
  require weakening a general-purpose integrity checker outside this task's
  scope. Resolved conservatively: a manually-adjudicated row's provenance
  (the exact review finding, and the original Luna bulk text it supersedes)
  is recorded truthfully in the checkpoint's `manual_adjudications` section
  instead, and no derivation edge is created for it. **Consequence for the
  regenerated output:** derivation edges are **58**, not 60 — 2 fewer than
  the pre-adjudication run, exactly matching the 2 material items each
  losing their 1 EN derivation edge. This is reported, not silently
  mismatched against the earlier assumption of an unchanged count.

### Regression tests (`tests/test_build_dict_stage04.py`, 5 new)

1. `test_manual_adjudication_requires_existing_bulk_completed_item` — an
   arbitrary/unknown item_id is refused; nothing is persisted.
2. `test_manual_adjudication_overrides_bulk_and_qa_finalization` — with
   distinct bulk and QA texts, a manual adjudication wins finalization;
   the historical bulk/QA records themselves are never overwritten or
   relabeled.
3. `test_manual_adjudication_resolves_provisional_item_without_qa` — a
   morphology-provisional item is finalized via manual adjudication alone,
   with no QA-capable transport ever required.
4. `test_manual_adjudication_checkpoint_round_trip_and_validation` — the
   section round-trips through `_load_checkpoint` unchanged, and
   `_validate_manual_adjudications_state` fails closed on a wrong `source`,
   a blank `reason`, and a non-dict payload.
5. `test_manual_adjudication_second_call_rejected` — an item cannot be
   silently re-adjudicated.

All prior regressions pass unmodified. `pytest -q tests/test_build_dict_stage04.py` —
**203 passed** (198 + 5 additions). Per instruction, this task did not touch
the three separately reported generic pre-production validators (English-
source-echo detection, unsupported-domain inflected-form recognition, the
bare-`perfect` ambiguity).

### Preserved paid history (zero provider calls)

Read the live checkpoint as durable evidence before touching anything:
`bulk.completed=50`, `bulk.rejected=0`, `qa.required=36`, `qa.completed=36`,
`qa.rejected=0`, `qa.in_flight=[]`; 86 ledger entries, all `ACTUAL`, all 86
response IDs unique; cumulative spend `USD 0.0716368`. Applied both manual
adjudications with the project's own `apply_manual_adjudication`; reloaded
and verified afterward: `bulk`, `qa`, identity, manifests, and all 86 ledger
entries byte-identical before/after — the only change is the new
`manual_adjudications` section (2 entries). No response ID was added,
removed, duplicated, or changed; no usage record changed; cumulative spend
unchanged at `USD 0.0716368`.

### Archived BLOCKED artifacts (pre-adjudication)

Before regenerating, archived the independent-review BLOCKED versions
byte-identical:

- `output.semantic-blocked.sqlite` — SHA
  `e3e1bb13d087fd4db21bd31cc2381284efd8a37a4235200160ae0ddbf9bc47eb` (match).
- `review-bundle.semantic-blocked.json` — SHA
  `99ff8ec49387e939fb35f90a55a301291fbe9dc30d359fa5c05c3edc8a62c20c` (match).
- `receipt.semantic-blocked.txt` — SHA
  `f2e3a663e2e6379dd3a94673de0a394193c36aad5dd03c59278e7990c5f98679` (match).

### Regenerated final output.sqlite

Regenerated via the project's own `build_stage04` finalization path
(`transport=None`; no pending bulk or QA work remained) from the
authoritative Stage-02 asset plus the existing checkpoint plus the two
manual adjudications:

- `PRAGMA quick_check` — `ok`.
- 50 generated-class rows total: 48 `llm_generated_v1` + 2 `contributed`
  (Marmarameer, Mod).
- All 50 licenses `CC BY-SA`.
- Derivation edges: **58** (60 minus the 2 material items' edges — see
  above).
- Cross-sense derivation violations: **0**.
- Stage-02 SHA unchanged
  (`75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`).
- `output.sqlite` SHA `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`,
  945418240 bytes.

### 48-item immutability check

Compared every non-material final `(text, kind)` in the regenerated database
against the archived BLOCKED review bundle:

**UNCHANGED_FINAL_ITEMS: 48/48 PASS.**

### Regenerated review bundle and receipt

`review-bundle.json` (all 50 items; `manual_adjudicated`,
`manual_adjudication_reason`, `manual_text`, `manual_kind`, `final_source`
fields added; unambiguous ORIGINAL provider output vs. FINAL manual
adjudication for both material items) — SHA
`04b18f6f6ff729ed14638ae9e1760b1c133dabc1d63206bf1c115045b5d07e34`,
51666 bytes.

`receipt.txt` — SHA `501fe92aed15b0aefe9bf437986a5e374f7b3ffdda19939c141be5e0125e5a96`.

### Canary semantic acceptance

Marmarameer (`Sea of Marmara` → `Marmarameer`): PASS. Mod (`mod` → `Mod`):
PASS. Review classification history preserved: **46 PASS / 2 MINOR / 2
MATERIAL** before adjudication → **48 PASS / 2 MINOR / 0 MATERIAL** after.
No MATERIAL defects remain.

**`GERMAN_CANARY_V4_SEMANTIC_REVIEW: PASS_WITH_2_MINOR`**

### Pre-production hardening still required (not run in this task)

Canary semantic acceptance does **not** authorize full production. Recorded,
not repaired here:

A. Generic German-target English-source-echo detection/routing, exposed by
   Marmarameer.
B. Unsupported-domain cue recognition for inflected `Computerspiel`/
   `Videospiel` forms, exposed by Mod.
C. The previously reported bare-`perfect` source-classifier ambiguity
   (`past perfect`/`future perfect`/`conditional perfect`).

### Frozen paid identities — re-verified unchanged

`SELECTION_SHA`, `REQUEST_SHA`, `BATCH_SHA`, `COST_PLAN_SHA` all re-hashed
against their on-disk artifacts and confirmed byte-identical to the frozen
values. No prompt, request body, schema, model, reasoning setting,
`max_output_tokens`, selection, cost plan, endpoint, price, cap, transport,
or retry policy was touched.

### Executable evidence

- `pytest -q tests/test_build_dict_stage04.py` — **203 passed**.
- `pytest -q tests/test_build_dict_stage03.py` — **16 passed**.
- `git diff --check` — PASS.
- `make gate` — Ruff PASS; mypy --strict PASS (18 source files); pytest
  **430 passed**; `check_agents.py` R1/R3/R7 PASS.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`. All canary run-directory artifacts (checkpoint,
output.sqlite, review-bundle.json, receipt.txt, and the three
`*.semantic-blocked.*` archives) are outside the repository; none are
tracked or pushed.

**Provider calls during repair:** 0. **Paid spend during repair:** USD 0.
**Cumulative v4 spend remains:** USD 0.0716368 (unchanged; 86/86 paid calls
preserved and accounted).

**Disposition:** `GERMAN_CANARY_V4_MANUAL_ADJUDICATION_COMPLETE` — the
German Canary v4 canary is semantically accepted
(`PASS_WITH_2_MINOR`, 0 MATERIAL defects). Production remains unauthorized
pending the three recorded generic pre-production hardening items and a
separate full-production planning/authorization decision.

---

## German Stage-04 pre-production semantic hardening (3 generic defects) — zero-spend

**Status:** local implementation repair only. No provider credential was
read, no provider request was made, no new German canary was run or
reopened. This task repairs exactly the three generic validator/classifier
defects recorded above as "Pre-production hardening still required" —
nothing else. `OPENAI_API_KEY` was not read.

### Repository/asset verification

- `branch == slice/6`; worktree clean (tracked files; only pre-existing
  ignored paths present) — **MATCH**.
- `git fetch origin`; `HEAD == origin/slice/6 == 4f2b0359299a252aecc885844338c4854b17d451`
  — **MATCH**. `main == origin/main == 2f2486a5021465842ada8e5cc3d43e9a030e6955`
  — **MATCH**.
- `/tmp/flashcard-stage03-v2.json` SHA-256
  `114dd20f1e071708ca43ff433284ce1be0e9662763db5a589930a8f5a045cf2a`,
  334605426 bytes — **MATCH**. Read-only throughout; not modified.

### A. English-source-echo detection (`tools/build_dict.py`)

New bounded detector `_is_english_source_echo` + `_ENGLISH_ECHO_FUNCTION_WORDS`
(a small closed set: "the", "of", "a", "and", "is", etc.), wired into
`_validate_de_semantic_contract` ahead of the morphology block, returning the
deterministic code `english_source_echo`. Deliberately not a general language
detector: a candidate is flagged only when it is (a) multi-token, (b) an
exact match (casefold + whitespace-collapsed) of one of the item's English
`derivation_inputs` rows, and (c) that source row contains an unambiguous
English function word as a whole token. A single identical token (acronym,
code, name, or legitimate cognate) is never rejected by equality alone, and
two candidates sharing a proper noun/acronym with no function word (e.g.
"New York", "NATO") are never flagged.

Added to `_QA_RECOVERABLE_SEMANTIC_ERRORS` (new section D below):
`english_source_echo` bulk failures are persisted as a PROVISIONAL bulk
completion and routed to mandatory Terra QA, never finalized without a full
QA PASS re-run through the identical validator — exactly the existing
`morphology_*` recovery mechanism, extended to this one additional class.

**Offline Stage-03 corpus audit** (480221 items, 577141 source rows, all DE,
0 EN — read-only, no provider calls): **332791 of 577141 source rows
(332585 of 480221 items)** contain a multi-token phrase with at least one
unambiguous English function word and would therefore be *eligible* for the
echo check if a provider ever echoed them back verbatim unchanged (this is
an upper-bound eligibility count over source structure, not a defect count —
the Stage-03 queue holds no provider candidates to check against).

### B. Unsupported-domain inflected-form recognition (`tools/build_dict.py`)

`_UNSUPPORTED_DOMAIN_CUES`'s computer/video-game cue widened from
`\bcomputer(?:spiel|game)\b|\bvideospiel\b` to recognize the closed German
noun-inflection suffix family (nothing / "-e" / "-en" / "-s") via new
`_DE_SPIEL_INFLECTION_SUFFIX`, the same bounded-suffix technique as the
pre-existing `_DE_FORM_SUFFIX`. Covers all 4 required forms each of
`Computerspiel(e|en|s)` and `Videospiel(e|en|s)`; still `\b`-bounded so a
compound merely starting with the same stem (`Computerspielzeug`,
`Computerspielindustrie`, `Videospielkonsole`) does not match — a closed
linguistic strategy, not a substring test. Source-evidence gating is
unchanged: a source that itself states "computer game"/"video game"/
"gaming"/"videogame" still authorizes the corresponding candidate language.

Added to `_QA_RECOVERABLE_SEMANTIC_ERRORS`: `unsupported_domain_elaboration`
bulk failures are now PROVISIONAL + mandatory-QA-routed, same mechanism as
morphology and the new echo class (previously a hard rejection — see the
updated `test_unsupported_domain_elaboration_is_provisional_not_hard_rejection`,
which replaces the old `test_non_morphology_semantic_failure_remains_hard_rejection`).

**Offline Stage-03 corpus audit:** exactly **4 `Computerspiel` + 4
`Videospiel`** bare/singular source-evidence occurrences found across the
full queue; **zero inflected-form occurrences** (`Computerspiele`,
`Computerspielen`, `Computerspiels`, `Videospiele`, `Videospielen`,
`Videospiels`) in source text. Zero lookalike-compound occurrences
(`Computerspielzeug`, `Computerspielindustrie`, `Videospielkonsole`, etc.).
This is source-side evidence only — Stage-03 holds no candidate output to
audit for the actual defect (an inflected form appearing in a *candidate*,
as in the Mod canary evidence); the fix targets the candidate-side cue
regex directly, verified by the regressions below and by the exact Mod
canary re-validation in section D.

### C. `perfect` English source-classifier ambiguity (`tools/build_dict.py`)

**Full offline corpus audit** of every accepted Stage-03 DE-target source row
containing the token `perfect` (602 of 577141 rows; 28 distinct non-
participle texts):

| Class | Row occurrences | Distinct texts | Resolution |
|---|---|---|---|
| `past participle` / `perfect participle` (pre-existing feature) | 571 | — | unchanged |
| Ordinary Perfekt-tense grammar note (`forms the perfect aspect (have)`, `forms the perfect with sein`) | 2 | 2 | kept as the `perfect` feature, requires `Perfekt` in output — pattern narrowed to this closed context instead of the bare word |
| Bare adjectival/verb/idiomatic "perfect" (`perfect, impeccable`; `a perfect wedding`; `perfect fifth`/`fourth` [music interval]; `to perfect`; `practice makes perfect`; etc.) | 24 | 20 | **no morphology feature at all** (previously wrongly forced `Perfekt` into the required output — this was a real, previously undiscovered false-positive class) |
| Composite tense (`present perfect`, `past perfect`, `future perfect`, `conditional perfect`, `pluperfect`, and the compound row `forms the present perfect and past perfect tenses of certain verbs`) | 9 (row-level bucket sum; 6 distinct real source texts) | 6 | new `perfect_tense_composite` feature; **always** fails closed as `morphology_unsupported_composite_tense`, regardless of candidate content — never silently reduced to ordinary `Perfekt` |

No occurrences of `pluperfect`, `future perfect`, or `conditional perfect` as
standalone bare tokens outside the 6 distinct rows already counted above; no
unclassified/ambiguous `perfect` phrasing remained (`unclassified_count=0`).

Implementation: the `perfect` rule's source pattern narrowed from
`\bperfect\b(?!\s+participles?)` to the closed grammatical-context pattern
`\bperfect\s+aspect\b|\bforms?\s+the\s+perfect\b|\bperfect\s+with\s+(?:sein|haben)\b`.
A new `perfect_tense_composite` rule
(`\b(?:present|past|future|conditional)\s+perfect\b|\bpluperfect\b`) is
checked first inside `_validate_de_semantic_contract`'s morphology block and
always returns `morphology_unsupported_composite_tense` before the generic
per-feature loop is reached — its output pattern is an intentionally
unmatchable placeholder, never consulted. The pre-existing `present`/
`preterite` rules additionally exclude their own composite phrasing
(`(?!\s+perfect\b)`, mirroring the existing participle exclusion) — without
this, `present perfect`/`past perfect` would simultaneously (and wrongly)
also demand bare `Präsens`/`Präteritum`, a real collision the corpus audit
surfaced (`forms the present perfect and past perfect tenses of certain
verbs` contains both).

**Operational note for the production plan:** because
`morphology_unsupported_composite_tense` always fires regardless of output
content, a composite-tense item can never pass Terra QA either (QA re-runs
the identical validator) — it can only be resolved by a future contract
extension adding a verified output pattern for that tense, or by explicit
owner manual adjudication. This is intentional and matches the instruction
not to invent translations for an unsupported grammar class; it affects at
most 6 real Stage-03 rows.

### D. QA-recoverable error policy (`tools/build_dict.py`)

`_is_morphology_qa_recoverable` replaced by `_is_semantic_error_qa_recoverable`
(the one bulk call site updated) plus a new explicit, closed allowlist
constant `_QA_RECOVERABLE_SEMANTIC_ERRORS = {"english_source_echo",
"unsupported_domain_elaboration"}`. Recoverability logic: the `morphology_*`
prefix family (gated, as before, on the item carrying a source-supplied
morphology feature) **or** an exact code in the new allowlist. No other
semantic-contract code is recoverable — verified by
`test_non_recoverable_semantic_failure_remains_hard_rejection`
(`related_not_exact_synonym` still hard-rejects) and
`test_structural_failure_on_morphology_item_remains_hard_rejection`
(`echo_lemma`, a generic/structural code, still hard-rejects regardless of
morphology features present).

### Manual-adjudication safety (unchanged mechanism, new regression)

`apply_manual_adjudication` remains the sole writer of the checkpoint's
`manual_adjudications` section and is never called from inside
`build_stage04`'s own execution path (verified again: only 6 call sites in
the whole repository, all in test code exercising the explicit external
API). New regression
`test_normal_stage04_execution_never_creates_manual_adjudication_on_its_own`
runs a normal bulk+QA-corrected completion and a normal hard rejection
through `build_stage04` and asserts `manual_adjudications` stays empty in
both checkpoints. The two accepted German Canary v4 manual adjudications
(Marmarameer, Mod) were not read, re-applied, or altered by this task.

### Paid-request-contract identities — re-verified unchanged

Re-hashed all four frozen artifacts directly (outside the repository, under
`tmp/`, gitignored):

- `SELECTION_SHA` `1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475`
  (`tmp/de-canary-v2/de-canary-selection-v2.json`) — **MATCH**.
- `REQUEST_SHA` `185d2a592ef9e391008622b88adcb14a13d81dd615978f3c518925eae1d8f3d5`
  (`tmp/de-canary-v4/de-canary-requests-v4.jsonl`) — **MATCH**.
- `BATCH_SHA` `ca9fdc66a5924609cb16eea0385eba6ab223c2046b88af1209282170b60cf2a2`
  (`tmp/de-canary-v4/de-canary-batch-manifest-v4.jsonl`) — **MATCH**.
- `COST_PLAN_SHA` `e716609c93cf9e8e1d60307132486aac65eb869a247670614ab7a61863269a81`
  (`tmp/de-canary-v4/live-cost-plan-v4.json`) — **MATCH**.

No Luna instruction, Terra QA instruction, JSON schema, model name, reasoning
setting, `max_output_tokens`, endpoint, live transport, or retry behavior was
touched — this task only changed post-receipt local semantic validation
(`tools/build_dict.py`'s `_validate_de_semantic_contract` and the
QA-recoverability policy around it), never the outbound request.

### German Canary v4 full accepted-evidence re-validation (deterministic, zero-spend)

The complete real v4 accepted evidence (50 items: 48 non-manual finals + 2
owner-approved manual finals) was embedded verbatim from the durable local
canary evidence (`~/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/
checkpoint.json`, `review-bundle.json`; outside the repository) into a new
self-contained regression table (`_CANARY_V4_ACCEPTED_ITEMS`,
`tests/test_build_dict_stage04.py`) and re-validated read-only:

- **`test_all_48_non_manual_canary_v4_finals_still_pass`** (48 parametrized
  cases) — every recorded final `(text, kind)` still passes the complete
  hardened `_validate_de_semantic_contract` and `_validate_generated_
  candidate`. **48/48 PASS** — no previously accepted item became invalid.
- **`test_canary_v4_manual_finals_preserved_and_structurally_valid`** — the 2
  manual finals (`Marmarameer`, `Mod`, both kind `synonym`) are unchanged and
  structurally sound (manual adjudication deliberately bypasses the semantic
  contract, as documented above).
- **`test_canary_v4_original_marmarameer_bad_output_now_rejected`** — the
  exact original bad bulk candidate (`Sea of Marmara`) now returns
  `english_source_echo` (was a silent PASS at canary time; only caught by
  independent human review).
- **`test_canary_v4_original_mod_bad_output_now_rejected`** — the exact
  original bad bulk candidate (`eine Person, die Computerspiele verändert`)
  now returns `unsupported_domain_elaboration` (was a silent PASS at canary
  time; only caught by independent human review).

`output.sqlite`, the checkpoint, and provider/spend ledger were not touched;
no candidate text was retransmitted; no new canary ran. Cumulative v4 spend
remains **USD 0.0716368** (86/86 paid calls, unchanged).

### Tests (`tests/test_build_dict_stage04.py`)

88 new tests added (203 → 291): direct-validator truth tables for all three
hardenings (echo, domain inflections incl. 4+4 required forms and 3
substring-lookalike non-triggers, and the full 28-case `perfect` corpus
truth table), end-to-end `build_stage04` provisional→QA→final-output and
provisional→QA→hard-reject pairs for both new recoverable classes, the
still-hard non-recoverable-class regression, the manual-adjudication-safety
regression, and the 48-case canary re-validation table plus the two
"original bad output now rejected" regressions.

- `pytest -q tests/test_build_dict_stage04.py` — **291 passed**.
- `pytest -q tests/test_build_dict_stage03.py` — **16 passed** (file
  unchanged; source-feature parsing tests already lived in
  `test_build_dict_stage04.py`, so no stage03 changes were needed).
- `git diff --check` — PASS (no whitespace errors).
- `make gate` — `ruff check .` PASS; `mypy --strict .` PASS (18 source
  files); `pytest -q` **534 passed**; `check_agents.py` R1/R3/R7 PASS.

**Changed paths:** `tools/build_dict.py`, `tests/test_build_dict_stage04.py`,
`tasks/slice-6.report.md`.

**Provider calls:** `0`. **Paid spend:** `USD 0`. **New canary run:** `NO`.
Cumulative v4 canary spend unchanged at `USD 0.0716368`.

**Disposition:** `GERMAN_STAGE04_PREPRODUCTION_HARDENING_COMPLETE` — all
three recorded generic pre-production hardening defects (English-source
echo, inflected unsupported-domain forms, bare/composite `perfect`
ambiguity) are repaired and regression-covered; the German Canary v4
semantic gate remains `PASS_WITH_2_MINOR`. **Production remains
unauthorized** pending a separate measured full-Stage-04 production plan
(partition manifests, Batch limits/correlation verification, measured
bulk+QA token/cost bounds, hard spend cap, recovery/resume plan, exact
artifact SHAs) and explicit owner authorization.

---

## German Stage-04 full production plan (measured, ZERO-SPEND) — zero-spend

Fulfills the deferred item above: deterministic Luna Batch production
manifests plus measured bulk/QA cost bounds, built entirely from committed
repository code (`tools/build_dict.py`'s single-source request builders,
token constants, and worst-case cost helpers). No repository code or test
changed — every artifact below was produced by throwaway local scripts under
`tmp/de-production-v1/` (gitignored). **Zero provider calls. Zero
`OPENAI_API_KEY` reads. Zero Batches created.**

### 1. Repository/queue state verification

- `slice/6` HEAD = `origin/slice/6` = `ea8de9c7a138d374a778fe361c3889d8f973de96` — **MATCH**.
- `main` = `origin/main` = `2f2486a5021465842ada8e5cc3d43e9a030e6955` — **MATCH**.
- Working tree clean (including untracked) before and after — **MATCH**.
- `/tmp/flashcard-stage03-v2.json`: SHA-256
  `114dd20f1e071708ca43ff433284ce1be0e9662763db5a589930a8f5a045cf2a`, bytes
  `334605426`, format `flashcard-stage03-queue-v2` — all **MATCH** the
  expected values, verified from disk (not assumed). Queue not modified.
- Independently recomputed the queue's own `items_sha256` trailer
  (`dc32611224e20ab3bdaeb5ac8dd77d01e8a81ffe5a4922c55175edf458787198`) using
  the exact `build_stage03` algorithm (canonical per-item JSON, comma-joined,
  bracket-wrapped) — **MATCH**, an integrity check beyond the whole-file SHA.
- Full-queue census (single streaming pass, `_iter_stage03_queue_items`):
  `480221` items, all `language=de`, all `job_class=de_learner_meaning` — the
  file is DE-only; matches the task's `German jobs: 480221`.

### 2. Canary reuse determination — SAFE, reused

Checked all six required conditions against the durable local evidence
(`~/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/checkpoint.json`,
outside the repo) and the frozen selection
(`tmp/de-canary-v2/de-canary-selection-v2.json`, SHA
`1ffa5e76c7315467a39a5b7b953e07fba924b37dbc77512130e720adb3ab7475`, 50 IDs):

1. **Exact same Stage-03 item identity** — selection resolves against the
   same full-queue SHA (`114dd20f1...`) recorded in the checkpoint's
   `authorized_queue_sha256`.
2. **Exact same request body semantics** — checkpoint identity records
   `bulk_de_model=gpt-5.6-luna`, `bulk_de_reasoning_effort=none`,
   `bulk_de_max_output_tokens=512`, `bulk_pipeline_version=stage04-bulk-v4`,
   unchanged from the current accepted contract.
3. **Accepted final result available for all 50** — `bulk.completed=50`,
   `bulk.rejected=0`, `bulk.in_flight=0`; `qa.required=36`,
   `qa.completed=36`, `qa.rejected=0`, `qa.in_flight=0`. No ambiguous state.
4. **QA/manual adjudication history unambiguous** — confirmed by (3) plus the
   2 manual adjudications below.
5. **All validator rules now accept the accepted final** — independently
   re-ran (not just trusted the prior report) `pytest
   tests/test_build_dict_stage04.py -k "canary_v4 or
   non_recoverable_semantic_failure_remains_hard_rejection or
   structural_failure_on_morphology_item_remains_hard_rejection or
   manual_adjudication_on_its_own"` → **54 passed**, including the 48-case
   accepted-finals regression table and both manual-final preservation
   checks.
6. **Historical provider evidence retained; manual values labeled
   `contributed`, never model output** — 86 spend-ledger entries (50 bulk +
   36 QA), all `accounting=ACTUAL`, cumulative `USD 0.0716368`, unique
   `response_id`s; `manual_adjudications["queue:v2:3a99e45482575743acf4789f24789062"]`
   (→ `Marmarameer`) and `["queue:v2:fca20836b82737bbbe7083358ad66f93"]`
   (→ `Mod`) both carry `"source": "contributed"`, untouched.

**PRODUCTION_SEEDED_CANARY_ITEMS = 50, PENDING_BULK = 480171.** No canary
item is retransmitted in the bulk manifest below.

### 3. Measured bulk request set (all 480,171 pending items)

Single streaming pass over the full queue (bounded memory, no full-file
materialization), building each request via the committed
`de_learner_meaning_request_body(item, "gpt-5.6-luna")` and wrapping it in
the canonical Batch record `{"custom_id","method","url","body"}`
(`_canonical_line`, sorted keys, no spaces — same serializer the accepted
canary REQUEST/BATCH SHAs already use):

- `PENDING_BULK_REQUEST_COUNT` = **480171**
- `TOTAL_SERIALIZED_REQUEST_BYTES` = **1,377,518,105**
- `TOTAL_MEASURED_BULK_INPUT_TOKENS` = **321,576,223** (mean ≈669.7/request)
  — measured with `tiktoken==0.14.0`, encoding `o200k_base`, over the
  canonical JSON of `model+input+reasoning+max_output_tokens+text.format` per
  item, matching the previously established measurement method. `o200k_base`
  remains a nearest-available proxy — no public tokenizer for `gpt-5.6-luna`
  is confirmed. tiktoken is a local build-time measurement aid only, not a
  project dependency (`pyproject.toml` unchanged).
- Overall logical artifact `tmp/de-production-v1/bulk-logical-requests.jsonl`:
  SHA-256 `08db26906599d7ba6978dd5cb929c89d8954385efd1a79925ed62a4b1212dde9`,
  bytes `1377518105` (matches the sum of per-record bytes exactly).
- One record per pending item, zero duplicates, deterministic
  item_id-ascending order (identical to the queue's own file order).

### 4. Tier-safe partition manifests

**A. Tier-1-safe default** (`MAX_LUNA_PARTITION_PROMPT_TOKENS=4,500,000`,
plus the hard provider caps of ≤50,000 requests / ≤200MB per Batch):

- **72 partitions**, binding constraint = measured prompt tokens (not the
  request or byte cap) — first partition: 6,719 items / 4,499,705 tokens /
  19,275,865 bytes; last (72nd): 3,135 items / 2,098,946 tokens / 8,991,485
  bytes. Full 72-entry manifest (index, item count, first/last item ID,
  byte count, measured tokens, SHA-256, custom_id count, model, endpoint)
  in `tmp/de-production-v1/bulk-partition-manifest.json`.
- **Coverage proof:** union of all 72 partitions' custom_ids == the exact
  480,171-item pending set; pairwise intersection empty; zero duplicate
  `custom_id` within or across partitions — **PASS**.
- Submission policy: one Luna Batch at a time (Tier-1 default).

**B. Higher-tier informational plan** (no request body or custom_id
changes — partition *count* only):

| Tier | Queue token ceiling | Partitions | Binding constraint |
| --- | --- | --- | --- |
| 1 | 4,500,000 | 72 | tokens |
| 2 | 20,000,000 | 17 | tokens |
| 3 | 40,000,000 | 10 | requests (50,000 cap) |
| 4 | 1,000,000,000 | 10 | requests (50,000 cap) |
| 5 | 15,000,000,000 | 10 | requests (50,000 cap) |

From Tier 3 upward the 50,000-request-per-Batch hard cap binds before token
headroom does (`ceil(480171/50000)=10`); the 200MB byte cap never binds
(`ceil(1,377,518,105/209,715,200)=7`, always looser than the request cap).
Informational only — owner authorization must name one specific plan.

### 5. Bulk (Luna) cost — current Batch rates (input $0.10, output $0.60 /MTok)

| Figure | Value |
| --- | --- |
| Measured-input cost (321,576,223 tok × $0.10/MTok) | **$32.16** |
| Conservative output reservation (480,171 × 512 tok × $0.60/MTok) | **$147.51** |
| Conservative max (2× safety-multiplier input + full output reservation) | **$211.82** |
| Empirical canary-based projection (50-item Luna actuals: mean 602.68 in /
  34.4 out tok/req, scaled ×480,171) | **≈$38.85*** |
| **Recommended Phase-1 hard cap** | **$222.50** |

*Empirical figure is a labeled comparison only, not an authorization bound —
the canary's 50 items are not a representative token-length sample of the
full 480,171 (canary mean 602.68 vs. full-set mean 669.7 input
tokens/request; canary output ran far below the 512-token ceiling).
The 512-token output ceiling is a provider maximum, never disguised as
expected actual output; conservative figures charge it in full for every
request.

### 6. QA preknown floor — the dominant cost driver, surfaced explicitly

Computed strictly from **input-known** triggers only (never from bulk
output, which does not exist yet):

- **Morphology-routed** (`_morphology_feature_keys(item)` truthy — always
  QA-routed per `build_stage04`, source-verifiable from the queue item
  itself): **349,913 / 480,171 pending items (72.9%)**.
- **Deterministic audit sample** (`_deterministic_audit_sample`, seed = full
  queue SHA-256, `sample_size=2`, matching `build_stage04`'s committed
  default): 2 IDs, neither in the seeded canary; 1 already covered by the
  morphology set, 1 new.
- **PREKNOWN_QA_COUNT = 349,914** (union, no double count).
- Output-dependent QA triggers (provisional semantic-error recoverable
  routing, >50-char candidate text, `flag` substring) are explicitly **not**
  counted — they cannot be known before bulk generation runs.

QA reason breakdown: `{"morphology_de": 349913,
"deterministic_audit_sample_pending": 2, "overlap_morphology_and_audit": 1}`.

**This preknown floor alone (worst-case, current Batch Terra rates $1.00/
$6.00 per MTok, 2× safety multiplier on input, full 512-token output
reservation) = $1,429.16** — already far larger than the entire Luna bulk
cost. This is a measured floor, not a guess: German morphology forms are the
majority of the queue and are unconditionally QA-routed by the accepted
architecture. **The owner should not read Phase 1's ~$32–$212 bulk cost as
representative of total production cost; Terra QA is the larger line item
even before any output-dependent QA triggers fire.**

### 7. QA cost bounds (three tiers, per task contract)

| Tier | Count | Cost (USD) | Label |
| --- | --- | --- | --- |
| A. Preknown floor | 349,914 | **$1,429.16** | exact bound for the currently-knowable mandatory set |
| B. Empirical canary-based projection | 345,723 (72%×480,171, canary's 36/50 QA-selection rate) | **≈$305.13** | empirical comparison only, NOT an authorization bound |
| C. Absolute fail-closed ceiling | 480,171 (100%, every pending item) | **$1,961.17** | intentionally pessimistic, NOT expected actual spend |

(B is far lower than A primarily because A is a deliberately worst-case
bound — 2× input safety multiplier plus the full 512-token output ceiling
charged on every one of 349,914 requests — while B uses genuine canary
averages with no multiplier and a real mean QA output of only 78.5 tokens,
a small fraction of the 512 ceiling; B's smaller population (345,723 vs.
349,914) and smaller mean input-token estimate are secondary contributors.
Both effects are disclosed, not smoothed over.)

Full breakdown, methodology, and per-tier token sums:
`tmp/de-production-v1/qa-preknown-analysis.json`,
`tmp/de-production-v1/production-cost-plan.json`.

### 8. Recovery / correlation contract (design only, zero Batches created)

`tmp/de-production-v1/recovery-plan.json` documents, per partition: local
manifest SHA, provider input-file ID / Batch ID / status / output-file ID /
error-file ID (all empty pre-submission), and the exact
`custom_id -> item_id` mapping. Output reconciliation never depends on
order; exact-one `custom_id` match; unknown/duplicate custom_ids rejected;
missing IDs stay unresolved (never assumed complete or failed); completed
results survive a later Batch expiration; expired/failed requests are never
auto-resubmitted; a retry requires a new deterministic manifest naming only
explicitly approved unresolved IDs — never a full-partition replay.
Documented failure modes: validating failure, failed Batch, expired Batch
with partial outputs, network interruption during polling, output-download
interruption, malformed individual response, semantic candidate rejection,
duplicate/unknown/missing `custom_id`.

### 9. Production checkpoint design (new path, never the canary path)

Proposed run directory:
`/home/saber/.cache/flashcard/stage04-runs/slice-6-de-production-v1/`
(distinct from `slice-6-de-canary-v4/`; never reused). Identity binds: full
Stage-03 queue SHA, production-selection SHA, seeded-canary artifact SHA,
bulk/QA pipeline versions (`stage04-bulk-v4`/`stage04-qa-v4`), response
schema version, model IDs, reasoning efforts, `max_output_tokens=512`,
pricing contract, partition-manifest-set SHA, generation marker, generated
license. Any mismatch fails closed before any upload/submission.

### 10. Provider contract verification

Verified against **current** official OpenAI documentation (checked this
session, `2026-08-23`, since the assistant's training cutoff predates the
current date by several months): `/v1/responses` is Batch-supported; 50%
Batch discount; 24h completion window; ≤50,000 requests/Batch; ≤200MB input
file; unique `custom_id` required; output order not guaranteed; 2,000 Batch
creations/hour. All **MATCH** the task's stated contract, independently
re-confirmed via live documentation search, not assumed.

`gpt-5.6-luna` / `gpt-5.6-terra` are **this project's own internal model
identifiers** (`tools/build_dict.py:2172-2174`, `docs/plan.md`,
`WORKFLOW.md`) — they do not correspond to any real OpenAI product, so their
per-tier queued-prompt-token limits and prices cannot be independently
verified against real OpenAI documentation. The prices and Tier-1..5 limits
used above are the task-supplied values, which match the project's own
already-accepted contract (`bulk_input_price_per_mtok=0.2`,
`qa_input_price_per_mtok=2` non-Batch, in the accepted canary checkpoint
identity; Batch rates here are those non-Batch rates at the documented 50%
discount). This distinction is reported rather than glossed over.

### 11. Artifacts (all local, gitignored under `tmp/`)

| Artifact | SHA-256 |
| --- | --- |
| `production-selection.json` | `7b4ac3297bf0bc4b44f7a68767549ed370180ffc0dfb3017ddc433385206bb20` |
| `seeded-canary.json` | `79e6b5cf47fa2200ad90a02176fad679a52bd05a789eb4ff67025e48d2100ea9` |
| `bulk-logical-requests.jsonl` | `08db26906599d7ba6978dd5cb929c89d8954385efd1a79925ed62a4b1212dde9` |
| `bulk-partition-manifest.json` | `bb7ac594fab26b8d3b3a1e4e03101588da2a5824e7ee1ea89d8e04a9a6d0435f` |
| `production-cost-plan.json` | `99b9bc4e51d9985f20537c603fc11ac0156936d804d9144b89688bf4fb7f8dc9` |
| `qa-preknown-analysis.json` | `65c3c861aecd29f424c665061038e48459862070076645d1f45244d7817896e6` |
| `recovery-plan.json` | `cee8ee71e928cd763b2d7f779d3467ee851f1504076df53ca7a3e844776cc0de` |
| `production-plan.json` (binds all of the above) | `cdc9a5c1b49a30db1e9ec3c631b680facee7c23e6e0a3d186da6b3c2737377f8` |

### 12. No paid action

Provider calls: `0`. Files uploaded to OpenAI: `0`. Batches created: `0`.
Paid spend: `USD 0`. `OPENAI_API_KEY` read: `NO`.

### 13. Gate

`make gate` — `ruff check .` PASS; `mypy --strict .` PASS (18 source files);
`pytest -q` **534 passed** (unchanged from prior close — no test added, none
needed); `check_agents.py` R1/R3/R7 PASS. **Changed tracked paths:**
`tasks/slice-6.report.md` only.

**Disposition:** `GERMAN_STAGE04_PRODUCTION_PLAN_READY` — Phase-1
(Luna-bulk-only) plan is fully measured and ready for owner review:
recommended hard cap **$222.50** against a Phase-1 scope of 480,171 Luna
requests. **Production remains unauthorized.** The owner should weigh
Phase-1's bulk cost together with the measured Terra QA preknown floor
(§6–7, **$1,429.16** minimum once QA is separately authorized in Phase 2) —
this plan intentionally does not request or imply Phase-2 authorization.
`PHASE2_TERRA_AUTHORIZATION: NOT_REQUESTED_YET`.

---

## Final owner disposition — v1 simplification and Slice-6 closure

**Status:** Slice-6 implementation work accepted for closure. Full paid Stage-04 German production is NOT executed for v1.

### 1. Owner decision and rationale

The owner has decided to stop pursuing full paid Stage-04 German production for v1. This is a deliberate scope simplification, not a failed provider run.

The completed production planning demonstrated that the full-coverage LLM enrichment and selective QA architecture became economically and operationally disproportionate for v1 requirements, available budget, and implementation complexity:
- **Total German jobs:** `480221`
- **Pending bulk items:** `480171`
- **Measured Luna Batch input cost alone:** ≈ `USD 32.16` (previous proposed conservative Luna cap `USD 222.50`)
- **Preknown Terra QA population (morphology-routed):** `349914` items exposing ≈ `USD 1429.16` in mandatory QA floor before any output-dependent QA triggers fire.

No Phase-1 production authorization was granted, no full German production Batch was executed, and no further Stage-04 cost/QA optimization cycle is required for Slice-6.

### 2. Summary of Slice-6 accomplishments

Slice-6 has successfully implemented, tested, and hardened the entire offline enrichment and packaging pipeline:
1. **Deterministic Stage-03 queue construction:** Verified against real Stage-02 input (480,221 records, zero secret leakage, stable semantic references);
2. **Stage-04 offline generation infrastructure:** Implemented, tested with fake/local transports, and verified for structured responses, validation, and selective QA;
3. **Durable resilience mechanisms:** Checkpoint/resume, spend fencing, deterministic Batch manifest partitioning, correlation metadata (`batchcorr:v1:<manifest-sha256>`), validation, and fail-closed provider error handling implemented;
4. **German canary execution:** 50-item German Canary v4 executed and technically completed within the hard spend cap;
5. **Semantic review and transparent adjudication:** Independent semantic review found 46 PASS / 2 MINOR / 2 MATERIAL; both MATERIAL items (`Marmarameer` → `Marmarameer`, `Mod` → `Mod`) were manually and transparently adjudicated and preserved in audit records;
6. **Accepted canary verdict:** Final canary result `48 PASS / 2 MINOR / 0 MATERIAL` (`PASS_WITH_2_MINOR`);
7. **Canary provider spend:** Cumulative German v4 canary provider spend recorded as `USD 0.0716368` across 86 paid calls;
8. **Pre-production semantic hardening:** Repaired all three generic validator/classifier defects (English-source echo detection, inflected unsupported-domain form recognition, bare/composite `perfect` ambiguity) with 88 new regression tests;
9. **Stage-05 fixture packaging:** Packaging pipeline verified for SQLite quick_check, metadata generation, attribution integrity, and overwrite refusal;
10. **Piper/Docker prerequisite:** Standalone Dockerfile created and verified with pinned `piper-tts==1.6.0`, pinned `de_DE-thorsten-high` voice revision, SHA-256 digest check, bounded synthesis smoke test, and license/notice material;
11. **Runtime LLM prohibition:** Zero runtime LLM dependencies in `pyproject.toml` runtime graph, `app/`, or the Docker runtime container (AGENTS R1).

All historical investigations, cost plans, prompt repairs, canary evidence, adjudication receipts, and regression suites remain preserved as immutable engineering audit records.

### 3. Normative operational disposition for v1

1. **Slice-6 implementation work is accepted for closure.**
2. **Full paid Stage-04 DE production is NOT executed as part of v1 closure.**
3. **No further Stage-04 cost/QA optimization cycle is required for Slice-6.**
4. **v1 dictionary baseline:** For v1, the application relies on:
   - Existing source-backed dictionary data from Wiktionary and Tatoeba;
   - Deterministic grammar and morphology;
   - Existing source-backed English meanings;
   - Suitable source-backed German learner meanings when present;
   - Explicit absence/partial availability when a safe German learner meaning is unavailable.
5. **No synthetic coverage invention:** German meanings are never hallucinated or invented merely to achieve complete coverage.
6. **D43 meaning availability contract:** ADR-0004 D43's `meaning_state = none | partial | complete` remains the authoritative mechanism for representing incomplete selected-language coverage.
7. **Future enrichment is optional:** Full paid Stage-04 DE enrichment is deferred as an optional future enhancement, not a prerequisite for completing the standalone v1 application.
8. **Maintainer tooling preserved:** The Stage-04 LLM generation and QA machinery in `tools/build_dict.py` remains available in maintainer tooling for potential future use.
9. **Runtime LLM remains strictly forbidden:** AGENTS R1 applies without exception across all application and runtime code paths.
10. **Canary role:** The accepted canary remains historical validation evidence and does not imply authorization for full production.
11. **Production authorization:** Production authorization remains **NO**.
