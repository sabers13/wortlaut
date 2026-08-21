# Slice 6 — Phase A, post-ceiling Cycle Attempt 1

## T3 ceiling history

- Historical Attempt 1 (`a03cb6b1364d493d4443dc68448a8153e024dbbe`) = Failure 1.
- Historical Attempt 2 (`75ae9d4d555006f854982dbdd2c4b20615c3d4bb`) = Failure 2.
- T3-ceiling design repair main commit:
  `31606d5596ddae638b7a7211a68c35e960f65528`.
- Design merge / starting slice-6 commit:
  `d51331c83894626151791ef85d3ce0eaaaf62ee9`.
- Post-ceiling Cycle Attempt 1 is the current implementation. It does not erase
  or renumber either historical failure.

## Preserved real-data evidence

- Stage-02 input SHA-256: `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`.
- Stage-02 input bytes: `945410048`; fresh `PRAGMA quick_check`: `ok`; input
  mutation: no.
- Stage-03 production semantics changed: **no**. The accepted real measurement
  is reused: 960442 records, SHA-256
  `9433f7e236bbf621ff22b0e9ae7b3f350ec4986ec693b0b3408f08fc6ec71ef0`,
  bytes `914504842`; DE `480221`, EN `0`, FA `480221`; missing-EN `0`,
  German learner meaning `480221`, Persian translation `480221`.

## Repaired A6 checkpoint and paid-work boundary

- Checkpoint schema: `flashcard-stage04-checkpoint-v2`.
- Compatibility identity: Stage-03 queue SHA-256, generation/source version,
  generated-output classification, bulk model occupant, QA model occupant,
  bulk pipeline version, QA pipeline version, and provider-response schema
  version. Transport batch size is intentionally excluded.
- Bulk policy: queue-order deterministic units of `--batch-size` IDs (default
  100). Before each request, the exact IDs are atomically persisted as
  `bulk.in_flight`; complete structurally and deterministically validated units
  atomically become `bulk.completed` before the next request.
- QA policy: the deterministic required/not-required mapping is persisted in
  `qa.required` before paid QA. Selected units use the same bounded policy and
  atomically persist `qa.completed`.
- Restart refuses any non-empty bulk or QA `in_flight` set. It therefore never
  guesses whether an interrupted request was billed and never resubmits it.
- The checkpoint independently represents completed bulk candidates, QA
  required/not-required, and completed QA corrections. Corrupt phase state,
  corrupt completed candidates, unknown IDs, and incompatible identity all fail
  closed.

## Repaired A13 evidence

- Partial bulk interruption: PASS. Fixture unit 1 completed, then unit 2
  deliberately interrupted. Exact submitted IDs before failure:
  `enrichment-job:v1:1304356fc4e41c92bbbf33d992361fd0141b8d6f964d9bddf5a4c4ff520585bc`,
  then `enrichment-job:v1:2ff5ee2a299d6fe0cc0a2bc8f03017509f4b5be345a1b889a5655a39a9a04d65`.
  The first is durable; the second remains unresolved and is fail-closed with
  no resubmission.
- Bulk resume: PASS. A valid checkpoint interrupted immediately after its first
  durable completion skips
  `enrichment-job:v1:1304356fc4e41c92bbbf33d992361fd0141b8d6f964d9bddf5a4c4ff520585bc`.
  Interrupted/resumed and uninterrupted logical generated rows are identical.
- Partial QA interruption: PASS. First selected QA ID
  `enrichment-job:v1:938e0984e4abb093c098669dd993d263196a33e4dd1b92f84b3bb1987280486a`
  completed; the next selected ID
  `enrichment-job:v1:9cded056cf31933ed5e6bc46258a112ba0974c5358ef5c4769ce57ad9fdb0f95`
  remains unresolved and fails closed with no resubmission.
- QA resume: PASS. The completed first QA ID is skipped from a valid partial
  checkpoint; resumed and uninterrupted logical generated rows are identical.
- Classification, bulk-pipeline, QA-pipeline, and provider-schema identity
  changes: PASS (all invalidate reuse). Corrupt partial bulk/QA state: PASS.
- Malformed provider candidates, duplicate/missing unit IDs, and secret-bearing
  payload fields fail before completion checkpointing or output persistence.

## Explicit live provider adapter (not executed live)

- `stage04 --transport fixture` remains the default network-free test mode.
  Fixture mode does not read `OPENAI_API_KEY`.
- `stage04 --transport openai` is the explicit build-only opt-in. It requires
  `OPENAI_API_KEY` at execution time, explicit bulk/QA model occupants,
  classification, checkpoint, bounded-unit size, and versioned pipeline/schema
  arguments. The key is neither logged nor persisted.
- Adapter: OpenAI Responses API, `POST /v1/responses`, standard-library HTTP,
  `store=false`, strict JSON-schema output. Configured model names are used;
  defaults remain operationally `gpt-5.6-luna` for bulk and `gpt-5.6-terra` for
  QA, without embedding them in durable schema beyond a run's checkpoint
  identity.
- The live adapter test uses only a mocked local HTTP boundary. It verifies the
  Authorization header, configured models, `store=false`, strict structured
  output, parsing, and that a test credential is absent from checkpoint, SQLite,
  stdout, and stderr. Real OpenAI requests: **0**; paid credits: **no**.
- No OpenAI SDK/dependency was added; nothing in `app/` or the Docker runtime
  dependency graph changed.

## Validation, scope, and verification

- Existing deterministic candidate validation, provenance/derivation checks,
  generated row marker (`llm_generated_v1`), rollback behavior, and Stage-05
  fixture packaging remain covered. No real Stage-04 queue item was sent to a
  provider; no real Stage-05 enriched asset or release was produced.
- Focused Stage-03/04/05 tests: **25 passed**.
- Stage-01 through Stage-05 regressions: **125 passed**. Pre-commit `make gate`:
  **248 passed**; AGENTS executable checks R1, R3, and R7 passed.
- Commit SHA, post-commit gate, and push identity are recorded by the mechanical
  receipt; this report cannot self-contain the SHA of the commit that contains it.
- Changed paths are limited to `tools/build_dict.py`,
  `tests/test_build_dict_stage04.py`, and this report. Allowlist: PASS. No
  private absolute path, credential, queue, checkpoint,
  provider artifact, or SQLite file is tracked.
- Stop conditions hit: none. Deliberately undone: live canary, paid full bulk
  generation, real selective QA, real final packaging/release, and runtime
  pronunciation work.
