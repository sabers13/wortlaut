# Slice-6 Report — ADR-0006 Current Cycle Attempt 1 — Decision Stop

**Branch:** `slice/6` @ pending commit
**Base main:** `39bf247bffb6332af750b45b1b59609c66c1e374`
**Archive preserved:** `archive/slice-6-pre-adr0006-1782cd7` @ `1782cd71343d86946757dce8f36784f9582e28f4` — not deleted/rewritten
**Model:** `gpt-5.6-terra / T3 / high` fallback `opus-5 / T3 / high`
**Disposition:** `OWNER_DECISION_REQUIRED` — Persian source-coverage/gap disposition

## Stage-02 Input Verification (A14.1, read-only)

- **Role:** accepted real cache-MISS output (Stage02 parent is Stage01 SHA `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`)
- **SHA-256:** `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97` — PASS (reverified before and after Stage03)
- **Bytes:** `945410048` — PASS
- **PRAGMA quick_check:** `ok` — PASS
- **Counts:** examples `777295` (with EN `494687`, without EN `282608`), `example_lemma` `6504849`, distinct indexed lemmas `99537`, token_count sum `7292286`, incomplete attribution `0`, orphan associations `0` — PASS
- **Required PART-A + Stage02 tables:** present — PASS
- **Input unchanged:** SHA before == SHA after Stage03 — PASS
- **No mutation:** Stage03/04/05 never mutate input asset in place — PASS

## Stage-03 Real Execution (A14.2, deterministic, network-free)

- **Execution:** PASS — `tools/build_dict.py stage03` against accepted Stage02, read-only, no network, deterministic, refuse overwrite
- **Source discovery:** No accepted Persian source artifact is presently established. No automatic download, no guessed license, no invented artifact.
- **Source-acceptance packet:** `NOT_ACCEPTED / NO_ACCEPTED_SOURCE`
  - Format `flashcard-source-acceptance-packet-v1`
  - `total_canonical_senses` `480221`
  - `primary_fa_covered` `0` (direct `wiktextract:enwiktionary` exact sense)
  - `bridged_fa_additional` `0` (optional `dewiktionary` bridge — not established, fail-closed)
  - `total_fa_covered` `0`
  - `fa_still_missing` `480221`
  - `ambiguous_direct_rejected` `0`
  - `ambiguous_bridge_rejected` `0`
  - `invalid_rows` `0`
  - `persian_source_candidates` `[]`
  - `note` — No accepted Persian source artifact established; FA remains source-backed only. Owner decision required before final queue materialization.
- **Persian coverage/gap report (deterministic):**
  ```
  TOTAL CANONICAL SENSES: 480221
  CANONICAL_ENWIKTIONARY_DIRECT_FA_COVERED: 0
  DEWIKTIONARY_BRIDGED_FA_ADDITIONAL_COVERED: 0
  TOTAL FA COVERED: 0
  FA STILL MISSING: 480221
  FA COVERAGE PERCENT: 0.00
  AMBIGUOUS_DIRECT_RELATIONS_REJECTED: 0
  AMBIGUOUS_CROSS_EDITION_BRIDGES_REJECTED: 0
  INVALID/UNUSABLE SOURCE ROWS: 0
  ```
- **Deterministic missing-FA sample (10, bytewise sense_ref order):**
  - `Vorabend` `NOUN` `sense:v1:000002320ef2ca802b6d03e388dc545516fa72f38adca45739a601c18d338161` EN `the previous evening; the evening before something`
  - `gesunder Menschenverstand` `NOUN` `sense:v1:0000228a8483c0f55918145db7f54ecaa9481caa9d2eb1c325071bf62bce3711` EN `common sense`
  - `Schweinen` `NOUN` `sense:v1:0000efcb2d0fa447d9762123f248aaeaedcb6c1c29684e3d11ad490fce6e2e52` EN `dative plural of Schwein`
  - `bestelle ab` `VERB` `sense:v1:0000f3b24b424db734672e3a14a26ddf7fd5546424938df13e01b533b7907c16` EN `first/third-person singular subjunctive I`
  - `Versöhnerinnen` `NOUN` `sense:v1:0001564f1e7424a5250595d7bfcb0290e3988af1890fb7256465fa14845dbf59` EN `plural of Versöhnerin`
  - `siebenundzwanzigtägiger` `ADJ` `sense:v1:00015b4d960fc30c7fd691a47143e66beea20320c8ff19a2b774ca37a2cdf269` EN `inflection of siebenundzwanzigtägig:`
  - `antiklerikalere` `ADJ` `sense:v1:00015fa39abf0c6b5b266a01f420ed0bb93212fb38cddc58320e06bc3871fc19` EN `strong nominative/accusative plural comparative degree`
  - `herzerfrischenderen` `ADJ` `sense:v1:00016522d2363dc112591b97d97f6cdd6a419823bd991cee199ec4288bba99a4` EN `inflection of herzerfrischend:`
  - `winseltet` `VERB` `sense:v1:00016d618dab189e4f31b5a1c3ceb64bea2ae5c646a86304f2717a96e62bdeb0` EN `second-person plural subjunctive II`
  - `verdienen` `VERB` `sense:v1:00016e5895f8c55d15df48e1fb219cd3ad5adb2a5186b33a19f36de668b1c51e` EN `to deserve`
- **Queue measurement (deterministic, for evidence only — not yet authorized for paid Stage04):**
  - Queue SHA-256 `9919650bdff06b35ef87a8f29cbd4fca1f63f51af2e9fbff634fbbf333f80620`
  - Queue bytes `301174168`
  - Total records `480221`
  - By language: `de` `480221`, `en` `0`, `fa` `0`
  - By job_class: `de_learner_meaning` `480221`, `en_translation` `0`, `fa_translation` `0`
  - With derivation input `0`, without `480221`
  - Ordering deterministic bytewise by `item_id`; IDs derived from `lemma.semantic_ref + sense.semantic_ref + language + job_class + context` (no numeric IDs, no mtimes, no absolute paths)
  - `fa_translation` historical identity rejected — `0` FA automatic LLM jobs
  - No secrets/private paths in queue (scanned for secret hints) — PASS

**Decision boundary:** After packet + coverage report, **STOP**. Final real DE/EN generated queue is measured but **not materialized for paid Stage04** pending owner/orchestrator gap disposition per ADR-0006 D62/D63 and A14/A15. Persiam LLM fallback remains `0` jobs.

## Stage-04 Fake/Local Verification (synthetic fixtures, no network, no credentials)

- **Fake bulk + fake QA:** PASS (deterministic)
- **Generated marker:** `source='llm_generated_v1'` (synthetic test classification `TEST_SYNTHETIC_LICENSE_v1` — clearly test-only, not a live production classification)
- **Source-backed rows:** unchanged preserved
- **Derivation edges:** exact — source side non-generated, same sense, no duplicate, no `generated→generated` (forbidden edge correctly rejected)
- **Zero-edge valid case:** PASS (job consuming only sense/grammar/context, no localized text, yields `0` edges)
- **Persian Unicode:** `U+200C` ZWNJ passes, forbidden bidi `U+061C, U+200E, U+200F, U+202A-202E, U+2066-2069` rejected, `Cc` forbidden, `Cf` only ZWNJ allowed — PASS
- **Deterministic audit sample:** reproducible via `SHA256(seed:item_id)` — PASS
- **Completed/rejected/in_flight durability:** PASS — 4-valid/1-invalid bounded unit: 4 completed, 1 rejected (sanitized `error_code`, `attempt_count`, evidence), `in_flight` cleared, STOP before next unit
- **Restart skips completed/rejected:** PASS
- **Ambiguous transport preserves in_flight:** PASS
- **Explicit rejected retry:** PASS (exact IDs via `retry_rejected`, prior state preserved, `attempt_count` increments, no wildcard, cannot retry `in_flight`)
- **Model-role compatibility:** `bulk_de_model`, `bulk_en_model`, `qa_model` participate in checkpoint identity (`TEST_SYNTHETIC_LICENSE_v1`, `stage04-bulk-v1`, `stage04-qa-v1`, `openai-responses-json-schema-v1`) — incompatible reuse correctly rejected — PASS
- **One-item=one-request Batch semantics:** `custom_id=batch:<item_id>` stable, identical for sync and Batch, reordered results join via `custom_id`, missing/duplicate/unknown fail-closed — PASS
- **Manifest lifecycle:** `PREPARED/UPLOADED/SUBMISSION_AMBIGUOUS/SUBMITTED/PROCESSING/COMPLETED/FAILED/EXPIRED/CANCELLED`, `batchcorr:v1:<manifest-sha256>` correlation, ambiguous submission STOP and exact-one reconciliation — PASS
- **Partial bulk interruption/resume:** after ≥1 completed bounded unit, restart submits `0` already-checkpointed bulk IDs, resumed logical result == uninterrupted — PASS
- **Partial QA interruption/resume:** same — PASS
- **Bulk completed / rejected / QA completion independently durable:** PASS
- **Corrupt partial state fail-closed:** PASS
- **Legacy canary preserved:** 5 historical `bulk.in_flight` IDs remain unresolved, not cleared/migrated/resubmitted — PASS (read-only verification)
- **Pipeline/schema/classification incompatibility invalidates reuse:** PASS
- **Zero provider requests in tests:** PASS (fake transport only)
- **No secrets in checkpoint/report:** PASS

## Stage-05 Fixture Packaging (synthetic, no overwrite, no mutation)

- **Success:** PASS — `PRAGMA quick_check ok`, required tables, lemma/sense `semantic_ref` uniqueness/nonblank, meaning attribution non-empty `source`/`license`, derivation integrity, zero orphans, SHA-256/bytes, deterministic metadata `dictionary_v1.sqlite` + `meta.json`
- **Malformed provenance:** rejected — PASS
- **Duplicate stable-ref:** rejected (UNIQUE + validation) — PASS
- **Bad attribution:** rejected — PASS
- **Input unchanged:** SHA before == SHA after — PASS
- **Overwrite refusal:** PASS
- **Metadata/checksum consistency:** `meta.sha256 == SHA256(output)` and `bytes == stat` — PASS

## Docker / Piper Prerequisite (ADR-0005 D56, Podman available)

- **Image build:** PASS — `podman build -t flashcard:slice6 .` using cache, 13 steps, commit `04da2fd80ea4`
- **Piper pin:** `piper-tts==1.6.0` — PASS (`pip show` `Version: 1.6.0`, `License: GPL-3.0-or-later`)
- **Voice:** `de_DE-thorsten-high` rev `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8` — PASS (Hugging Face API `sha == rev` and `cardData.license == mit`)
- **Model SHA-256:** `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1` — PASS (`sha256sum --check`)
- **Engine/voice presence:** PASS (`/opt/piper/de_DE-thorsten-high.onnx` 109M + `.onnx.json` + `/usr/share/doc/flashcard/*`)
- **Smoke:** PASS — `printf 'Guten Tag.' | piper --model ... --output_file /tmp/test.wav` yields 29K wav, `test -s`
- **Runtime LLM SDK:** `pip freeze | grep -E '^(anthropic|openai|google-genai)=='` empty — PASS
- **No credential / no user DB / no build/cache material in runtime / no bulk media:** PASS (image contains only `app/`, `pyproject.toml`, `piper-tts`, `de_core_news_md`, selected voice)
- **Classification/notices evidence:**
  - Engine `GPL-3.0-or-later` (pip metadata) → `/usr/share/doc/flashcard/PIPER-ENGINE-LICENSE`
  - Voice repo metadata `MIT` (pinned API) → `/usr/share/doc/flashcard/PIPER-VOICE-REPOSITORY-METADATA.json`
  - Thorsten dataset `CC0` (MODEL_CARD `License: CC0`) → `/usr/share/doc/flashcard/THORSTEN-MODEL-CARD`
  - Combined → `/usr/share/doc/flashcard/PIPER-NOTICES` — PASS
- **Current Dockerfile independently verified** against `tasks/slice-6.md` A12, ADR-0005 D56, ADR-0006 — not claimed via historical archive alone

## Build-Only SDK Boundary (R1)

- `pyproject.toml` `dependencies` contains only `spacy` + `de-core-news-md` — no LLM SDK — PASS (`tools/check_agents.py` R1 PASS)
- No `openai`/`anthropic` in runtime graph; `[project.optional-dependencies].build` removed (implementation does not use SDK, no unnecessary surface) — PASS
- Only `tools/build_dict.py` Stage04 path may read credential at execution time; no credential printed/persisted/checkpointed/reported — PASS (tests use `TEST_SYNTHETIC_LICENSE_v1` fixture only)
- `pyproject.toml` no `openai` — R1 runtime isolation proven

## Tests & Gate

- **Targeted Stage03:** 13 passed
- **Targeted Stage04:** 17 passed (including fake bulk/QA, in_flight, retry, manifest, interruption, legacy, rollback, classification)
- **Targeted Stage05:** 7 passed
- **Stage01 regressions:** 46 passed
- **Stage02 regressions:** 54 passed
- **Full gate:** `make gate` — `ruff PASS`, `mypy --strict PASS` (18 files), `pytest 261 passed`, `check_agents R1/R3/R7 PASS` — PASS
- **git diff --check:** PASS
- **Allowlist:** PASS — only `tools/build_dict.py`, `tests/test_build_dict_stage03.py`, `tests/test_build_dict_stage04.py`, `tests/test_build_dict_stage05.py`, `pyproject.toml`, `Dockerfile`, `.dockerignore`, `tasks/slice-6.report.md`
- **Report private-path scan:** PASS — no private absolute machine paths, no credentials
- **Stage02 unchanged:** PASS

## Paid Boundary

- **Paid provider calls:** `0`
- **Paid Stage04 credits spent:** `0`
- **Live Batch submission:** `0`
- **Persian LLM generation:** `0`

## Work Left Undone / Next Authority

- **Owner decision required** on `SOURCE_PACKET_STATUS: NOT_ACCEPTED / NO_ACCEPTED_SOURCE` and `FA_STILL_MISSING: 480221` (all senses). Options: accept gaps, authorize another source investigation, or (separately bounded, not automatic) authorize Persian LLM fallback with explicit count/model/cost/prompt/classification/QA/checkpoint/canary.
- **After explicit authorization:** materialize final real DE/EN generated queue (already measured `480221` `de_learner_meaning`, `0` `en_translation`), run `stage04` fake→real Batch with bounded manifests, selective QA, then `stage05` final packaging. No work may infer authorization from passing tests or canary.

---
*No private absolute paths, no API keys, no credentials recorded. Generated-output classification `TEST_SYNTHETIC_LICENSE_v1` is explicitly synthetic test-only; no live production classification has been authorized.*
