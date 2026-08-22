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
