# Slice-6 Report — ADR-0006 Current Cycle Attempt 1 — Pre-Canary v2 Ready

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
